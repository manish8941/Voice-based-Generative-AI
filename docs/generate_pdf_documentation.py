"""
Master PDF Documentation Generator
Compiles all engineering documents (Decisions.md, Flow.md, Architecture.md, PRD.md,
Test_Checklists_and_Rollback.md, tech_stack.md, design.md, rules.md) into a unified,
professionally styled PDF document.
"""

import html
import os
import re
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Custom canvas that adds professional running headers and 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))

        # Do not draw on cover page (Page 1)
        if self._pageNumber > 1:
            # Header
            self.drawString(54, letter[1] - 36, "VoGenFlow | Voice-based Generative AI for Workflows | Master Spec")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

            # Footer
            page_str = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(letter[0] - 54, 36, page_str)
            self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY — GITHUB REPOSITORY MASTER SPEC")
            self.line(54, 48, letter[0] - 54, 48)

        self.restoreState()


def clean_inline_formatting(text: str) -> str:
    """Safely convert Markdown inline formatting into ReportLab XML without tag collisions."""
    # 1. First extract backtick code blocks into tokens to protect them
    code_tokens = []
    def code_sub(match):
        idx = len(code_tokens)
        code_content = html.escape(match.group(1))
        code_tokens.append(f"<font face='Courier' color='#1A202C'>{code_content}</font>")
        return f"__CODETOKEN_{idx}__"

    text_no_code = re.sub(r"`([^`]+?)`", code_sub, text)

    # 2. Escape HTML for the remaining text
    safe = html.escape(text_no_code)

    # 3. Handle Math blocks ($...$)
    safe = re.sub(r"\$\$(.+?)\$\$", r"<i>\1</i>", safe)
    safe = re.sub(r"\$(.+?)\$", r"<i>\1</i>", safe)

    # 4. Bold formatting (**text**)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)

    # 5. Italic formatting with asterisks (*text*)
    safe = re.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", r"<i>\1</i>", safe)

    # 6. Re-insert code tokens
    for idx, token in enumerate(code_tokens):
        safe = safe.replace(f"__CODETOKEN_{idx}__", token)

    return safe


