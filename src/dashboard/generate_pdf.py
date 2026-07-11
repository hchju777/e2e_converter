"""대시보드 HTML을 캡처해 PsO H-Biologics Tracker 형식의 PDF 리포트를 생성한다."""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from src.dashboard import report_style as style
from src.dashboard.build_dashboard import _report_label
from src.dashboard.report_data import (
    ReportPage,
    capture_static_pages,
    collect_report_pages,
    label_column_count,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)

PAGE_SIZE = (style.PAGE_WIDTH_IN * inch, style.PAGE_HEIGHT_IN * inch)
MARGIN = style.MARGIN_IN * inch


def _rgb(t: tuple[int, int, int]):
    return colors.Color(t[0] / 255, t[1] / 255, t[2] / 255)


def _draw_full_bleed_image(c: canvas.Canvas, png_bytes: bytes):
    img = ImageReader(BytesIO(png_bytes))
    iw, ih = img.getSize()
    page_w, page_h = PAGE_SIZE
    scale = min(page_w / iw, page_h / ih)
    w, h = iw * scale, ih * scale
    x, y = (page_w - w) / 2, (page_h - h) / 2
    c.drawImage(img, x, y, width=w, height=h)


def _draw_static_page(c: canvas.Canvas, png_bytes: bytes):
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, *PAGE_SIZE, fill=1, stroke=0)
    _draw_full_bleed_image(c, png_bytes)
    c.showPage()


def _build_table_flowable(page: ReportPage) -> Table:
    table = page.table
    label_cols = label_column_count(table)
    data = [["" for _ in range(table.n_cols)] for _ in range(table.n_rows)]
    for (r, cy), text in table.cells.items():
        data[r][cy] = text.replace("\n", " ")

    header_style = ParagraphStyle("hdr", fontName=style.KOREAN_FONT_BOLD_NAME, fontSize=style.TABLE_HEADER_FONT_SIZE,
                                   textColor=_rgb(style.TABLE_HEADER_TEXT), alignment=1, leading=9)
    body_style = ParagraphStyle("body", fontName=style.KOREAN_FONT_NAME, fontSize=style.TABLE_FONT_SIZE,
                                 textColor=_rgb(style.TABLE_BODY_TEXT), alignment=1, leading=9)
    label_style = ParagraphStyle("label", fontName=style.KOREAN_FONT_NAME, fontSize=style.TABLE_FONT_SIZE,
                                  textColor=_rgb(style.TABLE_BODY_TEXT), alignment=0, leading=9)

    wrapped = []
    for r, row in enumerate(data):
        wrapped_row = []
        for c, text in enumerate(row):
            is_header = r < table.header_rows
            is_label = c < label_cols
            ps = header_style if is_header else (label_style if is_label else body_style)
            wrapped_row.append(Paragraph(text or "", ps))
        wrapped.append(wrapped_row)

    n_cols = table.n_cols
    total_width = PAGE_SIZE[0] - 2 * MARGIN
    label_width = total_width * 0.17 if label_cols == 1 else total_width * 0.26
    data_col_width = (total_width - label_width) / max(1, n_cols - label_cols)
    col_widths = [label_width / label_cols] * label_cols + [data_col_width] * (n_cols - label_cols)

    tbl = Table(wrapped, colWidths=col_widths, rowHeights=None)

    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, _rgb(style.TABLE_GRID_LINE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if table.header_rows >= 1:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), _rgb(style.TABLE_HEADER_TOP_BG)))
    if table.header_rows >= 2:
        cmds.append(("BACKGROUND", (0, 1), (-1, table.header_rows - 1), _rgb(style.TABLE_HEADER_PER_BG)))
    for r in sorted(table.bold_rows):
        row_i = r + table.header_rows
        if 0 <= row_i < table.n_rows:
            cmds.append(("BACKGROUND", (0, row_i), (-1, row_i), _rgb(style.TABLE_BOLD_ROW_BG)))
            cmds.append(("BACKGROUND", (0, row_i), (label_cols - 1, row_i), _rgb(style.TABLE_BOLD_ROW_LABEL_BG)))
    for (r1, c1, r2, c2) in table.merges:
        if (r1, c1) != (r2, c2):
            cmds.append(("SPAN", (c1, r1), (c2, r2)))

    tbl.setStyle(TableStyle(cmds))
    return tbl


