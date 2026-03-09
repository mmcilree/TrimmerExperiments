from collections import Counter
import re
import html
from get_results import get_all_solver_data, eprint, TOOLS
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.platypus.tableofcontents import TableOfContents

TOOL_LABELS = [
    "Trimmer",
    "VeriPB Elabarator",
    "CakePB (on trimmed proof)",
    "CakePB (on elaborated proof)",
]


def write_failure_report_pdf(dfs, tools, tool_labels, out_path="failure_report.pdf"):
    RE_IGNORE = re.compile(r"Running VeriPB|Warning|Switched to proof version")
    RE_PBP = re.compile(r"\S+\.pbp")
    RE_PB_SUM = re.compile(r"((?:\d+ ~?x[\d_]+ ?)+)")
    RE_LIST_NUMS = re.compile(r"(\d+ )+")
    RE_DIGITS = re.compile(r"\d+")

    # ── styles ─────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    style_h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor("#1a3a5c"),
    )
    style_h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=18,
        spaceAfter=6,
        textColor=colors.HexColor("#1a5276"),
    )
    style_normal = styles["Normal"]
    style_code = ParagraphStyle(
        "Code",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=10,
        wordWrap="CJK",
    )
    style_toc_entry = ParagraphStyle(
        "TOCEntry",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=0,
        spaceAfter=3,
    )

    # ── collect data ────────────────────────────────────────────────────────
    sections = []  # (solver, label, n_failures, rows)
    # rows: list of (count, normalised_display, raw_display)

    for solver in dfs:
        df = dfs[solver]
        for tool, label in zip(tools, tool_labels):
            failures = df[
                (df[f"{tool}_succeeded"] == False)
                & (df[f"{tool}_time_exit_code"] != 124)
            ]

            msgs_raw, msgs_normalised = [], []
            example_instance = {}
            for instance, lines in failures[f"{tool}_output_lines"].items():
                msg = "".join(l for l in lines if not RE_IGNORE.search(l))
                msg = msg.replace("\n", "\\n")
                raw = msg
                msg = RE_PBP.sub("<FILE>.pbp", msg)
                msg = RE_PB_SUM.sub("<PB CONSTRAINT>", msg)
                msg = RE_LIST_NUMS.sub("<LIST OF NUMS>", msg)
                if ".rs" not in msg:
                    msg = RE_DIGITS.sub("<N>", msg)
                msgs_normalised.append(msg)
                msgs_raw.append(raw)
                example_instance[msg] = instance

            counts = Counter(msgs_normalised)
            rows = []
            for pattern, count in counts.most_common():
                if count == 1:
                    idx = msgs_normalised.index(pattern)
                    display = msgs_raw[idx][:600]
                else:
                    display = pattern[:600]

                rows.append((count, display, example_instance[pattern]))

            sections.append((solver, label, len(failures), rows))

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Failure Report",
    )

    story = []

    # Title
    story.append(Paragraph("Failure Report", style_h1))
    story.append(Spacer(1, 0.3 * cm))

    # Table of contents (manual — links to each section heading)
    story.append(Paragraph("Contents", style_h2))
    for solver, label, n_failures, _ in sections:
        anchor = f"{solver}-{label}"
        link = f'<a href="#{anchor}" color="#1a5276">{solver} — {label} ({n_failures} failures)</a>'
        story.append(Paragraph(link, style_toc_entry))

    story.append(PageBreak())

    # Sections
    for solver, label, n_failures, rows in sections:
        anchor = f"{solver}-{label}"
        heading_text = f'<a name="{anchor}"/>{label} - {solver}'
        story.append(Paragraph(heading_text, style_h2))
        story.append(Paragraph(f"{n_failures} non-timeout failures", style_normal))
        story.append(Spacer(1, 0.2 * cm))

        if not rows:
            story.append(Paragraph("<i>No failures.</i>", style_normal))
        else:
            # Table: count | message
            table_data = [
                [
                    Paragraph("<b>Count</b>", style_code),
                    Paragraph("<b>Message</b>", style_code),
                ]
            ]
            for count, display, example in rows:
                # escape XML special chars for reportlab Paragraph
                safe = (
                    display.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                example = (
                    example.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                bg = colors.HexColor("#fff8e1") if count == 1 else colors.white
                table_data.append(
                    [
                        Paragraph(str(count), style_code),
                        Paragraph(safe, style_code),
                    ]
                )
                table_data.append(
                    [Paragraph("Example", style_code), Paragraph(example, style_code)],
                )

            col_widths = [1.5 * cm, 14.5 * cm]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)

            # alternate row shading + unique row highlight
            row_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d6e4f0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]
            for i in range(len(rows) * 2 + 2):
                if i % 2 == 0:
                    row_styles.append(
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f4f4f4"))
                    )

            t.setStyle(TableStyle(row_styles))
            story.append(t)

        story.append(Spacer(1, 0.5 * cm))

    doc.build(story)
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    dfs = get_all_solver_data()
    write_failure_report_pdf(dfs, TOOLS, TOOL_LABELS, "failure_report.pdf")
