"""DOCX Renderer — Sprint 4 Document Engine.

Takes a validated CV JSON (dict matching CV_SCHEMA / CVOutput) and produces an
ATS-compliant .docx file.  Uses python-docx with real styles, proper margins,
and single-column layout per the Sprint 4 spec.

Spec reference: SPRINTS.md Part A.2 Section 8 + Sprint 4 task list.
"""

from __future__ import annotations

from typing import Any

from backend.config import settings
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

# ── Helper utilities ────────────────────────────────────────────────────────────

def _set_cell_border(cell: Any, **kwargs: Any) -> None:
    """Add a bottom border to a table cell (used for the name/contact divider)."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge, attrs in kwargs.items():
        element = OxmlElement(f"w:{edge}")
        for key, val in attrs.items():
            element.set(qn(f"w:{key}"), str(val))
        tcBorders.append(element)
    tcProperties = tcPr.find(qn("w:tcBorders"))
    if tcProperties is not None:
        tcPr.remove(tcProperties)
    tcPr.append(tcBorders)


def _add_horizontal_rule(doc: Document, space_before: float = 0, space_after: float = 6) -> None:
    """Insert a thin horizontal rule paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")       # 0.75pt
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def _heading(doc: Document, text: str, level: int = 1) -> None:
    """Add a section heading paragraph.

    Uses bold + slightly larger font (not the built-in heading styles, which
    carry numbering in some templates).  ATS-safe: single-column, no tables.
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(12)
    run.font.name = settings.default_docx_font
    if level > 1:
        run.font.size = Pt(11)


def _body(doc: Document, text: str, bold: bool = False, italic: bool = False,
          size: int | None = None, indent: float = 0) -> None:
    """Add a body paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.line_spacing = settings.default_docx_line_spacing
    run = p.add_run(text)
    run.font.name = settings.default_docx_font
    run.font.size = Pt(size or settings.default_docx_font_size)
    run.bold = bold
    run.italic = italic
    return p


def _bullet(doc: Document, text: str) -> None:
    """Add a bullet point paragraph (List Bullet style)."""
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = settings.default_docx_line_spacing
    # Clear auto-style font then set our own
    for run in p.runs:
        run.font.name = settings.default_docx_font
        run.font.size = Pt(settings.default_docx_font_size)
    if not p.runs:
        run = p.add_run(text)
        run.font.name = settings.default_docx_font
        run.font.size = Pt(settings.default_docx_font_size)
    else:
        p.runs[0].text = text
        p.runs[0].font.name = settings.default_docx_font
        p.runs[0].font.size = Pt(settings.default_docx_font_size)
    return p


def _format_dates(start: str | None, end: str | None) -> str:
    """Return 'MMM YYYY – MMM YYYY' or 'MMM YYYY – Present' or ''."""
    if not start:
        return ""
    end_clean = (end or "").strip().lower()
    if end_clean in ("", "present", "now", "current"):
        return " – Present"
    return f" – {end}"


# ── CV Renderer ────────────────────────────────────────────────────────────────

