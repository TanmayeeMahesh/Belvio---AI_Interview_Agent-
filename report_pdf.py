"""
report_pdf.py — Generate the read-only HR PDF report (US-AG-08 AC-06).

Reads the report row + per-topic detail + transcript and renders a professional PDF:
Candidate, Role, Date, Per-Topic Scores, 4-Dimension Composite, Executive Summary,
Strengths, Gaps, Recommendation + Justification, and the full transcript.

Usage:
    from report_pdf import build_report_pdf
    path = build_report_pdf(report_dict, transcript_list, out_dir="/path")
where report_dict is what evaluator.evaluate_session returns (the `full` dict).
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak)

ACCENT = colors.HexColor("#2563eb")
GREY   = colors.HexColor("#6b7280")
LIGHT  = colors.HexColor("#f3f4f6")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("ReportTitle", parent=s["Title"], fontSize=20, textColor=ACCENT, spaceAfter=4))
    s.add(ParagraphStyle("Sub", parent=s["Normal"], fontSize=9, textColor=GREY, spaceAfter=12))
    s.add(ParagraphStyle("H", parent=s["Heading2"], fontSize=13, textColor=ACCENT, spaceBefore=14, spaceAfter=6))
    s.add(ParagraphStyle("Body", parent=s["Normal"], fontSize=10, leading=15, spaceAfter=6))
    s.add(ParagraphStyle("Rec", parent=s["Normal"], fontSize=14, leading=18, spaceAfter=6))
    s.add(ParagraphStyle("TXspeaker", parent=s["Normal"], fontSize=9, textColor=ACCENT, spaceBefore=6))
    s.add(ParagraphStyle("TXtext", parent=s["Normal"], fontSize=9, leading=13, textColor=colors.black))
    return s


def _esc(t):
    return (str(t or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_report_pdf(report: dict, transcript: list = None, out_dir: str = ".") -> str:
    os.makedirs(out_dir, exist_ok=True)
    cand = report.get("candidate", {}) or {}
    name = cand.get("name") or report.get("candidate_name") or "Candidate"
    role = cand.get("role") or report.get("role") or "Unspecified"
    sid  = report.get("session_id", "")
    fn = os.path.join(out_dir, f"report_{sid[:8] or 'session'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    s = _styles()
    story = []

    # ── Header ──
    story.append(Paragraph("Interview Evaluation Report", s["ReportTitle"]))
    story.append(Paragraph(
        f"Candidate: <b>{_esc(name)}</b> &nbsp;|&nbsp; Role: <b>{_esc(role)}</b> &nbsp;|&nbsp; "
        f"Date: {datetime.now().strftime('%d %b %Y')}", s["Sub"]))

    # ── Recommendation banner ──
    rec = report.get("recommendation", "—")
    rec_color = {"Strongly Recommended": colors.HexColor("#16a34a"),
                 "Recommended": colors.HexColor("#22c55e"),
                 "Needs Further Review": colors.HexColor("#d97706"),
                 "Not Recommended": colors.HexColor("#dc2626")}.get(rec.split(" (")[0], GREY)
    story.append(Paragraph(f'<b>Recommendation:</b> <font color="{rec_color.hexval()}">{_esc(rec)}</font>',
                           s["Rec"]))
    story.append(Paragraph(f"Overall Composite Score: <b>{report.get('overall_score','—')}/10</b>", s["Body"]))

    # ── Executive summary ──
    if report.get("executive_summary"):
        story.append(Paragraph("Executive Summary", s["H"]))
        story.append(Paragraph(_esc(report["executive_summary"]), s["Body"]))

    # ── Dimension scores ──
    story.append(Paragraph("Score Breakdown (4 Dimensions)", s["H"]))
    dims = [["Dimension", "Weight", "Score /10"],
            ["Technical Accuracy", "40%", report.get("technical_accuracy", "—")],
            ["Depth of Explanation", "30%", report.get("depth", "—")],
            ["Clarity & Communication", "20%", report.get("clarity_communication", "—")],
            ["Problem-Solving Approach", "10%", report.get("problem_solving", "—")]]
    t = Table(dims, colWidths=[80*mm, 30*mm, 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), ACCENT),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(t)

    # ── Per-topic ──
    per_topic = report.get("per_topic", [])
    if per_topic:
        story.append(Paragraph("Per-Topic Detail", s["H"]))
        cell = ParagraphStyle("Cell", parent=s["Normal"], fontSize=8, leading=11)
        rows = [["Topic", "Score", "Note"]]
        for tp in per_topic:
            ans = "" if tp.get("answered", True) else " (no answer)"
            rows.append([
                Paragraph(f"{_esc(tp.get('topic'))}{ans}", cell),   # wraps within column
                f"{tp.get('topic_score','—')}",
                Paragraph(_esc(tp.get("note", "")), cell),          # wraps — no more overflow
            ])
        tt = Table(rows, colWidths=[45*mm, 20*mm, 85*mm])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), GREY),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(tt)

    # ── Strengths / Gaps / Justification ──
    if report.get("strengths"):
        story.append(Paragraph("Key Strengths", s["H"]))
        story.append(Paragraph(_esc(report["strengths"]), s["Body"]))
    if report.get("gaps"):
        story.append(Paragraph("Identified Gaps", s["H"]))
        story.append(Paragraph(_esc(report["gaps"]), s["Body"]))
    if report.get("justification"):
        story.append(Paragraph("Justification", s["H"]))
        story.append(Paragraph(_esc(report["justification"]), s["Body"]))

    # ── Transcript ──
    if transcript:
        story.append(PageBreak())
        story.append(Paragraph("Full Interview Transcript", s["H"]))
        for row in transcript:
            sp = row.get("speaker", "")
            tx = row.get("text", "")
            if not tx:
                continue
            story.append(Paragraph(f"{_esc(sp)} <font color='{GREY.hexval()}'>"
                                   f"[{_esc(row.get('timestamp',''))}]</font>", s["TXspeaker"]))
            story.append(Paragraph(_esc(tx), s["TXtext"]))

    SimpleDocTemplate(fn, pagesize=A4,
                      topMargin=18*mm, bottomMargin=18*mm,
                      leftMargin=18*mm, rightMargin=18*mm).build(story)
    print(f"📄 PDF report written → {fn}")
    return fn