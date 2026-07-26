"""calc_metrics 결과를 기존 PsO HTML 템플릿의 새 Wave로 추가한다."""

import json
import re
from pathlib import Path

import pandas as pd

from src.metrics.calc_metrics import calc_metrics, load_settings, load_spec
from src.utils.banner import (
    REQUIRED_DASHBOARD_BANNERS,
    filter_banner_data,
    validate_banner_configs,
)
from src.utils.excel_history import (
    check_new_wave,
    read_history,
    validate_against_spec,
    write_history,
)
from src.utils.logger import get_logger
from src.utils.read_sav import read_sav_files


logger = get_logger(__name__)

BRANDS = ["Cosentyx", "Taltz", "Tremfya", "Skyrizi", "Bimzelx"]
SEGMENT_OFFSETS = {
    "Total": (133, False),
    "Dynamic": (139, True),
    "Naive": (147, False),
    "Switching": (153, False),
    "Maintain": (159, False),
}
SOV_OFFSETS = {"p24": 225, "p25": 231, "p30": 305, "p31": 311, "p32": 317, "p33": 323}
TIER_KEYS = ["전체", "T1", "T2", "T3"]
ALL_BANNERS = REQUIRED_DASHBOARD_BANNERS
MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def calculate_banner_values(
    df: pd.DataFrame, specs: list, result_column: str, banner_configs: list[dict]
) -> dict[str, list]:
    """동일한 전체 스펙을 6개 배너 DataFrame에 적용한다."""
    validate_banner_configs(banner_configs)
    values = {}
    for banner_config in banner_configs:
        banner = banner_config["name"]
        banner_df = filter_banner_data(df, banner_config)
        logger.info("🧮 %s 배너 계산 시작 (%d명)", banner, len(banner_df))
        result = calc_metrics(banner_df, specs, result_column)
        failures = result[result["오류"] != ""]
        if not failures.empty:
            details = failures[["문항", "SAV 변수", "오류"]].to_dict("records")
            logger.error("❌ %s 배너에서 %d개 지표 계산 실패", banner, len(failures))
            raise ValueError(f"{banner} 배너 계산 실패: {details}")
        values[banner] = [_json_value(value) for value in result[result_column].tolist()]
        warning_count = int((result["경고"] != "").sum())
        if warning_count:
            logger.warning("⚠️ %s 배너 계산 완료: %d개 지표, 경고 %d개", banner, len(result), warning_count)
            for row in result[result["경고"] != ""][["항목", "문항", "경고"]].to_dict("records"):
                logger.warning(
                    "↳ %s | %s | %s",
                    row["항목"],
                    row["문항"],
                    row["경고"],
                )
        else:
            logger.info("✅ %s 배너 계산 완료: %d개 지표", banner, len(result))
    return values


def _json_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def _constant_span(html: str, name: str) -> tuple[int, int]:
    """JSON 객체/배열로 선언된 JS const 값의 시작과 끝 위치를 찾는다."""
    marker = f"const {name} ="
    start = html.index(marker) + len(marker)
    while html[start].isspace():
        start += 1
    opening = html[start]
    if opening not in "{[":
        raise ValueError(f"{name}은 JSON 객체 또는 배열 상수가 아닙니다.")
    closing = {"{": "}", "[": "]"}[opening]
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(html)):
        char = html[pos]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return start, pos + 1
    raise ValueError(f"{name} 상수의 닫는 괄호를 찾을 수 없습니다.")


def read_json_constant(html: str, name: str):
    start, end = _constant_span(html, name)
    return json.loads(html[start:end])


def replace_json_constant(html: str, name: str, value) -> str:
    start, end = _constant_span(html, name)
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return html[:start] + encoded + html[end:]


def _append_rows(target: dict, banner: str, response_count, rows: list):
    target[banner]["resp"].append(response_count)
    for series, value in zip(target[banner]["rows"], rows, strict=True):
        series.append(value)


