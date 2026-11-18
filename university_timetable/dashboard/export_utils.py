"""
EXPORT UTILITIES — University Timetabling MAS
Generates downloadable Excel and PDF timetables.
"""
import io
import pandas as pd

DAYS  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIMES = ["08:00-10:00", "10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"]


# ─────────────────────────────────────────────────────────────
# EXCEL EXPORT
# ─────────────────────────────────────────────────────────────

def export_timetable_excel(sched_df, title="University Timetable"):
    """
    Generates an Excel workbook with:
      Sheet 1 — Visual timetable grid (days × time slots)
      Sheet 2 — Full session list (raw data)
      Sheet 3 — Per-group timetables
    Returns bytes buffer ready for st.download_button.
    """
    import openpyxl
    from openpyxl.styles import (PatternFill, Font, Alignment,
                                  Border, Side, GradientFill)
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    # ── Styles ──────────────────────────────────────────────
    navy   = "042C53"
    teal   = "1D9E75"
    light  = "EBF5FB"
    amber  = "FEF3C7"
    pink   = "FCE7F3"
    green  = "DCFCE7"
    white  = "FFFFFF"
    gray   = "F8FAFC"

    def hdr_cell(ws, row, col, value, bg=navy, fg=white, bold=True, sz=11):
        c = ws.cell(row=row, column=col, value=value)
        c.fill = PatternFill("solid", fgColor=bg)
        c.font = Font(bold=bold, color=fg, size=sz)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin = Side(style="thin", color="CCCCCC")
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        return c

    def data_cell(ws, row, col, value, bg=white, bold=False, sz=10, wrap=True):
        c = ws.cell(row=row, column=col, value=value)
        c.fill = PatternFill("solid", fgColor=bg)
        c.font = Font(bold=bold, color="1A1A2E", size=sz)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=wrap)
        thin = Side(style="thin", color="E0E0E0")
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        return c

    # ── SHEET 1: Grid timetable ──────────────────────────────
    ws1 = wb.active
    ws1.title = "Timetable Grid"

    # Title row
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
    tc = ws1.cell(row=1, column=1, value=title)
    tc.fill = PatternFill("solid", fgColor=navy)
    tc.font = Font(bold=True, color=white, size=14)
    tc.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 30

    # Header row
    hdr_cell(ws1, 2, 1, "Time Slot", bg=navy)
    for i, day in enumerate(DAYS, 2):
        hdr_cell(ws1, 2, i, day, bg=teal)
    ws1.row_dimensions[2].height = 22

    # Column widths
    ws1.column_dimensions["A"].width = 16
    for col in ["B","C","D","E","F"]:
        ws1.column_dimensions[col].width = 28

    # Data rows
    cell_colors = [light, amber, pink, green, "EDE9FE"]
    for r_idx, ts in enumerate(TIMES):
        row = r_idx + 3
        ws1.row_dimensions[row].height = 55
        data_cell(ws1, row, 1, ts, bg=gray, bold=True)

        for c_idx, day in enumerate(DAYS, 2):
            if sched_df.empty:
                data_cell(ws1, row, c_idx, "—", bg=white)
                continue
            sessions = sched_df[(sched_df["day"] == day) & (sched_df["time_slot"] == ts)]
            if sessions.empty:
                data_cell(ws1, row, c_idx, "—", bg=white)
            else:
                lines = []
                for _, s in sessions.iterrows():
                    lines.append(f"{s['course_name']}")
                    lines.append(f"  👥 {s['group_name']}")
                    lines.append(f"  👨‍🏫 {s['teacher']}")
                    lines.append(f"  🏛️ {s['room_name']}")
                    lines.append("")
                bg = cell_colors[c_idx % len(cell_colors)]
                data_cell(ws1, row, c_idx, "\n".join(lines).strip(), bg=bg)

    # ── SHEET 2: Full session list ───────────────────────────
    ws2 = wb.create_sheet("All Sessions")
    headers = ["#", "Course", "Teacher", "Group", "Room", "Day", "Time Slot", "Status"]
    for i, h in enumerate(headers, 1):
        hdr_cell(ws2, 1, i, h, bg=navy)
    ws2.row_dimensions[1].height = 20
    col_widths = [5, 28, 22, 15, 18, 14, 16, 14]
    for i, w in enumerate(col_widths, 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    if not sched_df.empty:
        for i, (_, row) in enumerate(sched_df.iterrows(), 1):
            bg = light if i % 2 == 0 else white
            vals = [i, row.get("course_name",""), row.get("teacher",""),
                    row.get("group_name",""), row.get("room_name",""),
                    row.get("day",""), row.get("time_slot",""), row.get("status","")]
            for j, v in enumerate(vals, 1):
                data_cell(ws2, i + 1, j, v, bg=bg, sz=10)
            ws2.row_dimensions[i + 1].height = 18

    # ── SHEET 3: Per-group timetables ───────────────────────
    if not sched_df.empty:
        groups = sched_df["group_name"].unique()
        for grp in groups:
            safe_name = str(grp)[:31]
            ws = wb.create_sheet(safe_name)
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)
            tc = ws.cell(row=1, column=1, value=f"Timetable — {grp}")
            tc.fill = PatternFill("solid", fgColor=teal)
            tc.font = Font(bold=True, color=white, size=12)
            tc.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[1].height = 26

            hdr_cell(ws, 2, 1, "Time Slot", bg=navy)
            for i, day in enumerate(DAYS, 2):
                hdr_cell(ws, 2, i, day, bg=teal)
            ws.column_dimensions["A"].width = 16
            for col in ["B","C","D","E","F"]:
                ws.column_dimensions[col].width = 26

            grp_df = sched_df[sched_df["group_name"] == grp]
            for r_idx, ts in enumerate(TIMES):
                row_num = r_idx + 3
                ws.row_dimensions[row_num].height = 50
                data_cell(ws, row_num, 1, ts, bg=gray, bold=True)
                for c_idx, day in enumerate(DAYS, 2):
                    sess = grp_df[(grp_df["day"] == day) & (grp_df["time_slot"] == ts)]
                    if sess.empty:
                        data_cell(ws, row_num, c_idx, "—")
                    else:
                        s = sess.iloc[0]
                        txt = f"{s['course_name']}\n👨‍🏫 {s['teacher']}\n🏛️ {s['room_name']}"
                        data_cell(ws, row_num, c_idx, txt, bg=light)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# PDF EXPORT
