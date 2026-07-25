"""
blast_radius/report/docx_exporter.py -- Export Markdown report text to Microsoft Word (.docx) format.
"""

import re
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


def markdown_to_docx(md_text: str, output_path: Path) -> Path:
    """
    Convert a Markdown string into a styled Word Document (.docx).
    """
    doc = Document()
    
    # Set default margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    lines = md_text.split("\n")
    in_table = False
    table_lines = []

    def flush_table(t_lines):
        if not t_lines:
            return
        # Parse Markdown table
        header_raw = [c.strip() for c in t_lines[0].strip("|").split("|")]
        data_rows = []
        for r in t_lines[2:]:
            if "|" in r:
                data_rows.append([c.strip() for c in r.strip("|").split("|")])
        
        if not header_raw:
            return

        table = doc.add_table(rows=1 + len(data_rows), cols=len(header_raw))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Style Header Row
        hdr_cells = table.rows[0].cells
        for idx, text in enumerate(header_raw):
            if idx < len(hdr_cells):
                cell = hdr_cells[idx]
                cell.text = text.replace("`", "")
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs:
                        run.font.bold = True
                        run.font.size = Pt(10)
                        run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

        # Style Data Rows
        for r_idx, row_data in enumerate(data_rows):
            row_cells = table.rows[r_idx + 1].cells
            for c_idx, val in enumerate(row_data):
                if c_idx < len(row_cells):
                    cell = row_cells[c_idx]
                    cell.text = val.replace("`", "")
                    for p in cell.paragraphs:
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        for run in p.runs:
                            run.font.size = Pt(9.5)
                            run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        
        doc.add_paragraph()  # Blank spacing after table

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle Markdown Tables
        if "|" in stripped and ("---" in stripped or (i + 1 < len(lines) and "---" in lines[i + 1])):
            in_table = True
            table_lines.append(stripped)
            i += 1
            continue
        elif in_table:
            if "|" in stripped:
                table_lines.append(stripped)
                i += 1
                continue
            else:
                flush_table(table_lines)
                table_lines = []
                in_table = False

        # Ignore raw HTML details/summary tags
        if stripped.startswith("<details>") or stripped.startswith("</details>") or stripped.startswith("<summary>") or stripped.startswith("</summary>"):
            i += 1
            continue

        # Ignore Mermaid code block blocks in docx (or render as text summary)
        if stripped.startswith("```mermaid") or stripped == "```":
            if stripped.startswith("```mermaid"):
                p = doc.add_paragraph()
                r = p.add_run("[Visual Diagram embedded in HTML and PDF versions]")
                r.font.italic = True
                r.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
            i += 1
            continue

        # Headings
        if stripped.startswith("# "):
            p = doc.add_heading(level=1)
            r = p.add_run(stripped[2:])
            r.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            r.font.size = Pt(18)
            r.font.bold = True
        elif stripped.startswith("## "):
            p = doc.add_heading(level=2)
            r = p.add_run(stripped[3:])
            r.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            r.font.size = Pt(14)
            r.font.bold = True
        elif stripped.startswith("### "):
            p = doc.add_heading(level=3)
            r = p.add_run(stripped[4:])
            r.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
            r.font.size = Pt(12)
            r.font.bold = True
        elif stripped.startswith("> "):
            p = doc.add_paragraph(style='Quote' if 'Quote' in [s.name for s in doc.styles] else None)
            r = p.add_run(stripped[2:])
            r.font.italic = True
            r.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(style='List Bullet')
            text = stripped[2:]
            # Simple bold handler for **text**
            parts = re.split(r"(\*\*.*?\*\*)", text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    r = p.add_run(part[2:-2])
                    r.bold = True
                else:
                    r = p.add_run(part)
        elif re.match(r"^\d+\.\s", stripped):
            p = doc.add_paragraph(style='List Number')
            text = re.sub(r"^\d+\.\s", "", stripped)
            parts = re.split(r"(\*\*.*?\*\*)", text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    r = p.add_run(part[2:-2])
                    r.bold = True
                else:
                    r = p.add_run(part)
        elif stripped:
            p = doc.add_paragraph()
            parts = re.split(r"(\*\*.*?\*\*)", stripped)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    r = p.add_run(part[2:-2])
                    r.bold = True
                else:
                    r = p.add_run(part)

        i += 1

    if table_lines:
        flush_table(table_lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
