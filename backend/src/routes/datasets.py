from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Dataset, Holdback
from src.schemas.dataset import DatasetInput
from src.middlewares.auth import current_user, can_write
from src.services import datasets
from src.services.audit import record
from src.utils.serialization import dataset_dict, holdback_dict
router=APIRouter(prefix='/datasets')
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    batches=list(db.scalars(select(Dataset).order_by(Dataset.id.desc())))
    sealed={}
    for h in db.scalars(select(Holdback).order_by(Holdback.id.desc())):
        sealed.setdefault(h.dataset_id,[]).append(holdback_dict(h))
    return [{**dataset_dict(d),'holdbacks':sealed.get(d.id,[])} for d in batches]
@router.post('',status_code=201)
def create(data:DatasetInput,db=Depends(get_db),u=Depends(can_write)):
    d,h=datasets.create(db,data); record(db,u.email,'dataset.create',{'id':d.id,'rows':len(d.records),'holdback_rows':len(h.records) if h else 0})
    db.commit()
    return {**dataset_dict(d),'holdback':holdback_dict(h) if h else None}
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    d=db.get(Dataset,id)
    if not d:raise HTTPException(404,'数据批次不存在')
    return {**dataset_dict(d),'records':d.records}
