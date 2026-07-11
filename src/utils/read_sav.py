"""db 디렉터리의 .sav(SPSS) 파일을 읽어 DataFrame으로 출력하는 스크립트."""

import glob
import os

import pandas as pd
import pyreadstat

from src.utils.logger import get_logger


logger = get_logger(__name__)


def read_sav_files(db_dir: str = "db", sav_filename: str | None = None):
    if sav_filename:
        sav_paths = [os.path.join(db_dir, sav_filename)]
        if not os.path.isfile(sav_paths[0]):
            raise FileNotFoundError(f"설정한 SAV 파일을 찾을 수 없습니다: {sav_paths[0]}")
    else:
        sav_paths = glob.glob(os.path.join(db_dir, "*.sav")) + glob.glob(os.path.join(db_dir, "*.SAV"))

    results = {}
    for path in sav_paths:
        df, meta = pyreadstat.read_sav(path)
        results[path] = (df, meta)
    return results


def main():
    try:
        logger.info("🚀 SAV 파일 조회를 시작합니다")
        logger.info("🔍 db 디렉터리에서 SAV 파일 검색 중")
        files = read_sav_files()

        if not files:
            logger.warning("⚠️ db 디렉터리에서 SAV 파일을 찾지 못했습니다")
            return

        logger.info("📚 SAV 파일 %d개를 찾았습니다", len(files))
        for path, (df, _meta) in files.items():
            logger.info("📊 %s | 응답자 %d명 | 변수 %d개", path, len(df), len(df.columns))
            logger.info("🏷️ 앞쪽 컬럼: %s%s", list(df.columns)[:10], " ..." if df.shape[1] > 10 else "")
            print(df.head())
        logger.info("🎉 SAV 파일 조회가 완료되었습니다")
    except Exception:
        logger.exception("💥 SAV 파일 조회 중 오류가 발생했습니다")
        raise


if __name__ == "__main__":
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 200)
    main()
