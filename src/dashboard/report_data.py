"""완성된 대시보드 HTML을 헤드리스 브라우저로 열어, PDF/PPTX 리포트에 필요한
장표 데이터(제목/인사이트/표/차트 이미지/각주)를 추출한다.

표는 화면에 보이는 DOM 구조(rowspan/colspan 포함)를 그대로 읽어와 표 형태를
유지한 채로 reportlab/pptx 표에 옮겨 담을 수 있도록 그리드 + 병합 정보로 변환한다.
"""

from dataclasses import dataclass, field
from pathlib import Path

from src.dashboard.browser_capture import DashboardCapture
from src.dashboard.report_pages import REPORT_PAGES
from src.utils.logger import get_logger


logger = get_logger(__name__)

BOLD_ROW_CLASSES = {"row-bold", "row-pct"}

_TABLE_EXTRACT_JS = """
(function(sel){
  var table = document.querySelector(sel + ' table');
  if (!table) return null;
  function rowsOf(sectionTag){
    var section = table.querySelector(sectionTag);
    if (!section) return [];
    return Array.from(section.querySelectorAll('tr')).map(function(tr){
      return {
        className: tr.className || '',
        cells: Array.from(tr.children).map(function(td){
          return {
            text: td.innerText,
            colSpan: td.colSpan || 1,
            rowSpan: td.rowSpan || 1,
            isHeader: td.tagName === 'TH',
          };
        }),
      };
    });
  }
  return {thead: rowsOf('thead'), tbody: rowsOf('tbody')};
})(%s)
""".strip()


@dataclass
class TableGrid:
    """rowspan/colspan을 반영해 펼친 표 그리드."""

    n_rows: int
    n_cols: int
    cells: dict[tuple[int, int], str]  # (row, col) -> 텍스트 (병합 영역의 좌상단 셀만 존재)
    merges: list[tuple[int, int, int, int]]  # (row1, col1, row2, col2) 0-indexed 포함 범위
    header_rows: int  # 상단 몇 개 행이 헤더인지
    bold_rows: set[int]  # 굵게 표시할 본문 행 인덱스(0-indexed, 헤더 제외)


@dataclass
class ChartSeries:
    """Chart.js 데이터셋 하나 (막대 또는 선 한 줄)."""

    label: str
    kind: str  # 'bar' 또는 'line'
    values: list[float | None]
    color: str  # '#rrggbb'
    secondary_axis: bool


@dataclass
class ChartData:
    """PPTX 네이티브 차트를 만드는 데 필요한, Chart.js에서 그대로 읽어온 데이터."""

    categories: list[str]
    series: list[ChartSeries]


@dataclass
class ReportPage:
    section_id: str
    banner: str | None
    page_num: str
    title: str
    insight_lines: list[str]
    unit_note: str | None
    table: TableGrid | None
    chart_png: bytes | None
    chart_data: ChartData | None
    footnote: str | None


def _layout_grid(thead_rows: list[dict], tbody_rows: list[dict]) -> TableGrid:
    """DOM에서 읽은 행/셀(rowspan/colspan 포함) 목록을 그리드로 펼친다."""
    all_rows = thead_rows + tbody_rows
    n_rows = len(all_rows)
    occupancy: dict[tuple[int, int], bool] = {}
    cells: dict[tuple[int, int], str] = {}
    merges: list[tuple[int, int, int, int]] = []
    bold_rows: set[int] = set()

    max_col = 0
    for r, row in enumerate(all_rows):
        c = 0
        for cell in row["cells"]:
            while occupancy.get((r, c)):
                c += 1
            row_span = max(1, cell["rowSpan"])
            col_span = max(1, cell["colSpan"])
            cells[(r, c)] = cell["text"]
            for dr in range(row_span):
                for dc in range(col_span):
                    occupancy[(r + dr, c + dc)] = True
            if row_span > 1 or col_span > 1:
                merges.append((r, c, r + row_span - 1, c + col_span - 1))
            max_col = max(max_col, c + col_span)
            c += col_span
        if row.get("className", "") in BOLD_ROW_CLASSES:
            bold_rows.add(r - len(thead_rows))

    return TableGrid(
        n_rows=n_rows,
        n_cols=max_col,
        cells=cells,
        merges=merges,
        header_rows=len(thead_rows),
        bold_rows=bold_rows,
    )


def label_column_count(table: TableGrid) -> int:
    """맨 앞쪽, 기간(월) 데이터가 아닌 '라벨' 컬럼이 몇 개인지 센다.

    라벨 칸은 상단 헤더에서 rowspan으로 병합되어 마지막 헤더 행에는
    자신의 셀이 없다 — 그 특징으로 라벨 컬럼과 기간 컬럼을 구분한다.
    """
    last_header_row = table.header_rows - 1
    count = 0
    for col in range(table.n_cols):
        if (last_header_row, col) in table.cells:
            break
        count += 1
    return count or 1


def _extract_table(cap: DashboardCapture, section_selector: str) -> TableGrid | None:
    result = cap.evaluate_json(_TABLE_EXTRACT_JS % _js_string(section_selector))
    if result is None:
        return None
    return _layout_grid(result["thead"], result["tbody"])


def _js_string(value: str) -> str:
    import json

    return json.dumps(value)


