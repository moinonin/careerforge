"""PDF Renderer — Sprint 4 Document Engine.

Converts .docx artifacts to .pdf using headless LibreOffice (soffice).
Produces pixel-perfect PDFs matching the Word rendering of the DOCX.

Spec reference: SPRINTS.md Part B.2 (PDF Generation).
"""

from __future__ import annotations

import asyncio
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.llm.docx_renderer import DocxRenderer


def find_libreoffice() -> str | None:
    """Locate the LibreOffice/soffice binary. Returns path or None."""
    candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/opt/homebrew/bin/soffice",           # macOS Homebrew ARM
        "/usr/local/bin/libreoffice",           # Linux/macOS x86
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS app bundle
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


async def convert_docx_to_pdf(docx_path: str, output_dir: str | None = None) -> str:
    """Convert a .docx file to .pdf using headless LibreOffice.

    Args:
        docx_path: Absolute or relative path to the source .docx file.
        output_dir: Directory for the output PDF. Defaults to the same
                     directory as the source .docx.

    Returns:
        Absolute path to the generated .pdf file.

    Raises:
        RuntimeError: If LibreOffice is not found or the conversion fails.
    """
    soffice = find_libreoffice()
    if soffice is None:
        raise RuntimeError(
            "LibreOffice not found. Install it to enable PDF generation. "
            "On macOS: brew install --cask libreoffice. "
            "On Linux: sudo apt install libreoffice."
        )

    docx_path = os.path.abspath(docx_path)
    if not os.path.isfile(docx_path):
        raise FileNotFoundError(f"DOCX not found: {docx_path}")

    if output_dir is None:
        output_dir = os.path.dirname(docx_path)
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")

    proc = await asyncio.create_subprocess_exec(
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        docx_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {proc.returncode}): {stderr.decode().strip()}"
        )

    if not os.path.isfile(pdf_path):
        raise RuntimeError(f"PDF was not produced at expected path: {pdf_path}")

    return pdf_path


class PDFRenderer:
    """Renders a CV or cover letter dict to a .pdf file.

    Works by first generating the .docx (via DocxRenderer)
    then converting with LibreOffice.
    """

    def __init__(self) -> None:
        self._docx_renderer: DocxRenderer | None = None

    def _get_docx_renderer(self) -> DocxRenderer:
        if self._docx_renderer is None:
            from backend.llm.docx_renderer import DocxRenderer
            self._docx_renderer = DocxRenderer()
        return self._docx_renderer

    async def render(self, data: dict, output_path: str) -> str:
        """Render data to DOCX then convert to PDF.

        Args:
            data: CV or cover letter dict (matching CV_SCHEMA or COVER_LETTER_SCHEMA).
            output_path: Desired .pdf output path (must end with .pdf).

        Returns:
            Absolute path to the .pdf file.
        """
        from backend.llm.docx_renderer import DocxRenderer

        docx_path = output_path.rsplit(".", 1)[0] + ".docx"
        os.makedirs(os.path.dirname(docx_path) or ".", exist_ok=True)

        renderer = DocxRenderer()
        renderer.render(data).save(docx_path)

        # Convert to PDF using LibreOffice
        output_dir = os.path.dirname(output_path)
        return await convert_docx_to_pdf(docx_path, output_dir)


async def await_convert(docx_path: str, output_dir: str) -> str:
    """Async wrapper for convert_docx_to_pdf (for use in async contexts)."""
    return await convert_docx_to_pdf(docx_path, output_dir)
