import time, json, logging
from pathlib import Path
from sqlalchemy import select
from redis import Redis
from src.config.database import Session
from src.config.settings import REDIS_URL
from src.models import Job, Dataset, Report, ValidationCase
from src.services.business import analyze
from src.services.reports import deliver
from src.services import validation
from src.services.audit import record
logging.basicConfig(level=logging.INFO)
def execute(job_id):
    with Session() as db:
        j=db.get(Job,job_id)
        if not j or j.status!='queued':return
        j.status='running'; db.commit()
        try:
            d=db.get(Dataset,j.dataset_id)
            result=analyze(d.records,j.params)
            json.dumps(result,allow_nan=False)
            j.result=result;j.status='completed';j.finished_at=time.time()
            record(db,'worker','job.completed',{'id':j.id})
        except Exception as e:
            logging.exception('Analysis failed')
            j.status='failed';j.error=str(e)[:990];j.finished_at=time.time()
            record(db,'worker','job.failed',{'id':j.id,'error':j.error})
        db.commit()
def execute_case(case_id):
    with Session() as db:
        c=db.get(ValidationCase,case_id)
        if not c or c.status!='queued':return
        c.status='running'; db.commit()
        try:
            validation.compute(db,c)
            json.dumps(c.result,allow_nan=False)
            record(db,'worker','case.completed',{'id':c.id,'verdict':c.verdict})
        except Exception as e:
            logging.exception('Validation failed')
            c.status='failed';c.error=str(e)[:990];c.finished_at=time.time()
            record(db,'worker','case.failed',{'id':c.id,'error':c.error})
        db.commit()
def tick():
    with Session() as db:
        queued=list(db.scalars(select(Job.id).where(Job.status=='queued').limit(3)))
        queued_cases=list(db.scalars(select(ValidationCase.id).where(ValidationCase.status=='queued').limit(3)))
    for job_id in queued:execute(job_id)
    for case_id in queued_cases:execute_case(case_id)
    with Session() as db:
        for r in db.scalars(select(Report).where(Report.enabled==True,Report.next_run<=time.time())):
            d=deliver(db,r)
            if d:record(db,'worker','report.delivered',{'id':r.id,'delivery':d.id})
        db.commit()
def recover_interrupted(db):
    # This Compose stack has a single worker. A crash must not strand its jobs.
    for j in db.scalars(select(Job).where(Job.status=='running')):
        j.status='queued';record(db,'worker','job.recovered',{'id':j.id})
    # 计算中断的验证案恢复为排队：留样占用仍属原案，重算不重复消耗。
    for c in db.scalars(select(ValidationCase).where(ValidationCase.status=='running')):
        c.status='queued';record(db,'worker','case.recovered',{'id':c.id})
def main():
    r=Redis.from_url(REDIS_URL,socket_timeout=3)
    with Session() as db:
        recover_interrupted(db)
        db.commit()
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=r.blpop(['analysis:queue','validation:queue'],timeout=1)
            if item:
                queue,value=item[0].decode(),int(item[1])
                if queue=='validation:queue':execute_case(value)
                else:execute(value)
            tick()
        except Exception:
            logging.exception('Worker retry');time.sleep(2)
if __name__=='__main__':main()
