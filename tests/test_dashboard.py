import unittest
from pathlib import Path

import pandas as pd

import json
import tempfile

from src.dashboard.build_dashboard import (
    DATA_CONSTANTS,
    _period_label,
    add_period,
    build_dashboard_from_history,
    clear_wave_data,
    history_path,
    overview_from_settings,
    read_json_constant,
    read_overview,
    replace_json_constant,
    replace_periods,
)
from src.utils.banner import REQUIRED_DASHBOARD_BANNERS
from src.utils.banner import filter_banner_data, validate_banner_configs


class JavascriptConstantTests(unittest.TestCase):
    def test_reads_and_replaces_nested_json_constant(self):
        html = '<script>const DATA = {"a":{"values":[1,2]}};</script>'
        self.assertEqual(read_json_constant(html, "DATA")["a"]["values"], [1, 2])

        updated = replace_json_constant(html, "DATA", {"한글": [3, None]})
        self.assertEqual(read_json_constant(updated, "DATA"), {"한글": [3, None]})


class PeriodTests(unittest.TestCase):
    def test_adds_period_and_updates_latest_index(self):
        html = "const PERIODS_ASC = [\n  {key:'26년 4차', label:'26\\nApr', idx:0},\n];\nconst LATEST_IDX = 0;"
        updated = add_period(html, "26년 6차", 1)

        self.assertIn("{key:'26년 6차', label:'26\\nJun', idx:1}", updated)
        self.assertIn("const LATEST_IDX = 1;", updated)

    def test_rejects_duplicate_period(self):
        html = "const PERIODS_ASC = [{key:'26년 6차', label:'26\\nJun', idx:0}];"
        with self.assertRaisesRegex(ValueError, "이미 존재"):
            add_period(html, "26년 6차", 1)

    def test_rejects_wave_outside_month_range(self):
        with self.assertRaisesRegex(ValueError, "지원하지 않는 차수"):
            _period_label("26년 13차")


class ClearWaveDataTests(unittest.TestCase):
    def test_empties_leaf_arrays_but_keeps_structure(self):
        data = {"전체": {"resp": [1, 2], "rows": [[1, 2], [3, 4]]}, "T1": [[5, 6]]}
        clear_wave_data(data)

        self.assertEqual(data, {"전체": {"resp": [], "rows": [[], []]}, "T1": [[]]})

    def test_covers_every_dashboard_constant(self):
        def count_values(node) -> int:
            if isinstance(node, dict):
                return sum(count_values(value) for value in node.values())
            if isinstance(node, list):
                if node and isinstance(node[0], list):
                    return sum(count_values(value) for value in node)
                return len(node)
            return 0

        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")
        for name in DATA_CONSTANTS:
            constant = read_json_constant(html, name)
            self.assertGreater(count_values(constant), 0, f"{name}에 원래 값이 없습니다")
            clear_wave_data(constant)
            self.assertEqual(count_values(constant), 0, f"{name}에 값이 남았습니다")


class ReplacePeriodsTests(unittest.TestCase):
    def test_replaces_whole_period_list(self):
        html = (
            "const PERIODS_ASC = [\n  {key:'25년 1차', label:'25\\nJan', idx:0},\n];\n"
            "const LATEST_IDX = 0;"
        )
        updated = replace_periods(html, ["26년 1차", "26년 2차"])

        self.assertIn("{key:'26년 1차', label:'26\\nJan', idx:0}", updated)
        self.assertIn("{key:'26년 2차', label:'26\\nFeb', idx:1}", updated)
        self.assertIn("const LATEST_IDX = 1;", updated)
        self.assertNotIn("25년 1차", updated)


class BannerFilterTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "Area": [1, 2, 3, 6, 7, None],
                "UCB_Tier": [1, 2, 3, 99, 4, None],
            }
        )

    def test_area_filter_only_includes_explicit_values(self):
        result = filter_banner_data(
            self.frame, {"name": "지방", "column": "Area", "values": [2, 3, 4, 5, 6]}
        )
        self.assertEqual(result["Area"].tolist(), [2, 3, 6])

    def test_t3_filter_includes_3_and_99(self):
        result = filter_banner_data(
            self.frame, {"name": "T3", "column": "UCB_Tier", "values": [3, 99]}
        )
        self.assertEqual(result["UCB_Tier"].tolist(), [3, 99])

    def test_missing_filter_column_is_rejected(self):
        with self.assertRaisesRegex(KeyError, "찾을 수 없습니다"):
            filter_banner_data(self.frame, {"name": "잘못됨", "column": "Unknown", "values": [1]})

    def test_banner_order_is_validated(self):
        with self.assertRaisesRegex(ValueError, "name과 순서"):
            validate_banner_configs([{"name": "전체"}, {"name": "T1"}])


