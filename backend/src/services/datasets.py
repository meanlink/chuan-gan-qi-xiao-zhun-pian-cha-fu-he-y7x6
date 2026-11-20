from fastapi import HTTPException
from sqlalchemy import select
from src.models import Dataset, Holdback
from src.services.business import metadata
from src.utils.serialization import checksum
import math, time
def _validate_rows(rows):
    for index,row in enumerate(rows):
        for c in metadata()['columns']:
            value=row.get(c['key'])
            if value is None or value=='': raise HTTPException(422, f'第 {index+1} 行缺少字段 {c["label"]}')
            if c['type']=='number':
                try:
                    if isinstance(value,bool) or not math.isfinite(float(value)): raise ValueError()
                    row[c['key']]=float(value)
                except (TypeError, ValueError, OverflowError): raise HTTPException(422, f'第 {index+1} 行 {c["label"]} 必须为有限数值')
def create(db, data):
    name=data.name.strip()
    if len(name)<2: raise HTTPException(422, '批次名称去除空格后至少需要两个字符')
    if db.scalar(select(Dataset).where(Dataset.name==name)):
        raise HTTPException(409, '该数据批次名已存在，请修改名称')
    _validate_rows(data.records)
    d=Dataset(name=name, source=data.source, records=data.records, checksum=checksum(data.records), created_at=time.time())
    db.add(d); db.flush()
    holdback=None
    if data.holdback_records:
        _validate_rows(data.holdback_records)
        ordinary={str(r.get('sample')) for r in data.records}
        sealed={str(r.get('sample')) for r in data.holdback_records}
        overlap=sorted(ordinary & sealed)
        if overlap: raise HTTPException(422, '留样与普通批不得共用测量编号：'+'、'.join(overlap[:5]))
        hname=name+' · 留样'
        if db.scalar(select(Holdback).where(Holdback.name==hname)):
            raise HTTPException(409, '该留样批名已存在，请修改批次名称')
        holdback=Holdback(name=hname, dataset_id=d.id, records=data.holdback_records, checksum=checksum(data.holdback_records), created_at=time.time())
        db.add(holdback); db.flush()
    return d, holdback
