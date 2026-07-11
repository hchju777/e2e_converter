"""pytest 설정 및 공통 fixture"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """pytest 시작 시 실행되는 구성 함수"""
    config.addinivalue_line(
        "markers", "integration: integration 테스트"
    )
    config.addinivalue_line(
        "markers", "unit: unit 테스트"
    )
