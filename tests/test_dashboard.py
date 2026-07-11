import unittest

import pandas as pd

from src.dashboard.build_dashboard import _period_label, add_period, read_json_constant, replace_json_constant
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
