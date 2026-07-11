#!/usr/bin/env python
"""e2e_converter CLI 진입점

사용 방법:
  python main.py web              # 웹 애플리케이션 실행
  python main.py calc --banner    # 지표 계산 및 대시보드 생성
  python main.py sav-info         # SAV 파일 정보 출력
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """CLI 메인 진입점"""
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1]
    
    if command == "web":
        run_web_app()
    elif command == "calc":
        run_calc(sys.argv[2:])
    elif command == "sav-info":
        run_sav_info()
    elif command in ("-h", "--help", "help"):
        print_usage()
    else:
        print(f"알 수 없는 명령: {command}")
        print_usage()
        return 1
    
    return 0


def run_web_app():
    """웹 애플리케이션 실행"""
    logger.info("웹 애플리케이션을 시작합니다...")
    from src.dashboard.web_app import main as web_main
    web_main()


def run_calc(args):
    """지표 계산 및 대시보드 생성"""
    import argparse
    from src.metrics.calc_metrics import main as calc_main
    from src.dashboard.build_dashboard import main as dashboard_main
    
    parser = argparse.ArgumentParser(description="지표 계산 및 대시보드 생성")
    parser.add_argument(
        "--banner",
        action="store_true",
        help="배너별 계산 결과 포함"
    )
    parser.add_argument(
        "--config",
        default="config/settings.json",
        help="설정 파일 경로 (기본값: config/settings.json)"
    )
    
    parsed_args = parser.parse_args(args)
    
    try:
        # 지표 계산
        logger.info("지표 계산을 시작합니다...")
        calc_main()
        logger.info("✅ 지표 계산이 완료되었습니다")
        
        # 대시보드 생성
        logger.info("대시보드 생성을 시작합니다...")
        dashboard_main()
        logger.info("✅ 대시보드 생성이 완료되었습니다")
        
    except Exception:
        logger.exception("계산 중 오류가 발생했습니다")
        return 1


def run_sav_info():
    """SAV 파일 정보 출력"""
    from src.utils.read_sav import main as sav_main
    sav_main()


def print_usage():
    """사용 방법 출력"""
    print("""
PsO Dashboard Converter v1.0.0

사용 방법:
  python main.py web                         웹 애플리케이션 실행
  python main.py calc [--banner] [--config] 지표 계산 및 대시보드 생성
  python main.py sav-info                    SAV 파일 정보 출력
  python main.py -h, --help                  도움말 출력

예시:
  python main.py web
  python main.py calc --banner --config config/settings.json
  python main.py sav-info

패키지 설치:
  프로덕션:  pip install -r requirements/base.txt
  개발용:    pip install -r requirements/dev.txt
    """.strip())


if __name__ == "__main__":
    sys.exit(main())
