
from pydantic import BaseModel
from typing import Optional, Dict

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None