# ─────────────────────────────────────────────────────────────

def export_timetable_pdf(sched_df, title="University Timetable"):
    """
    Generates a PDF with the full timetable grid.
    Returns bytes ready for st.download_button.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    navy   = colors.HexColor("#042C53")
    teal   = colors.HexColor("#1D9E75")
    light  = colors.HexColor("#EBF5FB")
    amber  = colors.HexColor("#FEF3C7")

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  textColor=navy, fontSize=16, spaceAfter=10,
                                  alignment=TA_CENTER)
    cell_style  = ParagraphStyle("cell", parent=styles["Normal"],
                                  fontSize=7.5, leading=11, alignment=TA_CENTER)

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.3*cm))

    # Build table data
    header = ["Time"] + DAYS
    data   = [header]

    for ts in TIMES:
        row_data = [Paragraph(f"<b>{ts}</b>", cell_style)]
        for day in DAYS:
            if sched_df.empty:
                row_data.append(Paragraph("—", cell_style))
                continue
            sess = sched_df[(sched_df["day"] == day) & (sched_df["time_slot"] == ts)]
            if sess.empty:
                row_data.append(Paragraph("—", cell_style))
            else:
                lines = []
                for _, s in sess.iterrows():
                    lines.append(f"<b>{s['course_name']}</b>")
                    lines.append(f"{s['group_name']}")
                    lines.append(f"{s['teacher']}")
                    lines.append(f"{s['room_name']}")
                row_data.append(Paragraph("<br/>".join(lines), cell_style))
        data.append(row_data)

    # Column widths
    page_w = landscape(A4)[0] - 2*cm
    col_widths = [2.8*cm] + [(page_w - 2.8*cm) / 5] * 5

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), teal),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        # Time col
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F8FAFC")),
        ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 1), (0, -1), 8),
        # Data cells
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",   (1, 1), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, light]),
        # Grid
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ("ROWHEIGHT",  (0, 1), (-1, -1), 60),
        ("ROWHEIGHT",  (0, 0), (-1, 0), 22),
        # Top-left cell
        ("BACKGROUND", (0, 0), (0, 0), navy),
    ]))

    elements.append(tbl)
    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
# CSV EXPORT
# ─────────────────────────────────────────────────────────────

def export_timetable_csv(sched_df):
    """Simple CSV export of all sessions."""
    cols = ["course_name", "teacher", "group_name", "room_name",
            "day", "time_slot", "status"]
    available = [c for c in cols if c in sched_df.columns]
    return sched_df[available].to_csv(index=False).encode("utf-8")
