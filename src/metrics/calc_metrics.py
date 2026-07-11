"""config/metric_spec.csv의 지표 스펙(배너조건=전체)을 SAV 데이터로 계산해 결과 파일로 저장하는 스크립트.

스펙은 원래 db/UCB_...xlsx의 Summary 시트에서 관리했으나, 원본 수식 오타 3건을 보정해
config/metric_spec.csv로 옮겨 관리한다 (export_spec.py 참고). 이 스크립트는 xlsx를 열지 않는다.

경로/배너조건 등 실행 설정은 config/settings.json에서 읽는다.
"""

import ast
import json
import operator
import os
import re
from dataclasses import dataclass

import pandas as pd

from src.utils.banner import filter_banner_data, validate_banner_configs
from src.utils.read_sav import read_sav_files
from src.utils.logger import get_logger

SETTINGS_PATH = "config/settings.json"
logger = get_logger(__name__)

_WS_RE = re.compile(r"\s+")


def load_settings(settings_path: str = SETTINGS_PATH) -> dict:
    with open(settings_path, encoding="utf-8") as f:
        return json.load(f)


def normalize(text) -> str:
    return _WS_RE.sub(" ", str(text).strip())


@dataclass
class MetricSpec:
    gubun: str
    item: str
    question: str
    sav_expr: str
    calc_type: str
    banner: str


def load_spec(spec_path: str, banner_filter: str) -> list[MetricSpec]:
    spec_df = pd.read_csv(spec_path, encoding="utf-8-sig")

    specs = []
    for row in spec_df.to_dict("records"):
        if row["배너조건"] != banner_filter:
            continue
        specs.append(
            MetricSpec(
                row["구분"], row["항목"], row["문항"], row["SAV 변수"], row["계산"], row["배너조건"]
            )
        )
    return specs


# ---- 안전한 산술식 평가기 (eval 미사용) ----

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def eval_arith(expr: str, context: dict, warnings: list[str] | None = None):
    tree = ast.parse(normalize(expr), mode="eval")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Div):
                zero_found = bool((right == 0).any()) if isinstance(right, pd.Series) else right == 0
                if zero_found and warnings is not None:
                    warnings.append("0으로 나눈 값은 NaN으로 처리됨")
                if zero_found and not isinstance(left, pd.Series) and not isinstance(right, pd.Series):
                    return float("nan")
                result = operator.truediv(left, right)
                if isinstance(result, pd.Series):
                    return result.replace([float("inf"), float("-inf")], float("nan"))
                if result == float("inf") or result == float("-inf"):
                    return float("nan")
                return result
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise KeyError(f"알 수 없는 SAV 변수: {node.id}")
            return context[node.id]
        raise ValueError(f"지원하지 않는 표현식 구성: {ast.dump(node)}")

    return _eval(tree)


# ---- 계산식(수식) 참조 해석 ----
# "[식 SUM]", "[식 Mean]", "(식 SUM)" 형태로 다른 행의 계산값을 참조하는 패턴을
# 안쪽(innermost, 같은 종류 괄호가 중첩되지 않은) 것부터 반복적으로 실제 숫자값으로
# 치환한다. 참조 대상 식 자체에 괄호가 포함될 수 있어(예: "Q3_1-(...)-(...)"),
# 정규식 하나로는 처리할 수 없고 괄호 짝을 직접 맞춰야 한다.
_AGG_SUFFIX_RE = re.compile(r"^\s*(.+?)\s+(SUM|Sum|sum|Mean|mean|Count|count)\s*$")