class DocxRenderer:
    """Render a CV JSON dict to an ATS-compliant .docx Document.

    Usage::

        renderer = DocxRenderer()
        doc = renderer.render(cv_dict)
        doc.save("/path/to/output.docx")
    """

    def __init__(self, config: Any = None) -> None:
        self.cfg = config or settings

    def render(self, cv: dict[str, Any]) -> Document:
        """Return a python-docx ``Document`` for *cv*."""
        doc = Document()
        self._setup_page(doc)
        self._render_header(doc, cv)
        self._render_summary(doc, cv)
        self._render_skills(doc, cv)
        self._render_experience(doc, cv)
        self._render_education(doc, cv)
        self._render_publications(doc, cv)
        self._render_certifications(doc, cv)
        self._render_languages(doc, cv)
        self._render_projects(doc, cv)
        self._render_additional_info(doc, cv)
        return doc

    # ── page setup ────────────────────────────────────────────────────────────

    def _setup_page(self, doc: Document) -> None:
        section = doc.sections[0]
        section.top_margin = Inches(self.cfg.default_docx_margin_inches)
        section.bottom_margin = Inches(self.cfg.default_docx_margin_inches)
        section.left_margin = Inches(self.cfg.default_docx_margin_inches)
        section.right_margin = Inches(self.cfg.default_docx_margin_inches)

        # Page size
        if self.cfg.default_docx_page_size.lower() == "a4":
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)
        else:
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)

        # Default style
        style = doc.styles["Normal"]
        style.font.name = self.cfg.default_docx_font
        style.font.size = Pt(self.cfg.default_docx_font_size)
        style.paragraph_format.line_spacing = self.cfg.default_docx_line_spacing

    # ── header: name + contact ────────────────────────────────────────────────

    def _render_header(self, doc: Document, cv: dict[str, Any]) -> None:
        contact = cv.get("contact", {})
        full_name = contact.get("full_name", "")
        if not full_name:
            return

        # Name — large bold
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(full_name)
        run.bold = True
        run.font.size = Pt(self.cfg.default_docx_name_font_size)
        run.font.name = self.cfg.default_docx_font

        # Contact line — smaller
        contact_parts: list[str] = []
        if contact.get("location"):
            contact_parts.append(contact["location"])
        if contact.get("phone"):
            contact_parts.append(contact["phone"])
        if contact.get("email"):
            contact_parts.append(contact["email"])
        if contact.get("linkedin"):
            contact_parts.append(contact["linkedin"])
        if contact.get("website_portfolio"):
            contact_parts.append(contact["website_portfolio"])

        if contact_parts:
            p2 = doc.add_paragraph()
            p2.paragraph_format.space_before = Pt(0)
            p2.paragraph_format.space_after = Pt(4)
            run2 = p2.add_run("  |  ".join(contact_parts))
            run2.font.size = Pt(10)
            run2.font.name = self.cfg.default_docx_font

        _add_horizontal_rule(doc, space_before=0, space_after=8)

    # ── sections ──────────────────────────────────────────────────────────────

    def _render_summary(self, doc: Document, cv: dict[str, Any]) -> None:
        summary = cv.get("summary", "")
        if not summary:
            return
        _heading(doc, "Professional Summary")
        _body(doc, summary)

    def _render_skills(self, doc: Document, cv: dict[str, Any]) -> None:
        skills = cv.get("skills", {})
        # Check if any skill group has items — skip the section if all are empty
        has_any = any(skills.get(g, []) for g in ("technical", "domain", "tools", "soft"))
        if not has_any:
            return
        _heading(doc, "Core Competencies")
        for group_key, label in [
            ("technical", "Technical Skills"),
            ("domain", "Domain Knowledge"),
            ("tools", "Tools"),
            ("soft", "Soft Skills"),
        ]:
            items = skills.get(group_key, [])
            if not items:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1)
            run_label = p.add_run(f"{label}: ")
            run_label.bold = True
            run_label.font.name = self.cfg.default_docx_font
            run_label.font.size = Pt(self.cfg.default_docx_font_size)
            run_items = p.add_run(", ".join(items))
            run_items.font.name = self.cfg.default_docx_font
            run_items.font.size = Pt(self.cfg.default_docx_font_size)

    def _render_experience(self, doc: Document, cv: dict[str, Any]) -> None:
        experience = cv.get("experience", [])
        if not experience:
            return
        _heading(doc, "Professional Experience")
        for exp in experience:
            role = exp.get("role", "")
            company = exp.get("company", "")
            if not role and not company:
                continue

            # Role + Company + Location + Dates — single line
            parts: list[str] = []
            if role:
                parts.append(role)
            if company:
                parts.append(f"at {company}")
            loc = exp.get("location")
            if loc:
                parts.append(loc)
            dates = _format_dates(exp.get("start_date"), exp.get("end_date"))
            if dates:
                parts.append(dates.strip())

            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run("  ".join(parts))
            run.bold = True
            run.font.name = self.cfg.default_docx_font
            run.font.size = Pt(self.cfg.default_docx_font_size)

            # Relevance note (italic, indented)
            relevance = exp.get("relevance_note", "")
            if relevance:
                _body(doc, f"Relevance to target role: {relevance}",
                      italic=True, indent=0.25)

            # Bullets
            for b in exp.get("bullets", []):
                if b:
                    _bullet(doc, b)

    def _render_education(self, doc: Document, cv: dict[str, Any]) -> None:
        education = cv.get("education", [])
        if not education:
            return
        _heading(doc, "Education")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            if not degree and not institution:
                continue

            parts: list[str] = []
            if degree:
                parts.append(degree)
            if institution:
                parts.append(f"at {institution}")
            loc = edu.get("location")
            if loc:
                parts.append(loc)
            dates = _format_dates(edu.get("start_date"), edu.get("end_date"))
            if dates:
                parts.append(dates.strip())

            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run("  ".join(parts))
            run.bold = True
            run.font.name = self.cfg.default_docx_font
            run.font.size = Pt(self.cfg.default_docx_font_size)

            thesis = edu.get("thesis", "")
            if thesis:
                _body(doc, thesis, italic=True, indent=0.25)

    def _render_publications(self, doc: Document, cv: dict[str, Any]) -> None:
        publications = cv.get("publications", [])
        if not publications:
            return
        _heading(doc, "Publications")
        for pub in publications:
            citation = pub.get("citation", "")
            if not citation:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(citation)
            run.font.name = self.cfg.default_docx_font
            run.font.size = Pt(self.cfg.default_docx_font_size)

    def _render_certifications(self, doc: Document, cv: dict[str, Any]) -> None:
        certifications = cv.get("certifications", [])
        if not certifications:
            return
        _heading(doc, "Certifications")
        for cert in certifications:
            name = cert.get("name", "")
            if not name:
                continue
            issuer = cert.get("issuer", "")
            year = cert.get("year")
            parts = [name]
            if issuer:
                parts.append(f" — {issuer}")
            if year:
                parts.append(f" ({year})")
            _body(doc, "  ".join(parts))

    def _render_languages(self, doc: Document, cv: dict[str, Any]) -> None:
        languages = cv.get("languages", [])
        if not languages:
            return
        _heading(doc, "Languages")
        for lang in languages:
            language = lang.get("language", "")
            proficiency = lang.get("proficiency", "")
            if language:
                _body(doc, f"{language}: {proficiency}")

    def _render_projects(self, doc: Document, cv: dict[str, Any]) -> None:
        projects = cv.get("projects", [])
        if not projects:
            return
        _heading(doc, "Projects")
        for proj in projects:
            name = proj.get("name", "")
            if not name:
                continue
            _body(doc, name, bold=True)
            desc = proj.get("description", "")
            if desc:
                _body(doc, desc)
            tech = proj.get("tech_stack", [])
            if tech:
                _body(doc, "Tech: " + ", ".join(tech))
            link = proj.get("link", "")
            if link:
                _body(doc, f"Link: {link}")

    def _render_additional_info(self, doc: Document, cv: dict[str, Any]) -> None:
        addl = cv.get("additional_info", "")
        if not addl:
            return
        _heading(doc, "Additional Information")
        _body(doc, addl)