_CHART_DATA_EXTRACT_JS = """
(function(pageId){
  var canvas = document.getElementById(pageId + 'Chart');
  if (!canvas || typeof Chart === 'undefined') return null;
  var chart = Chart.getChart(canvas);
  if (!chart) return null;
  return {
    labels: chart.data.labels,
    datasets: chart.data.datasets.map(function(ds){
      return {
        label: ds.label,
        kind: ds.type || 'bar',
        data: ds.data,
        color: ds.type === 'line' ? (ds.borderColor || '#000000') : (ds.backgroundColor || '#999999'),
        secondary: !!(ds.yAxisID && ds.yAxisID !== 'y'),
      };
    }),
  };
})(%s)
""".strip()


def _extract_chart_data(cap: DashboardCapture, section_id: str) -> ChartData | None:
    result = cap.evaluate_json(_CHART_DATA_EXTRACT_JS % _js_string(section_id))
    if result is None:
        return None
    series = [
        ChartSeries(
            label=ds["label"] or "",
            kind=ds["kind"],
            values=ds["data"],
            color=ds["color"] if str(ds["color"]).startswith("#") else "#999999",
            secondary_axis=ds["secondary"],
        )
        for ds in result["datasets"]
    ]
    return ChartData(categories=result["labels"], series=series)


def _extract_insight_lines(cap: DashboardCapture, section_id: str) -> list[str]:
    lines = []
    for suffix in ("Insight", "Insight2"):
        text = cap.text_of(f"#page-{section_id} #{section_id}{suffix}")
        if text:
            lines.append(text)
    if not lines:
        text = cap.text_of(f"#page-{section_id} .insight-text")
        if text:
            lines.append(text)
    return lines


def collect_report_pages(dashboard_html: str | Path) -> list[ReportPage]:
    """대시보드 HTML을 열어 REPORT_PAGES에 정의된 순서대로 장표 데이터를 수집한다."""
    pages: list[ReportPage] = []
    with DashboardCapture() as cap:
        cap.navigate(dashboard_html)
        current_section = None
        for section_id, banner in REPORT_PAGES:
            if section_id != current_section:
                cap.goto_page(section_id)
                current_section = section_id
            if banner is not None:
                cap.select_banner(section_id, banner)

            card_selector = f"#page-{section_id} .slide-card"
            title = cap.text_of(f"#page-{section_id} .slide-title") or ""
            page_num = cap.text_of(f"#page-{section_id} .page-num") or ""
            unit_note = cap.text_of(f"#page-{section_id} .unit-note")
            footnote = cap.text_of(f"#page-{section_id} .footnote")
            insight_lines = _extract_insight_lines(cap, section_id)
            table = _extract_table(cap, f"#page-{section_id}")

            chart_png = None
            if cap.exists(f"#page-{section_id} .chart-box"):
                chart_png = cap.screenshot_element(f"#page-{section_id} .chart-box")
            elif cap.exists(f"#page-{section_id} .chart-canvas-wrap"):
                chart_png = cap.screenshot_element(f"#page-{section_id} .chart-canvas-wrap")
            chart_data = _extract_chart_data(cap, section_id) if chart_png else None

            logger.info("📄 장표 캡처: %s%s (page %s)", section_id, f" [{banner}]" if banner else "", page_num)
            pages.append(
                ReportPage(
                    section_id=section_id,
                    banner=banner,
                    page_num=page_num,
                    title=title,
                    insight_lines=insight_lines,
                    unit_note=unit_note,
                    table=table,
                    chart_png=chart_png,
                    chart_data=chart_data,
                    footnote=footnote,
                )
            )
    return pages


_TOC_HTML = Path(__file__).parent / "report_assets" / "toc.html"


def capture_static_pages(dashboard_html: str | Path, report_date_label: str) -> dict[str, bytes]:
    """표지, 목차(x2), 조사 설계 페이지를 캡처한다 (report_date_label 예: 'Apr. 2026')."""
    images: dict[str, bytes] = {}
    with DashboardCapture() as cap:
        cap.navigate(dashboard_html)
        cap.evaluate(
            "var c=document.getElementById('coverPage'); if(c){"
            "c.style.display='flex';"
            "Array.from(c.querySelectorAll('div')).forEach(function(d){"
            "  if(d.children.length && d.innerText && d.innerText.indexOf('클릭하여') !== -1) d.remove();"
            "});"
            "var h1=c.querySelector('h1'); if(h1 && !document.getElementById('reportDateInjected')){"
            "  var d=document.createElement('div');"
            "  d.id='reportDateInjected';"
            "  d.style.cssText='font-size:16px;color:rgba(255,255,255,0.85);margin-top:2px;';"
            f" d.textContent={_js_string(report_date_label)};"
            "  h1.insertAdjacentElement('afterend', d);"
            "}}"
        )
        images["cover"] = cap.screenshot_element("#coverPage")

        cap.evaluate("var c=document.getElementById('coverPage'); if(c) c.style.display='none';")
        cap.goto_page("overview")
        images["overview"] = cap.screenshot_element("#page-overview .slide-card")

    with DashboardCapture() as cap:
        cap.navigate(_TOC_HTML, wait=0.3)
        cap.evaluate("document.getElementById('tocRow01').classList.add('active');")
        images["toc_survey"] = cap.screenshot_element("#tocPage")
        cap.evaluate(
            "document.getElementById('tocRow01').classList.remove('active');"
            "document.getElementById('tocRow02').classList.add('active');"
        )
        images["toc_result"] = cap.screenshot_element("#tocPage")
    return images