def _substitute_innermost_ref(text: str, open_ch: str, close_ch: str, lookup: dict):
    """open_ch/close_ch로 감싸인, 같은 종류 괄호가 내부에 없는 참조를 하나 찾아 치환한다."""
    idx = 0
    while True:
        start = text.find(open_ch, idx)
        if start == -1:
            return None
        depth = 1
        pos = start + 1
        while pos < len(text) and depth > 0:
            if text[pos] == open_ch:
                depth += 1
            elif text[pos] == close_ch:
                depth -= 1
            pos += 1
        if depth != 0:
            return None  # 짝이 맞지 않음
        end = pos - 1
        inner = text[start + 1 : end]
        if open_ch in inner or close_ch in inner:
            idx = start + 1  # innermost 아님, 다음 후보 탐색
            continue
        m = _AGG_SUFFIX_RE.match(inner)
        if not m:
            idx = start + 1  # AGG로 끝나지 않으면 참조가 아니라 단순 그룹핑 괄호
            continue
        inner_expr, agg = m.group(1), m.group(2)
        key = (normalize(inner_expr), agg.upper())
        if key not in lookup:
            raise KeyError(f"참조를 찾을 수 없음: [{inner_expr} {agg}]")
        value = lookup[key]
        return text[:start] + f"({value})" + text[end + 1 :]


def resolve_formula(expr: str, lookup: dict, col_sums: dict, warnings: list[str] | None = None) -> float:
    text = expr
    changed = True
    while changed:
        changed = False
        for open_ch, close_ch in (("[", "]"), ("(", ")")):
            new_text = _substitute_innermost_ref(text, open_ch, close_ch, lookup)
            if new_text is not None:
                text = new_text
                changed = True
                break

    # 참조 치환 후 남은 대괄호는 단순 그룹핑 괄호로 취급
    text = text.replace("[", "(").replace("]", ")")
    return eval_arith(text, col_sums, warnings)


# ---- 지표 계산 ----

def _is_total_placeholder(sav_expr) -> bool:
    """SAV 변수 칸에 수식 대신 '아래 값의 합계' 같은 안내 텍스트만 적힌 행인지 판별."""
    text = normalize(sav_expr)
    return "아래" in text and "합계" in text


def calc_metrics(df: pd.DataFrame, specs: list, result_column: str = "결과") -> pd.DataFrame:
    col_series = {col: pd.to_numeric(df[col], errors="coerce") for col in df.columns}
    col_sums = {col: series.sum(skipna=True) for col, series in col_series.items()}

    lookup = {}
    results = {}
    formula_specs = []
    placeholder_specs = []
    item_values: dict[str, list[float]] = {}

    # Pass 1: Count / Sum / Mean (배너 내 다른 계산식이 참조할 수 있는 원자 값들)
    for index, spec in enumerate(specs):
        calc = normalize(spec.calc_type).upper()

        if calc == "계산식".upper():
            formula_specs.append((index, spec))
            continue

        if calc == "SUM" and _is_total_placeholder(spec.sav_expr):
            placeholder_specs.append((index, spec))
            continue

        try:
            warnings = []
            if calc == "SUM":
                value = eval_arith(spec.sav_expr, col_series, warnings).sum(skipna=True)
            elif calc == "MEAN":
                value = eval_arith(spec.sav_expr, col_series, warnings).mean(skipna=True)
            elif calc == "COUNT":
                value = eval_arith(spec.sav_expr, col_series, warnings).notna().sum()
            else:
                formula_specs.append((index, spec))
                continue
        except Exception as e:  # noqa: BLE001 - 계산 실패 행은 오류로 표기하고 계속 진행
            results[index] = (spec, None, str(e), "")
            continue

        lookup.setdefault((normalize(spec.sav_expr), calc), value)
        item_values.setdefault(spec.item, []).append(value)
        results[index] = (spec, value, "", "; ".join(dict.fromkeys(warnings)))

    # Pass 1b: "아래 값의 합계" 형태의 Total 행 - 같은 항목 그룹 내 이미 계산된 값들의 합
    for index, spec in placeholder_specs:
        values = item_values.get(spec.item)
        if not values:
            results[index] = (spec, None, f"'{spec.item}' 항목 내 합산할 값을 찾지 못함", "")
            continue
        value = sum(values)
        lookup.setdefault((normalize(spec.sav_expr), "SUM"), value)
        results[index] = (spec, value, "", "")

    # Pass 2: 계산식 (Pass 1 결과 또는 원본 SAV 변수 합계를 참조)
    for index, spec in formula_specs:
        try:
            warnings = []
            value = resolve_formula(spec.sav_expr, lookup, col_sums, warnings)
            results[index] = (spec, value, "", "; ".join(dict.fromkeys(warnings)))
        except Exception as e:  # noqa: BLE001
            results[index] = (spec, None, str(e), "")

    return pd.DataFrame(
        [
            {
                "구분": spec.gubun,
                "항목": spec.item,
                "문항": spec.question,
                "SAV 변수": spec.sav_expr,
                "계산": spec.calc_type,
                "배너조건": spec.banner,
                result_column: value,
                "오류": error,
                "경고": warning,
            }
            for _, (spec, value, error, warning) in sorted(results.items())
        ]
    )


