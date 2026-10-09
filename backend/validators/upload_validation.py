"""Upload validation for CV imports (T4 tightening).

Rules:
  - Extension allowlist: .pdf, .docx
  - MIME allowlist (if the client sends one)
  - Max size 10 MB
  - DOCX macro strip: reject files whose archive contains VBA parts
  - PDF header sniffing for obvious type spoofing
"""

from __future__ import annotations

import io
import zipfile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

_ALLOWED_EXTENSIONS = {"pdf", "docx"}
_ALLOWED_MIME_PREFIXES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some browsers send this for .docx
}

_DOCX_MACRO_MARKERS = (
    "vbaProject.bin",
    "word/vba",
    "activeX/",
)


def validate_cv_upload(file_bytes: bytes, filename: str, content_type: str | None) -> None:
    """Validate an uploaded CV file. Raises ValueError with a user-safe message."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '.{ext}'. Upload a PDF or DOCX.")

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 10 MB limit.")

    if content_type and not any(content_type.startswith(p) for p in _ALLOWED_MIME_PREFIXES):
        raise ValueError(f"Unexpected content type '{content_type}'.")

    if ext == "pdf":
        if not file_bytes[:5] == b"%PDF-":
            raise ValueError("The file is not a valid PDF (missing %PDF header).")

    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                names = zf.namelist()
        except zipfile.BadZipFile as exc:
            raise ValueError("The file is not a valid DOCX archive.") from exc
        lowered = [n.lower() for n in names]
        for marker in _DOCX_MACRO_MARKERS:
            if any(marker.lower() in n for n in lowered):
                raise ValueError("DOCX files with macros or ActiveX are not accepted.")
