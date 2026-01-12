import os
import shutil
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
from starlette.background import BackgroundTask
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging

setup_logging()

from app.job_executor import run_saintexpress_job, SaintexpressExecutionResult

# Configuration
SESSION_BASE_DIR = "/tmp/app-sessions"
INPUT_SLOTS = {"interaction", "prey", "bait"}
INPUT_FILENAMES = {
    "interaction": "interaction.txt",
    "prey": "prey.txt",
    "bait": "bait.txt",
}
OUTPUT_FILENAME = "list.txt"

# Ensure session base exists
os.makedirs(SESSION_BASE_DIR, exist_ok=True)

app = FastAPI()

origins = os.getenv("FRONTEND_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _session_dir(session_id: str) -> Path:
    """Get the path to the session directory for a given session_id."""
    # UUID validation for additional safety
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid session_id")
    return Path(SESSION_BASE_DIR) / session_id


def _validate_session(session_id: str) -> Path:
    """Raise if session_id/session folder does not exist."""
    session_path = _session_dir(session_id)
    if not session_path.is_dir():
        raise HTTPException(status_code=404, detail="Session not found")
    return session_path

# -------- API Endpoints --------

@app.post("/session/start")
def start_session():
    # Stateless: don't store anything outside session dirs
    session_id = str(uuid.uuid4())
    session_path = _session_dir(session_id)
    try:
        session_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # Should never happen, but guard against rare UUID collisions
        raise HTTPException(status_code=500, detail="Failed to create session directory")
    return {"session_id": session_id}


@app.post("/session/{session_id}/upload/{slot}")
def upload_input_file(session_id: str, slot: str, file: UploadFile = File(...)):
    if slot not in INPUT_SLOTS:
        raise HTTPException(status_code=400, detail=f"Invalid slot: {slot}")
    session_path = _validate_session(session_id)
    dest_file = session_path / INPUT_FILENAMES[slot]
    try:
        with open(dest_file, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")
    return {"uploaded": slot}


@app.post("/session/{session_id}/run")
async def run_saintexpress(session_id: str):
    session_path = _validate_session(session_id)
    # Validate presence of all required input files
    missing = [name for name in INPUT_FILENAMES.values() if not (session_path / name).is_file()]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required input files: {', '.join(missing)}"
        )

    # Run the SAINTexpress job via Docker
    result: SaintexpressExecutionResult = await run_saintexpress_job(str(session_path))
    
    # On failure, propagate the error
    if result.exit_code != 0:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "exit_code": result.exit_code,
                "stderr": result.stderr,
            }
        )

    # On success, return output metadata
    output_path = session_path / OUTPUT_FILENAME
    if not output_path.exists():
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Output file not found (job may have failed)."},
        )
    
    # Return output file contents as result
    try:
        with open(output_path, "r") as f:
            output_text = f.read()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Failed to read output file: {e}"},
        )

    meta = {
        "success": True,
        "output_file": OUTPUT_FILENAME,
        "size": output_path.stat().st_size,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "output_text": output_text,
    }
    return meta


@app.get("/session/{session_id}/download")
def download_output(session_id: str):
    session_path = _validate_session(session_id)
    file_path = session_path / OUTPUT_FILENAME
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Output file not found. Run must be completed before download."
        )
    def file_iterator():
        with open(file_path, "rb") as f:
            yield from f

    return StreamingResponse(
        file_iterator(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={OUTPUT_FILENAME}"
        }
    )


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    session_path = _validate_session(session_id)

    # Use background task to remove even if files are open
    def rm_tree(p):
        shutil.rmtree(p, ignore_errors=True)

    return Response(
        content="Session deleted",
        status_code=204,
        background=BackgroundTask(rm_tree, session_path)
    )


# ----------- Notes & Design Choices -----------
# - API is fully stateless; session data is only on disk.
# - All functions modular, especially job execution logic (see job_executor.py), aiding future Go port.
# - All I/O is local to session dir with no global mutable state.
# - Proper error handling returns explicit status codes/messages.
# - Uses pathlib and shutil for atomic file/directory operations.
# - Comments explain helper functions and critical behaviors.
# - job_executor only returns file contents if exit_code==0 and file exists.
