from sqlalchemy.orm import Session
from models.job import Job, JobStatus
from schemas.job import JobCreate


def create_job(db:Session,job_in:JobCreate):
    db_job = Job(payload=job_in.payload)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job(db:Session,job_id:int):
    return db.query(Job).filter(Job.id==job_id).first()
    
def get_jobs(db:Session,skip: int=0,limit: int=100):
    return db.query(Job).offset(skip).limit(limit).all()
    
def update_job_status(db:Session,job_id:int, new_status: JobStatus, error_message:str=None):
    db_job = get_job(db,job_id)
    if db_job:
        db_job.status = new_status
        if error_message:
            db_job.error_message = error_message
    db.commit()
    db.refresh(db_job)
    return db_job

def delete_job(db:Session,job_id:int):
    db_job = get_job(db,job_id)
    db.delete(db_job)
    db.commit()
    return None
