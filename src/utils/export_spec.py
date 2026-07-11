"""Summary 시트(db/UCB_...xlsx)의 지표 스펙을 config/metric_spec.csv로 내보내는 1회성 스크립트.

원본 xlsx의 SAV 변수 수식 중 3곳에 오타가 있어 여기서 보정해서 저장한다.
이후 calc_metrics.py는 xlsx가 아니라 이 config 파일을 읽어 계산한다.
"""

import csv

import openpyxl

from src.utils.logger import get_logger


logger = get_logger(__name__)

XLSX_PATH = "db/UCB_20260518_180044 - (dummy).xlsx"
OUTPUT_PATH = "config/metric_spec.csv"
TARGET_BANNER = "전체"

# (항목, 문항) 기준으로 원본 오타를 보정한 수식.
_FORMULA_FIXES = {
    (
        "건선 환자 타입별 구성 - Dynamic 환자 수 비율",
        "Dynamic 내 Bx Bx Switching",
    ): "(Q5_2 - Q6_B_11 - Q6_B_16 SUM) / [[Q5_1 - Q6_A_11 - Q6_A_16 SUM] + [Q5_2 - Q6_B_11 - Q6_B_16 SUM]] *100",
    (
        "주요 브랜드별 처방 비율 - Dynamic",
        "IL 17 % (Cosentyx,Taltz, Bimzelx)",
    ): "[(Q6_A_5+Q6_B_5)+(Q6_A_6+Q6_B_6)+(Q6_A_12+Q6_B_12)] / [(Q6_A_5+Q6_B_5)+(Q6_A_6+Q6_B_6)+(Q6_A_7+Q6_B_7)+(Q6_A_10+Q6_B_10)+(Q6_A_12+Q6_B_12)]*100",
    (
        "주요 브랜드별 처방 비율 - Dynamic",
        "Bimzelx % in IL 17 ",
    ): "(Q6_A_12+Q6_B_12) / [(Q6_A_5+Q6_B_5)+(Q6_A_6+Q6_B_6)+(Q6_A_12+Q6_B_12)]*100",
}


def main():
    try:
        logger.info("🚀 지표 스펙 내보내기를 시작합니다")
        logger.info("📂 Excel 파일 읽는 중: %s", XLSX_PATH)
        wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
        ws = wb["Summary"]
        rows = ws.iter_rows(values_only=True)
        next(rows)  # header

        records = []
        applied_fixes = set()
        for row in rows:
            gubun, item, question, sav_expr, calc_type, banner = row[:6]
            if gubun is None and item is None:
                continue
            if banner != TARGET_BANNER:
                continue

            fix_key = (item, question)
            if fix_key in _FORMULA_FIXES:
                sav_expr = _FORMULA_FIXES[fix_key]
                applied_fixes.add(fix_key)
                logger.info("🛠️ 수식 오타 보정: %s | %s", item, question)

            records.append(
                {
                    "구분": gubun,
                    "항목": item,
                    "문항": question,
                    "SAV 변수": sav_expr,
                    "계산": calc_type,
                    "배너조건": banner,
                }
            )

        logger.info("💾 지표 스펙 저장 중: %s", OUTPUT_PATH)
        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["구분", "항목", "문항", "SAV 변수", "계산", "배너조건"])
            writer.writeheader()
            writer.writerows(records)

        logger.info("✅ %d개 지표 저장 완료", len(records))
        missing = set(_FORMULA_FIXES) - applied_fixes
        if missing:
            logger.warning("⚠️ 보정 대상을 찾지 못했습니다: %s", missing)
        logger.info("🎉 지표 스펙 내보내기가 완료되었습니다")
    except Exception:
        logger.exception("💥 지표 스펙 내보내기 중 오류가 발생했습니다")
        raise


if __name__ == "__main__":
    main()
