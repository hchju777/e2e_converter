"""대시보드 HTML을 캡처해 PsO H-Biologics Tracker 형식의 PPTX 리포트를 생성한다.

표/텍스트/차트 모두 파워포인트에서 직접 편집 가능한 네이티브 개체(표, 텍스트박스,
차트)로 만든다. 차트 이미지(chart_png)는 PDF 전용이며, PPTX에는 Chart.js에서 그대로
읽어온 계열 데이터(chart_data)로 네이티브 차트를 그린다.
"""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

from src.dashboard import report_style as style
from src.dashboard.build_dashboard import _report_label
from src.dashboard.report_data import (
    ChartData,
    ReportPage,
    capture_static_pages,
    collect_report_pages,
    label_column_count,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)

KOREAN_FONT = "맑은 고딕"

EMU_PER_IN = 914400
PAGE_W = Emu(int(style.PAGE_WIDTH_IN * EMU_PER_IN))
PAGE_H = Emu(int(style.PAGE_HEIGHT_IN * EMU_PER_IN))
MARGIN = Emu(int(style.MARGIN_IN * EMU_PER_IN))


def _rgb(t: tuple[int, int, int]) -> RGBColor:
    return RGBColor(*t)




def _add_textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return box, tf


def _set_run(run, text, size, color, bold=False):
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = _rgb(color)
    run.font.bold = bold
    run.font.name = KOREAN_FONT


def _add_full_bleed_picture(slide, png_bytes: bytes):
    img = Image.open(BytesIO(png_bytes))
    iw, ih = img.size
    scale = min(PAGE_W / iw, PAGE_H / ih)
    w, h = int(iw * scale), int(ih * scale)
    x, y = (PAGE_W - w) // 2, (PAGE_H - h) // 2
    slide.shapes.add_picture(BytesIO(png_bytes), x, y, width=w, height=h)


def _add_static_slide(prs: Presentation, png_bytes: bytes):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_full_bleed_picture(slide, png_bytes)


C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _hex(color: str) -> str:
    return color.lstrip("#").upper() or "808080"


def _add_native_chart(slide, chart_data: ChartData, left, top, width, height):
    """Chart.js 데이터를 그대로 옮겨 파워포인트 네이티브 차트(막대, 필요하면 보조축 꺾은선)로 그린다."""
    bar_series = [s for s in chart_data.series if s.kind != "line"]
    line_series = [s for s in chart_data.series if s.kind == "line"]

    cdata = CategoryChartData()
    cdata.categories = chart_data.categories
    for s in bar_series:
        cdata.add_series(s.label, [v if v is not None else 0 for v in s.values])

    graphic_frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, left, top, width, height, cdata)
    chart = graphic_frame.chart
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(7)
    chart.legend.font.name = KOREAN_FONT

    plot = chart.plots[0]
    plot.gap_width = 40
    plot.overlap = 100
    for series, s in zip(plot.series, bar_series):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = RGBColor.from_string(_hex(s.color))
        series.format.line.fill.background()

    for axis in (chart.category_axis, chart.value_axis):
        axis.tick_labels.font.size = Pt(7)
        axis.tick_labels.font.name = KOREAN_FONT

    if line_series:
        try:
            _add_secondary_line_series(chart, line_series, chart_data.categories)
        except Exception:
            logger.exception("⚠️ 보조축 꺾은선 계열 추가 실패 — 막대 차트만 유지합니다")

    return graphic_frame