def _draw_data_page(c: canvas.Canvas, page: ReportPage):
    page_w, page_h = PAGE_SIZE
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    x = MARGIN
    y = page_h - MARGIN

    # 강조 바 + 제목
    c.setFillColor(_rgb(style.ACCENT_BAR))
    c.rect(x, y - 14, 3, 14, fill=1, stroke=0)
    c.setFillColor(_rgb(style.TITLE_TEXT))
    c.setFont(style.KOREAN_FONT_BOLD_NAME, style.TITLE_FONT_SIZE)
    c.drawString(x + 8, y - 11, page.title)
    y -= 22

    # 인사이트
    c.setFont(style.KOREAN_FONT_NAME, style.INSIGHT_FONT_SIZE)
    c.setFillColor(_rgb(style.INSIGHT_TEXT))
    for line in page.insight_lines:
        c.drawString(x + 8, y - 9, f"▶ {line}")
        y -= 15

    # Unit note (우측 정렬, 제목 라인과 동일한 y 부근)
    if page.unit_note:
        c.setFont(style.KOREAN_FONT_NAME, style.UNIT_NOTE_FONT_SIZE)
        c.setFillColor(_rgb(style.UNIT_NOTE_TEXT))
        c.drawRightString(page_w - MARGIN, y - 9, page.unit_note)
        y -= 13

    y -= 4

    # 하단 각주/페이지번호 영역 높이 미리 확보
    footnote_lines = (page.footnote or "").count("\n") + 1 if page.footnote else 0
    bottom_reserved = 10 + footnote_lines * 9 if page.footnote else 12

    content_top = y
    content_bottom = MARGIN + bottom_reserved
    content_height = content_top - content_bottom

    chart_h = 0.0
    if page.chart_png:
        img = ImageReader(BytesIO(page.chart_png))
        iw, ih = img.getSize()
        avail_w = page_w - 2 * MARGIN
        chart_h = min(content_height * 0.62, avail_w * ih / iw)
        chart_w = chart_h * iw / ih
        if chart_w > avail_w:
            chart_w = avail_w
            chart_h = chart_w * ih / iw
        c.drawImage(img, x + (avail_w - chart_w) / 2, content_top - chart_h, width=chart_w, height=chart_h,
                    preserveAspectRatio=True, anchor="n")

    if page.table is not None:
        tbl = _build_table_flowable(page)
        tw, th = tbl.wrapOn(c, page_w - 2 * MARGIN, content_height)
        table_y = content_top - chart_h - th
        if chart_h:
            table_y -= 6
        table_y = max(table_y, content_bottom)
        tbl.drawOn(c, x, table_y)

    # 각주
    if page.footnote:
        fy = MARGIN + 4
        c.setStrokeColor(_rgb(style.TABLE_GRID_LINE))
        c.line(x, fy + footnote_lines * 9 + 2, page_w - MARGIN, fy + footnote_lines * 9 + 2)
        c.setFont(style.KOREAN_FONT_NAME, style.FOOTNOTE_FONT_SIZE)
        c.setFillColor(_rgb(style.FOOTNOTE_TEXT))
        lines = page.footnote.split("\n")
        for i, line in enumerate(reversed(lines)):
            c.drawString(x, fy + i * 9, line.strip())

    # 페이지 번호
    c.setFont(style.KOREAN_FONT_NAME, style.PAGE_NUM_FONT_SIZE)
    c.setFillColor(_rgb(style.PAGE_NUM_TEXT))
    c.drawRightString(page_w - MARGIN, MARGIN - 8, page.page_num)

    c.showPage()


def generate_pdf(output_path: str, dashboard_html: str, period: str) -> Path:
    """대시보드 HTML을 캡처해 PDF 리포트를 생성한다.

    Args:
        output_path: 생성할 PDF 파일 경로
        dashboard_html: build_dashboard()가 방금 만든 대시보드 HTML 경로
        period: 보고 차수 (예: "26년 6차")
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    style.register_korean_fonts()

    report_date_label = _report_label(period)
    logger.info("🖨️ PDF 리포트용 장표 캡처 시작 (%s)", period)
    static_pages = capture_static_pages(dashboard_html, report_date_label)
    data_pages = collect_report_pages(dashboard_html)
    logger.info("🖨️ 장표 %d개 캡처 완료, PDF 조립 시작", len(data_pages))

    c = canvas.Canvas(str(output), pagesize=PAGE_SIZE)

    _draw_static_page(c, static_pages["cover"])
    _draw_static_page(c, static_pages["toc_survey"])
    _draw_static_page(c, static_pages["overview"])
    _draw_static_page(c, static_pages["toc_result"])
    for page in data_pages:
        _draw_data_page(c, page)

    c.save()
    logger.info("✅ PDF 리포트 저장 완료: %s", output)
    return output
