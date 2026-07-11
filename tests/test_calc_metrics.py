import math
import unittest

import pandas as pd

from src.metrics.calc_metrics import MetricSpec, calc_all_banners, calc_metrics, eval_arith, resolve_formula


def spec(item, expression, calc_type, question="테스트"):
    return MetricSpec("전체", item, question, expression, calc_type, "전체")


class EvalArithmeticTests(unittest.TestCase):
    def test_supports_series_arithmetic(self):
        context = {"A": pd.Series([1, 2]), "B": pd.Series([3, 4])}
        self.assertEqual(eval_arith("A + B * 2", context).tolist(), [7, 10])

    def test_rejects_function_calls(self):
        with self.assertRaises(ValueError):
            eval_arith("sum(A)", {"A": pd.Series([1])})

    def test_zero_division_becomes_nan_and_warns(self):
        warnings = []
        result = eval_arith("A / B", {"A": pd.Series([2, 4]), "B": pd.Series([0, 2])}, warnings)
        self.assertTrue(math.isnan(result.iloc[0]))
        self.assertEqual(result.iloc[1], 2)
        self.assertEqual(warnings, ["0으로 나눈 값은 NaN으로 처리됨"])


class FormulaTests(unittest.TestCase):
    def test_resolves_aggregate_reference(self):
        lookup = {("A + B", "SUM"): 12}
        self.assertEqual(resolve_formula("[A + B SUM] / 3", lookup, {}), 4)

    def test_scalar_zero_division_becomes_nan_and_warns(self):
        warnings = []
        result = resolve_formula("A / B", {}, {"A": 3, "B": 0}, warnings)
        self.assertTrue(math.isnan(result))
        self.assertEqual(warnings, ["0으로 나눈 값은 NaN으로 처리됨"])


class MetricCalculationTests(unittest.TestCase):
    def test_sum_mean_count_formula_placeholder_and_original_order(self):
        frame = pd.DataFrame({"A": [1, 2, None], "B": [2, 0, 4], "PID": [1, 2, 3]})
        specs = [
            spec("비율", "[A SUM] / [B SUM] * 100", "계산식"),
            spec("그룹", "아래 값의 합계", "Sum"),
            spec("그룹", "A", "Sum"),
            spec("그룹", "B", "Sum"),
            spec("평균", "A", "Mean"),
            spec("응답자", "PID", "Count"),
        ]

        result = calc_metrics(frame, specs, "테스트 결과")

        self.assertEqual(result["SAV 변수"].tolist(), [s.sav_expr for s in specs])
        self.assertEqual(result["테스트 결과"].tolist(), [50, 9, 3, 6, 1.5, 3])
        self.assertTrue((result["오류"] == "").all())

    def test_zero_division_warning_is_separate_from_error(self):
        frame = pd.DataFrame({"A": [2, 4], "B": [0, 2]})
        result = calc_metrics(frame, [spec("비율", "A / B", "Mean")])

        self.assertEqual(result.loc[0, "결과"], 2)
        self.assertEqual(result.loc[0, "오류"], "")
        self.assertIn("0으로 나눈", result.loc[0, "경고"])

    def test_calculates_all_configured_banners(self):
        frame = pd.DataFrame(
            {"PID": [1, 2, 3, 4], "Area": [1, 1, 2, 3], "UCB_Tier": [1, 2, 3, 99]}
        )
        configs = [
            {"name": "전체"},
            {"name": "수도권", "column": "Area", "values": [1]},
            {"name": "지방", "column": "Area", "values": [2, 3, 4, 5, 6]},
            {"name": "T1", "column": "UCB_Tier", "values": [1]},
            {"name": "T2", "column": "UCB_Tier", "values": [2]},
            {"name": "T3", "column": "UCB_Tier", "values": [3, 99]},
        ]

        result = calc_all_banners(frame, [spec("응답자", "PID", "Count")], "값", configs)

        self.assertEqual(result["배너조건"].tolist(), ["전체", "수도권", "지방", "T1", "T2", "T3"])
        self.assertEqual(result["값"].tolist(), [4, 2, 2, 1, 1, 2])


if __name__ == "__main__":
    unittest.main()