def _append_brand(target: dict, banner: str | None, values: list):
    root = target if banner is None else target[banner]
    for segment, (offset, has_extra) in SEGMENT_OFFSETS.items():
        segment_data = root[segment]
        segment_data["sum"].append(values[offset])
        for index, brand in enumerate(BRANDS, start=1):
            segment_data[brand].append(values[offset + index])
        if has_extra:
            segment_data["IL17_pct"].append(values[offset + 6])
            segment_data["Bimzelx_IL17"].append(values[offset + 7])


def _append_sov(target: dict, banner: str | None, values: list, pages: list[str]):
    root = target if banner is None else target[banner]
    for page in pages:
        offset = SOV_OFFSETS[page]
        root[page]["sum"].append(values[offset])
        for index, brand in enumerate(BRANDS, start=1):
            root[page][brand].append(values[offset + index])


def append_dashboard_wave(data: dict[str, object], banner_values: dict[str, list]) -> None:
    """파싱된 대시보드 데이터 객체에 한 차수 값을 추가한다."""
    for banner in ALL_BANNERS:
        values = banner_values[banner]
        response_count = values[0]
        data["P5_RESP"][banner].append(response_count)
        for row, value in zip(data["P5_DATA"][banner], values[14:26], strict=True):
            row.append(value)

        _append_rows(data["P11B_DATA"], banner, response_count, values[29:33])
        _append_rows(data["P12B_DATA"], banner, response_count, values[42:45])

        if banner in TIER_KEYS:
            _append_rows(data["P11_DATA"], banner, response_count, values[29:33])
            _append_rows(data["P12_DATA"], banner, response_count, values[42:45])
            p13 = data["P13_DATA"][banner]
            p13["resp"].append(response_count)
            p13["dyn_count"].append(values[45])
            p13["naive_pct"].append(values[46])
            p13["switch_pct"].append(values[47])

        _append_brand(data["BRAND_TABLE_DATA"], banner, values)
        if banner == "전체":
            _append_brand(data["BRAND_DATA"], None, values)
            _append_sov(data["SOV_DATA"], None, values, list(SOV_OFFSETS))
        else:
            _append_brand(data["BRAND_BANNER_DATA"], banner, values)
            _append_sov(data["SOV_BANNER_DATA"], banner, values, list(SOV_OFFSETS))
            _append_sov(data["SOV_TABLE_DATA"], banner, values, ["p24", "p25"])


def _period_label(period: str) -> str:
    match = re.fullmatch(r"(\d{2})년\s*(\d{1,2})차", period.strip())
    if not match:
        raise ValueError(f"result_column은 '26년 6차' 형식이어야 합니다: {period}")
    year, wave = match.groups()
    wave_number = int(wave)
    if wave_number not in MONTH_LABELS:
        raise ValueError(f"지원하지 않는 차수입니다: {wave_number}차")
    return f"{year}\\n{MONTH_LABELS[wave_number]}"


def _report_label(period: str) -> str:
    match = re.fullmatch(r"(\d{2})년\s*(\d{1,2})차", period.strip())
    if not match:
        raise ValueError(f"result_column은 '26년 6차' 형식이어야 합니다: {period}")
    year, wave = match.groups()
    return f"{MONTH_LABELS[int(wave)]}. 20{year}"


def add_period(html: str, period: str, index: int) -> str:
    if re.search(rf"key\s*:\s*['\"]{re.escape(period)}['\"]", html):
        raise ValueError(f"템플릿에 이미 존재하는 차수입니다: {period}")
    pattern = re.compile(r"(const\s+PERIODS_ASC\s*=\s*\[)(.*?)(\]\s*;)", re.DOTALL)
    match = pattern.search(html)
    if not match:
        raise ValueError("PERIODS_ASC 선언을 찾을 수 없습니다.")
    item = f"  {{key:'{period}', label:'{_period_label(period)}', idx:{index}}},\n"
    body = match.group(2)
    if body and not body.endswith("\n"):
        body += "\n"
    html = html[: match.start()] + match.group(1) + body + item + match.group(3) + html[match.end() :]
    return re.sub(r"const\s+LATEST_IDX\s*=\s*\d+\s*;", f"const LATEST_IDX = {index};", html, count=1)


