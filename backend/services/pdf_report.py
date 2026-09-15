"""
LANDNEXUS PDF Report Service
Reusable PDF generation for Project, Bottleneck, District, and State reports.
Uses ReportLab to produce professional government-style PDF documents.
"""
import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.lib.colors import HexColor

# ─── Brand Colors ───
BRAND_PRIMARY = HexColor("#0f6c70")
BRAND_DARK = HexColor("#0d5457")
BRAND_LIGHT = HexColor("#f0fdfa")
BRAND_ACCENT = HexColor("#134e4a")
HEADER_BG = HexColor("#0f6c70")
ROW_ALT = HexColor("#f8fafc")
BORDER_COLOR = HexColor("#cbd5e1")


def _header_footer(canvas, doc, report_title, subtitle=""):
    """Draw header and footer on every page."""
    canvas.saveState()
    w, h = doc.pagesize

    # Header bar
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, h - 50, w, 50, fill=True, stroke=False)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(30, h - 35, "LANDNEXUS")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(140, h - 33, "| Smart Land Acquisition Management System")

    # Report title line
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, h - 72, w, 22, fill=True, stroke=False)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(30, h - 67, report_title)
    if subtitle:
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 30, h - 67, subtitle)

    # Generated timestamp
    canvas.setFillColor(HexColor("#64748b"))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - 30, h - 33, f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M:%S IST')}")

    # Footer
    canvas.setFillColor(HexColor("#e2e8f0"))
    canvas.rect(0, 0, w, 30, fill=True, stroke=False)
    canvas.setFillColor(HexColor("#64748b"))
    canvas.setFont("Helvetica", 7)
    canvas.drawString(30, 12, "LANDNEXUS | Smart Land Acquisition Management System")
    canvas.drawRightString(w - 30, 12, f"Page {doc.page}")

    canvas.restoreState()


def _styles():
    """Return custom paragraph styles."""
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "SectionTitle", parent=ss["Heading2"],
        textColor=BRAND_PRIMARY, fontSize=13, spaceAfter=8, spaceBefore=14,
        borderWidth=0, borderPadding=0
    ))
    ss.add(ParagraphStyle(
        "SubSection", parent=ss["Heading3"],
        textColor=BRAND_DARK, fontSize=11, spaceAfter=6, spaceBefore=10
    ))
    ss.add(ParagraphStyle(
        "BodySmall", parent=ss["BodyText"],
        fontSize=9, leading=12, spaceAfter=4
    ))
    ss.add(ParagraphStyle(
        "KVLabel", parent=ss["BodyText"],
        fontSize=9, textColor=HexColor("#64748b"), leading=11
    ))
    ss.add(ParagraphStyle(
        "KVValue", parent=ss["BodyText"],
        fontSize=10, fontName="Helvetica-Bold", textColor=HexColor("#0f172a"), leading=13
    ))
    ss.add(ParagraphStyle(
        "TableHeader", parent=ss["BodyText"],
        fontSize=8, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER
    ))
    return ss


def _make_table(headers, rows, col_widths=None, font_size=8):
    """Create a styled table with repeated headers across pages."""
    header_row = [Paragraph(f'<b>{h}</b>', ParagraphStyle('th', fontSize=font_size, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_CENTER)) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([
            Paragraph(str(cell if cell is not None else "N/A"), ParagraphStyle('td', fontSize=font_size, leading=font_size + 3))
            for cell in row
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), font_size),
        ('FONTSIZE', (0, 1), (-1, -1), font_size),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _kv_block(pairs, ss):
    """Key-value detail block as a two-column table."""
    elements = []
    data = []
    for label, value in pairs:
        data.append([
            Paragraph(f'<b>{label}:</b>', ss['KVLabel']),
            Paragraph(str(value if value is not None else "N/A"), ss['KVValue'])
        ])
    if data:
        t = Table(data, colWidths=[160, 340])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, HexColor("#e2e8f0")),
        ]))
        elements.append(t)
    return elements


def _safe(val, default="N/A"):
    """Safely convert a value to string for display."""
    if val is None or val == "":
        return default
    return str(val)


def _fmt_amount(val):
    """Format a numeric amount for display."""
    try:
        v = float(val or 0)
        if v >= 10000000:
            return f"₹{v/10000000:.2f} Cr"
        elif v >= 100000:
            return f"₹{v/100000:.2f} L"
        else:
            return f"₹{v:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


def _build_pdf(elements, report_title, subtitle="", orientation="portrait"):
    """Build PDF bytes from elements list."""
    buf = io.BytesIO()
    page_size = A4 if orientation == "portrait" else landscape(A4)

    doc = SimpleDocTemplate(
        buf, pagesize=page_size,
        topMargin=85, bottomMargin=40,
        leftMargin=30, rightMargin=30
    )

    def on_page(canvas, doc):
        _header_footer(canvas, doc, report_title, subtitle)

    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════
