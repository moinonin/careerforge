"""Tests for NotebookLM-style Career Corpus retrieval, domain routing, and prompt assembly."""

from __future__ import annotations

import io
import zipfile

from backend.llm.prompts import assemble_prompt, detect_target_domain
from backend.profiles.corpus import (
    build_source_entry,
    chunk_text,
    extract_source_text,
    retrieve_relevant_evidence,
)
from backend.profiles.schemas import ContactInfo, ExperienceEntry, MasterProfileData


def _make_sample_pptx(slide_texts: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for idx, text in enumerate(slide_texts, start=1):
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p>"
                "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
            )
            zf.writestr(f"ppt/slides/slide{idx}.xml", xml)
    return buf.getvalue()


def test_extract_pptx_and_markdown_sources():
    pptx_bytes = _make_sample_pptx(
        ["Ice Crystal Icing Accretion Kinetics", "Coupled DEM-CFD Validation Results"]
    )
    extracted = extract_source_text(pptx_bytes, "presentation.pptx")
    assert "Ice Crystal Icing" in extracted
    assert "DEM-CFD Validation" in extracted

    md_text = extract_source_text(b"# Project WINICE\nEutectic freeze crystallization.", "winice.md")
    assert "Eutectic freeze crystallization" in md_text


def test_chunk_and_bm25_corpus_retrieval_routes_to_matching_source():
    winice = build_source_entry(
        title="winice-project.pdf",
        text=(
            "The WINICE project modeled sub-zero eutectic freeze crystallization, "
            "heat transfer, and mechanical ice shedding for industrial wastewater salt recovery "
            "published in Chemical Engineering Journal (2017)."
        ),
        source_type="pdf",
        filename="winice-project.pdf",
    )
    ai_safety = build_source_entry(
        title="sgo-alignment.md",
        text=(
            "Developed Structural Geometry Optimization (SGO) and Outcome-Geometry Governors "
            "for RLHF alignment and PyTorch LLM training stability, preventing reward hacking."
        ),
        source_type="md",
        filename="sgo-alignment.md",
    )

    cfd_matches = retrieve_relevant_evidence(
        [winice, ai_safety],
        "Senior Process Engineer: heat transfer, eutectic freeze crystallization, wastewater",
        top_k=1,
    )
    assert len(cfd_matches) == 1
    assert cfd_matches[0]["source"] == "winice-project.pdf"

    ml_matches = retrieve_relevant_evidence(
        [winice, ai_safety],
        "AI Safety Researcher: RLHF alignment, PyTorch LLM training, prevent reward hacking",
        top_k=1,
    )
    assert len(ml_matches) == 1
    assert ml_matches[0]["source"] == "sgo-alignment.md"


def test_detect_target_domain_tracks():
    assert (
        detect_target_domain(
            "Postdoctoral Research Fellow in University Department of Engineering. "
            "PhD required, strong peer-reviewed publications and grant writing."
        )
        == "academic_research"
    )
    assert (
        detect_target_domain(
            "Senior CFD Engineer: ANSYS fluid dynamics, heat transfer, thermodynamics, aerospace."
        )
        == "physical_engineering"
    )
    assert (
        detect_target_domain(
            "ML Engineer working on PyTorch LLM training, RLHF alignment, and generative AI."
        )
        == "ai_ml"
    )
    assert (
        detect_target_domain(
            "Quantitative Software Engineer: low-latency C++ and Rust distributed systems."
        )
        == "quant_software"
    )
    assert detect_target_domain("Office Coordinator for local bakery") == "general_industry"


def test_assemble_prompt_includes_evidence_domain_translation_and_language():
    profile = MasterProfileData(
        contact=ContactInfo(full_name="Jane Doe", location="Helsinki, Finland"),
        experience=[
            ExperienceEntry(
                role="Quant Researcher",
                company="Alpha Labs",
                start_date="2021",
                end_date="Present",
                bullets=["Built real-time control loops in Python."],
            )
        ],
    )
    prompt = assemble_prompt(
        profile,
        "Postdoctoral Research Fellow in CFD and heat transfer at University. PhD required, publications.",
        output_language="fi",
        evidence_chunks=[
            {
                "source": "winice-project.pdf",
                "score": 4.2,
                "excerpt": "Modeled sub-zero ice accretion kinetics in Chemical Engineering Journal.",
            }
        ],
    )
    assert "VERIFIED EVIDENCE FROM CANDIDATE CORPUS" in prompt
    assert "winice-project.pdf" in prompt
    assert "TARGET TRACK: Academic / Postdoc / Research" in prompt
    assert "relevance_note" in prompt
    assert "Finnish (fi)" in prompt
    assert chunk_text("hello world") == ["hello world"]