# ── Cover Letter Renderer ───────────────────────────────────────────────────────

class CoverLetterDocxRenderer:
    """Render a cover letter JSON dict to a .docx Document."""

    def __init__(self, config: Any = None) -> None:
        self.cfg = config or settings

    def render(self, cl: dict[str, Any]) -> Document:
        doc = Document()
        self._setup_page(doc)
        self._render_header(doc, cl)
        self._render_salutation(doc, cl)
        self._render_opening(doc, cl)
        self._render_body(doc, cl)
        self._render_call_to_action(doc, cl)
        self._render_closing(doc, cl)
        return doc

    def _setup_page(self, doc: Document) -> None:
        section = doc.sections[0]
        section.top_margin = Inches(self.cfg.default_docx_margin_inches)
        section.bottom_margin = Inches(self.cfg.default_docx_margin_inches)
        section.left_margin = Inches(self.cfg.default_docx_margin_inches)
        section.right_margin = Inches(self.cfg.default_docx_margin_inches)
        if self.cfg.default_docx_page_size.lower() == "a4":
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)
        else:
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)
        style = doc.styles["Normal"]
        style.font.name = self.cfg.default_docx_font
        style.font.size = Pt(self.cfg.default_docx_font_size)
        style.paragraph_format.line_spacing = self.cfg.default_docx_line_spacing

    def _render_header(self, doc: Document, cl: dict[str, Any]) -> None:
        header = cl.get("header", "")
        if header:
            _body(doc, header)

    def _render_salutation(self, doc: Document, cl: dict[str, Any]) -> None:
        salutation = cl.get("salutation", "")
        if salutation:
            _body(doc, salutation)

    def _render_opening(self, doc: Document, cl: dict[str, Any]) -> None:
        opening = cl.get("opening", "")
        if opening:
            _body(doc, opening)

    def _render_body(self, doc: Document, cl: dict[str, Any]) -> None:
        for para in cl.get("body_paragraphs", []):
            if para:
                _body(doc, para)

    def _render_call_to_action(self, doc: Document, cl: dict[str, Any]) -> None:
        cta = cl.get("call_to_action", "")
        if cta:
            _body(doc, cta)

    def _render_closing(self, doc: Document, cl: dict[str, Any]) -> None:
        closing = cl.get("closing", "")
        if closing:
            _body(doc, closing)
        signature = cl.get("signature", "")
        if signature:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            run = p.add_run(signature)
            run.bold = True
            run.font.name = self.cfg.default_docx_font
            run.font.size = Pt(self.cfg.default_docx_font_size)
