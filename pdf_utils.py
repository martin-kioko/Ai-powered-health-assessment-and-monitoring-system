"""pdf_utils.py — Clinical PDF report generation."""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

_RISK_COLOR  = {"Low": "#3fb950", "Medium": "#d29922", "High": "#f85149"}
_RISK_BG     = {"Low": "#f0faf2", "Medium": "#fffbe6", "High": "#fff1f0"}

_DARK   = colors.HexColor("#0d1117")
_MID    = colors.HexColor("#8b949e")
_BORDER = colors.HexColor("#21262d")


def generate_pdf(patient_info: dict, assessment: dict,
                 doctor_notes: list | None = None) -> bytes:
    buf  = BytesIO()
    doc  = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2.2 * cm, leftMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Helpers ────────────────────────────────────────────────────────────
    def h1(text):
        return Paragraph(text, ParagraphStyle(
            "H1", parent=styles["Normal"],
            fontSize=18, fontName="Helvetica-Bold",
            textColor=_DARK, spaceAfter=2,
        ))

    def h2(text):
        return Paragraph(text, ParagraphStyle(
            "H2", parent=styles["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=_DARK, spaceBefore=14, spaceAfter=6,
        ))

    def body(text):
        return Paragraph(text, ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#444c56"), spaceAfter=3,
        ))

    def rule():
        return HRFlowable(width="100%", thickness=0.5, color=_BORDER, spaceAfter=10)

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(h1("Clinical Assessment Report"))
    story.append(Paragraph(
        f"ClinicalAI Decision Support &nbsp;&nbsp;·&nbsp;&nbsp; "
        f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')}",
        ParagraphStyle("Meta", parent=styles["Normal"],
                       fontSize=8, textColor=_MID, spaceAfter=10),
    ))
    story.append(rule())

    # ── Risk summary box ────────────────────────────────────────────────────
    risk = assessment.get("final_risk", "Unknown")
    rc   = colors.HexColor(_RISK_COLOR.get(risk, "#888"))
    rbg  = colors.HexColor(_RISK_BG.get(risk, "#f5f5f5"))
    mp   = assessment.get("ml_probability", 0) or 0

    summary_t = Table(
        [[
            Paragraph(f"<b>Risk level: {risk.upper()}</b>",
                      ParagraphStyle("RS", parent=styles["Normal"],
                                     fontSize=14, fontName="Helvetica-Bold",
                                     textColor=rc)),
            Paragraph(
                f"Model: {assessment.get('ml_prediction', 'N/A')} &nbsp;&nbsp; "
                f"Confidence: {mp:.0%}",
                ParagraphStyle("RM", parent=styles["Normal"],
                               fontSize=9, textColor=_MID, alignment=TA_RIGHT)),
        ]],
        colWidths=[9 * cm, 7.4 * cm],
    )
    summary_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rbg),
        ("PADDING",    (0, 0), (-1, -1), 12),
        ("LINEBELOW",  (0, 0), (-1, -1), 1, rc),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_t)
    story.append(Spacer(1, 0.3 * cm))

    # ── Patient information ─────────────────────────────────────────────────
    story.append(h2("Patient information"))
    pt = Table(
        [
            ["Name",  patient_info.get("name", "N/A"),
             "Assessment", f"#{assessment.get('id', 'N/A')}"],
            ["Email", patient_info.get("email", "N/A"),
             "Age",   str(patient_info.get("age", "N/A"))],
            ["Gender", patient_info.get("gender", "N/A"),
             "Conditions", patient_info.get("conditions", "None reported")],
        ],
        colWidths=[2.5 * cm, 6.5 * cm, 2.5 * cm, 4.9 * cm],
    )
    pt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), _DARK),
        ("TEXTCOLOR", (2, 0), (2, -1), _DARK),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#444c56")),
        ("TEXTCOLOR", (3, 0), (3, -1), colors.HexColor("#444c56")),
        ("PADDING",  (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#f9fafb"), colors.white]),
        ("GRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#e1e4e8")),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.3 * cm))

    # ── Vital signs ──────────────────────────────────────────────────────────
    story.append(h2("Vital signs"))
    vt = Table(
        [
            ["Parameter",         "Value",                         "Parameter",   "Value"],
            ["Respiratory rate",  f"{assessment.get('respiratory_rate', 'N/A')} breaths/min",
             "Heart rate",        f"{assessment.get('heart_rate', 'N/A')} bpm"],
            ["Oxygen saturation", f"{assessment.get('oxygen_saturation', 'N/A')}%",
             "Temperature",       f"{assessment.get('temperature', 'N/A')} °C"],
            ["Systolic BP",       f"{assessment.get('systolic_bp', 'N/A')} mmHg",
             "On oxygen",         "Yes" if assessment.get("on_oxygen") else "No"],
            ["Consciousness",     assessment.get("consciousness", "N/A"),
             "O₂ scale",          f"Scale {assessment.get('o2_scale', 'N/A')}"],
        ],
        colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 3.4 * cm],
    )
    vt.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("PADDING",     (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f9fafb")]),
        ("GRID",        (0, 0), (-1, -1), 0.3, colors.HexColor("#e1e4e8")),
    ]))
    story.append(vt)
    story.append(Spacer(1, 0.3 * cm))

    # ── Recommendation ───────────────────────────────────────────────────────
    story.append(h2("Clinical recommendation"))
    rec_t = Table([[
        Paragraph(assessment.get("recommendation", ""),
                  ParagraphStyle("Rec", parent=styles["Normal"],
                                 fontSize=9, textColor=rc))
    ]])
    rec_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rbg),
        ("PADDING",    (0, 0), (-1, -1), 10),
        ("LINERIGHT",  (0, 0), (-1, -1), 3, rc),
    ]))
    story.append(rec_t)
    story.append(Spacer(1, 0.3 * cm))

    # ── Model explanation ────────────────────────────────────────────────────
    if assessment.get("explanation"):
        story.append(h2("Model explanation"))
        story.append(body(
            assessment["explanation"].replace("\n", "<br/>")
        ))
        story.append(Spacer(1, 0.2 * cm))

    # ── Physician notes ──────────────────────────────────────────────────────
    if doctor_notes:
        story.append(rule())
        story.append(h2("Physician notes"))
        for n in doctor_notes:
            story.append(body(
                f"<b>Dr. {n.get('doctor_name', '')}  ·  {n.get('date', '')}</b><br/>"
                f"{n.get('note', '')}"
            ))
            story.append(Spacer(1, 0.15 * cm))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(rule())
    story.append(Paragraph(
        "This report is generated by a computer-aided decision support tool and must be "
        "interpreted by a licensed medical professional. It does not constitute a diagnosis.",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontSize=7.5, textColor=_MID, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buf.getvalue()
