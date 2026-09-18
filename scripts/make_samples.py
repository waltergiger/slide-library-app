"""Generates a small sample library so you can try the app immediately,
before pointing it at your real file share. Run once:

    python scripts/make_samples.py

Creates ./sample-library/<Domain>/*.pptx (and one .pdf) with a handful of
slides each — title text, bullets, a table, and a picture — so indexing,
thumbnails, search and export all have something real to chew on.
"""
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "sample-library"


def _placeholder_image(path: Path, text: str, color: str):
    img = Image.new("RGB", (640, 360), color)
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 620, 340], outline="white", width=3)
    d.text((40, 160), text, fill="white")
    img.save(path)


def _add_title_slide(prs, title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = subtitle


def _add_bullets_slide(prs, title, bullets):
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.text = bullets[0]
    for b in bullets[1:]:
        p = body.add_paragraph()
        p.text = b
        p.level = 0


def _add_table_slide(prs, title, headers, rows):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    rows_n, cols_n = len(rows) + 1, len(headers)
    table = slide.shapes.add_table(rows_n, cols_n, Inches(0.6), Inches(1.6), Inches(9), Inches(0.4 * rows_n)).table
    for c, h in enumerate(headers):
        table.cell(0, c).text = h
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            table.cell(r, c).text = str(val)


def _add_picture_slide(prs, title, image_path):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    slide.shapes.add_picture(str(image_path), Inches(1.5), Inches(1.6), width=Inches(7))


def build_strategy_deck(out_dir: Path, assets: Path):
    prs = Presentation()
    _add_title_slide(prs, "2027 Digital Wealth Strategy", "Enterprise Architecture & IT Strategy")
    _add_bullets_slide(prs, "Executive Summary", [
        "Consolidate client platforms onto a single digital core",
        "Cut integration lead time from 9 weeks to under 2",
        "Fund the shift by retiring three legacy portals",
    ])
    _add_bullets_slide(prs, "Market Backdrop", [
        "Client expectations set by consumer fintech, not private banking peers",
        "Regulatory reporting demands are rising across all booking centers",
        "Talent for legacy platforms is shrinking year over year",
    ])
    _add_table_slide(prs, "Investment by Workstream", ["Workstream", "2026", "2027"],
                      [["Digital core", "4.2M", "6.8M"], ["Data platform", "2.1M", "3.4M"], ["Client onboarding", "1.6M", "2.0M"]])
    _add_picture_slide(prs, "Target Operating Model", assets / "diagram.png")
    prs.save(out_dir / "2027 Digital Wealth Strategy.pptx")


def build_architecture_deck(out_dir: Path, assets: Path):
    prs = Presentation()
    _add_title_slide(prs, "Target State Architecture v3", "Architecture Review Board")
    _add_bullets_slide(prs, "Key Design Principles", [
        "API-first: every capability exposed as a governed service",
        "Domain-driven boundaries aligned to business capabilities",
        "Buy for commodity, build for differentiation",
    ])
    _add_picture_slide(prs, "Integration Layer", assets / "diagram2.png")
    _add_table_slide(prs, "Migration Roadmap", ["Phase", "Scope", "Target"],
                      [["1", "Client data platform", "Q1 2027"], ["2", "Core banking API layer", "Q3 2027"], ["3", "Legacy decommission", "Q1 2028"]])
    _add_bullets_slide(prs, "Open Questions", [
        "Vendor lock-in risk on the new data platform",
        "Sequencing against the core banking upgrade",
    ])
    prs.save(out_dir / "Target State Architecture v3.pptx")


def build_projects_deck(out_dir: Path):
    prs = Presentation()
    _add_title_slide(prs, "Project Atlas — Kickoff", "Client Onboarding Revamp")
    _add_bullets_slide(prs, "Objectives", [
        "Cut onboarding time from 12 days to 3",
        "Single case file across relationship manager and compliance",
        "Straight-through processing for standard KYC cases",
    ])
    _add_table_slide(prs, "Milestones", ["Milestone", "Owner", "Date"],
                      [["Design sign-off", "Walter", "Oct 2026"], ["Pilot branch live", "Ops", "Jan 2027"], ["Full rollout", "Ops", "Apr 2027"]])
    prs.save(out_dir / "Project Atlas – Kickoff.pptx")


def convert_one_to_pdf(pptx_path: Path, out_dir: Path):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
                    check=True, capture_output=True)


def main():
    (LIB / "Strategy").mkdir(parents=True, exist_ok=True)
    (LIB / "Architecture").mkdir(parents=True, exist_ok=True)
    (LIB / "Projects").mkdir(parents=True, exist_ok=True)

    assets = LIB / "_assets"
    assets.mkdir(exist_ok=True)
    _placeholder_image(assets / "diagram.png", "Target Operating Model", "#2B3A55")
    _placeholder_image(assets / "diagram2.png", "Integration Layer", "#1F5C52")

    build_strategy_deck(LIB / "Strategy", assets)
    build_architecture_deck(LIB / "Architecture", assets)
    build_projects_deck(LIB / "Projects")

    # One PDF-sourced example, per the "PDF slides come in as images" behavior.
    convert_one_to_pdf(LIB / "Strategy" / "2027 Digital Wealth Strategy.pptx", LIB / "Strategy")
    (LIB / "Strategy" / "2027 Digital Wealth Strategy.pdf").rename(LIB / "Strategy" / "Market Entry - APAC.pdf")

    print(f"Sample library written to {LIB}")
    print("Add these as source directories in the app (Manage sources):")
    print(f"  {LIB / 'Strategy'}  ->  domain: Strategy")
    print(f"  {LIB / 'Architecture'}  ->  domain: Architecture")
    print(f"  {LIB / 'Projects'}  ->  domain: Projects")


if __name__ == "__main__":
    sys.exit(main())
