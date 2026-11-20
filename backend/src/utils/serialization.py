import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','released','created_at','finished_at']}
def report_dict(r):
    return {k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled']}
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination']}
def holdback_dict(h):
    # 封存读数不开放查看：任何接口都不返回 records。
    return {'id':h.id, 'name':h.name, 'dataset_id':h.dataset_id, 'rows':len(h.records), 'checksum':h.checksum, 'status':h.status, 'case_id':h.case_id, 'created_at':h.created_at}
def case_dict(c):
    return {k:getattr(c,k) for k in ['id','name','job_id','tolerances','locked_params','holdback_id','status','verdict','result','error','created_at','finished_at']}
