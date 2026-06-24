from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from models.job import JobStatus


class JobBase(BaseModel):
    payload: Optional[Dict[str,Any]] = None

class JobCreate(JobBase):
    #sadece payload 
    pass

class JobResponse(JobBase):
    id: int
    status: JobStatus
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
    
