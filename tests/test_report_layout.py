import unittest

from pptx.util import Emu

from src.dashboard.generate_pptx import EMU_PER_IN, _add_data_slide, _table_height_for
from src.dashboard.report_data import ReportPage, TableGrid


def report_page(rows: int, with_chart: bool) -> ReportPage:
    return ReportPage(
        section_id="test",
        banner=None,
        page_num="1",
        title="test",
        insight_lines=[],
        unit_note=None,
        table=TableGrid(rows, 2, {}, [], 1, set()),
        chart_png=b"png" if with_chart else None,
        chart_data=None,
        footnote=None,
    )


class ReportLayoutTests(unittest.TestCase):
    def test_chart_and_table_never_allocate_more_than_available_height(self):
        available = Emu(int(5 * EMU_PER_IN))
        table_height = _table_height_for(report_page(30, True), available, True)

        self.assertLessEqual(table_height, available * 0.48)

    def test_table_only_page_can_use_all_available_height(self):
        available = Emu(int(3 * EMU_PER_IN))
        table_height = _table_height_for(report_page(30, False), available, False)

        self.assertEqual(table_height, available)

    def test_insight_box_has_nonzero_height_and_does_not_overlap_unit_note(self):
        from pptx import Presentation

        page = report_page(4, False)
        page.insight_lines = ["첫 번째 인사이트", "두 번째 인사이트"]
        page.unit_note = "[Unit: %]"
        prs = Presentation()
        _add_data_slide(prs, page)
        slide = prs.slides[0]
        insight = next(shape for shape in slide.shapes if shape.has_text_frame and "첫 번째" in shape.text)
        unit = next(shape for shape in slide.shapes if shape.has_text_frame and "[Unit" in shape.text)

        self.assertGreater(insight.height, 0)
        self.assertLessEqual(insight.top + insight.height, unit.top)