class DashboardImageDownloadTests(unittest.TestCase):
    def test_dashboard_contains_offline_slide_image_download(self):
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

        self.assertIn("installSlideDownloadButtons", html)
        self.assertIn("downloadSlideImage", html)
        self.assertIn("장표 이미지 저장", html)
        self.assertNotIn("html2canvas", html)

    def test_picks_save_destination_before_rendering(self):
        """이미지 생성 뒤에 저장 위치를 물으면 대화상자 권한이 만료될 수 있다."""
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

        self.assertIn("async function pickSaveTarget(", html)
        self.assertIn("async function writeToTarget(", html)
        picker = html.index("const target = await pickSaveTarget(")
        render = html.index("const output = renderElementToCanvas(card, 2)")
        self.assertLess(picker, render, "저장 위치를 먼저 물어야 합니다")


class HistoryPathTests(unittest.TestCase):
    """CLI(calc)도 웹 화면과 같은 과거 데이터 엑셀을 쓴다."""

    def test_resolves_against_the_sav_directory(self):
        settings = {"sav_dir": "db", "history_filename": "UCB_20260518_180044 - (dummy).xlsx"}
        path = history_path(settings)

        self.assertEqual(path.parent.name, "db")
        self.assertTrue(path.is_file())

    def test_reports_a_missing_setting(self):
        with self.assertRaisesRegex(FileNotFoundError, "history_filename"):
            history_path({"sav_dir": "db"})

    def test_reports_a_missing_file(self):
        with self.assertRaisesRegex(FileNotFoundError, "찾을 수 없습니다"):
            history_path({"sav_dir": "db", "history_filename": "없는파일.xlsx"})

    def test_settings_file_declares_the_excel(self):
        settings = json.loads(Path("config/settings.json").read_text(encoding="utf-8"))

        self.assertIn("history_filename", settings)
        self.assertIn("history_output", settings)
        self.assertTrue(settings["history_output"].endswith(".xlsx"))


class OverviewFromSettingsTests(unittest.TestCase):
    """조사 설계도 웹 화면처럼 config로 지정할 수 있어야 한다."""

    BASE = {
        "target": ["A", "", "  B "],
        "sample": " N = 1 ",
        "region": "서울",
        "method": "온라인",
        "fieldwork_start": "2025-01-01",
        "fieldwork_end": "2026-05-12",
    }

    def test_builds_dashboard_overview(self):
        overview = overview_from_settings({"overview": self.BASE})

        self.assertEqual(overview["target"], ["A", "B"])       # 빈 줄과 앞뒤 공백은 정리한다
        self.assertEqual(overview["sample"], "N = 1")
        self.assertEqual(overview["fieldwork"], "2025년 1월 1일 ~ 2026년 5월 12일")

    def test_missing_block_falls_back_to_the_template(self):
        self.assertIsNone(overview_from_settings({}))

    def test_requires_both_dates(self):
        broken = dict(self.BASE, fieldwork_end=None)
        with self.assertRaisesRegex(ValueError, "fieldwork_start와 fieldwork_end"):
            overview_from_settings({"overview": broken})

    def test_rejects_reversed_and_malformed_dates(self):
        with self.assertRaisesRegex(ValueError, "빠를 수 없"):
            overview_from_settings({"overview": dict(self.BASE, fieldwork_start="2026-06-01")})
        with self.assertRaisesRegex(ValueError, "형식"):
            overview_from_settings({"overview": dict(self.BASE, fieldwork_start="2025/01/01")})

    def test_settings_file_has_the_overview_block(self):
        settings = json.loads(Path("config/settings.json").read_text(encoding="utf-8"))

        self.assertIn("overview", settings)
        for key in ("target", "sample", "region", "method", "fieldwork_start", "fieldwork_end"):
            self.assertIn(key, settings["overview"])