def read_overview(template_path: str) -> dict:
    """템플릿의 조사 설계 기본값(OVERVIEW 상수)을 읽어 반환한다."""
    html = Path(template_path).read_text(encoding="utf-8")
    return read_json_constant(html, "OVERVIEW")


DATA_CONSTANTS = [
    "P5_RESP", "P5_DATA", "P11_DATA", "P11B_DATA", "P12_DATA", "P12B_DATA",
    "P13_DATA", "BRAND_DATA", "BRAND_BANNER_DATA", "BRAND_TABLE_DATA",
    "SOV_DATA", "SOV_BANNER_DATA", "SOV_TABLE_DATA",
]


def clear_wave_data(node) -> None:
    """중첩 구조는 그대로 두고 차수 값이 담긴 말단 배열만 비운다.

    템플릿에서 구조(어떤 배너·세그먼트·브랜드 키가 있는지)만 빌려오고 값은 모두
    버리기 위한 것이다. 덕분에 템플릿 HTML을 직접 편집하지 않고도 히스토리를
    엑셀 한 곳에서만 관리할 수 있다.
    """
    if isinstance(node, dict):
        for value in node.values():
            clear_wave_data(value)
    elif isinstance(node, list):
        if node and isinstance(node[0], list):
            for value in node:
                clear_wave_data(value)
        else:
            node.clear()


def replace_periods(html: str, periods: list[str]) -> str:
    """PERIODS_ASC와 LATEST_IDX를 주어진 차수 목록으로 통째로 교체한다."""
    pattern = re.compile(r"(const\s+PERIODS_ASC\s*=\s*\[)(.*?)(\]\s*;)", re.DOTALL)
    match = pattern.search(html)
    if not match:
        raise ValueError("PERIODS_ASC 선언을 찾을 수 없습니다.")
    items = "".join(
        f"  {{key:'{period}', label:'{_period_label(period)}', idx:{index}}},\n"
        for index, period in enumerate(periods)
    )
    html = (
        html[: match.start()]
        + match.group(1) + "\n" + items + match.group(3)
        + html[match.end() :]
    )
    return re.sub(
        r"const\s+LATEST_IDX\s*=\s*\d+\s*;",
        f"const LATEST_IDX = {len(periods) - 1};",
        html,
        count=1,
    )


