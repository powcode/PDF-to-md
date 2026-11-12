import os
import shutil
import time
import uuid
import threading
from pathlib import Path
import config

jobs_lock = threading.Lock()
jobs_store: dict[str, dict] = {}

def cleanup_old_files_and_jobs():
    cutoff = time.time() - config.FILE_TTL_SECONDS

    # 1. Cleanup jobs
    with jobs_lock:
        to_del = [jid for jid, j in jobs_store.items() if j.get("created_at", 0) < cutoff]
        for jid in to_del:
            del jobs_store[jid]

    # 2. Cleanup upload and output dirs
    for d in (config.UPLOAD_DIR, config.OUTPUT_DIR):
        if d.exists():
            for p in d.iterdir():
                try:
                    if p.stat().st_mtime < cutoff:
                        if p.is_dir():
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            p.unlink(missing_ok=True)
                except Exception:
                    pass

def create_job(total_slides: int = 0, total_figures: int = 0) -> str:
    cleanup_old_files_and_jobs()
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs_store[job_id] = {
            "id": job_id,
            "status": "queued",  # queued | running | done | error
            "progress": {
                "slide": 0,
                "total_slides": total_slides,
                "figure": 0,
                "total_figures": total_figures
            },
            "message": "Menunggu giliran...",
            "markdown": "",
            "stats": {},
            "error": None,
            "created_at": time.time()
        }
    return job_id

def get_job(job_id: str) -> dict | None:
    with jobs_lock:
        job = jobs_store.get(job_id)
        if not job:
            return None
        # Return shallow copy
        return dict(job)

def update_job(job_id: str, **kwargs):
    with jobs_lock:
        if job_id in jobs_store:
            jobs_store[job_id].update(kwargs)

def update_job_progress(job_id: str, slide: int = None, figure: int = None, message: str = None):
    with jobs_lock:
        if job_id in jobs_store:
            prog = jobs_store[job_id]["progress"]
            if slide is not None:
                prog["slide"] = slide
            if figure is not None:
                prog["figure"] = figure
            if message is not None:
                jobs_store[job_id]["message"] = message
