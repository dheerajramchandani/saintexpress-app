# FastAPI SAINTexpress Backend

## Architecture Overview

- **Stateless API:** All per-user state is stored on disk under `/tmp/app-sessions/{session_id}/`
- **Session Isolation:** Each session gets a unique UUID-based workspace directory.
- **Modular Design:** Execution logic is fully separated in `job_executor.py` for porting to Go.
- **No authentication:** Sessions are unguarded and public.
- **Concurrency:** Designed to allow concurrent requests safely via isolated disk workspaces.
- **No global mutable state**

## API Usage

### 1. Start a new session

```
POST /session/start
Response: {"session_id": "uuid-..."}
```

### 2. Upload input files

```
POST /session/{session_id}/upload/{slot}
(slot is one of: interaction, prey, bait)
Multipart file upload with form field: file
```

Accepted files:
- interaction → interaction.txt
- prey → prey.txt
- bait → bait.txt

### 3. Run the job

```
POST /session/{session_id}/run
Validates all 3 files, runs the Dockerized job. Returns output metadata or error.
```

### 4. Download results

```
GET /session/{session_id}/download
Streams output file back to client.
```

### 5. Delete session

```
DELETE /session/{session_id}
Erases the session directory and all user data.
```

## Implementation Notes

- All API routes are stateless, session info is encoded in session directory and `session_id`.
- Execution logic is 100% modular and can be ported to Go by reimplementing `job_executor.py`.
- Docker containers launched with `--rm` so they are cleaned up automatically.
- Each session receives its own file workspace, and workspace is mounted to `/data` inside the container.
- Handles container timeouts and job errors gracefully.

## Development

- Python 3.9, tested with FastAPI
- Start app: `uvicorn app.main:app --reload`
- No special database/configs required!