def _add_secondary_line_series(chart, line_series: list, categories: list[str]):
    """이미 만들어진 누적 막대 차트에, 보조축을 쓰는 꺾은선 계열을 XML로 직접 추가한다.

    python-pptx는 콤보(막대+꺾은선) 차트를 공개 API로 지원하지 않아, OOXML의
    표준 콤보 차트 구조(보조 값축 + 숨겨진 보조 항목축)를 그대로 만들어 삽입한다.
    """
    chart_space = chart._chartSpace
    plot_area = chart_space.find(f".//{{{C_NS}}}plotArea")
    bar_chart_el = plot_area.find(f"{{{C_NS}}}barChart")
    primary_cat_ax = plot_area.find(f"{{{C_NS}}}catAx")
    primary_val_ax = plot_area.find(f"{{{C_NS}}}valAx")
    primary_cat_ax_id = primary_cat_ax.find(f"{{{C_NS}}}axId").get("val")
    primary_val_ax_id = primary_val_ax.find(f"{{{C_NS}}}axId").get("val")

    secondary_cat_ax_id = str(int(primary_cat_ax_id) + 1)
    secondary_val_ax_id = str(int(primary_val_ax_id) + 1)

    n = len(categories)
    cat_pts = "".join(
        f'<c:pt idx="{i}"><c:v>{xml_escape(str(cat))}</c:v></c:pt>' for i, cat in enumerate(categories)
    )
    series_xml = []
    for idx, s in enumerate(line_series):
        color = _hex(s.color)
        val_pts = "".join(
            f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i, v in enumerate(s.values) if v is not None
        )
        series_xml.append(f"""
        <c:ser xmlns:c="{C_NS}" xmlns:a="{A_NS}">
          <c:idx val="{idx}"/>
          <c:order val="{idx}"/>
          <c:tx><c:v>{xml_escape(s.label)}</c:v></c:tx>
          <c:spPr><a:ln w="19050"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:ln></c:spPr>
          <c:marker><c:symbol val="circle"/><c:size val="5"/>
            <c:spPr><a:solidFill><a:srgbClr val="{color}"/></a:solidFill></c:spPr>
          </c:marker>
          <c:cat><c:strRef><c:f>Sheet1!$A$2:$A${n + 1}</c:f>
            <c:strCache><c:ptCount val="{n}"/>{cat_pts}</c:strCache></c:strRef></c:cat>
          <c:val><c:numRef><c:f>Sheet1!$B$2:$B${n + 1}</c:f>
            <c:numCache><c:formatCode>General</c:formatCode><c:ptCount val="{n}"/>{val_pts}</c:numCache></c:numRef></c:val>
          <c:smooth val="0"/>
        </c:ser>
        """)

    line_chart_xml = f"""
    <c:lineChart xmlns:c="{C_NS}">
      <c:grouping val="standard"/>
      <c:varyColors val="0"/>
      {''.join(series_xml)}
      <c:marker val="1"/>
      <c:axId val="{secondary_cat_ax_id}"/>
      <c:axId val="{secondary_val_ax_id}"/>
    </c:lineChart>
    """
    line_chart_el = etree.fromstring(line_chart_xml)
    bar_chart_el.addnext(line_chart_el)

    secondary_val_ax_xml = f"""
    <c:valAx xmlns:c="{C_NS}">
      <c:axId val="{secondary_val_ax_id}"/>
      <c:scaling><c:orientation val="minMax"/></c:scaling>
      <c:delete val="0"/>
      <c:axPos val="r"/>
      <c:numFmt formatCode="0.0&quot;%&quot;" sourceLinked="0"/>
      <c:majorTickMark val="out"/>
      <c:minorTickMark val="none"/>
      <c:tickLblPos val="nextTo"/>
      <c:txPr><a:bodyPr xmlns:a="{A_NS}"/><a:lstStyle xmlns:a="{A_NS}"/>
        <a:p xmlns:a="{A_NS}"><a:pPr><a:defRPr sz="700"/></a:pPr><a:endParaRPr lang="ko-KR"/></a:p>
      </c:txPr>
      <c:crossAx val="{secondary_cat_ax_id}"/>
      <c:crosses val="max"/>
    </c:valAx>
    """
    secondary_cat_ax_xml = f"""
    <c:catAx xmlns:c="{C_NS}">
      <c:axId val="{secondary_cat_ax_id}"/>
      <c:scaling><c:orientation val="minMax"/></c:scaling>
      <c:delete val="1"/>
      <c:axPos val="b"/>
      <c:majorTickMark val="out"/>
      <c:minorTickMark val="none"/>
      <c:tickLblPos val="nextTo"/>
      <c:crossAx val="{secondary_val_ax_id}"/>
      <c:crosses val="autoZero"/>
      <c:auto val="1"/>
      <c:lblAlgn val="ctr"/>
      <c:lblOffset val="100"/>
      <c:noMultiLvlLbl val="0"/>
    </c:catAx>
    """
    primary_val_ax.addnext(etree.fromstring(secondary_cat_ax_xml))
    primary_val_ax.addnext(etree.fromstring(secondary_val_ax_xml))


