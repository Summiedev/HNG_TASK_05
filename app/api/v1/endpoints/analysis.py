from __future__ import annotations

import os
from uuid import UUID, uuid4
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.api.deps import DBSession
from app.core.config import settings
from app.models.analysis import Analysis, AnalysisStatus

router = APIRouter()


async def _store_upload(source: UploadFile, destination: Path, chunk_size: int = 1024 * 1024) -> None:
    with destination.open("wb") as target:
        while True:
            chunk = await source.read(chunk_size)
            if not chunk:
                break
            target.write(chunk)


@router.post("/analysis/upload")
async def upload_analysis(db: DBSession, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not 1 <= len(files) <= 3:
        raise HTTPException(status_code=400, detail="provide between 1 and 3 documents")

    analysis_id = uuid4()
    upload_dir = Path(settings.UPLOAD_DIR)
    job_dir = upload_dir / str(analysis_id)
    os.makedirs(job_dir, exist_ok=True)

    stored_paths: list[str] = []
    for index, file in enumerate(files, start=1):
        filename = file.filename or f"document-{index}"
        ext = Path(filename).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".pdf"):
            raise HTTPException(status_code=400, detail="unsupported file type")
        dest = job_dir / f"{index:02d}-{Path(filename).name}"
        await _store_upload(file, dest)
        stored_paths.append(str(dest))

    analysis = Analysis(
        id=analysis_id,
        status=AnalysisStatus.uploaded.value,
        file_path=stored_paths[0],
        document_paths=stored_paths,
    )
    db.add(analysis)
    await db.commit()
    from app.services.tasks import process_analysis

    process_analysis.delay(str(analysis_id))
    return {"analysis_id": str(analysis_id), "status": AnalysisStatus.uploaded.value, "message": "Analysis has been queued for processing"}


@router.get("/analysis/{analysis_id}/status")
async def get_status(analysis_id: UUID, db: DBSession) -> dict[str, str]:
    q = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = q.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"analysis_id": str(analysis.id), "status": analysis.status}


@router.get("/analysis/{analysis_id}")
async def get_result(analysis_id: UUID, db: DBSession) -> dict[str, Any]:
    q = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = q.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status,
        "ocr_result": analysis.ocr_result,
        "ai_interpretation": analysis.ai_interpretation,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "failure_reason": analysis.failure_reason,
        "failed_at": analysis.failed_at.isoformat() if analysis.failed_at else None,
    }
