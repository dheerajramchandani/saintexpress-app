import subprocess
from typing import Optional
from dataclasses import dataclass
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import shlex
import logging

# This module contains only the job execution logic. All arguments are explicit:
# No imported global state. This aids re-implementation in Go or other languages.

logger = logging.getLogger("app")

@dataclass
class SaintexpressExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


def _run_job(session_dir: str, timeout: int = 120) -> SaintexpressExecutionResult:
    """
    Runs SAINTexpress inside a Docker container.
    session_dir: absolute path to the workspace (mounted in container)
    Returns: result object with stdout, stderr, exit code
    """
    # Replace these values with actual details for your container/image/binary
    # REQUIREMENT: Docker daemon must be available on host
    # Backend process must have permission to run docker commands
    docker_image = "eaf77086b681"
    container_mount_path = "/work"
    saintexec_binary = "./saintexpress"  # Assuming it is in the root of the image
    args = [
        "docker", "run", "--rm",
        "--cpus", "1.0",
        "--memory", "2g",
        "-v", f"{os.path.abspath(session_dir)}:{container_mount_path}",
        "-w", "/work",
        docker_image,
        # "bash", "-c",
        "interaction.txt",
        "prey.txt",
        "bait.txt",
        # Add extra arguments for SAINTexpress as needed
        # All your .dat files and output location should be in /data/
    ]

    logger.info("Docker argv: %r", args)
    logger.info("Running docker command:\n%s", shlex.join(args))

    # This assumes all relevant handling is internal to your image/C binary;
    # modify to suit the binary's actual instructions.
    try:
        proc = subprocess.run(
            args,
            cwd=session_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        return SaintexpressExecutionResult(
            exit_code=124,  # Unix timeout code
            stdout=e.stdout or "",
            stderr=(e.stderr or "") + "\nTimeout expired.",
        )
    except Exception as e:
        return SaintexpressExecutionResult(
            exit_code=1,
            stdout="",
            stderr=f"Failed to execute docker run: {e}",
        )

    return SaintexpressExecutionResult(
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )

async def run_saintexpress_job(session_dir: str, timeout: int = 120) -> SaintexpressExecutionResult:
    """
    Async interface to make execution concurrent (in a thread/executor).
    """
    loop = asyncio.get_running_loop()
    # You can increase max_workers for more concurrency if needed
    with ThreadPoolExecutor(max_workers=4) as pool:
        return await loop.run_in_executor(pool, _run_job, session_dir, timeout)


# ----------- Notes & Design Choices -----------
# - job_executor.py is a pure logic module, portable to other languages.
# - No FastAPI or HTTP imports—API code is in main.py.
# - Exposes results including stdout/stderr for error reporting, and explicit exit code for control by caller.