def _build_table(slide, page: ReportPage, top: Emu, height: Emu) -> Emu:
    """표를 그리고 실제로 차지한 높이를 반환한다."""
    table_data = page.table
    label_cols = label_column_count(table_data)
    n_rows, n_cols = table_data.n_rows, table_data.n_cols

    total_width = PAGE_W - 2 * MARGIN
    label_frac = 0.17 if label_cols == 1 else 0.26
    label_total_w = int(total_width * label_frac)
    data_col_w = (total_width - label_total_w) // max(1, n_cols - label_cols)
    label_col_w = label_total_w // label_cols

    row_h = max(Emu(int(0.22 * EMU_PER_IN)), Emu(int(height / n_rows))) if n_rows else Emu(0)
    row_h = min(row_h, Emu(int(0.26 * EMU_PER_IN)))
    table_height = row_h * n_rows

    gframe = slide.shapes.add_table(n_rows, n_cols, MARGIN, top, total_width, table_height)
    tbl = gframe.table
    for c in range(label_cols):
        tbl.columns[c].width = label_col_w
    for c in range(label_cols, n_cols):
        tbl.columns[c].width = data_col_w
    for r in range(n_rows):
        tbl.rows[r].height = row_h

    for (r, c), text in table_data.cells.items():
        cell = tbl.cell(r, c)
        cell.text = text.replace("\n", " ")
        cell.margin_left = cell.margin_right = Emu(18000)
        cell.margin_top = cell.margin_bottom = Emu(4000)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        is_header = r < table_data.header_rows
        is_bold_row = (r - table_data.header_rows) in table_data.bold_rows
        is_label = c < label_cols
        for para in cell.text_frame.paragraphs:
            para.alignment = PP_ALIGN.LEFT if is_label else PP_ALIGN.CENTER
            for run in para.runs:
                run.font.size = Pt(style.TABLE_FONT_SIZE)
                run.font.name = KOREAN_FONT
                if is_header:
                    run.font.bold = True
                    run.font.color.rgb = _rgb(style.TABLE_HEADER_TEXT)
                elif is_bold_row:
                    run.font.bold = True
                    run.font.color.rgb = _rgb(style.TABLE_BOLD_ROW_LABEL_TEXT if is_label else style.TABLE_BODY_TEXT)
                else:
                    run.font.color.rgb = _rgb(style.TABLE_BODY_TEXT)
        cell.fill.solid()
        if is_header:
            bg = style.TABLE_HEADER_TOP_BG if r == 0 else style.TABLE_HEADER_PER_BG
        elif is_bold_row:
            bg = style.TABLE_BOLD_ROW_LABEL_BG if is_label else style.TABLE_BOLD_ROW_BG
        else:
            bg = (0xFF, 0xFF, 0xFF)
        cell.fill.fore_color.rgb = _rgb(bg)

    for (r1, c1, r2, c2) in table_data.merges:
        if (r1, c1) != (r2, c2):
            tbl.cell(r1, c1).merge(tbl.cell(r2, c2))

    return table_height