class VerticalAlignmentTests(unittest.TestCase):
    """값이 칸 위쪽에 붙지 않고 세로 가운데에 오도록 한다."""

    def test_table_body_cells_are_middle_aligned(self):
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")
        self.assertIn("vertical-align: middle", html)

    def test_sum_row_numbers_are_centered_like_their_label(self):
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")
        self.assertIn(
            ".sum-row-cells > div { display: flex; align-items: center; justify-content: center; }",
            html,
        )


class ThinBarLabelTests(unittest.TestCase):
    """값이 작아 막대 조각이 얇으면 라벨이 잘려 보이지 않는다 — 그런 경우만 막대 위로 뺀다."""

    def setUp(self):
        self.html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

    def test_only_the_top_segment_is_lifted(self):
        self.assertIn("function thinBarLabel(outsideColor, insideColor)", self.html)
        self.assertIn("anchor: ctx => _labelPlacement(ctx).anchor", self.html)
        # 맨 위 조각이 아니면 위로 빼지 않는다.
        self.assertIn("if (Math.abs(mine.to - total) > 1e-9) return null;", self.html)

    def test_middle_segments_keep_their_place(self):
        """가운데 조각까지 위로 빼면 자기 조각에서 멀어져 어느 값인지 알 수 없다."""
        self.assertIn("return { anchor: 'center', align: 'center', offset: 0 };", self.html)
        self.assertIn("그런 조각은 칸을 조금 넘더라도 제자리", self.html)

    def test_applied_to_every_stacked_bar_chart(self):
        # 환자 타입(p12·p12b·p13)뿐 아니라 브랜드·SoV 차트에도 적용한다.
        self.assertEqual(self.html.count("...thinBarLabel("), 12)

    def test_lifted_label_keeps_clear_of_the_one_below(self):
        # 바로 아래 조각의 라벨은 제자리에 남으므로 그와 겹치지 않을 만큼 올려야 한다.
        self.assertIn("const LABEL_MIN_GAP = 11;", self.html)
        self.assertIn("if (gap + offset < LABEL_MIN_GAP) offset = LABEL_MIN_GAP - gap;", self.html)


class OverflowLabelTests(unittest.TestCase):
    """합계가 100%를 넘으면 막대가 화면 위로 솟아 라벨이 통째로 사라진다."""

    def setUp(self):
        self.html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

    def test_treats_the_axis_max_as_a_ceiling(self):
        self.assertIn("function _overflowLabel(", self.html)
        self.assertIn("const ceiling = scale.max;", self.html)
        self.assertIn("보이는 구간의 가운데에 놓는다", self.html)

    def test_tolerates_floating_point_sums(self):
        """96.72 + 2.51 + 0.77 처럼 딱 100인 값도 소수점 오차로 100을 넘길 수 있다."""
        self.assertIn("if (!(total > ceiling + 0.5)) return null;", self.html)

    def test_overflow_labels_are_readable_on_any_background(self):
        # 원래 조각이 아닌 다른 색 위에 놓이므로 흰 글자 + 어두운 테두리로 그린다.
        self.assertIn("placement.overflow) return '#fff'", self.html)
        self.assertIn("textStrokeColor", self.html)

    def test_chart_reserves_room_above_bars(self):
        # 막대 위로 뺀 라벨이 캔버스 밖으로 잘리지 않도록 위쪽 여백을 넓힌다.
        self.assertNotIn("layout:{ padding:{top:16} }", self.html)
        self.assertGreaterEqual(self.html.count("layout:{ padding:{top:36} }"), 3)


class ChartLegendTests(unittest.TestCase):
    """아이콘 폭이 달라도 설명 글이 같은 위치에서 시작해야 한다."""

    def test_legend_uses_two_column_grid(self):
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

        self.assertIn(".chart-legend { display: grid; grid-template-columns: auto 1fr;", html)
        self.assertIn(".chart-legend-item { display: contents; }", html)

    def test_no_inline_margin_shifts_legend_text(self):
        # 인라인 여백이 남아 있으면 그 항목만 오른쪽으로 밀린다.
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

        self.assertNotIn('<span style="margin-left:3px;">', html)

    def test_legend_items_stay_packed_at_the_top(self):
        # align-content가 없으면 남는 높이가 행 사이에 배분돼 항목이 세로로 흩어진다.
        html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

        self.assertIn("align-content: start", html)