def build_dashboard_from_history(
    template_path: str,
    output_path: str,
    periods: list[str],
    period_values: dict[str, dict[str, list]],
    overview: dict | None = None,
) -> Path:
    """템플릿의 하드코딩 데이터를 버리고, 주어진 모든 차수로 대시보드를 다시 만든다.

    periods는 시간 순서, period_values는 {차수: {배너: 지표값 리스트}} 형태다.
    """
    template = Path(template_path)
    logger.info("🎨 대시보드 템플릿 읽는 중: %s", template)
    html = template.read_text(encoding="utf-8")
    if overview is not None:
        logger.info("📝 조사 설계 값 주입 중")
        html = replace_json_constant(html, "OVERVIEW", overview)

    data = {name: read_json_constant(html, name) for name in DATA_CONSTANTS}
    for name in DATA_CONSTANTS:
        clear_wave_data(data[name])

    logger.info("📈 %d개 차수로 대시보드 데이터 재구성 중: %s ~ %s", len(periods), periods[0], periods[-1])
    for period in periods:
        append_dashboard_wave(data, period_values[period])

    for name in DATA_CONSTANTS:
        html = replace_json_constant(html, name, data[name])
    html = replace_periods(html, periods)
    html = html.replace("Apr. 2026", _report_label(periods[-1]))
    html = re.sub(
        r"</script>\s*</script>\s*</html>\s*$",
        "</script>\n</body>\n</html>\n",
        html,
        count=1,
        flags=re.IGNORECASE,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def build_dashboard(
    template_path: str,
    output_path: str,
    period: str,
    banner_values: dict[str, list],
    overview: dict | None = None,
) -> Path:
    template = Path(template_path)
    logger.info("🎨 대시보드 템플릿 읽는 중: %s", template)
    html = template.read_text(encoding="utf-8")
    if overview is not None:
        logger.info("📝 조사 설계 값 주입 중")
        html = replace_json_constant(html, "OVERVIEW", overview)
    data = {name: read_json_constant(html, name) for name in DATA_CONSTANTS}
    period_index = len(data["P5_RESP"]["전체"])
    logger.info("📈 새 Wave 추가 중: %s (index=%d)", period, period_index)
    append_dashboard_wave(data, banner_values)
    for name in DATA_CONSTANTS:
        html = replace_json_constant(html, name, data[name])
    html = add_period(html, period, period_index)
    html = html.replace("Apr. 2026", _report_label(period))
    html = re.sub(
        r"</script>\s*</script>\s*</html>\s*$",
        "</script>\n</body>\n</html>\n",
        html,
        count=1,
        flags=re.IGNORECASE,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output


def history_path(settings: dict) -> Path:
    """설정에 적힌 과거 데이터 엑셀의 경로를 돌려준다."""
    filename = settings.get("history_filename")
    if not filename:
        raise FileNotFoundError(
            "config/settings.json에 history_filename(과거 데이터 엑셀 파일명)이 없습니다."
        )
    path = Path(settings.get("sav_dir", "db")) / filename
    if not path.is_file():
        raise FileNotFoundError(f"과거 데이터 엑셀을 찾을 수 없습니다: {path}")
    return path


def main():
    try:
        logger.info("🚀 PsO 대시보드 생성을 시작합니다")
        logger.info("⚙️ 설정 파일 읽는 중: config/settings.json")
        settings = load_settings()

        specs = load_spec(settings["spec_path"], "전체")
        period = settings["result_column"]
        banner_configs = settings["dashboard_banners"]
        logger.info("📋 지표 스펙 로드 완료: %d개", len(specs))

        # 과거 차수는 엑셀이 정본이다. 웹 화면과 같은 방식으로 전체 차수를 다시 만든다.
        excel = history_path(settings)
        logger.info("📗 과거 데이터 엑셀 읽는 중: %s", excel)
        history = read_history(excel)
        validate_against_spec(history, [spec.question for spec in specs])
        period = check_new_wave(history, period)

        logger.info("📂 SAV 파일 읽는 중: %s/%s", settings["sav_dir"], settings.get("sav_filename"))
        files = read_sav_files(settings["sav_dir"], settings.get("sav_filename"))
        if not files:
            raise FileNotFoundError("계산할 SAV 파일을 찾을 수 없습니다.")
        sav_path, (df, _meta) = next(iter(files.items()))
        logger.info("📊 SAV 로드 완료: %s (응답자 %d명, 변수 %d개)", sav_path, len(df), len(df.columns))

        logger.info("🎯 배너 필터 설정 로드 완료: %d개", len(banner_configs))
        banner_values = calculate_banner_values(df, specs, period, banner_configs)

        periods = history.waves + [period]
        period_values = dict(history.values)
        period_values[period] = banner_values
        output = build_dashboard_from_history(
            settings["dashboard_template"], settings["dashboard_output"], periods, period_values
        )
        logger.info("💾 대시보드 저장 완료: %s (%d개 차수)", output, len(periods))

        # 다음 차수 입력으로 쓸 수 있도록 이번 차수를 더한 엑셀도 남긴다.
        history_out = settings.get("history_output")
        if history_out:
            saved = write_history(excel, history_out, period, banner_values)
            logger.info("💾 과거 데이터 엑셀 저장 완료: %s", saved)
        else:
            logger.warning("⚠️ history_output이 없어 갱신된 엑셀을 저장하지 않았습니다")

        logger.info("🎉 모든 작업이 성공적으로 완료되었습니다")
    except Exception:
        logger.exception("💥 대시보드 생성 중 오류가 발생했습니다")
        raise


if __name__ == "__main__":
    main()