def calc_all_banners(
    df: pd.DataFrame, specs: list, result_column: str, banner_configs: list[dict]
) -> pd.DataFrame:
    """설정된 6개 배너에 동일한 기준 스펙을 적용해 하나의 결과로 합친다."""
    validate_banner_configs(banner_configs)
    banner_results = []
    for banner_config in banner_configs:
        banner_df = filter_banner_data(df, banner_config)
        result = calc_metrics(banner_df, specs, result_column)
        result["배너조건"] = banner_config["name"]
        banner_results.append(result)
    return pd.concat(banner_results, ignore_index=True)


def main():
    try:
        logger.info("🚀 지표 계산을 시작합니다")
        logger.info("⚙️ 설정 파일 읽는 중: %s", SETTINGS_PATH)
        settings = load_settings()
        sav_dir = settings["sav_dir"]
        sav_filename = settings.get("sav_filename")
        spec_path = settings["spec_path"]
        output_dir = settings["output_dir"]
        output_path = os.path.join(output_dir, settings["output_filename"])
        banner_configs = settings["dashboard_banners"]
        result_column = settings.get("result_column", "결과")

        os.makedirs(output_dir, exist_ok=True)
        logger.info("📂 SAV 파일 읽는 중: %s/%s", sav_dir, sav_filename)
        files = read_sav_files(sav_dir, sav_filename)
        if not files:
            raise FileNotFoundError(f"{sav_dir} 디렉터리에서 .sav 파일을 찾을 수 없습니다.")

        sav_path, (df, _meta) = next(iter(files.items()))
        logger.info("📊 SAV 로드 완료: %s (응답자 %d명, 변수 %d개)", sav_path, len(df), len(df.columns))

        # metric_spec.csv의 '전체' 329개 행을 검증된 공통 기준 스펙으로 사용한다.
        specs = load_spec(spec_path, banner_filter="전체")
        logger.info("📋 배너별 계산 대상 지표: %d개", len(specs))
        validate_banner_configs(banner_configs)
        for banner_config in banner_configs:
            banner_df = filter_banner_data(df, banner_config)
            logger.info("🧮 %s 배너 계산 대상: %d명", banner_config["name"], len(banner_df))
        result_df = calc_all_banners(df, specs, result_column, banner_configs)
        n_error = int((result_df["오류"] != "").sum())
        n_warning = int((result_df["경고"] != "").sum())
        logger.info("✅ 6개 배너 계산 완료: 성공 %d건 / 실패 %d건", len(result_df) - n_error, n_error)

        if n_error:
            for row in result_df[result_df["오류"] != ""][["항목", "문항", "오류"]].to_dict("records"):
                logger.error("❌ %s | %s | %s", row["항목"], row["문항"], row["오류"])
        if n_warning:
            logger.warning("⚠️ 계산 경고: %d건", n_warning)
            for row in result_df[result_df["경고"] != ""][["항목", "문항", "경고"]].to_dict("records"):
                logger.warning("↳ %s | %s | %s", row["항목"], row["문항"], row["경고"])

        result_df.to_csv(output_path, index=False, encoding="utf-8-sig", na_rep="NaN")
        logger.info("💾 결과 CSV 저장 완료: %s", output_path)
        logger.info("🎉 모든 작업이 완료되었습니다")
    except Exception:
        logger.exception("💥 지표 계산 중 오류가 발생했습니다")
        raise


if __name__ == "__main__":
    main()