#  A) PROJECT DETAILED REPORT
# ═══════════════════════════════════════════════════════════════
def generate_project_report(db_conn, project_id: str) -> bytes:
    """Generate a comprehensive PDF report for a single project."""
    c = db_conn
    ss = _styles()
    elements = []

    # ── Project details ──
    proj = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not proj:
        raise ValueError(f"Project {project_id} not found")
    proj = dict(proj)

    elements.append(Paragraph(f"Project Detailed Report", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY, spaceAfter=8))

    elements.extend(_kv_block([
        ("Project ID", proj.get("project_id")),
        ("Project Name", proj.get("project_name")),
        ("Project Type", proj.get("project_type")),
        ("Department", proj.get("department", "N/A")),
        ("Authority", proj.get("authority", "N/A")),
        ("District", proj.get("district")),
        ("Taluk", proj.get("taluk")),
        ("Village", proj.get("village", "N/A")),
        ("Priority", proj.get("priority", "N/A")),
        ("Current Stage", proj.get("current_stage", "N/A")),
        ("Project Status", proj.get("project_status", "N/A")),
        ("Progress", f"{proj.get('progress', 0) or 0}%"),
        ("Responsible Officer", proj.get("responsible_officer", "N/A")),
        ("Project Start Date", proj.get("project_start_date")),
        ("Expected Completion", proj.get("expected_completion_date") or proj.get("planned_completion_date", "N/A")),
        ("Total Land Required", proj.get("total_land_required", "N/A")),
        ("Affected Parcels", proj.get("affected_parcels", "N/A")),
        ("Affected Families", proj.get("affected_families", "N/A")),
        ("Last Updated", proj.get("last_updated", "N/A")),
    ], ss))

    # ── Linked Parcels ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Linked Parcels & Survey Numbers", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    parcels = [dict(r) for r in c.execute("""
        SELECT * FROM parcels WHERE project_id=? ORDER BY id
    """, (project_id,)).fetchall()]

    total_parcels = len(parcels)
    survey_numbers = ", ".join(set(str(p["survey_no"]) for p in parcels if p.get("survey_no"))) or "N/A"
    landowners = set(p.get("owner_reference") for p in parcels if p.get("owner_reference"))
    legal_dispute_count = sum(1 for p in parcels if p.get("legal_disputes") and str(p["legal_disputes"]).strip() not in ("", "0", "None", "No"))

    elements.extend(_kv_block([
        ("Total Linked Parcels", total_parcels),
        ("Survey Numbers", survey_numbers[:200] + ("..." if len(survey_numbers) > 200 else "")),
        ("Unique Landowner Count", len(landowners)),
        ("Legal Disputes", legal_dispute_count),
    ], ss))

    if parcels:
        elements.append(Spacer(1, 6))
        parcel_headers = ["ID", "Survey No", "Village", "Area", "Risk", "Classification"]
        parcel_rows = [
            [p["id"], _safe(p.get("survey_no")), _safe(p.get("village")), _safe(p.get("area")),
             _safe(p.get("risk_category")), _safe(p.get("classification"))]
            for p in parcels[:100]
        ]
        elements.append(_make_table(parcel_headers, parcel_rows, col_widths=[40, 70, 90, 55, 65, 110]))
        if len(parcels) > 100:
            elements.append(Paragraph(f"<i>... and {len(parcels)-100} more parcels</i>", ss['BodySmall']))


    # ── Acquisition Progress ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Acquisition Progress", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    # Field verification
    try:
        verified_count = c.execute("""
            SELECT COUNT(DISTINCT fa.parcel_id) FROM field_assignments fa
            WHERE fa.parcel_id IN (SELECT id FROM parcels WHERE project_id=?) AND fa.status='Verified'
        """, (project_id,)).fetchone()[0]
    except Exception:
        verified_count = 0
    pending_verification = total_parcels - verified_count

    # Risk distribution
    risk_dist = {}
    for p in parcels:
        cat = _safe(p.get("risk_category"), "UNASSESSED")
        risk_dist[cat] = risk_dist.get(cat, 0) + 1

    elements.extend(_kv_block([
        ("Acquisition Progress", f"{proj.get('progress', 0) or 0}%"),
        ("Field Verified Parcels", f"{verified_count} / {total_parcels}"),
        ("Pending Verification", pending_verification),
        ("Risk Distribution", ", ".join(f"{k}: {v}" for k, v in sorted(risk_dist.items()))),
    ], ss))

    # ── Compensation ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Compensation Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        comp = c.execute("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(assessed_amount),0) as total_assessed,
                   COALESCE(SUM(approved_amount),0) as total_approved,
                   COALESCE(SUM(paid_amount),0) as total_paid,
                   COALESCE(SUM(pending_amount),0) as total_pending,
                   SUM(CASE WHEN status='Paid' THEN 1 ELSE 0 END) as paid_count
            FROM compensation WHERE project_id=?
        """, (project_id,)).fetchone()
        comp = dict(comp) if comp else {}
    except Exception:
        comp = {}

    elements.extend(_kv_block([
        ("Total Compensation Records", comp.get("cnt", 0)),
        ("Total Assessed", _fmt_amount(comp.get("total_assessed"))),
        ("Total Approved", _fmt_amount(comp.get("total_approved"))),
        ("Total Paid", _fmt_amount(comp.get("total_paid"))),
        ("Total Pending", _fmt_amount(comp.get("total_pending"))),
        ("Paid Count", comp.get("paid_count", 0)),
    ], ss))

    # ── R&R ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Rehabilitation & Resettlement (R&R)", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        rr = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN status='Delayed' THEN 1 ELSE 0 END) as delayed
            FROM r_and_r WHERE project_id=?
        """, (project_id,)).fetchone()
        rr = dict(rr) if rr else {}
    except Exception:
        rr = {}

    try:
        rr_families_data = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk,
                   SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) as med_risk,
                   SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) as low_risk,
                   SUM(CASE WHEN verification_status='Verified' THEN 1 ELSE 0 END) as verified,
                   SUM(CASE WHEN grievance_status != 'No Grievance' THEN 1 ELSE 0 END) as with_grievance
            FROM rr_families WHERE project_id=?
        """, (project_id,)).fetchone()
        rr_fam = dict(rr_families_data) if rr_families_data else {}
    except Exception:
        rr_fam = {}

    elements.extend(_kv_block([
        ("Total R&R Families (r_and_r)", rr.get("total", 0)),
        ("R&R Completed", rr.get("completed", 0)),
        ("R&R Pending", rr.get("pending", 0)),
        ("R&R Delayed", rr.get("delayed", 0)),
        ("RR Families (detailed)", rr_fam.get("total", 0)),
        ("High Risk Families", rr_fam.get("high_risk", 0)),
        ("Medium Risk Families", rr_fam.get("med_risk", 0)),
        ("Low Risk Families", rr_fam.get("low_risk", 0)),
        ("Verified Families", rr_fam.get("verified", 0)),
        ("Families with Grievance", rr_fam.get("with_grievance", 0)),
    ], ss))

    # ── SLA & Milestones ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("SLA Status & Project Milestones", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        milestones = [dict(r) for r in c.execute("""
            SELECT stage, status, planned_date, expected_date, actual_date,
                   responsible_officer, delay_days, remarks
            FROM project_milestones WHERE project_id=? ORDER BY id
        """, (project_id,)).fetchall()]
    except Exception:
        milestones = []

    sla_breached = sum(1 for m in milestones if (m.get("delay_days") or 0) > 0)

    elements.extend(_kv_block([
        ("Total Milestones", len(milestones)),
        ("SLA Breached Stages", sla_breached),
    ], ss))

    if milestones:
        ms_headers = ["Stage", "Status", "Planned", "Expected", "Actual", "Delay Days", "Officer"]
        ms_rows = [
            [m["stage"], _safe(m["status"]), _safe(m["planned_date"]),
             _safe(m["expected_date"]), _safe(m["actual_date"]),
             _safe(m["delay_days"], "0"), _safe(m["responsible_officer"])]
            for m in milestones
        ]
        elements.append(_make_table(ms_headers, ms_rows, col_widths=[100, 65, 65, 65, 65, 45, 95]))

    # ── Grievances ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Grievances", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        grievances = [dict(r) for r in c.execute("""
            SELECT id, type, status, description, submitted_by, created_at
            FROM grievances WHERE project_id=? ORDER BY created_at DESC
        """, (project_id,)).fetchall()]
    except Exception:
        grievances = []

    try:
        rr_grv = [dict(r) for r in c.execute("""
            SELECT id, grievance_type, status, description, assigned_to, raised_date
            FROM rr_grievances WHERE project_id=? ORDER BY raised_date DESC
        """, (project_id,)).fetchall()]
    except Exception:
        rr_grv = []

    elements.extend(_kv_block([
        ("Project Grievances", len(grievances)),
        ("Open Grievances", sum(1 for g in grievances if g.get("status") != "Resolved")),
        ("R&R Grievances", len(rr_grv)),
        ("Open R&R Grievances", sum(1 for g in rr_grv if g.get("status") not in ("Resolved", "Closed"))),
    ], ss))

    if grievances:
        g_headers = ["ID", "Type", "Status", "Submitted By", "Date"]
        g_rows = [[g["id"], _safe(g.get("type")), _safe(g.get("status")), _safe(g.get("submitted_by")), _safe(g.get("created_at"))] for g in grievances[:50]]
        elements.append(_make_table(g_headers, g_rows, col_widths=[40, 100, 70, 150, 110]))

    # ── Bottlenecks for this project ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Current Bottlenecks", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        bottlenecks = [dict(r) for r in c.execute("""
            SELECT m.stage, m.status, m.delay_days, m.planned_date, m.expected_date,
                   m.responsible_officer, m.remarks,
                   CAST(COALESCE(MAX(0, julianday('now') - julianday(m.planned_date)), 0) AS INTEGER) AS days_at_stage
            FROM project_milestones m
            WHERE m.project_id=? AND m.status != 'Completed'
              AND (m.delay_days > 0 OR (m.planned_date IS NOT NULL AND julianday('now') > julianday(m.planned_date)))
            ORDER BY m.delay_days DESC
        """, (project_id,)).fetchall()]
    except Exception:
        bottlenecks = []

    if bottlenecks:
        bn_headers = ["Stage", "Status", "Delay Days", "Days at Stage", "Planned Date", "Officer", "Remarks"]
        bn_rows = [
            [b["stage"], _safe(b["status"]), _safe(b["delay_days"], "0"),
             b["days_at_stage"], _safe(b["planned_date"]), _safe(b["responsible_officer"]),
             _safe(b["remarks"], "-")[:60]]
            for b in bottlenecks
        ]
        elements.append(_make_table(bn_headers, bn_rows, col_widths=[90, 60, 50, 55, 65, 95, 90]))
    else:
        elements.append(Paragraph("No active bottlenecks detected.", ss['BodySmall']))

    return _build_pdf(
        elements,
        f"Project Detailed Report — {proj.get('project_id')}",
        f"{proj.get('district', '')} District"
    )


# ═══════════════════════════════════════════════════════════════
#  B) PROJECT BOTTLENECK REPORT
# ═══════════════════════════════════════════════════════════════
def generate_project_bottleneck_report(db_conn, project_id: str) -> bytes:
    """Generate a bottleneck-focused PDF report for a single project."""
    c = db_conn
    ss = _styles()
    elements = []

    proj = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
    if not proj:
        raise ValueError(f"Project {project_id} not found")
    proj = dict(proj)

    elements.append(Paragraph("Project Bottleneck Report", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY, spaceAfter=8))

    elements.extend(_kv_block([
        ("Project ID", proj.get("project_id")),
        ("Project Name", proj.get("project_name")),
        ("District", proj.get("district")),
        ("Current Stage", proj.get("current_stage", "N/A")),
        ("Project Status", proj.get("project_status", "N/A")),
        ("Progress", f"{proj.get('progress', 0) or 0}%"),
    ], ss))

    # ── All bottleneck milestones ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Active Bottlenecks — Milestone Detail", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        bottlenecks = [dict(r) for r in c.execute("""
            SELECT m.stage, m.status, m.delay_days, m.planned_date, m.expected_date,
                   m.actual_date, m.responsible_officer, m.remarks, m.risk_score, m.next_action,
                   CAST(COALESCE(MAX(0, julianday('now') - julianday(m.planned_date)), 0) AS INTEGER) AS days_at_stage,
                   CASE
                       WHEN m.expected_date IS NOT NULL AND julianday('now') > julianday(m.expected_date) THEN 'SLA Breached'
                       WHEN m.expected_date IS NOT NULL AND julianday(m.expected_date) - julianday('now') <= 7 THEN 'SLA Due Soon'
                       ELSE 'Within SLA'
                   END AS sla_status
            FROM project_milestones m
            WHERE m.project_id=? AND m.status != 'Completed'
              AND (m.delay_days > 0 OR (m.planned_date IS NOT NULL AND julianday('now') > julianday(m.planned_date)))
            ORDER BY m.delay_days DESC, days_at_stage DESC
        """, (project_id,)).fetchall()]

        pending_count = c.execute("""
            SELECT COUNT(*) FROM project_milestones WHERE project_id=? AND status != 'Completed'
        """, (project_id,)).fetchone()[0]
    except Exception:
        bottlenecks = []
        pending_count = 0

    # Severity classification
    high_risk = sum(1 for b in bottlenecks if (b.get("delay_days") or 0) > 30)
    med_risk = sum(1 for b in bottlenecks if 7 < (b.get("delay_days") or 0) <= 30)
    low_risk = sum(1 for b in bottlenecks if 0 < (b.get("delay_days") or 0) <= 7)

    elements.extend(_kv_block([
        ("Total Active Bottlenecks", len(bottlenecks)),
        ("Pending Milestones", pending_count),
        ("High Severity (>30 days delay)", high_risk),
        ("Medium Severity (7-30 days)", med_risk),
        ("Low Severity (<7 days)", low_risk),
    ], ss))

    if bottlenecks:
        elements.append(Spacer(1, 8))
        for i, b in enumerate(bottlenecks):
            delay = b.get("delay_days") or 0
            severity = "HIGH" if delay > 30 else ("MEDIUM" if delay > 7 else "LOW")
            reason = f"{delay} days recorded delay" if delay else f"{b['days_at_stage']} days since stage started"
            recommended = _safe(b.get("next_action"), "Review and escalate")
            if b["stage"] == "Compensation":
                recommended = "Prioritize compensation assessment and payment processing."
            elif b["stage"] == "Approval":
                recommended = "Escalate to District Authority for approval."

            elements.append(Paragraph(f"Bottleneck #{i+1}: {b['stage']}", ss['SubSection']))
            elements.extend(_kv_block([
                ("Category", b["stage"]),
                ("Severity", severity),
                ("Affected Stage", b["stage"]),
                ("Days Delayed", delay),
                ("Days at Stage", b["days_at_stage"]),
                ("SLA Breach Status", b["sla_status"]),
                ("Root Cause / Reason", reason),
                ("Current Owner / Department", _safe(b.get("responsible_officer"), "Unassigned")),
                ("Recommended Action", recommended),
                ("Remarks", _safe(b.get("remarks"), "-")),
            ], ss))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No active bottlenecks detected for this project.", ss['BodySmall']))

    # ── Affected parcels at risk ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Affected Parcels — High/Critical Risk", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    risky_parcels = [dict(r) for r in c.execute("""
        SELECT id, survey_no, village, risk_category, risk_score, delay_probability
        FROM parcels WHERE project_id=? AND risk_category IN ('HIGH', 'CRITICAL')
        ORDER BY risk_score DESC
    """, (project_id,)).fetchall()]

    if risky_parcels:
        rp_headers = ["Parcel ID", "Survey No", "Village", "Risk Category", "Risk Score", "Delay Prob"]
        rp_rows = [
            [p["id"], _safe(p.get("survey_no")), _safe(p.get("village")), p["risk_category"],
             _safe(p.get("risk_score")), _safe(p.get("delay_probability"))]
            for p in risky_parcels[:50]
        ]
        elements.append(_make_table(rp_headers, rp_rows, col_widths=[55, 70, 90, 80, 70, 70]))
    else:
        elements.append(Paragraph("No high/critical risk parcels found.", ss['BodySmall']))

    # ── Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Bottleneck Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    summary_headers = ["Metric", "Value"]
    summary_rows = [
        ["Total Bottlenecks", len(bottlenecks)],
        ["Pending Milestone Count", pending_count],
        ["High Risk (>30 days)", high_risk],
        ["Medium Risk (7-30 days)", med_risk],
        ["Low Risk (<7 days)", low_risk],
        ["Affected High/Critical Parcels", len(risky_parcels)],
        ["SLA Breached", sum(1 for b in bottlenecks if b["sla_status"] == "SLA Breached")],
    ]
    elements.append(_make_table(summary_headers, summary_rows, col_widths=[250, 200]))

    return _build_pdf(
        elements,
        f"Project Bottleneck Report — {proj.get('project_id')}",
        f"{proj.get('district', '')} District"
    )


# ═══════════════════════════════════════════════════════════════
#  C) DISTRICT REPORT
# ═══════════════════════════════════════════════════════════════
def generate_district_report(db_conn, district: str) -> bytes:
    """Generate a comprehensive PDF report for a single district."""
    c = db_conn
    ss = _styles()
    elements = []
    dist = district.strip()

    elements.append(Paragraph(f"District Report — {dist}", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY, spaceAfter=8))

    # ── District Overview ──
    projects = [dict(r) for r in c.execute("""
        SELECT * FROM projects WHERE lower(district)=lower(?) ORDER BY project_id
    """, (dist,)).fetchall()]

    total_parcels = c.execute("SELECT COUNT(*) FROM parcels WHERE lower(district)=lower(?)", (dist,)).fetchone()[0]

    # Acquisition progress (average) - progress column may not exist
    try:
        avg_progress = c.execute("""
            SELECT AVG(progress) FROM projects WHERE lower(district)=lower(?) AND progress IS NOT NULL
        """, (dist,)).fetchone()[0] or 0
    except Exception:
        avg_progress = 0

    elements.extend(_kv_block([
        ("District", dist),
        ("State", "Tamil Nadu"),
        ("Total Projects", len(projects)),
        ("Total Parcels", total_parcels),
        ("Average Acquisition Progress", f"{avg_progress:.1f}%"),
    ], ss))

    # ── Compensation Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Compensation Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        comp = c.execute("""
            SELECT COUNT(*) as cnt,
                   COALESCE(SUM(co.assessed_amount),0) as total_assessed,
                   COALESCE(SUM(co.paid_amount),0) as total_paid,
                   COALESCE(SUM(co.pending_amount),0) as total_pending,
                   SUM(CASE WHEN co.status='Paid' THEN 1 ELSE 0 END) as paid_count
            FROM compensation co
            JOIN parcels p ON co.parcel_id=p.id
            WHERE lower(p.district)=lower(?)
        """, (dist,)).fetchone()
        comp = dict(comp) if comp else {}
    except Exception:
        comp = {}

    elements.extend(_kv_block([
        ("Total Records", comp.get("cnt", 0)),
        ("Total Assessed", _fmt_amount(comp.get("total_assessed"))),
        ("Total Paid", _fmt_amount(comp.get("total_paid"))),
        ("Total Pending", _fmt_amount(comp.get("total_pending"))),
        ("Paid Count", comp.get("paid_count", 0)),
    ], ss))

    # ── R&R Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("R&R Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        rr = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN rr.status='Completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN rr.status='Pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN rr.status='Delayed' THEN 1 ELSE 0 END) as delayed
            FROM r_and_r rr
            JOIN projects p ON rr.project_id=p.project_id
            WHERE lower(p.district)=lower(?)
        """, (dist,)).fetchone()
        rr = dict(rr) if rr else {}
    except Exception:
        rr = {}

    try:
        rr_fam = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END) as high_risk,
                   SUM(CASE WHEN risk_level='Medium' THEN 1 ELSE 0 END) as med_risk,
                   SUM(CASE WHEN risk_level='Low' THEN 1 ELSE 0 END) as low_risk,
                   SUM(CASE WHEN verification_status='Verified' THEN 1 ELSE 0 END) as verified
            FROM rr_families WHERE lower(district)=lower(?)
        """, (dist,)).fetchone()
        rr_fam = dict(rr_fam) if rr_fam else {}
    except Exception:
        rr_fam = {}

    elements.extend(_kv_block([
        ("Total R&R Records", rr.get("total", 0)),
        ("Completed", rr.get("completed", 0)),
        ("Pending", rr.get("pending", 0)),
        ("Delayed", rr.get("delayed", 0)),
        ("RR Families (detailed)", rr_fam.get("total", 0)),
        ("High Risk", rr_fam.get("high_risk", 0)),
        ("Medium Risk", rr_fam.get("med_risk", 0)),
        ("Low Risk", rr_fam.get("low_risk", 0)),
        ("Verified", rr_fam.get("verified", 0)),
    ], ss))

    # ── Field Verification Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Field Verification Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        fv = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN fa.status='Verified' THEN 1 ELSE 0 END) as verified,
                   SUM(CASE WHEN fa.status='Pending Verification' THEN 1 ELSE 0 END) as pending
            FROM field_assignments fa
            JOIN parcels p ON fa.parcel_id=p.id
            WHERE lower(p.district)=lower(?)
        """, (dist,)).fetchone()
        fv = dict(fv) if fv else {}
    except Exception:
        fv = {}

    elements.extend(_kv_block([
        ("Total Assignments", fv.get("total", 0)),
        ("Verified", fv.get("verified", 0)),
        ("Pending", fv.get("pending", 0)),
    ], ss))

    # ── Grievances ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Grievance Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        grv = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN g.status='Open' THEN 1 ELSE 0 END) as open_count,
                   SUM(CASE WHEN g.status='Resolved' THEN 1 ELSE 0 END) as resolved
            FROM grievances g
            LEFT JOIN projects pr ON g.project_id=pr.project_id
            LEFT JOIN parcels pa ON g.parcel_id=pa.id
            WHERE lower(pr.district)=lower(?) OR lower(pa.district)=lower(?)
        """, (dist, dist)).fetchone()
        grv = dict(grv) if grv else {}
    except Exception:
        grv = {}

    try:
        rr_grv = c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status NOT IN ('Resolved','Closed') THEN 1 ELSE 0 END) as open_count
            FROM rr_grievances WHERE lower(district)=lower(?)
        """, (dist,)).fetchone()
        rr_grv = dict(rr_grv) if rr_grv else {}
    except Exception:
        rr_grv = {}

    elements.extend(_kv_block([
        ("Total Grievances", grv.get("total", 0)),
        ("Open", grv.get("open_count", 0)),
        ("Resolved", grv.get("resolved", 0)),
        ("R&R Grievances", rr_grv.get("total", 0)),
        ("R&R Open", rr_grv.get("open_count", 0)),
    ], ss))

    # ── SLA & Bottleneck ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("SLA Breaches & Bottlenecks", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        sla_breached = c.execute("""
            SELECT COUNT(*) FROM project_milestones m
            JOIN projects p ON m.project_id=p.project_id
            WHERE lower(p.district)=lower(?) AND m.delay_days > 0
        """, (dist,)).fetchone()[0]

        bottleneck_count = c.execute("""
            SELECT COUNT(*) FROM project_milestones m
            JOIN projects p ON m.project_id=p.project_id
            WHERE lower(p.district)=lower(?)
              AND m.status != 'Completed'
              AND (m.delay_days > 0 OR (m.planned_date IS NOT NULL AND julianday('now') > julianday(m.planned_date)))
        """, (dist,)).fetchone()[0]
    except Exception:
        sla_breached = 0
        bottleneck_count = 0

    elements.extend(_kv_block([
        ("SLA Breached Milestones", sla_breached),
        ("Active Bottlenecks", bottleneck_count),
    ], ss))

    # ── Risk Distribution ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Risk Distribution", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    try:
        risk_rows = [dict(r) for r in c.execute("""
            SELECT risk_category, COUNT(*) as cnt
            FROM parcels WHERE lower(district)=lower(?) AND risk_category IS NOT NULL
            GROUP BY risk_category ORDER BY cnt DESC
        """, (dist,)).fetchall()]
    except Exception:
        risk_rows = []

    if risk_rows:
        elements.append(_make_table(
            ["Risk Category", "Parcel Count"],
            [[r["risk_category"], r["cnt"]] for r in risk_rows],
            col_widths=[250, 200]
        ))

    # ── Legal Disputes ──
    try:
        legal_count = c.execute("""
            SELECT COUNT(*) FROM parcels
            WHERE lower(district)=lower(?) AND legal_disputes IS NOT NULL
              AND legal_disputes != '' AND legal_disputes != '0' AND legal_disputes != 'No'
        """, (dist,)).fetchone()[0]
    except Exception:
        legal_count = 0

    elements.append(Spacer(1, 6))
    elements.extend(_kv_block([("Parcels with Legal Disputes", legal_count)], ss))

    # ── Project-wise breakdown ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Project-wise Breakdown", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    if projects:
        pw_headers = ["Project ID", "Name", "Type", "Taluk", "Parcels", "Families"]
        pw_rows = [
            [p["project_id"], (p.get("project_name") or "")[:35], _safe(p.get("project_type")),
             _safe(p.get("taluk")),
             _safe(p.get("affected_parcels"), "0"), _safe(p.get("affected_families"), "0")]
            for p in projects[:100]
        ]
        elements.append(_make_table(pw_headers, pw_rows, col_widths=[70, 130, 90, 80, 50, 50]))
        if len(projects) > 100:
            elements.append(Paragraph(f"<i>... and {len(projects)-100} more projects</i>", ss['BodySmall']))

    # ── Project-wise Bottleneck Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Project-wise Bottleneck Summary", ss['SubSection']))

    try:
        bn_summary = [dict(r) for r in c.execute("""
            SELECT p.project_id, p.project_name, COUNT(m.id) as bottleneck_count,
                   MAX(m.delay_days) as max_delay
            FROM project_milestones m
            JOIN projects p ON m.project_id=p.project_id
            WHERE lower(p.district)=lower(?)
              AND m.status != 'Completed'
              AND (m.delay_days > 0 OR (m.planned_date IS NOT NULL AND julianday('now') > julianday(m.planned_date)))
            GROUP BY p.project_id
            ORDER BY max_delay DESC
        """, (dist,)).fetchall()]
    except Exception:
        bn_summary = []

    if bn_summary:
        elements.append(_make_table(
            ["Project ID", "Project Name", "Bottlenecks", "Max Delay (days)"],
            [[b["project_id"], (b.get("project_name") or "")[:40], b["bottleneck_count"], b.get("max_delay", 0)] for b in bn_summary[:50]],
            col_widths=[80, 180, 80, 80]
        ))

    # ── District Performance Summary ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("District Performance Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    completed_projects = sum(1 for p in projects if p.get("project_status") == "Completed")
    active_projects = sum(1 for p in projects if p.get("project_status") in ("Active", "In Progress", None))

    elements.extend(_kv_block([
        ("Total Projects", len(projects)),
        ("Active Projects", active_projects),
        ("Completed Projects", completed_projects),
        ("Average Progress", f"{avg_progress:.1f}%"),
        ("Total Parcels", total_parcels),
        ("SLA Breached", sla_breached),
        ("Bottleneck Count", bottleneck_count),
        ("Grievances", grv.get("total", 0)),
        ("Legal Disputes", legal_count),
        ("Compensation Paid", _fmt_amount(comp.get("total_paid"))),
        ("Compensation Pending", _fmt_amount(comp.get("total_pending"))),
        ("R&R Completed", rr.get("completed", 0)),
        ("R&R Pending", rr.get("pending", 0)),
    ], ss))

    return _build_pdf(
        elements,
        f"District Report — {dist}",
        f"{dist} District, Tamil Nadu"
    )


# ═══════════════════════════════════════════════════════════════
#  D) STATE DISTRICT-WISE REPORT
# ═══════════════════════════════════════════════════════════════
def generate_state_report(db_conn, districts=None) -> bytes:
    """Generate a state-level PDF report comparing all districts."""
    c = db_conn
    ss = _styles()
    elements = []

    if not districts:
        districts = ["Coimbatore", "Tiruppur", "Erode", "Salem", "Namakkal"]

    elements.append(Paragraph("State District-wise Report — Tamil Nadu", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_PRIMARY, spaceAfter=8))

    # ── State-level Summary ──
    total_projects = c.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    total_parcels = c.execute("SELECT COUNT(*) FROM parcels").fetchone()[0]
    try:
        avg_progress = c.execute("SELECT AVG(progress) FROM projects WHERE progress IS NOT NULL").fetchone()[0] or 0
    except Exception:
        avg_progress = 0

    elements.extend(_kv_block([
        ("State", "Tamil Nadu"),
        ("Total Districts", len(districts)),
        ("Total Projects (all districts)", total_projects),
        ("Total Parcels (all districts)", total_parcels),
        ("Overall Average Progress", f"{avg_progress:.1f}%"),
    ], ss))

    # ── District Comparison Table ──
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("District Comparison", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    dist_data = []
    for dist in districts:
        d = {}
        d["district"] = dist
        d["projects"] = c.execute("SELECT COUNT(*) FROM projects WHERE lower(district)=lower(?)", (dist,)).fetchone()[0]
        d["parcels"] = c.execute("SELECT COUNT(*) FROM parcels WHERE lower(district)=lower(?)", (dist,)).fetchone()[0]
        try:
            d["avg_progress"] = c.execute("SELECT AVG(progress) FROM projects WHERE lower(district)=lower(?) AND progress IS NOT NULL", (dist,)).fetchone()[0] or 0
        except Exception:
            d["avg_progress"] = 0

        try:
            comp = c.execute("""
                SELECT COALESCE(SUM(co.paid_amount),0) as paid,
                       COALESCE(SUM(co.pending_amount),0) as pending
                FROM compensation co JOIN parcels p ON co.parcel_id=p.id
                WHERE lower(p.district)=lower(?)
            """, (dist,)).fetchone()
            d["comp_paid"] = comp["paid"] if comp else 0
            d["comp_pending"] = comp["pending"] if comp else 0
        except Exception:
            d["comp_paid"] = 0
            d["comp_pending"] = 0

        try:
            rr = c.execute("""
                SELECT SUM(CASE WHEN rr.status='Completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN rr.status='Pending' THEN 1 ELSE 0 END) as pending
                FROM r_and_r rr JOIN projects p ON rr.project_id=p.project_id
                WHERE lower(p.district)=lower(?)
            """, (dist,)).fetchone()
            d["rr_completed"] = (rr["completed"] or 0) if rr else 0
            d["rr_pending"] = (rr["pending"] or 0) if rr else 0
        except Exception:
            d["rr_completed"] = 0
            d["rr_pending"] = 0

        try:
            d["bottlenecks"] = c.execute("""
                SELECT COUNT(*) FROM project_milestones m
                JOIN projects p ON m.project_id=p.project_id
                WHERE lower(p.district)=lower(?) AND m.status != 'Completed'
                  AND (m.delay_days > 0 OR (m.planned_date IS NOT NULL AND julianday('now') > julianday(m.planned_date)))
            """, (dist,)).fetchone()[0]

            d["sla_breaches"] = c.execute("""
                SELECT COUNT(*) FROM project_milestones m
                JOIN projects p ON m.project_id=p.project_id
                WHERE lower(p.district)=lower(?) AND m.delay_days > 0
            """, (dist,)).fetchone()[0]
        except Exception:
            d["bottlenecks"] = 0
            d["sla_breaches"] = 0

        try:
            d["high_risk"] = c.execute("""
                SELECT COUNT(*) FROM parcels
                WHERE lower(district)=lower(?) AND risk_category IN ('HIGH', 'CRITICAL')
            """, (dist,)).fetchone()[0]
        except Exception:
            d["high_risk"] = 0

        try:
            grv = c.execute("""
                SELECT COUNT(*) FROM grievances g
                LEFT JOIN projects pr ON g.project_id=pr.project_id
                LEFT JOIN parcels pa ON g.parcel_id=pa.id
                WHERE lower(pr.district)=lower(?) OR lower(pa.district)=lower(?)
            """, (dist, dist)).fetchone()[0]
            rr_grv = c.execute("""
                SELECT COUNT(*) FROM rr_grievances WHERE lower(district)=lower(?)
            """, (dist,)).fetchone()[0]
            d["grievances"] = grv + rr_grv
        except Exception:
            d["grievances"] = 0

        dist_data.append(d)

    # Main comparison table
    comp_headers = ["District", "Projects", "Parcels", "Acq %", "Comp Paid", "R&R Done",
                    "R&R Pending", "Bottlenecks", "SLA Breach", "High Risk", "Grievances"]
    comp_rows = [
        [dd["district"], dd["projects"], dd["parcels"], f"{dd['avg_progress']:.1f}%",
         _fmt_amount(dd["comp_paid"]), dd["rr_completed"], dd["rr_pending"],
         dd["bottlenecks"], dd["sla_breaches"], dd["high_risk"], dd["grievances"]]
        for dd in dist_data
    ]
    # Totals row
    comp_rows.append([
        "TOTAL",
        sum(dd["projects"] for dd in dist_data),
        sum(dd["parcels"] for dd in dist_data),
        f"{avg_progress:.1f}%",
        _fmt_amount(sum(dd["comp_paid"] for dd in dist_data)),
        sum(dd["rr_completed"] for dd in dist_data),
        sum(dd["rr_pending"] for dd in dist_data),
        sum(dd["bottlenecks"] for dd in dist_data),
        sum(dd["sla_breaches"] for dd in dist_data),
        sum(dd["high_risk"] for dd in dist_data),
        sum(dd["grievances"] for dd in dist_data),
    ])

    elements.append(_make_table(comp_headers, comp_rows,
        col_widths=[65, 45, 45, 38, 60, 42, 48, 52, 48, 48, 48], font_size=7))

    # ── District Rankings ──
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("District Performance Ranking", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    # Rank by progress (descending)
    ranked_by_progress = sorted(dist_data, key=lambda x: x["avg_progress"], reverse=True)
    elements.append(Paragraph("<b>By Acquisition Progress (highest first):</b>", ss['BodySmall']))
    rank_rows = [[i+1, d["district"], f"{d['avg_progress']:.1f}%"] for i, d in enumerate(ranked_by_progress)]
    elements.append(_make_table(["Rank", "District", "Avg Progress"], rank_rows, col_widths=[50, 200, 100]))

    # Highest bottleneck district
    worst_bottleneck = max(dist_data, key=lambda x: x["bottlenecks"])
    worst_risk = max(dist_data, key=lambda x: x["high_risk"])

    elements.append(Spacer(1, 8))
    elements.extend(_kv_block([
        ("Highest Bottleneck District", f"{worst_bottleneck['district']} ({worst_bottleneck['bottlenecks']} bottlenecks)"),
        ("Highest Risk District", f"{worst_risk['district']} ({worst_risk['high_risk']} high/critical parcels)"),
    ], ss))

    # ── Compensation Progress Comparison ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Compensation Progress Comparison", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    comp_cmp_headers = ["District", "Compensation Paid", "Compensation Pending", "Paid %"]
    comp_cmp_rows = []
    for dd in dist_data:
        total_comp = dd["comp_paid"] + dd["comp_pending"]
        pct = f"{(dd['comp_paid']/total_comp*100):.1f}%" if total_comp > 0 else "N/A"
        comp_cmp_rows.append([dd["district"], _fmt_amount(dd["comp_paid"]), _fmt_amount(dd["comp_pending"]), pct])
    elements.append(_make_table(comp_cmp_headers, comp_cmp_rows, col_widths=[100, 130, 130, 80]))

    # ── R&R Progress Comparison ──
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("R&R Progress Comparison", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    rr_cmp_headers = ["District", "R&R Completed", "R&R Pending", "Completion %"]
    rr_cmp_rows = []
    for dd in dist_data:
        total_rr = dd["rr_completed"] + dd["rr_pending"]
        pct = f"{(dd['rr_completed']/total_rr*100):.1f}%" if total_rr > 0 else "N/A"
        rr_cmp_rows.append([dd["district"], dd["rr_completed"], dd["rr_pending"], pct])
    elements.append(_make_table(rr_cmp_headers, rr_cmp_rows, col_widths=[100, 130, 130, 80]))

    # ── Overall State Summary ──
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("Overall State Summary", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    elements.extend(_kv_block([
        ("State", "Tamil Nadu"),
        ("Total Districts Covered", len(districts)),
        ("Total Projects", sum(dd["projects"] for dd in dist_data)),
        ("Total Parcels", sum(dd["parcels"] for dd in dist_data)),
        ("Overall Progress", f"{avg_progress:.1f}%"),
        ("Total Compensation Paid", _fmt_amount(sum(dd["comp_paid"] for dd in dist_data))),
        ("Total Compensation Pending", _fmt_amount(sum(dd["comp_pending"] for dd in dist_data))),
        ("Total R&R Completed", sum(dd["rr_completed"] for dd in dist_data)),
        ("Total R&R Pending", sum(dd["rr_pending"] for dd in dist_data)),
        ("Total Bottlenecks", sum(dd["bottlenecks"] for dd in dist_data)),
        ("Total SLA Breaches", sum(dd["sla_breaches"] for dd in dist_data)),
        ("Total High Risk Parcels", sum(dd["high_risk"] for dd in dist_data)),
        ("Total Grievances", sum(dd["grievances"] for dd in dist_data)),
    ], ss))

    return _build_pdf(
        elements,
        "State District-wise Report — Tamil Nadu",
        "All Districts"
    )


def generate_privacy_safe_pdf(doc_info: dict, privacy_eval: dict, purpose: str, user_info: dict, policy_version: str = "v2.0-TN-GOV-PRIVACY-GUARD"):
    """
    Generate a formal Government of India / Tamil Nadu Department style Privacy-Safe PDF.
    Masks unauthorized sensitive fields and includes an auditable Privacy Processing Summary.
    """
    ss = _styles()
    elements = []

    doc_id = doc_info.get("document_id", "N/A")
    parcel_id = doc_info.get("parcel_id", "N/A")
    project_id = doc_info.get("project_id", "N/A")
    survey_no = doc_info.get("survey_no", "N/A")
    village = doc_info.get("village", "N/A")
    taluk = doc_info.get("taluk", "N/A")
    district = doc_info.get("district", "N/A")
    doc_name = doc_info.get("document_name", "Land Record Document")
    doc_date = doc_info.get("document_date", datetime.now().strftime("%Y-%m-%d"))

    # ── Privacy Banner & Watermark Header ──
    elements.append(Paragraph("GOVERNMENT OF TAMIL NADU · LAND ACQUISITION & REVENUE DEPARTMENT", ParagraphStyle("GovHeader", parent=ss["Normal"], fontSize=10, fontName="Helvetica-Bold", textColor=BRAND_PRIMARY, alignment=TA_CENTER)))
    elements.append(Paragraph("PURPOSE-AWARE PRIVACY-SAFE DISCLOSURE COPY", ParagraphStyle("SafeDocTitle", parent=ss["Heading1"], fontSize=15, fontName="Helvetica-Bold", textColor=BRAND_DARK, alignment=TA_CENTER, spaceAfter=4)))
    elements.append(Paragraph(f"Authorized Operational Purpose: <b>{purpose.replace('_', ' ').title()}</b> · Policy Version: <b>{policy_version}</b>", ParagraphStyle("PurposeSub", parent=ss["Normal"], fontSize=9, textColor=HexColor("#475569"), alignment=TA_CENTER, spaceAfter=10)))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_PRIMARY, spaceAfter=10))

    # ── Security & Risk Assessment Summary Box ──
    risk_level = privacy_eval.get("risk_level", "LOW")
    risk_score = privacy_eval.get("risk_score", 0)
    summary = privacy_eval.get("summary", {})

    risk_badge_color = HexColor("#dc2626") if risk_level == "CRITICAL" else HexColor("#ea580c") if risk_level == "HIGH" else HexColor("#d97706") if risk_level == "MEDIUM" else HexColor("#16a34a")

    summary_table_data = [
        [
            Paragraph("<b>DOCUMENT CLASSIFICATION:</b>", ss["KVLabel"]),
            Paragraph(f"<font color='{risk_badge_color}'><b>PRIVACY RISK: {risk_score}/100 ({risk_level})</b></font>", ss["KVValue"]),
            Paragraph("<b>DISCLOSURE STATUS:</b>", ss["KVLabel"]),
            Paragraph("<b>CONTROLLED / MINIMISED</b>", ss["KVValue"])
        ],
        [
            Paragraph("<b>Total Sensitive Entities:</b>", ss["KVLabel"]),
            Paragraph(f"<b>{summary.get('total_detected', 0)} Detected</b>", ss["KVValue"]),
            Paragraph("<b>Fields Masked / Redacted:</b>", ss["KVLabel"]),
            Paragraph(f"<b>{summary.get('masked', 0) + summary.get('redacted', 0)} Protected</b>", ss["KVValue"])
        ]
    ]
    t_summary = Table(summary_table_data, colWidths=[130, 120, 120, 130])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 10))

    # ── Section 1: Land Parcel & Document Metadata ──
    elements.append(Paragraph("1. Land Document Identification & Geospatial Metadata", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    elements.extend(_kv_block([
        ("Document ID", doc_id),
        ("Document File Name", doc_name),
        ("Project Reference", project_id),
        ("Parcel ID", str(parcel_id)),
        ("Survey / Subdivision Number", str(survey_no)),
        ("Village / Taluk", f"{village} / {taluk}"),
        ("Revenue District", district),
        ("Document / Deed Date", str(doc_date))
    ], ss))

    elements.append(Spacer(1, 10))

    # ── Section 2: Purpose-Controlled Field Disclosure & Masking Ledger ──
    elements.append(Paragraph("2. Purpose-Controlled Field Disclosures & Protection Status", ss['SectionTitle']))
    elements.append(Paragraph("Personal, biometric, and financial identifiers are masked in compliance with purpose minimisation principles.", ss['BodySmall']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    headers = ["Field / Information Entity", "Category", "Disclosure Status", "Disclosed / Masked Value", "Purpose Rationale"]
    rows = []
    
    for f in privacy_eval.get("fields", []):
        vis = f.get("visibility", "MASKED")
        cat = f.get("category", "OPERATIONAL")
        label = f.get("field_label", f.get("field_key", ""))
        disp_val = f.get("display_value", f.get("masked_value", "XXXX"))
        reason = f.get("reason_why", "Controlled disclosure")
        
        status_color = "#16a34a" if vis in ("VISIBLE", "AUTHORIZED") else "#dc2626" if vis == "REDACTED" else "#ea580c"
        status_cell = f"<font color='{status_color}'><b>{vis}</b></font>"

        rows.append([
            label,
            cat,
            status_cell,
            f"<b>{disp_val}</b>",
            reason
        ])

    elements.append(_make_table(headers, rows, col_widths=[110, 65, 75, 120, 130], font_size=7))

    elements.append(Spacer(1, 12))

    # ── Section 3: Privacy Processing & Audit Compliance Summary ──
    elements.append(Paragraph("3. Privacy Governance, Audit & Verification Ledger", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    auth_email = user_info.get("email", "officer@tngov.in")
    auth_role = user_info.get("role", "acquisition_officer").replace("_", " ").title()
    gen_time = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")
    
    import hashlib
    fingerprint = hashlib.sha256(f"{doc_id}:{purpose}:{auth_email}:{gen_time}".encode()).hexdigest()[:24].upper()

    elements.extend(_kv_block([
        ("Operational Purpose", purpose.replace("_", " ").title()),
        ("Generated By", f"{auth_email} ({auth_role})"),
        ("Access Authorization Level", "Purpose-Minimised Operational Copy"),
        ("Generation Timestamp", gen_time),
        ("Applied Privacy Policy", f"Tamil Nadu Smart Land Acquisition Privacy Protocol ({policy_version})"),
        ("Audit Ledger Reference Fingerprint", f"SHA256:{fingerprint}")
    ], ss))

    elements.append(Spacer(1, 10))
    notice_text = (
        "<b>LEGAL & COMPLIANCE NOTICE:</b> This document is a purpose-minimised privacy-safe copy generated "
        "dynamically by the LANDNEXUS Platform. Sensitive national identity (Aadhaar/PAN) and banking identifiers "
        "have been masked in accordance with purpose-based data minimisation principles. The original archival "
        "deed remains unchanged in the secure government evidence repository."
    )
    elements.append(Paragraph(notice_text, ParagraphStyle("NoticeStyle", parent=ss["Normal"], fontSize=7, textColor=HexColor("#64748b"), leading=9)))

    return _build_pdf(
        elements,
        f"Privacy-Safe Land Record — {doc_id[:12]}",
        f"Purpose: {purpose.replace('_', ' ').title()}"
    )


# ═══════════════════════════════════════════════════════════════
#  E) INDIVIDUAL PARCEL INTELLIGENCE DOSSIER REPORT
# ═══════════════════════════════════════════════════════════════
def generate_parcel_report(db_conn, parcel_id_or_record_id, user_info=None) -> bytes:
    """Generate a comprehensive government-grade PDF dossier for an individual land parcel."""
    c = db_conn
    pid = parcel_id_or_record_id
    
    # Try finding parcel by id or record_id
    row = None
    if isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit()):
        row = c.execute("SELECT * FROM parcels WHERE id = ?", (int(pid),)).fetchone()
    if not row and isinstance(pid, str):
        row = c.execute("SELECT * FROM parcels WHERE record_id = ?", (pid,)).fetchone()
    if not row:
        row = c.execute("SELECT * FROM parcels WHERE id = ?", (pid,)).fetchone()
    if not row:
        raise ValueError(f"Parcel '{parcel_id_or_record_id}' not found")
        
    p = dict(row)
    actual_id = p["id"]
    ss = _styles()
    elements = []
    
    # Header title & subtitle
    survey_label = f"{p.get('survey_no') or 'N/A'}/{p.get('subdivision') or 'N/A'}"
    village_loc = f"{p.get('village') or ''}, {p.get('taluk') or ''}, {p.get('district') or ''}".strip(", ")
    
    # ── Section 1: Executive Summary & Geographic Location ──
    elements.append(Paragraph("1. Parcel Identification & Cadastral Details", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    lat = p.get("latitude")
    lon = p.get("longitude")
    if lat is not None and lon is not None and str(lat).strip() != "" and str(lon).strip() != "":
        gps_display = f"{float(lat):.6f}° N, {float(lon):.6f}° E (GPS Verified)"
        gmaps_info = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    else:
        gps_display = "Coordinates Not Available (Pending DGPS/ETS Field Survey)"
        gmaps_info = "Google Maps unavailable: coordinates missing"
        
    elements.extend(_kv_block([
        ("Parcel Record ID", p.get("record_id") or f"PCL-{p.get('id'):06d}"),
        ("Survey / Subdivision", survey_label),
        ("Revenue Village", _safe(p.get("village"))),
        ("Taluk / Tehsil", _safe(p.get("taluk"))),
        ("District", _safe(p.get("district"))),
        ("Land Extent / Area", f"{p.get('area', 0)} {p.get('area_unit', 'Acres')}"),
        ("Land Classification", _safe(p.get("classification"))),
        ("Current Land Use", _safe(p.get("land_use", "Agricultural / Unspecified"))),
        ("Acquisition Status / Stage", _safe(p.get("acquisition_status", "Proposal"))),
        ("Geographic Coordinates", gps_display),
        ("Google Maps Reference Link", gmaps_info)
    ], ss))
    
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<i>Cadastral Spatial Notice: Demonstration GIS geometry — not an authoritative cadastral boundary. Authoritative boundary requires revenue survey confirmation.</i>", ss['BodySmall']))
    elements.append(Spacer(1, 10))
    
    # ── Section 2: Project Linkage ──
    elements.append(Paragraph("2. Project Alignment & Infrastructure Purpose", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    proj_id = p.get("project_id")
    proj_row = c.execute("SELECT * FROM projects WHERE project_id = ?", (proj_id,)).fetchone() if proj_id else None
    if proj_row:
        pr = dict(proj_row)
        elements.extend(_kv_block([
            ("Project ID", pr.get("project_id", "N/A")),
            ("Project Name", pr.get("name", "N/A")),
            ("Executing Department / Agency", pr.get("department", "Public Works / Highways")),
            ("Project Category / Type", pr.get("project_type", p.get("project_type", "Infrastructure"))),
            ("Priority Level", pr.get("priority", "Normal")),
            ("Total Land Extent Required", f"{pr.get('land_required', 0)} Acres")
        ], ss))
    else:
        elements.append(Paragraph("Parcel is currently unassigned or standalone.", ss['BodySmall']))
    elements.append(Spacer(1, 10))
    
    # ── Section 3: AI Risk Intelligence & Stage Bottlenecks ──
    elements.append(Paragraph("3. AI Acquisition Risk & Predictive Intelligence", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    risk_cat = (p.get("risk_category") or "LOW").upper()
    risk_score = float(p.get("risk_score") or 0)
    delay_prob = float(p.get("delay_probability") or p.get("risk_probability") or 0) * 100
    pred_delay = p.get("delay_days", 0)
    
    elements.extend(_kv_block([
        ("Composite Risk Category", f"{risk_cat} (Risk Score: {risk_score:.1f}/100)"),
        ("Delay Probability", f"{delay_prob:.1f}%"),
        ("Estimated Delay Window", f"{pred_delay} Days"),
        ("Legal Disputes Pending", "Yes (Litigation Flagged)" if p.get("legal_disputes") else "None Reported"),
        ("Compensation Pending", "Yes (Award/Disbursement Incomplete)" if p.get("compensation_pending") else "Disbursed / Not Pending"),
        ("Approval / Consent Pending", "Yes" if p.get("approval_pending") else "Cleared"),
        ("Documentation / Title Status", "Pending Verification" if p.get("documentation_pending") else "Verified"),
        ("R&R Pending", "Yes" if p.get("rehabilitation_pending") else "Not Applicable / Settled")
    ], ss))
    elements.append(Spacer(1, 10))
    
    # ── Section 4: Compensation & Rehabilitation (R&R) ──
    elements.append(Paragraph("4. Compensation Assessment & Rehabilitation Status", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    comp_rows = c.execute("SELECT * FROM compensation WHERE parcel_id = ?", (actual_id,)).fetchall()
    if comp_rows:
        comp_headers = ["Award Ref", "Assessed Amt", "Approved Amt", "Paid Amt", "Pending Amt", "Status"]
        comp_data = []
        for cr in comp_rows:
            crd = dict(cr)
            comp_data.append([
                _safe(crd.get("award_reference", crd.get("award_number", f"CMP-{crd.get('id', 'N/A')}"))),
                _fmt_amount(crd.get("assessed_amount", crd.get("market_value", 0))),
                _fmt_amount(crd.get("approved_amount", crd.get("total_compensation", 0))),
                _fmt_amount(crd.get("paid_amount", crd.get("disbursed_amount", 0))),
                _fmt_amount(crd.get("pending_amount", 0)),
                _safe(crd.get("status", "Pending"))
            ])
        elements.append(_make_table(comp_headers, comp_data, col_widths=[85, 85, 85, 85, 80, 70], font_size=7))
    else:
        elements.append(Paragraph("No formal Section 23/30 compensation determination record logged yet.", ss['BodySmall']))
        
    elements.append(Spacer(1, 10))
    
    # ── Section 5: Documents & OCR Intelligence ──
    elements.append(Paragraph("5. Linked Title Documents & OCR Intelligence", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    doc_rows = c.execute("SELECT * FROM documents WHERE parcel_id = ? ORDER BY id DESC", (actual_id,)).fetchall()
    if doc_rows:
        doc_headers = ["Doc ID", "Document Title", "Document Type", "File Format", "Verification Status", "Upload Date"]
        doc_data = []
        for dr in doc_rows:
            drd = dict(dr)
            doc_data.append([
                _safe(drd.get("document_id", f"DOC-{drd.get('id')}"))[:14],
                _safe(drd.get("document_name", "Land Document"))[:25],
                _safe(drd.get("document_type", "Deed")),
                _safe(drd.get("format", "PDF")).upper(),
                _safe(drd.get("status", drd.get("verification_status", "Active"))),
                _safe(drd.get("upload_date", drd.get("created_at", "N/A")))[:10]
            ])
        elements.append(_make_table(doc_headers, doc_data, col_widths=[80, 150, 80, 50, 70, 70], font_size=7))
    else:
        elements.append(Paragraph("No documents currently archived for this parcel.", ss['BodySmall']))
        
    elements.append(Spacer(1, 10))
    
    # ── Section 6: Field Verification & Inspections ──
    elements.append(Paragraph("6. Field Verification & Ground Truth Inspections", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    try:
        fv_rows = c.execute("SELECT * FROM field_verifications WHERE parcel_id = ? ORDER BY id DESC", (actual_id,)).fetchall()
    except Exception:
        fv_rows = []
    if fv_rows:
        fv_headers = ["Task Ref", "Field Officer", "Inspection Date", "Verification Result", "GPS Coordinates", "Remarks"]
        fv_data = []
        for fvr in fv_rows:
            fvrd = dict(fvr)
            fv_data.append([
                _safe(fvrd.get("task_id", f"VER-{fvrd.get('id')}"))[:12],
                _safe(fvrd.get("officer_email", fvrd.get("verified_by", "Officer")))[:20],
                _safe(fvrd.get("created_at", fvrd.get("verification_date", "N/A")))[:10],
                _safe(fvrd.get("status", "Completed")),
                f"{fvrd.get('gps_lat', '')}, {fvrd.get('gps_lon', '')}" if fvrd.get("gps_lat") else "Not Recorded",
                _safe(fvrd.get("remarks", "Inspection conducted"))[:30]
            ])
        elements.append(_make_table(fv_headers, fv_data, col_widths=[75, 100, 75, 75, 85, 90], font_size=7))
    else:
        elements.append(Paragraph("No physical field inspection records filed yet.", ss['BodySmall']))
        
    elements.append(Spacer(1, 10))
    
    # ── Section 7: Citizen Grievances & Disputes ──
    elements.append(Paragraph("7. Citizen Grievances & Objections", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    try:
        gr_rows = c.execute("SELECT * FROM grievances WHERE parcel_id = ? ORDER BY id DESC", (actual_id,)).fetchall()
    except Exception:
        gr_rows = []
    if gr_rows:
        gr_headers = ["Grievance Ref", "Category", "Filing Date", "Status", "Submitted By", "Description"]
        gr_data = []
        for gr in gr_rows:
            grd = dict(gr)
            gr_data.append([
                _safe(grd.get("grievance_id", f"GRV-{grd.get('id')}"))[:12],
                _safe(grd.get("type", grd.get("category", "Objection")))[:16],
                _safe(grd.get("created_at", grd.get("filed_date", "N/A")))[:10],
                _safe(grd.get("status", "Submitted")),
                _safe(grd.get("submitted_by", "Citizen"))[:18],
                _safe(grd.get("description", "Objection filed"))[:28]
            ])
        elements.append(_make_table(gr_headers, gr_data, col_widths=[75, 80, 70, 65, 75, 135], font_size=7))
    else:
        elements.append(Paragraph("No public objections or citizen grievances lodged against this parcel.", ss['BodySmall']))
        
    elements.append(Spacer(1, 10))
    
    # ── Section 8: Audit Trail & Official Governance ──
    elements.append(Paragraph("8. Official Audit Trail & Governance Log", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))
    
    try:
        audit_rows = c.execute("SELECT * FROM audit_logs WHERE entity_id = ? OR entity_id = ? ORDER BY id DESC LIMIT 5", (str(actual_id), str(p.get("record_id")))).fetchall()
    except Exception:
        audit_rows = []
    if audit_rows:
        aud_headers = ["Timestamp (UTC)", "Actor Email", "Action Performed", "Entity", "Log Details"]
        aud_data = []
        for ar in audit_rows:
            ard = dict(ar)
            aud_data.append([
                _safe(ard.get("timestamp", "N/A"))[:16],
                _safe(ard.get("user_email", "system"))[:20],
                _safe(ard.get("action", "UPDATE")),
                _safe(ard.get("entity_type", "parcel")),
                _safe(ard.get("new_value", ard.get("details", "-")))[:25]
            ])
        elements.append(_make_table(aud_headers, aud_data, col_widths=[85, 100, 85, 60, 170], font_size=7))
    else:
        elements.append(Paragraph("No audit log events recorded.", ss['BodySmall']))
        
    elements.append(Spacer(1, 14))
    
    # Government Sign-off & Privacy Protocol footer
    officer_email = user_info.get("email", "officer@tngov.in") if user_info else "officer@tngov.in"
    officer_role = (user_info.get("role", "Acquisition Officer") if user_info else "Acquisition Officer").replace("_", " ").title()
    gen_time = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")
    
    elements.extend(_kv_block([
        ("Generating Authority", f"{officer_email} ({officer_role})"),
        ("Dossier Generation Time", gen_time),
        ("Statutory Reference", "Right to Fair Compensation & Transparency in Land Acquisition (RFCTLARR) Act, 2013"),
        ("Compliance Protocol", "Tamil Nadu Smart Land Acquisition Purpose-Aware Governance Protocol")
    ], ss))
    
    return _build_pdf(
        elements,
        f"Individual Parcel Intelligence Dossier — {survey_label}",
        f"District: {p.get('district', 'Tamil Nadu')}"
    )


def generate_multilingual_ocr_report(db_conn, document_id: str, user_info: dict = None) -> bytes:
    """
    Generate an official government Multilingual Land Record OCR Intelligence Dossier.
    Includes document metadata, detected language/script, extraction confidence metrics,
    verification status, audit trail, and Purpose-Aware privacy masking.
    """
    c = db_conn
    d_row = c.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
    if not d_row:
        raise ValueError("Document not found")
    d = dict(d_row)

    extractions = c.execute("SELECT * FROM ocr_extractions WHERE document_id=?", (document_id,)).fetchall()
    extractions = [dict(e) for e in extractions]

    # Check parcel if linked
    parcel = None
    if d["parcel_id"]:
        p_row = c.execute("SELECT * FROM parcels WHERE id=?", (d["parcel_id"],)).fetchone()
        if p_row:
            parcel = dict(p_row)

    ss = _styles()
    elements = []

    # Title & Metadata Banner
    elements.append(Paragraph(f"Official Land Record OCR Dossier: {d['document_name']}", ss['SectionTitle']))
    elements.append(Paragraph(f"Document ID: {document_id} | Security Classification: OFFICIAL LAND RECORD", ss['SubSection']))
    elements.append(Spacer(1, 10))

    # Document Overview Block
    lang_name = d.get("language", "en").upper()
    lang_conf = round(float(d.get("language_confidence", 1.0) or 1.0) * 100, 1)
    ocr_conf = round(float(d.get("ocr_confidence", 0.0) or 0.0) * 100, 1)
    dup_text = "POTENTIAL DUPLICATE DETECTED" if d.get("duplicate_flag") else "Unique Record"

    doc_info = [
        ("Document File Name", _safe(d.get("document_name", "N/A"))),
        ("Format / Size", f"{_safe(d.get('format', 'PDF'))} / Processed"),
        ("Project Reference", _safe(d.get("project_id", "N/A"))),
        ("Parcel Reference ID", _safe(parcel.get("record_id", f"PARCEL-{d['parcel_id']}") if parcel else "Unlinked")),
        ("Detected Language", f"{lang_name} ({lang_conf}% confidence)"),
        ("OCR Processing Mode", _safe(d.get("processing_mode", "auto")).title()),
        ("OCR Engine Used", _safe(d.get("ocr_engine", "Tesseract Multilingual Engine"))),
        ("Overall Confidence", f"{ocr_conf}%"),
        ("Verification Status", _safe(d.get("verification_status", "Pending"))),
        ("Duplicate Status", dup_text),
        ("Verified By Officer", _safe(d.get("verified_by", "Pending Verification"))),
        ("Upload Timestamp", _safe(d.get("created_at", "N/A"))[:19]),
    ]
    elements.extend(_kv_block(doc_info, ss))
    elements.append(Spacer(1, 12))

    # Section 2: Multilingual Extracted Fields
    elements.append(Paragraph("1. Normalized Multilingual Land Record Extractions", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    if extractions:
        ext_headers = ["Field Name", "Extracted Value", "Confidence", "Validation Status", "Human Verified"]
        ext_data = []
        for e in extractions:
            conf_val = round(float(e.get("confidence", 1.0) or 1.0) * 100, 1)
            verified_label = "YES (Officer Confirmed)" if e.get("human_verified") else "NO (AI Extraction)"
            val_text = _safe(e.get("corrected_value") or e.get("value") or "-")
            ext_data.append([
                _safe(e.get("field_name", "")).replace("_", " ").title(),
                val_text[:40],
                f"{conf_val}%",
                _safe(e.get("validation_status", "Pending")),
                verified_label
            ])
        elements.append(_make_table(ext_headers, ext_data, col_widths=[120, 160, 65, 85, 100], font_size=7))
    else:
        elements.append(Paragraph("No structured OCR extractions available for this document.", ss['BodySmall']))

    elements.append(Spacer(1, 14))

    # Section 3: Active Learning & Retraining Audit
    elements.append(Paragraph("2. Active Learning Feedback & Corrections Ledger", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    learn_rows = c.execute("SELECT * FROM ocr_learning_records WHERE document_id=? ORDER BY id DESC LIMIT 10", (document_id,)).fetchall()
    if learn_rows:
        lr_headers = ["Field", "Original (AI)", "Corrected (Human)", "Verified By", "Model Version", "Status"]
        lr_data = []
        for lr in learn_rows:
            lrd = dict(lr)
            lr_data.append([
                _safe(lrd.get("field_name", "")).replace("_", " ").title(),
                _safe(lrd.get("original_value", "-"))[:20],
                _safe(lrd.get("corrected_value", "-"))[:20],
                _safe(lrd.get("verified_by", "Officer"))[:18],
                _safe(lrd.get("model_version", "v1.0.0")),
                _safe(lrd.get("status", "Pending Retraining"))
            ])
        elements.append(_make_table(lr_headers, lr_data, col_widths=[90, 100, 100, 90, 75, 75], font_size=7))
    else:
        elements.append(Paragraph("No human corrections recorded for this document (AI extractions accepted or pending review).", ss['BodySmall']))

    elements.append(Spacer(1, 14))

    # Section 4: Privacy & Compliance Verification
    elements.append(Paragraph("3. Statutory Compliance & Purpose-Aware Redaction Certification", ss['SectionTitle']))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_PRIMARY, spaceAfter=6))

    actor_email = user_info.get("email", "officer@tngov.in") if user_info else "officer@tngov.in"
    actor_role = (user_info.get("role", "Acquisition Officer") if user_info else "Acquisition Officer").replace("_", " ").title()
    gen_time = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC")

    cert_info = [
        ("Certifying Officer", f"{actor_email} ({actor_role})"),
        ("Dossier Generation Time", gen_time),
        ("Statutory Protocol", "Right to Fair Compensation & Transparency in Land Acquisition (RFCTLARR) Act, 2013"),
        ("Multilingual Script Engine", "Unicode Statistical Distribution & Tesseract Indian-Language Model Stack"),
        ("PII Protection Guard", "Compliant with Purpose-Aware Redaction Protocol (Raw Aadhaar/PAN Suppressed)"),
    ]
    elements.extend(_kv_block(cert_info, ss))

    return _build_pdf(
        elements,
        f"Multilingual OCR Dossier — {d.get('document_name', document_id)}",
        f"District: {parcel.get('district', 'Tamil Nadu') if parcel else 'Tamil Nadu'}"
    )



