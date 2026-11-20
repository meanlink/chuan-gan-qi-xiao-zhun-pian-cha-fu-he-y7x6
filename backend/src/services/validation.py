"""留样验证案：锁定补偿值后用封存留样复算，决定分析是否放行。

留样生命周期：sealed（封存可启用）→ in_use（被一案占用）→ consumed（验收结论作出即消耗，无论放行与否）。
计算中断不消耗留样：占用仍属原案，恢复后重试继续同一占用，不重复消耗。
"""
import math
import time
from fastapi import HTTPException
from redis import Redis
from sqlalchemy import update
from src.config.settings import REDIS_URL
from src.models import Holdback, Job, ValidationCase
from src.services.business import analyze

TOLERANCE_MAX = 5.0

def create_case(db, data, user):
    j = db.get(Job, data.job_id)
    if not j: raise HTTPException(404, '分析任务不存在')
    if j.status != 'completed': raise HTTPException(409, '仅已完成分析可以开立验证案')
    bands = [r['band'] for r in (j.result or {}).get('table', {}).get('rows', [])]
    if not bands: raise HTTPException(409, '该分析没有可验证的温区结果')
    name = data.name.strip()
    if len(name) < 2: raise HTTPException(422, '验证案名称去除空格后至少需要两个字符')
    given = {}
    for band, tol in data.tolerances.items():
        b = str(band).strip()
        if not b: raise HTTPException(422, '温区名称不能为空')
        try:
            t = float(tol)
        except (TypeError, ValueError):
            raise HTTPException(422, f'温区 {b} 的容差必须为数值')
        if not math.isfinite(t) or not 0 < t <= TOLERANCE_MAX:
            raise HTTPException(422, f'温区 {b} 的容差须在 0–{TOLERANCE_MAX:g} °C 之间')
        given[b] = t
    missing = [b for b in bands if b not in given]
    extra = [b for b in given if b not in bands]
    if missing: raise HTTPException(422, '缺少温区容差：' + '、'.join(missing))
    if extra: raise HTTPException(422, '容差包含该分析不存在的温区：' + '、'.join(extra))
    c = ValidationCase(name=name, job_id=j.id, tolerances=given, created_by=user.id, created_at=time.time())
    db.add(c); db.flush()
    return c

def lock(db, case):
    if case.status != 'open': raise HTTPException(409, '补偿值已锁定，不能重复锁定')
    j = db.get(Job, case.job_id)
    params = dict(j.params or {})
    case.locked_params = {'offset': params.get('offset', 0), 'confidence': params.get('confidence', .95), 'resamples': params.get('resamples', 2000)}
    case.status = 'locked'

def enable(db, case, holdback_id):
    if case.status == 'open': raise HTTPException(409, '锁定补偿值后才可启用留样')
    if case.status != 'locked': raise HTTPException(409, '本案已启用留样，不能重复启用')
    if not db.get(Holdback, holdback_id): raise HTTPException(404, '留样批不存在')
    # 并发安全：仅封存中的留样可被占用；同批留样并发启用只有一案成功。
    res = db.execute(update(Holdback).where(Holdback.id == holdback_id, Holdback.status == 'sealed').values(status='in_use', case_id=case.id))
    if res.rowcount != 1: raise HTTPException(409, '该留样已被其他验证案占用或已消耗')
    case.holdback_id = holdback_id
    case.status = 'queued'
    db.flush()
    enqueue(case.id)

def retry(db, case):
    if case.status != 'failed': raise HTTPException(409, '仅计算中断的验证案可以重试')
    h = db.get(Holdback, case.holdback_id) if case.holdback_id else None
    if not h or h.case_id != case.id or h.status != 'in_use':
        raise HTTPException(409, '留样占用已变更，无法恢复本案')
    # 占用仍属本案：重试继续同一占用，不重复消耗留样。
    case.status = 'queued'; case.error = ''; case.finished_at = None
    db.flush()
    enqueue(case.id)

def enqueue(case_id):
    try:
        r = Redis.from_url(REDIS_URL); r.rpush('validation:queue', case_id); r.close()
    except Exception:
        pass # SQL queued status is the durable fallback

def compute(db, case):
    """按锁定的补偿值复算封存留样并作出验收结论。结论一经提交留样即消耗。"""
    h = db.get(Holdback, case.holdback_id)
    if not h or h.case_id != case.id or h.status != 'in_use':
        raise ValueError('留样占用状态异常，已中止复算')
    outcome = analyze(h.records, case.locked_params or {})
    rows = {r['band']: r for r in outcome['table']['rows']}
    checks = []
    for band, tol in sorted(case.tolerances.items()):
        r = rows.get(band)
        if r is None:
            checks.append({'band': band, 'tolerance': tol, 'pass': False, 'reason': '缺温区：留样中无该温区读数'})
            continue
        ok = r['low'] >= -tol and r['high'] <= tol
        checks.append({'band': band, 'n': r['n'], 'bias': r['bias'], 'low': r['low'], 'high': r['high'], 'tolerance': tol, 'pass': ok, 'reason': '偏差区间在容差内' if ok else '偏差区间超出容差'})
    for band in sorted(set(rows) - set(case.tolerances)):
        r = rows[band]
        checks.append({'band': band, 'n': r['n'], 'bias': r['bias'], 'low': r['low'], 'high': r['high'], 'tolerance': None, 'pass': False, 'reason': '留样温区未在验证案容差中定义'})
    released = all(x['pass'] for x in checks)
    offset = (case.locked_params or {}).get('offset', 0)
    case.verdict = 'released' if released else 'rejected'
    case.result = {'summary': f"按锁定补偿值 {offset:g}°C 复算留样 {sum(r['n'] for r in rows.values())} 对读数，{len(checks)} 项温区核验{'全部在容差内，准许该分析放行' if released else '未全部通过，该分析不予放行'}。",
                   'locked_params': case.locked_params, 'bands': checks}
    case.status = 'completed'; case.finished_at = time.time()
    h.status = 'consumed' # 验收结论一经作出，留样即消耗，验收失败也算用过
    j = db.get(Job, case.job_id)
    j.released = released # 放行状态以最近一次验收结论为准
    db.flush()
