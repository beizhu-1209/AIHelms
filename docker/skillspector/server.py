import asyncio
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from skillspector import __version__ as skillspector_version
from skillspector.mcp_server import run_scan


INPUT_ROOT = Path(os.getenv("SKILLSPECTOR_SERVICE_INPUT_ROOT", "/scan-input")).resolve()
TIMEOUT_SECONDS = int(os.getenv("SKILLSPECTOR_SERVICE_TIMEOUT_SECONDS", "180"))

app = FastAPI(title="AIHelms Skill Audit Scanner", version="0.1.0")


class ScanRequest(BaseModel):
    target: str = Field(..., min_length=1)
    output_format: Literal["json", "sarif", "markdown"] = "json"


def _resolve_target(target: str) -> str:
    if target.startswith(("http://", "https://", "git+")):
        raise HTTPException(status_code=400, detail="Only shared-volume local paths are enabled")

    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = INPUT_ROOT / target_path
    resolved = target_path.resolve()

    if not resolved.is_relative_to(INPUT_ROOT):
        raise HTTPException(status_code=400, detail="Target path is outside scan input root")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Target path does not exist")
    return str(resolved)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "scanner": "skillspector",
        "scanner_version": skillspector_version,
        "mode": "static-only",
    }


@app.post("/scan")
async def scan(req: ScanRequest) -> dict:
    target = _resolve_target(req.target)
    try:
        result = await asyncio.wait_for(
            run_scan(target, use_llm=False, output_format=req.output_format),
            timeout=TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Scan timed out") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "code": 200,
        "message": "ok",
        "data": result,
    }
