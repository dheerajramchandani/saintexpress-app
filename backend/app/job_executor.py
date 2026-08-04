import subprocess
from typing import Optional
from dataclasses import dataclass
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import shlex
import logging
import docker
import requests

# This module contains only the job execution logic. All arguments are explicit:
# No imported global state. This aids re-implementation in Go or other languages.

logger = logging.getLogger("app")

@dataclass
class SaintexpressExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


def _run_job(session_dir: str, saint_version: str, timeout: int = 120) -> SaintexpressExecutionResult:
    """
    Runs SAINTexpress inside a Docker container using the Python Docker SDK.
    session_dir: absolute path to the workspace (mounted in container)
    Returns: result object with stdout, stderr, exit code
    """
    # Replace these values with actual details for your container/image/binary
    # REQUIREMENT: Docker daemon must be available on host
    # Backend process must have permission to run docker commands
    docker_image = "saintexpress:1.0.0"
    container_mount_path = "/work"
    
    # Construct the bash command using the selected binary
    # saint_version will be 'SAINTexpress-spc' or 'SAINTexpress-int'
    cmd = f"/usr/local/bin/{saint_version}"
    args = [
        # "bash", "-c",
        cmd,
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
        # Initialize the Docker client via the mounted socket
        client = docker.from_env()

        # Run the container in detached mode
        container = client.containers.run(
            image=docker_image,
            command=args,
            volumes={
                os.path.abspath(session_dir): {
                    "bind": container_mount_path,
                    "mode": "rw"
                }
            },
            working_dir=container_mount_path,
            nano_cpus=int(1.0 * 1e9),  # 1.0 CPU core limit
            mem_limit="2g",
            stdout=True,
            stderr=True,
            detach=True,
        )

        # Wait for the container with the specified timeout
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", 0)

        # Fetch stdout and stderr logs after completion
        stdout_bytes = container.logs(stdout=True, stderr=False)
        stderr_bytes = container.logs(stdout=False, stderr=True)

        stdout = stdout_bytes.decode('utf-8', errors='replace') if isinstance(stdout_bytes, bytes) else str(stdout_bytes)
        stderr = stderr_bytes.decode('utf-8', errors='replace') if isinstance(stderr_bytes, bytes) else str(stderr_bytes)
        
    except (requests.exceptions.ReadTimeout, TimeoutError):
        logger.error("Container execution exceeded timeout of %d seconds", timeout)
        if container:
            try:
                container.stop(timeout=2)
            except Exception as stop_err:
                logger.error("Failed to stop timed-out container: %s", stop_err)
        
        # Capture whatever logs were produced before the timeout happened
        stdout_bytes = container.logs(stdout=True, stderr=False) if container else b""
        stderr_bytes = container.logs(stdout=False, stderr=True) if container else b""
        
        stdout = stdout_bytes.decode('utf-8', errors='replace') if isinstance(stdout_bytes, bytes) else ""
        stderr = (stderr_bytes.decode('utf-8', errors='replace') if isinstance(stderr_bytes, bytes) else "") + f"\nTimeout expired after {timeout} seconds."

        return SaintexpressExecutionResult(
            exit_code=124,  # Standard Unix timeout exit code
            stdout=stdout,
            stderr=stderr,
        )
    except Exception as e:
        return SaintexpressExecutionResult(
            exit_code=1,
            stdout="",
            stderr=f"Failed to execute docker run: {e}",
        )
    finally:
        # Always clean up the container manually since detach=True was used
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass

    return SaintexpressExecutionResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )

async def run_saintexpress_job(session_dir: str, saint_version: str, timeout: int = 120) -> SaintexpressExecutionResult:
    """
    Async interface to make execution concurrent (in a thread/executor).
    """
    loop = asyncio.get_running_loop()
    # You can increase max_workers for more concurrency if needed
    with ThreadPoolExecutor(max_workers=4) as pool:
        return await loop.run_in_executor(pool, _run_job, session_dir, saint_version, timeout)


# ----------- Notes & Design Choices -----------
# - job_executor.py is a pure logic module, portable to other languages.
# - No FastAPI or HTTP imports—API code is in main.py.
# - Exposes results including stdout/stderr for error reporting, and explicit exit code for control by caller.