class ChartLabelTests(unittest.TestCase):
    """모든 값을 보여주되, 조각이 얇으면 막대 위로 빼서 읽히게 한다."""

    def setUp(self):
        self.html = Path("db/PsO_dashboard_v4.html").read_text(encoding="utf-8")

    def test_never_hides_a_value(self):
        # 값을 감추면 안 된다. display를 꺼버린 예전 방식이 남아 있으면 실패한다.
        self.assertNotIn("ChartDataLabels.defaults.display", self.html)
        self.assertNotIn("Chart.defaults.plugins.datalabels.display", self.html)

    def test_thin_top_segment_is_lifted_above_the_bar(self):
        self.assertIn("function thinBarLabel(", self.html)
        self.assertIn("return { anchor: 'end', align: 'top', offset: lifted.offset, outside: true };", self.html)

    def test_position_comes_from_values_not_drawn_bars(self):
        """막대 좌표로 계산하면 차트를 처음 그릴 때만 위치가 틀린다."""
        self.assertIn("const scale = ctx.chart.scales.y;", self.html)
        self.assertIn("scale.getPixelForValue", self.html)
        self.assertNotIn("_stackTop(", self.html)

    def test_every_bar_chart_uses_the_helper(self):
        # 막대 차트 데이터셋이 예전처럼 고정 가운데 정렬만 쓰고 있으면 얇은 칸이 겹친다.
        self.assertNotIn("datalabels:{ anchor:'center', align:'center', color:'#fff',\n", self.html)


class OverviewTests(unittest.TestCase):
    TEMPLATE = "db/PsO_dashboard_v4.html"

    def test_template_renders_overview_from_constant(self):
        html = Path(self.TEMPLATE).read_text(encoding="utf-8")
        self.assertIn("const OVERVIEW =", html)
        self.assertIn("function renderOverview", html)
        for anchor in ('id="ovTarget"', 'id="ovSample"', 'id="ovRegion"', 'id="ovMethod"', 'id="ovPeriod"'):
            self.assertIn(anchor, html)

    def test_read_overview_returns_template_defaults(self):
        overview = read_overview(self.TEMPLATE)
        self.assertEqual(overview["sample"], "N = 35")
        self.assertEqual(overview["region"], "전국")
        self.assertEqual(len(overview["target"]), 3)
        self.assertIn("fieldwork", overview)

    def test_rebuild_from_history_replaces_all_waves(self):
        """엑셀의 모든 차수로 다시 만들면 템플릿의 하드코딩 차수는 남지 않는다."""
        periods = ["25년 1차", "25년 2차", "25년 3차"]
        values = {
            period: {banner: [float(index)] * 329 for banner in REQUIRED_DASHBOARD_BANNERS}
            for index, period in enumerate(periods)
        }
        output = Path(tempfile.mkdtemp()) / "rebuilt.html"
        build_dashboard_from_history(self.TEMPLATE, str(output), periods, values)
        html = output.read_text(encoding="utf-8")

        self.assertEqual(len(read_json_constant(html, "P5_RESP")["전체"]), len(periods))
        self.assertEqual(len(read_json_constant(html, "BRAND_DATA")["Total"]["Cosentyx"]), len(periods))
        self.assertIn("const LATEST_IDX = 2;", html)
        self.assertIn("{key:'25년 3차', label:'25\\nMar', idx:2}", html)
        self.assertNotIn("26년 4차", html)  # 템플릿에 있던 차수가 사라진다

    def test_overview_constant_round_trips(self):
        html = Path(self.TEMPLATE).read_text(encoding="utf-8")
        custom = {
            "target": ["대상 A"],
            "sample": "N = 1",
            "region": "서울",
            "method": "온라인",
            "fieldwork": "2026년 1월 1일 ~ 1월 2일",
        }
        updated = replace_json_constant(html, "OVERVIEW", custom)
        self.assertEqual(read_json_constant(updated, "OVERVIEW"), custom)
