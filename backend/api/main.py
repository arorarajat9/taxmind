"""FastAPI app exposing the TaxMind pipeline to the frontend.

Endpoints
---------
GET  /api/health          -> mode + knowledge backend
GET  /api/demo            -> run the pipeline on the bundled kirana dataset
POST /api/analyze         -> run the pipeline on uploaded sales/purchase/2A files
POST /api/kb/query        -> ask the GST knowledge base directly (cited answer)
GET  /api/download        -> download the last generated filing-ready Excel
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.agents.agent_framework_workflow import run_analysis_via_workflow as run_analysis
from backend.config import OUTPUT_DIR, SYNTHETIC_DIR, get_settings
from backend.foundry_iq.factory import get_knowledge_base
from backend.returns.excel_writer import write_filing_excel

app = FastAPI(title="TaxMind API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_LAST_EXCEL = OUTPUT_DIR / "taxmind_filing_summary.xlsx"


@app.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "mode": s.mode,
        "knowledge_backend": get_knowledge_base().name,
        "auto_submit": False,
    }


def _finalize(result: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_filing_excel(_LAST_EXCEL, result)
    result["download_url"] = "/api/download"
    return result


@app.get("/api/demo")
def demo() -> dict:
    result = run_analysis(
        SYNTHETIC_DIR / "sales_register.xlsx",
        SYNTHETIC_DIR / "purchase_register.xlsx",
        SYNTHETIC_DIR / "gstr2a.json",
    )
    return _finalize(result)


async def _save(upload: UploadFile | None, suffix: str) -> Path | None:
    if upload is None:
        return None
    tmp = Path(tempfile.mkdtemp()) / (upload.filename or f"upload{suffix}")
    tmp.write_bytes(await upload.read())
    return tmp


@app.post("/api/analyze")
async def analyze(
    sales: UploadFile | None = File(None),
    purchase: UploadFile | None = File(None),
    gstr2a: UploadFile | None = File(None),
) -> dict:
    sales_path = await _save(sales, ".xlsx") or SYNTHETIC_DIR / "sales_register.xlsx"
    purchase_path = await _save(purchase, ".xlsx") or SYNTHETIC_DIR / "purchase_register.xlsx"
    g2a_path = await _save(gstr2a, ".json") or SYNTHETIC_DIR / "gstr2a.json"
    result = run_analysis(sales_path, purchase_path, g2a_path)
    return _finalize(result)


class KBQuery(BaseModel):
    question: str


@app.post("/api/kb/query")
def kb_query(body: KBQuery) -> dict:
    result = get_knowledge_base().query(body.question)
    return result.model_dump(mode="json")


@app.get("/api/download")
def download() -> FileResponse:
    if not _LAST_EXCEL.exists():
        demo()  # generate on demand
    return FileResponse(
        _LAST_EXCEL,
        filename="taxmind_filing_summary.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
