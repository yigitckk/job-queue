from models.job import Job, JobStatus
from worker.worker import process_job, MAX_RETRIES

def test_job_created_and_completed(db_session):
    job = Job(
        payload={"action": "send_email"}
    )
    db_session.add(job)
    db_session.commit()
    process_job(job, db_session)
    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at

def test_job_failure_goes_back_to_pending(db_session):
    job = Job(
        payload={"action": "activate_plan"},
        status=JobStatus.RUNNING,
        retry_count = 0,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    process_job(job,db_session)
    db_session.refresh(job)
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 1 


def test_job_reaches_dead_letter(db_session):
    MAX_RETRIES = 5

    job = Job(
        payload={"action":"activate_plan"},
        status=JobStatus.PENDING,
        retry_count = MAX_RETRIES -1,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    process_job(job,db_session)
    updated_job = db_session.query(Job).filter(Job.id == job.id).first()
    assert updated_job.retry_count >= MAX_RETRIES
    assert updated_job.status == JobStatus.DEAD_LETTER

def test_skip_locked_two_workers_same_job(db_session, db_session_factory):
    # 1. SETUP: Veritabanına bekleyen (PENDING) tek bir job ekliyoruz.
    job = Job(
        payload={"action": "send_email"},
        status=JobStatus.PENDING
    )
    db_session.add(job)
    db_session.commit()
    
    # 2. İkinci Worker'ı temsil eden yepyeni, tamamen bağımsız bir DB bağlantısı açıyoruz.
    session2 = db_session_factory()
    
    try:
        # 3. WORKER 1 (db_session): İşi veritabanından çeker ve kilitler.
        # Burada "with_for_update(skip_locked=True)" sihirli noktadır.
        worker1_job = (
            db_session.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .with_for_update(skip_locked=True)
            .first()
        )
        
        # Worker 1'in job'ı başarıyla yakaladığını doğrulayalım
        assert worker1_job is not None
        assert worker1_job.id == job.id
        
        # ⚠️ DİKKAT: db_session henüz commit yapmadı. Transaction açık.
        # Veritabanında bu satır şu an Worker 1'e tahsis edildi (Row-level lock).
        
        # 4. WORKER 2 (session2): Aynı saniye içinde o da veritabanından iş arıyor.
        worker2_job = (
            session2.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .with_for_update(skip_locked=True)
            .first()
        )
        
        # ASSERT: Worker 2, Worker 1'in kitlediği satırı atlamalı (SKIP LOCKED) 
        # ve sistemde başka PENDING iş olmadığı için None almalı.
        # Bu test geçerse, Race Condition (iki worker'ın aynı işi alması) engellenmiş demektir!
        assert worker2_job is None
        
        # 5. WORKER 1 işi tamamlar ve durumu günceller
        worker1_job.status = JobStatus.COMPLETED
        db_session.commit() # Kilit burada serbest kalır (Lock Release)

        
    finally:
        # Temizlik: İkinci session'ı kapatıyoruz ki veritabanı connection limiti dolmasın (Connection Leak)
        session2.close()

