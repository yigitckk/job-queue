from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.config import settings
from db.database import get_db, engine
from models.job import Base, JobStatus
import schemas.job as schemas
import services.services as services
from core.logging import configure_logging

from core.middleware import RequestIDMiddleware



configure_logging()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(RequestIDMiddleware)


#endpoint kısmı

@app.post("/jobs/",response_model=schemas.JobResponse)
def create_work(job_in:schemas.JobCreate, db:Session=Depends(get_db)):
    return services.create_job(db=db,job_in=job_in)

@app.get("/jobs/",response_model=list[schemas.JobResponse])
def list_works(skip: int=0,limit:int=100, db:Session=Depends(get_db)):
    return services.get_jobs(db=db, skip=skip, limit=limit)

@app.get("/jobs/{job_id}",response_model=schemas.JobResponse)
def list_work(job_id: int, db:Session=Depends(get_db)):
    db_job = services.get_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404,detail="Job not found")
    return db_job

@app.put("/jobs/{job_id}", response_model=schemas.JobResponse)
def update_work(job_id:int, new_status:JobStatus, db:Session=Depends(get_db),error_message: str=None):
    db_job = services.get_job(db=db,job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404,detail="Work to be updated not found")
    return services.update_job_status(
        db=db,
        job_id=job_id,
        new_status=new_status,
        error_message=error_message
    )
 
@app.delete("/jobs/{job_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_work(job_id:int,db:Session=Depends(get_db)):
    db_job = services.get_job(db=db,job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404,detail="Not found to be deleted job")
    services.delete_job(db=db,job_id=job_id)
    return None
