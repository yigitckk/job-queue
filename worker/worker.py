from datetime import datetime, timezone
import time
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.job import Job, JobStatus
import structlog

log = structlog.get_logger()

MAX_RETRIES = 5

def complete_work(payload:dict):
    
    work_type = payload.get("action")

    if work_type =="send_email":
        email = payload.get("email")
        log.info("email_being_sent", email=email)

    elif work_type == "compress_video":
        video_id = payload.get("video_id")
        log.info("video_is_being_compressed", video_id=video_id)

    else:
        raise ValueError(f"Unknown Process: {work_type}")

def process_job(job,db):
        try:
            complete_work(job.payload)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            log.info("job_completed", job_id=job.id)
        except Exception as e:
            job.retry_count += 1
            job.error_message = str(e)
            log.error("job_failed", job_id=job.id,error=str(e))
            if job.retry_count >= MAX_RETRIES:
                job.status = JobStatus.DEAD_LETTER
                log.info("job_being_removed_to_dead_letter_box")
            else:
                job.status = JobStatus.PENDING
            db.commit()


def start_worker():
    log.info("worker_started")
    while True:
        db: Session = SessionLocal() #db session each time

        try:
            job = db.query(Job).filter(Job.status == JobStatus.PENDING).with_for_update(skip_locked=True).first()
            if not job:
                db.close()
                time.sleep(2)
                continue

            log.info("job_found", job_id=job.id)
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            db.commit()
            process_job(job,db)

        except Exception as db_error:
            log.error("database_error", error=str(db_error))
            time.sleep(5)
        finally:
            db.close()

if __name__ == "__main__":
    start_worker()