def parse_markdown_to_flowables(md_content: str, styles) -> list:
    """Convert basic markdown syntax into reportlab flowables."""
    flowables = []
    lines = md_content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            flowables.append(Spacer(1, 3))
            i += 1
            continue

        # Horizontal Rule
        if stripped in ["---", "***", "___"]:
            flowables.append(Spacer(1, 4))
            flowables.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceBefore=6, spaceAfter=8))
            i += 1
            continue

        # Code block (```)
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "<br/>".join([
                html.escape(c_line).replace(" ", "&nbsp;")
                for c_line in code_lines
            ])
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(code_text, styles["CodeBlockStyle"]))
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        # Table (| col1 | col2 |)
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            parsed_rows = []
            for t_line in table_lines:
                if re.match(r"^\|[\s\:\-\|]+\|$", t_line):
                    continue
                raw_cells = [c.strip() for c in t_line.split("|")[1:-1]]
                row_cells = []
                for c in raw_cells:
                    formatted_cell = clean_inline_formatting(c)
                    row_cells.append(Paragraph(formatted_cell, styles["TableBody"]))
                if row_cells:
                    parsed_rows.append(row_cells)

            if parsed_rows:
                t = Table(parsed_rows, colWidths=None)
                t.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ])
                )
                flowables.append(Spacer(1, 4))
                flowables.append(t)
                flowables.append(Spacer(1, 6))
            continue

        # Headers
        if stripped.startswith("# "):
            text = clean_inline_formatting(stripped[2:].strip())
            flowables.append(Spacer(1, 10))
            flowables.append(Paragraph(text, styles["CustomH1"]))
            flowables.append(Spacer(1, 4))
        elif stripped.startswith("## "):
            text = clean_inline_formatting(stripped[3:].strip())
            flowables.append(Spacer(1, 8))
            flowables.append(Paragraph(text, styles["CustomH2"]))
            flowables.append(Spacer(1, 3))
        elif stripped.startswith("### "):
            text = clean_inline_formatting(stripped[4:].strip())
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(text, styles["CustomH3"]))
            flowables.append(Spacer(1, 2))
        elif stripped.startswith("#### "):
            text = clean_inline_formatting(stripped[5:].strip())
            flowables.append(Spacer(1, 4))
            flowables.append(Paragraph(text, styles["CustomH4"]))
            flowables.append(Spacer(1, 2))

        # Checklists & Bullets
        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            checked = "[X]" if stripped.startswith("- [x]") else "[ ]"
            text = clean_inline_formatting(stripped[5:].strip())
            formatted = f"<b>{checked}</b> {text}"
            flowables.append(Paragraph(formatted, styles["BulletItem"]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = clean_inline_formatting(stripped[2:].strip())
            formatted = f"&bull; {text}"
            flowables.append(Paragraph(formatted, styles["BulletItem"]))
        elif re.match(r"^\d+\.\s", stripped):
            num_prefix = re.match(r"^(\d+\.\s)", stripped).group(1)
            raw_text = stripped[len(num_prefix):]
            formatted = f"<b>{num_prefix}</b>{clean_inline_formatting(raw_text)}"
            flowables.append(Paragraph(formatted, styles["BulletItem"]))

        # Blockquote (>)
        elif stripped.startswith("> "):
            text = clean_inline_formatting(stripped[2:].strip())
            flowables.append(Paragraph(text, styles["BlockQuote"]))

        # Normal Paragraph
        else:
            formatted = clean_inline_formatting(stripped)
            flowables.append(Paragraph(formatted, styles["BodyText"]))

        i += 1

    return flowables


def generate_master_pdf(output_pdf_path: str):
    """Compile all docs into a master PDF."""
    docs_dir = Path(__file__).resolve().parent
    Path(output_pdf_path).parent.mkdir(parents=True, exist_ok=True)

    chapters = [
        ("PRD.md", "Chapter 1: Product Requirements Document (PRD)"),
        ("Decisions.md", "Chapter 2: Engineering Decisions & Architectural Rationale"),
        ("Flow.md", "Chapter 3: System Execution Flow & Code Lifecycle"),
        ("Architecture.md", "Chapter 4: System Architecture & Component Specifications"),
        ("tech_stack.md", "Chapter 5: Technology Stack & Environment Setup"),
        ("design.md", "Chapter 6: UI/UX Design System & Aesthetics"),
        ("rules.md", "Chapter 7: Engineering Rules & Code Standards"),
        ("Test_Checklists_and_Rollback.md", "Chapter 8: QA Test Checklists & Rollback Procedures"),
        ("comparison.md", "Chapter 9: Market Comparison, Positioning & Commercialization"),
    ]

    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    base_styles = getSampleStyleSheet()

    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=colors.HexColor("#1A365D"),
            alignment=0,
            spaceAfter=12,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=24,
        ),
        "CoverMeta": ParagraphStyle(
            "CoverMeta",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#718096"),
        ),
        "ChapterHeader": ParagraphStyle(
            "ChapterHeader",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=14,
            spaceAfter=10,
        ),
        "CustomH1": ParagraphStyle(
            "CustomH1",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#2D3748"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "CustomH2": ParagraphStyle(
            "CustomH2",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#3182CE"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "CustomH3": ParagraphStyle(
            "CustomH3",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#4A5568"),
            spaceBefore=8,
            spaceAfter=3,
        ),
        "CustomH4": ParagraphStyle(
            "CustomH4",
            parent=base_styles["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#718096"),
            spaceBefore=6,
            spaceAfter=2,
        ),
        "BodyText": ParagraphStyle(
            "BodyText",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=4,
        ),
        "BulletItem": ParagraphStyle(
            "BulletItem",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            leftIndent=14,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=2,
        ),
        "CodeBlockStyle": ParagraphStyle(
            "CodeBlockStyle",
            parent=base_styles["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#1A202C"),
            backColor=colors.HexColor("#F7FAFC"),
            borderColor=colors.HexColor("#E2E8F0"),
            borderWidth=0.5,
            borderPadding=6,
            spaceBefore=4,
            spaceAfter=6,
        ),
        "TableBody": ParagraphStyle(
            "TableBody",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#2D3748"),
        ),
        "BlockQuote": ParagraphStyle(
            "BlockQuote",
            parent=base_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            leftIndent=14,
            textColor=colors.HexColor("#4A5568"),
            spaceBefore=4,
            spaceAfter=4,
        ),
    }

    story = []

    # 1. Cover Page
    story.append(Spacer(1, 40))
    story.append(Paragraph("VOGENFLOW", styles["CoverTitle"]))
    story.append(
        Paragraph(
            "Voice-based Generative AI for Workflows<br/>"
            "Complete Engineering Specification, Architecture, Decision Rationale, "
            "Signal Processing Mechanics, RAG Grounding &amp; QA Blueprints",
            styles["CoverSubtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3182CE"), spaceBefore=10, spaceAfter=20))
    story.append(Spacer(1, 100))

    meta_text = """
    <b>Author / Architect:</b> Antigravity Systems &amp; Core Engineering<br/>
    <b>Document Version:</b> 1.0.0 (Production Master)<br/>
    <b>Target Platform:</b> Windows / macOS / Linux (PyQt6 &amp; Python 3.10+)<br/>
    <b>STT &amp; LLM Engines:</b> Groq Whisper LPU &amp; Llama-3.3-70B / Local Ollama<br/>
    <b>Context Retrieval:</b> Embedded Okapi BM25 RAG Engine<br/>
    <b>Date:</b> August 2026
    """
    story.append(Paragraph(meta_text, styles["CoverMeta"]))
    story.append(PageBreak())

    # 2. Table of Contents
    story.append(Paragraph("Table of Contents", styles["CustomH1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceBefore=4, spaceAfter=14))

    toc_items = [
        "1. Product Requirements Document (PRD.md) — Scope, Vision, Personas &amp; Functional Requirements",
        "2. Engineering Decisions (Decisions.md) — File-by-file implementation choices &amp; trade-off rationale",
        "3. System Execution Flow (Flow.md) — Entry points, execution sequences &amp; call hierarchy",
        "4. System Architecture (Architecture.md) — C4 container diagrams, data models &amp; concurrency",
        "5. Technology Stack (tech_stack.md) — Dependency matrix, hardware specs &amp; setup commands",
        "6. UI/UX Design System (design.md) — Aesthetic tokens, 3-pane layout &amp; visualizer physics",
        "7. Engineering Rules (rules.md) — Coding conventions, signal processing &amp; prompt standards",
        "8. QA Test Checklists &amp; Rollback (Test_Checklists_and_Rollback.md) — Test cases &amp; disaster recovery",
        "9. Market Comparison &amp; Commercialization (comparison.md) — Wispr Flow analysis &amp; SaaS unit economics",
    ]

    for item in toc_items:
        story.append(Paragraph(f"&bull; {item}", styles["BulletItem"]))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # 3. Chapters
    for filename, chapter_title in chapters:
        file_path = docs_dir / filename
        if not file_path.exists():
            continue

        story.append(Paragraph(chapter_title, styles["ChapterHeader"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3182CE"), spaceBefore=4, spaceAfter=12))

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            md_text = f.read()

        flowables = parse_markdown_to_flowables(md_text, styles)
        story.extend(flowables)
        story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_pdf_path


if __name__ == "__main__":
    out_file = str(Path(__file__).resolve().parent.parent / "output" / "VoGenFlow_Master_Documentation.pdf")
    generate_master_pdf(out_file)
    print(f"Master documentation PDF generated at: {out_file}")
