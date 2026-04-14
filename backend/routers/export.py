"""
Export Router
=============
Endpoints for exporting scripts to Fountain, PDF (via HTML), and FDX.
Uses screenplain for real format conversion.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

# Ensure services are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.fountain_export import fountain_to_fdx, fountain_to_html, fountain_to_pdf_html

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    title: str = Field(default="Untitled", description="Script title")
    author: str = Field(default="", description="Script author")
    content: str = Field(..., description="Fountain-formatted script content")


def _content_disposition(filename: str) -> str:
    """RFC 6266 Content-Disposition with UTF-8 filename support."""
    encoded = quote(filename)
    return f"attachment; filename*=UTF-8''{encoded}"


@router.post("/fountain")
async def export_fountain(req: ExportRequest):
    """Export script as Fountain plain-text."""
    # Prepend title page metadata
    header = f"Title: {req.title}\nAuthor: {req.author}\nDraft date: auto\n\n===\n\n"
    fountain_text = header + req.content
    return PlainTextResponse(
        content=fountain_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(f"{req.title}.fountain")},
    )


@router.post("/pdf")
async def export_pdf(req: ExportRequest):
    """Export script as print-ready HTML (open in browser and print to PDF)."""
    html = fountain_to_pdf_html(req.content, title=req.title, author=req.author)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": _content_disposition(f"{req.title}.html")},
    )


@router.post("/fdx")
async def export_fdx(req: ExportRequest):
    """Export script as Final Draft XML (.fdx)."""
    fdx_xml = fountain_to_fdx(req.content)
    return Response(
        content=fdx_xml.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": _content_disposition(f"{req.title}.fdx")},
    )
