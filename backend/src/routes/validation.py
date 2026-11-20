from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Holdback, ValidationCase
from src.schemas.validation import CaseInput, EnableInput
from src.middlewares.auth import current_user, can_write
from src.services import validation
from src.services.audit import record
from src.utils.serialization import holdback_dict, case_dict
router=APIRouter()
@router.get('/holdbacks')
def holdbacks(db=Depends(get_db),u=Depends(current_user)):
    return [holdback_dict(h) for h in db.scalars(select(Holdback).order_by(Holdback.id.desc()))]
@router.get('/validation-cases')
def listing(db=Depends(get_db),u=Depends(current_user)):
    return [case_dict(c) for c in db.scalars(select(ValidationCase).order_by(ValidationCase.id.desc()).limit(100))]
@router.post('/validation-cases',status_code=201)
def create(data:CaseInput,db=Depends(get_db),u=Depends(can_write)):
    c=validation.create_case(db,data,u); record(db,u.email,'case.create',{'id':c.id,'job_id':c.job_id,'tolerances':c.tolerances})
    db.commit(); return case_dict(c)
@router.get('/validation-cases/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    c=db.get(ValidationCase,id)
    if not c: raise HTTPException(404,'验证案不存在')
    return case_dict(c)
@router.post('/validation-cases/{id}/lock')
def lock(id:int,db=Depends(get_db),u=Depends(can_write)):
    c=db.get(ValidationCase,id)
    if not c: raise HTTPException(404,'验证案不存在')
    validation.lock(db,c); record(db,u.email,'case.lock',{'id':id,'locked_params':c.locked_params}); db.commit()
    return case_dict(c)
@router.post('/validation-cases/{id}/enable')
def enable(id:int,data:EnableInput,db=Depends(get_db),u=Depends(can_write)):
    c=db.get(ValidationCase,id)
    if not c: raise HTTPException(404,'验证案不存在')
    validation.enable(db,c,data.holdback_id); record(db,u.email,'case.enable',{'id':id,'holdback_id':data.holdback_id}); db.commit()
    return case_dict(c)
@router.post('/validation-cases/{id}/retry')
def retry(id:int,db=Depends(get_db),u=Depends(can_write)):
    c=db.get(ValidationCase,id)
    if not c: raise HTTPException(404,'验证案不存在')
    validation.retry(db,c); record(db,u.email,'case.retry',{'id':id}); db.commit()
    return case_dict(c)
