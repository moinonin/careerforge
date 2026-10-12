"""DOCX Renderer — Enhanced Document Engine.

Takes a validated CV/cover letter JSON and produces professional .docx files.
Uses python-docx with custom styles, proper margins, and cross-platform fonts.
Supports multiple templates: modern, classic, minimal, executive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.config import settings
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


# ════════════════════════════════════════════════════════════════════════════════
# COLOR PALETTE & FONT CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

BRAND_COLOR = RGBColor(0x25, 0x63, 0xEB)      # #2563EB - Professional blue
BRAND_COLOR_DARK = RGBColor(0x1D, 0x4E, 0xD8) # Darker shade
ACCENT_COLOR = RGBColor(0x16, 0xA3, 0x4A)     # #16A34A - Green for highlights
TEXT_COLOR = RGBColor(0x1F, 0x29, 0x37)       # #1F2937 - Dark gray (not black)
LIGHT_TEXT_COLOR = RGBColor(0x6B, 0x72, 0x80) # #6B7280 - Medium gray
DIVIDER_COLOR = RGBColor(0xD1, 0xD5, 0xDB)    # #D1D5DB - Light gray

# Cross-platform font stack
FONT_STACK = [
    "Calibri",           # Windows default
    "Liberation Sans",   # Linux (LibreOffice default)
    "DejaVu Sans",       # Cross-platform
    "Helvetica Neue",    # macOS
    "Arial",             # Universal fallback
]
FONT_NAME = ", ".join(FONT_STACK)

MONOSPACE_FONT_STACK = [
    "Consolas",
    "Liberation Mono",
    "DejaVu Sans Mono",
    "Menlo",
    "Monospace",
]
MONOSPACE_FONT = ", ".join(MONOSPACE_FONT_STACK)


# ════════════════════════════════════════════════════════════════════════════════
# TEMPLATE CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class TemplateConfig:
    """Visual configuration for a document template."""
    name: str
    primary_color: RGBColor
    secondary_color: RGBColor
    heading_font_size: int
    body_font_size: int
    name_font_size: int
    margin_inches: float
    line_spacing: float
    use_horizontal_rules: bool
    use_shaded_sections: bool
    skills_layout: str  # "inline" | "columns" | "badges"
    header_style: str   # "centered" | "left" | "split"


TEMPLATES = {
    "modern": TemplateConfig(
        name="Modern",
        primary_color=BRAND_COLOR,
        secondary_color=ACCENT_COLOR,
        heading_font_size=12,
        body_font_size=11,
        name_font_size=26,
        margin_inches=0.8,
        line_spacing=1.15,
        use_horizontal_rules=True,
        use_shaded_sections=False,
        skills_layout="badges",
        header_style="centered",
    ),
    "classic": TemplateConfig(
        name="Classic",
        primary_color=RGBColor(0x11, 0x18, 0x27),  # Near black
        secondary_color=RGBColor(0x37, 0x41, 0x51),
        heading_font_size=13,
        body_font_size=11,
        name_font_size=24,
        margin_inches=1.0,
        line_spacing=1.15,
        use_horizontal_rules=True,
        use_shaded_sections=False,
        skills_layout="inline",
        header_style="left",
    ),
    "minimal": TemplateConfig(
        name="Minimal",
        primary_color=RGBColor(0x37, 0x41, 0x51),
        secondary_color=RGBColor(0x6B, 0x72, 0x80),
        heading_font_size=11,
        body_font_size=10,
        name_font_size=22,
        margin_inches=1.2,
        line_spacing=1.2,
        use_horizontal_rules=False,
        use_shaded_sections=False,
        skills_layout="inline",
        header_style="left",
    ),
    "executive": TemplateConfig(
        name="Executive",
        primary_color=RGBColor(0x1E, 0x3A, 0x8A),  # Dark blue
        secondary_color=RGBColor(0xF5, 0x9E, 0x0B), # Gold accent
        heading_font_size=13,
        body_font_size=11,
        name_font_size=28,
        margin_inches=1.0,
        line_spacing=1.15,
        use_horizontal_rules=True,
        use_shaded_sections=True,
        skills_layout="columns",
        header_style="split",
    ),
}


DEFAULT_TEMPLATE = "modern"


# ════════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def _hex_to_rgb(hex_color: str) -> RGBColor:
    """Convert hex color string to RGBColor."""
    hex_color = hex_color.lstrip("#")
    return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _get_template(template_name: str) -> TemplateConfig:
    """Get template by name, fallback to default."""
    return TEMPLATES.get(template_name, TEMPLATES[DEFAULT_TEMPLATE])


def _set_cell_border(cell: Any, **kwargs: Any) -> None:
    """Add border to table cell."""
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


def _add_horizontal_rule(doc: Document, color: RGBColor = DIVIDER_COLOR,
                         space_before: float = 0, space_after: float = 6,
                         thickness: int = 6) -> None:
    """Insert a horizontal rule paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(thickness))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), f"{color[0]:02X}{color[1]:02X}{color[2]:02X}")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_shaded_paragraph(doc: Document, text: str, shade_color: RGBColor,
                          bold: bool = False, size: int = 11,
                          space_before: float = 4, space_after: float = 2) -> None:
    """Add a paragraph with background shading."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), f"{shade_color[0]:02X}{shade_color[1]:02X}{shade_color[2]:02X}")
    shd.set(qn("w:val"), "clear")
    pPr.append(shd)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = FONT_NAME
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _format_dates(start: str | None, end: str | None) -> str:
    """Return formatted date range."""
    if not start:
        return ""
    end_clean = (end or "").strip().lower()
    if end_clean in ("", "present", "now", "current"):
        return " – Present"
    return f" – {end}"


def _setup_document_styles(doc: Document, template: TemplateConfig) -> None:
    """Create custom paragraph and character styles."""
    styles = doc.styles

    # Normal style
    normal = styles["Normal"]
    normal.font.name = FONT_NAME
    normal.font.size = Pt(template.body_font_size)
    normal.font.color.rgb = TEXT_COLOR
    normal.paragraph_format.line_spacing = template.line_spacing
    normal.paragraph_format.space_after = Pt(2)

    # Heading 1 - Section headers
    if "CV Section" not in styles:
        h1 = styles.add_style("CV Section", WD_STYLE_TYPE.PARAGRAPH)
        h1.font.name = FONT_NAME
        h1.font.size = Pt(template.heading_font_size)
        h1.font.bold = True
        h1.font.color.rgb = template.primary_color
        h1.paragraph_format.space_before = Pt(12)
        h1.paragraph_format.space_after = Pt(6)
        h1.paragraph_format.line_spacing = 1.0

    # Heading 2 - Subsections
    if "CV Subsection" not in styles:
        h2 = styles.add_style("CV Subsection", WD_STYLE_TYPE.PARAGRAPH)
        h2.font.name = FONT_NAME
        h2.font.size = Pt(template.heading_font_size - 1)
        h2.font.bold = True
        h2.font.color.rgb = template.secondary_color
        h2.paragraph_format.space_before = Pt(8)
        h2.paragraph_format.space_after = Pt(4)
        h2.paragraph_format.line_spacing = 1.0

    # Body text
    if "CV Body" not in styles:
        body = styles.add_style("CV Body", WD_STYLE_TYPE.PARAGRAPH)
        body.font.name = FONT_NAME
        body.font.size = Pt(template.body_font_size)
        body.font.color.rgb = TEXT_COLOR
        body.paragraph_format.space_before = Pt(0)
        body.paragraph_format.space_after = Pt(2)
        body.paragraph_format.line_spacing = template.line_spacing

    # Bullet style
    if "CV Bullet" not in styles:
        bullet = styles.add_style("CV Bullet", WD_STYLE_TYPE.PARAGRAPH)
        bullet.font.name = FONT_NAME
        bullet.font.size = Pt(template.body_font_size)
        bullet.font.color.rgb = TEXT_COLOR
        bullet.paragraph_format.space_before = Pt(0)
        bullet.paragraph_format.space_after = Pt(1)
        bullet.paragraph_format.line_spacing = template.line_spacing
        bullet.paragraph_format.left_indent = Cm(0.75)
        bullet.paragraph_format.first_line_indent = Cm(-0.75)

    # Contact info
    if "CV Contact" not in styles:
        contact = styles.add_style("CV Contact", WD_STYLE_TYPE.PARAGRAPH)
        contact.font.name = FONT_NAME
        contact.font.size = Pt(10)
        contact.font.color.rgb = LIGHT_TEXT_COLOR
        contact.paragraph_format.space_before = Pt(0)
        contact.paragraph_format.space_after = Pt(0)
        contact.paragraph_format.line_spacing = 1.15

    # Name
    if "CV Name" not in styles:
        name_style = styles.add_style("CV Name", WD_STYLE_TYPE.PARAGRAPH)
        name_style.font.name = FONT_NAME
        name_style.font.size = Pt(template.name_font_size)
        name_style.font.bold = True
        name_style.font.color.rgb = template.primary_color
        name_style.paragraph_format.space_before = Pt(0)
        name_style.paragraph_format.space_after = Pt(2)
        name_style.paragraph_format.line_spacing = 1.0
        if template.header_style == "centered":
            name_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Date/Location (right-aligned meta info)
    if "CV Meta" not in styles:
        meta = styles.add_style("CV Meta", WD_STYLE_TYPE.PARAGRAPH)
        meta.font.name = FONT_NAME
        meta.font.size = Pt(template.body_font_size - 1)
        meta.font.color.rgb = LIGHT_TEXT_COLOR
        meta.font.italic = True
        meta.paragraph_format.space_before = Pt(0)
        meta.paragraph_format.space_after = Pt(1)
        meta.paragraph_format.line_spacing = 1.0
        meta.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT


# ════════════════════════════════════════════════════════════════════════════════
# DOCX RENDERER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class DocxRenderer:
    """Render a CV JSON dict to a professional .docx Document with template support."""

    def __init__(self, template: str = DEFAULT_TEMPLATE, config: Any = None) -> None:
        self.cfg = config or settings
        self.template = _get_template(template)

    def render(self, cv: dict[str, Any]) -> Document:
        """Return a python-docx ``Document`` for *cv*."""
        doc = Document()
        self._setup_page(doc)
        _setup_document_styles(doc, self.template)
        self._render_header(doc, cv)
        self._render_summary(doc, cv)
        self._render_skills(doc, cv)
        self._render_experience(doc, cv)
        self._render_education(doc, cv)
        self._render_projects(doc, cv)
        self._render_publications(doc, cv)
        self._render_certifications(doc, cv)
        self._render_languages(doc, cv)
        self._render_additional_info(doc, cv)
        return doc

    # ═══════════════════════════════════════════════════════════════════════════════
    # PAGE SETUP
    # ═══════════════════════════════════════════════════════════════════════════════

    def _setup_page(self, doc: Document) -> None:
        section = doc.sections[0]
        margin = self.template.margin_inches
        section.top_margin = Inches(margin)
        section.bottom_margin = Inches(margin)
        section.left_margin = Inches(margin)
        section.right_margin = Inches(margin)

        if self.cfg.default_docx_page_size.lower() == "a4":
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)
        else:
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)

    # ═══════════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════════

    def _render_header(self, doc: Document, cv: dict[str, Any]) -> None:
        contact = cv.get("contact", {})
        full_name = contact.get("full_name", "")
        if not full_name:
            return

        # Name
        if self.template.header_style == "centered":
            p = doc.add_paragraph(full_name, style="CV Name")
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif self.template.header_style == "split":
            # Name left, contact right
            table = doc.add_table(rows=1, cols=2)
            table.autofit = True

            # Left cell - Name
            left_cell = table.cell(0, 0)
            left_p = left_cell.paragraphs[0]
            left_run = left_p.add_run(full_name)
            left_run.bold = True
            left_run.font.size = Pt(self.template.name_font_size)
            left_run.font.name = FONT_NAME
            left_run.font.color.rgb = self.template.primary_color
            left_p.paragraph_format.space_before = Pt(0)
            left_p.paragraph_format.space_after = Pt(0)

            # Right cell - Contact
            right_cell = table.cell(0, 1)
            right_p = right_cell.paragraphs[0]
            right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            self._add_contact_line(right_p, contact)
            right_p.paragraph_format.space_before = Pt(0)
            right_p.paragraph_format.space_after = Pt(0)

            # Remove table borders
            for row in table.rows:
                for cell in row.cells:
                    _set_cell_border(cell, top={"val": "none"}, bottom={"val": "none"},
                                     left={"val": "none"}, right={"val": "none"})

            doc.add_paragraph()  # spacer
        else:
            # Left-aligned (default)
            p = doc.add_paragraph(full_name, style="CV Name")
            # Contact line
            self._add_contact_line(doc.add_paragraph(style="CV Contact"), contact)

        # Horizontal rule under header
        if self.template.use_horizontal_rules:
            _add_horizontal_rule(doc, color=self.template.primary_color,
                                 space_before=2, space_after=10, thickness=12)

    def _add_contact_line(self, paragraph: Any, contact: dict) -> None:
        """Add formatted contact info to a paragraph."""
        parts = []
        if contact.get("location"):
            parts.append(contact["location"])
        if contact.get("phone"):
            parts.append(contact["phone"])
        if contact.get("email"):
            parts.append(contact["email"])
        if contact.get("linkedin"):
            parts.append(contact["linkedin"])
        if contact.get("website_portfolio"):
            parts.append(contact["website_portfolio"])

        if parts:
            run = paragraph.add_run("  |  ".join(parts))
            run.font.size = Pt(10)
            run.font.name = FONT_NAME
            run.font.color.rgb = LIGHT_TEXT_COLOR

    # ═══════════════════════════════════════════════════════════════════════════════
    # SECTION RENDERERS
    # ═══════════════════════════════════════════════════════════════════════════════

    def _render_summary(self, doc: Document, cv: dict[str, Any]) -> None:
        summary = cv.get("summary", "")
        if not summary:
            return
        doc.add_paragraph("Professional Summary", style="CV Section")
        doc.add_paragraph(summary, style="CV Body")

    def _render_skills(self, doc: Document, cv: dict[str, Any]) -> None:
        skills = cv.get("skills", {})
        skill_groups = [
            ("technical", "Technical Skills"),
            ("domain", "Domain Knowledge"),
            ("tools", "Tools & Technologies"),
            ("soft", "Soft Skills"),
        ]
        has_any = any(skills.get(g, []) for g, _ in skill_groups)
        if not has_any:
            return

        doc.add_paragraph("Core Competencies", style="CV Section")

        if self.template.skills_layout == "badges":
            # Badge-style skills in a table
            for group_key, label in skill_groups:
                items = skills.get(group_key, [])
                if not items:
                    continue

                p = doc.add_paragraph()
                run = p.add_run(f"{label}: ")
                run.bold = True
                run.font.size = Pt(self.template.body_font_size)
                run.font.name = FONT_NAME
                run.font.color.rgb = self.template.primary_color

                # Add each skill as a "badge" run
                for i, item in enumerate(items):
                    badge_run = p.add_run(f" {item} ")
                    badge_run.font.size = Pt(9)
                    badge_run.font.name = FONT_NAME
                    badge_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    # Add shading via XML
                    rPr = badge_run._r.get_or_add_rPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:fill"), f"{self.template.primary_color[0]:02X}"
                                     f"{self.template.primary_color[1]:02X}"
                                     f"{self.template.primary_color[2]:02X}")
                    shd.set(qn("w:val"), "clear")
                    rPr.append(shd)
                    if i < len(items) - 1:
                        sep = p.add_run(" ")
                        sep.font.size = Pt(6)

        elif self.template.skills_layout == "columns":
            # Two-column table layout
            table = doc.add_table(rows=0, cols=2)
            table.autofit = True
            for group_key, label in skill_groups:
                items = skills.get(group_key, [])
                if not items:
                    continue
                row = table.add_row()
                label_cell = row.cells[0]
                label_p = label_cell.paragraphs[0]
                label_run = label_p.add_run(label)
                label_run.bold = True
                label_run.font.size = Pt(self.template.body_font_size)
                label_run.font.name = FONT_NAME
                label_run.font.color.rgb = self.template.primary_color

                items_cell = row.cells[1]
                items_p = items_cell.paragraphs[0]
                items_run = items_p.add_run(", ".join(items))
                items_run.font.size = Pt(self.template.body_font_size)
                items_run.font.name = FONT_NAME
                items_run.font.color.rgb = TEXT_COLOR

            # Remove borders
            for row in table.rows:
                for cell in row.cells:
                    _set_cell_border(cell, top={"val": "none"}, bottom={"val": "none"},
                                     left={"val": "none"}, right={"val": "none"})

        else:
            # Inline (default)
            for group_key, label in skill_groups:
                items = skills.get(group_key, [])
                if not items:
                    continue
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(1)
                run_label = p.add_run(f"{label}: ")
                run_label.bold = True
                run_label.font.size = Pt(self.template.body_font_size)
                run_label.font.name = FONT_NAME
                run_label.font.color.rgb = self.template.primary_color
                run_items = p.add_run(", ".join(items))
                run_items.font.size = Pt(self.template.body_font_size)
                run_items.font.name = FONT_NAME
                run_items.font.color.rgb = TEXT_COLOR

    def _render_experience(self, doc: Document, cv: dict[str, Any]) -> None:
        experience = cv.get("experience", [])
        if not experience:
            return
        doc.add_paragraph("Professional Experience", style="CV Section")

        for exp in experience:
            role = exp.get("role", "")
            company = exp.get("company", "")
            if not role and not company:
                continue

            # Role + Company line
            parts = []
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
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run("  ".join(parts))
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = Pt(self.template.body_font_size)
            run.font.color.rgb = self.template.primary_color

            # Relevance note
            relevance = exp.get("relevance_note", "")
            if relevance:
                p_rel = doc.add_paragraph()
                p_rel.paragraph_format.space_before = Pt(0)
                p_rel.paragraph_format.space_after = Pt(2)
                p_rel.paragraph_format.left_indent = Cm(0.5)
                run = p_rel.add_run(f"Relevance: {relevance}")
                run.italic = True
                run.font.size = Pt(self.template.body_font_size - 1)
                run.font.name = FONT_NAME
                run.font.color.rgb = LIGHT_TEXT_COLOR

            # Bullets
            for b in exp.get("bullets", []):
                if b:
                    p_bullet = doc.add_paragraph(b, style="CV Bullet")
                    # Add custom bullet character
                    p_bullet.paragraph_format.first_line_indent = Cm(-0.75)

    def _render_education(self, doc: Document, cv: dict[str, Any]) -> None:
        education = cv.get("education", [])
        if not education:
            return
        doc.add_paragraph("Education", style="CV Section")

        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            if not degree and not institution:
                continue

            parts = []
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
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run("  ".join(parts))
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = Pt(self.template.body_font_size)
            run.font.color.rgb = self.template.primary_color

            thesis = edu.get("thesis", "")
            if thesis:
                p_thesis = doc.add_paragraph()
                p_thesis.paragraph_format.space_before = Pt(0)
                p_thesis.paragraph_format.space_after = Pt(2)
                p_thesis.paragraph_format.left_indent = Cm(0.5)
                run = p_thesis.add_run(f"Thesis: {thesis}")
                run.italic = True
                run.font.size = Pt(self.template.body_font_size - 1)
                run.font.name = FONT_NAME
                run.font.color.rgb = LIGHT_TEXT_COLOR

            for d in edu.get("details", []):
                if d:
                    p_detail = doc.add_paragraph()
                    p_detail.paragraph_format.space_before = Pt(0)
                    p_detail.paragraph_format.space_after = Pt(1)
                    p_detail.paragraph_format.left_indent = Cm(0.5)
                    run = p_detail.add_run(f"• {d}")
                    run.font.size = Pt(self.template.body_font_size)
                    run.font.name = FONT_NAME
                    run.font.color.rgb = TEXT_COLOR

    def _render_projects(self, doc: Document, cv: dict[str, Any]) -> None:
        projects = cv.get("projects", [])
        if not projects:
            return
        doc.add_paragraph("Projects", style="CV Section")

        for proj in projects:
            name = proj.get("name", "")
            if not name:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(name)
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = Pt(self.template.body_font_size)
            run.font.color.rgb = self.template.primary_color

            desc = proj.get("description", "")
            if desc:
                doc.add_paragraph(desc, style="CV Body")

            tech = proj.get("tech_stack", [])
            if tech:
                p_tech = doc.add_paragraph()
                p_tech.paragraph_format.space_before = Pt(0)
                p_tech.paragraph_format.space_after = Pt(2)
                run = p_tech.add_run("Tech: ")
                run.bold = True
                run.font.size = Pt(self.template.body_font_size - 1)
                run.font.name = FONT_NAME
                run.font.color.rgb = self.template.secondary_color
                run2 = p_tech.add_run(", ".join(tech))
                run2.font.size = Pt(self.template.body_font_size - 1)
                run2.font.name = FONT_NAME
                run2.font.color.rgb = TEXT_COLOR

            link = proj.get("link", "")
            if link:
                p_link = doc.add_paragraph()
                p_link.paragraph_format.space_before = Pt(0)
                p_link.paragraph_format.space_after = Pt(2)
                run = p_link.add_run("Link: ")
                run.bold = True
                run.font.size = Pt(self.template.body_font_size - 1)
                run.font.name = FONT_NAME
                run2 = p_link.add_run(link)
                run2.font.size = Pt(self.template.body_font_size - 1)
                run2.font.name = MONOSPACE_FONT
                run2.font.color.rgb = BRAND_COLOR

    def _render_publications(self, doc: Document, cv: dict[str, Any]) -> None:
        publications = cv.get("publications", [])
        if not publications:
            return
        doc.add_paragraph("Publications", style="CV Section")
        for pub in publications:
            citation = pub.get("citation", "")
            if not citation:
                continue
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(citation)
            run.font.name = FONT_NAME
            run.font.size = Pt(self.template.body_font_size)
            run.font.color.rgb = TEXT_COLOR

    def _render_certifications(self, doc: Document, cv: dict[str, Any]) -> None:
        certifications = cv.get("certifications", [])
        if not certifications:
            return
        doc.add_paragraph("Certifications", style="CV Section")
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
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run("  ".join(parts))
            run.font.name = FONT_NAME
            run.font.size = Pt(self.template.body_font_size)
            run.font.color.rgb = TEXT_COLOR

    def _render_languages(self, doc: Document, cv: dict[str, Any]) -> None:
        languages = cv.get("languages", [])
        if not languages:
            return
        doc.add_paragraph("Languages", style="CV Section")
        for lang in languages:
            language = lang.get("language", "")
            proficiency = lang.get("proficiency", "")
            if language:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                run = p.add_run(f"{language}")
                run.bold = True
                run.font.name = FONT_NAME
                run.font.size = Pt(self.template.body_font_size)
                run.font.color.rgb = TEXT_COLOR
                if proficiency:
                    run2 = p.add_run(f" — {proficiency}")
                    run2.font.name = FONT_NAME
                    run2.font.size = Pt(self.template.body_font_size)
                    run2.font.color.rgb = LIGHT_TEXT_COLOR

    def _render_additional_info(self, doc: Document, cv: dict[str, Any]) -> None:
        addl = cv.get("additional_info", "")
        if not addl:
            return
        doc.add_paragraph("Additional Information", style="CV Section")
        doc.add_paragraph(addl, style="CV Body")


# ════════════════════════════════════════════════════════════════════════════════
# COVER LETTER RENDERER
# ════════════════════════════════════════════════════════════════════════════════

class CoverLetterDocxRenderer:
    """Render a cover letter JSON dict to a professional .docx Document."""

    def __init__(self, template: str = DEFAULT_TEMPLATE, config: Any = None) -> None:
        self.cfg = config or settings
        self.template = _get_template(template)

    def render(self, cl: dict[str, Any]) -> Document:
        doc = Document()
        self._setup_page(doc)
        _setup_document_styles(doc, self.template)
        self._render_header(doc, cl)
        self._render_date_and_recipient(doc, cl)
        self._render_salutation(doc, cl)
        self._render_opening(doc, cl)
        self._render_body(doc, cl)
        self._render_call_to_action(doc, cl)
        self._render_closing(doc, cl)
        return doc

    def _setup_page(self, doc: Document) -> None:
        section = doc.sections[0]
        margin = self.template.margin_inches
        section.top_margin = Inches(margin)
        section.bottom_margin = Inches(margin)
        section.left_margin = Inches(margin)
        section.right_margin = Inches(margin)
        if self.cfg.default_docx_page_size.lower() == "a4":
            section.page_width = Inches(8.27)
            section.page_height = Inches(11.69)
        else:
            section.page_width = Inches(8.5)
            section.page_height = Inches(11.0)

    def _render_header(self, doc: Document, cl: dict[str, Any]) -> None:
        """Render sender info (from header field)."""
        header = cl.get("header", "")
        if header:
            lines = header.strip().split("\n")
            for i, line in enumerate(lines):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0 if i == 0 else 0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(line)
                run.font.name = FONT_NAME
                run.font.size = Pt(10)
                run.font.color.rgb = TEXT_COLOR
                if i == 0:
                    run.bold = True
            doc.add_paragraph()  # spacer

    def _render_date_and_recipient(self, doc: Document, cl: dict[str, Any]) -> None:
        """Add date and recipient address block."""
        from datetime import date
        today = date.today().strftime("%B %d, %Y")

        # Date
        p = doc.add_paragraph(today)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        run = p.runs[0] if p.runs else p.add_run(today)
        run.font.name = FONT_NAME
        run.font.size = Pt(11)
        run.font.color.rgb = TEXT_COLOR

        # Recipient (from header if it contains company info)
        header = cl.get("header", "")
        if "company" in header.lower() or "hiring" in header.lower():
            lines = header.split("\n")[1:]  # Skip sender name
            for line in lines:
                if line.strip():
                    p = doc.add_paragraph(line.strip())
                    p.paragraph_format.space_before = Pt(0)
                    p.paragraph_format.space_after = Pt(0)
                    run = p.runs[0] if p.runs else p.add_run(line.strip())
                    run.font.name = FONT_NAME
                    run.font.size = Pt(11)
                    run.font.color.rgb = TEXT_COLOR

        doc.add_paragraph()  # spacer

    def _render_salutation(self, doc: Document, cl: dict[str, Any]) -> None:
        salutation = cl.get("salutation", "Dear Hiring Manager,")
        p = doc.add_paragraph(salutation)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        run = p.runs[0] if p.runs else p.add_run(salutation)
        run.font.name = FONT_NAME
        run.font.size = Pt(11)
        run.font.color.rgb = TEXT_COLOR

    def _render_opening(self, doc: Document, cl: dict[str, Any]) -> None:
        opening = cl.get("opening", "")
        if opening:
            p = doc.add_paragraph(opening)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.line_spacing = 1.15
            run = p.runs[0] if p.runs else p.add_run(opening)
            run.font.name = FONT_NAME
            run.font.size = Pt(11)
            run.font.color.rgb = TEXT_COLOR

    def _render_body(self, doc: Document, cl: dict[str, Any]) -> None:
        for i, para in enumerate(cl.get("body_paragraphs", [])):
            if para:
                p = doc.add_paragraph(para)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.line_spacing = 1.15
                run = p.runs[0] if p.runs else p.add_run(para)
                run.font.name = FONT_NAME
                run.font.size = Pt(11)
                run.font.color.rgb = TEXT_COLOR

    def _render_call_to_action(self, doc: Document, cl: dict[str, Any]) -> None:
        cta = cl.get("call_to_action", "")
        if cta:
            p = doc.add_paragraph(cta)
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(12)
            p.paragraph_format.line_spacing = 1.15
            run = p.runs[0] if p.runs else p.add_run(cta)
            run.font.name = FONT_NAME
            run.font.size = Pt(11)
            run.font.bold = True
            run.font.color.rgb = BRAND_COLOR

    def _render_closing(self, doc: Document, cl: dict[str, Any]) -> None:
        closing = cl.get("closing", "Sincerely,")
        p = doc.add_paragraph(closing)
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        run = p.runs[0] if p.runs else p.add_run(closing)
        run.font.name = FONT_NAME
        run.font.size = Pt(11)
        run.font.color.rgb = TEXT_COLOR

        signature = cl.get("signature", "")
        if signature:
            p_sig = doc.add_paragraph()
            p_sig.paragraph_format.space_before = Pt(18)
            p_sig.paragraph_format.space_after = Pt(0)
            run = p_sig.add_run(signature)
            run.bold = True
            run.font.name = FONT_NAME
            run.font.size = Pt(11)
            run.font.color.rgb = TEXT_COLOR


# ════════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════════

def create_cv_renderer(template: str = DEFAULT_TEMPLATE, config: Any = None) -> DocxRenderer:
    """Factory for CV renderer."""
    return DocxRenderer(template=template, config=config)


def create_cover_letter_renderer(template: str = DEFAULT_TEMPLATE, config: Any = None) -> CoverLetterDocxRenderer:
    """Factory for cover letter renderer."""
    return CoverLetterDocxRenderer(template=template, config=config)


def get_available_templates() -> dict[str, str]:
    """Return available template names and descriptions."""
    return {name: tpl.name for name, tpl in TEMPLATES.items()}