def _add_data_slide(prs: Presentation, page: ReportPage):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    x = MARGIN
    y = MARGIN

    # 강조 바
    bar = slide.shapes.add_shape(1, x, y, Emu(int(0.045 * EMU_PER_IN)), Emu(int(0.22 * EMU_PER_IN)))
    bar.fill.solid()
    bar.fill.fore_color.rgb = _rgb(style.ACCENT_BAR)
    bar.line.fill.background()

    # 제목
    _, tf = _add_textbox(slide, x + Emu(int(0.12 * EMU_PER_IN)), y, PAGE_W - 2 * MARGIN, Emu(int(0.3 * EMU_PER_IN)))
    _set_run(tf.paragraphs[0].add_run(), page.title, style.TITLE_FONT_SIZE, style.TITLE_TEXT, bold=True)
    y += Emu(int(0.34 * EMU_PER_IN))

    # 인사이트
    if page.insight_lines:
        _, tf = _add_textbox(slide, x + Emu(int(0.12 * EMU_PER_IN)), y, PAGE_W - 2 * MARGIN,
                                    Emu(int(0.02 + 0.19 * len(page.insight_lines)) * EMU_PER_IN))
        for i, line in enumerate(page.insight_lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            _set_run(p.add_run(), f"▶ {line}", style.INSIGHT_FONT_SIZE, style.INSIGHT_TEXT)
        y += Emu(int(0.02 + 0.19 * len(page.insight_lines)) * EMU_PER_IN)

    # Unit note
    if page.unit_note:
        _, tf = _add_textbox(slide, x, y, PAGE_W - 2 * MARGIN, Emu(int(0.16 * EMU_PER_IN)))
        tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
        _set_run(tf.paragraphs[0].add_run(), page.unit_note, style.UNIT_NOTE_FONT_SIZE, style.UNIT_NOTE_TEXT)
        y += Emu(int(0.2 * EMU_PER_IN))

    y += Emu(int(0.04 * EMU_PER_IN))

    footnote_lines = (page.footnote or "").split("\n") if page.footnote else []
    bottom_reserved = Emu(int((0.14 + 0.11 * len(footnote_lines)) * EMU_PER_IN))
    content_bottom = PAGE_H - MARGIN - bottom_reserved
    content_height = content_bottom - y

    chart_h = Emu(0)
    if page.chart_png:
        img = Image.open(BytesIO(page.chart_png))
        iw, ih = img.size
        avail_w = PAGE_W - 2 * MARGIN
        chart_h = min(Emu(int(content_height * 0.62)), Emu(int(avail_w * ih / iw)))
        chart_w = Emu(int(chart_h * iw / ih))
        if chart_w > avail_w:
            chart_w = avail_w
            chart_h = Emu(int(chart_w * ih / iw))
        chart_x = x + (avail_w - chart_w) // 2

        if page.chart_data and page.chart_data.series:
            try:
                _add_native_chart(slide, page.chart_data, chart_x, y, chart_w, chart_h)
            except Exception:
                logger.exception("⚠️ 네이티브 차트 생성 실패 — 이미지로 대체합니다 (%s)", page.section_id)
                slide.shapes.add_picture(BytesIO(page.chart_png), chart_x, y, width=chart_w, height=chart_h)
        else:
            slide.shapes.add_picture(BytesIO(page.chart_png), chart_x, y, width=chart_w, height=chart_h)
        y += chart_h + Emu(int(0.06 * EMU_PER_IN))

    if page.table is not None:
        remaining = content_bottom - y
        _build_table(slide, page, y, remaining)

    # 각주
    if page.footnote:
        _, tf = _add_textbox(slide, x, content_bottom, PAGE_W - 2 * MARGIN, bottom_reserved)
        for i, line in enumerate(footnote_lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            _set_run(p.add_run(), line.strip(), style.FOOTNOTE_FONT_SIZE, style.FOOTNOTE_TEXT)

    # 페이지 번호
    _, tf = _add_textbox(slide, PAGE_W - MARGIN - Emu(int(0.6 * EMU_PER_IN)), PAGE_H - MARGIN,
                                 Emu(int(0.6 * EMU_PER_IN)), Emu(int(0.18 * EMU_PER_IN)))
    tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
    _set_run(tf.paragraphs[0].add_run(), page.page_num, style.PAGE_NUM_FONT_SIZE, style.PAGE_NUM_TEXT)


def generate_pptx(output_path: str, dashboard_html: str, period: str) -> Path:
    """대시보드 HTML을 캡처해 PPTX 리포트를 생성한다.

    Args:
        output_path: 생성할 PPTX 파일 경로
        dashboard_html: build_dashboard()가 방금 만든 대시보드 HTML 경로
        period: 보고 차수 (예: "26년 6차")
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    report_date_label = _report_label(period)
    logger.info("📊 PPTX 리포트용 장표 캡처 시작 (%s)", period)
    static_pages = capture_static_pages(dashboard_html, report_date_label)
    data_pages = collect_report_pages(dashboard_html)
    logger.info("📊 장표 %d개 캡처 완료, PPTX 조립 시작", len(data_pages))

    prs = Presentation()
    prs.slide_width = PAGE_W
    prs.slide_height = PAGE_H

    _add_static_slide(prs, static_pages["cover"])
    _add_static_slide(prs, static_pages["toc_survey"])
    _add_static_slide(prs, static_pages["overview"])
    _add_static_slide(prs, static_pages["toc_result"])
    for page in data_pages:
        _add_data_slide(prs, page)

    prs.save(str(output))
    logger.info("✅ PPTX 리포트 저장 완료: %s", output)
    return output
