"""e2e_converter: 과거 데이터 엑셀과 SPSS SAV를 읽어 대시보드·리포트를 만드는 도구"""

from pathlib import Path


def _read_version() -> str:
    """버전은 config/VERSION 한 곳에서만 관리한다(EXE 파일명·화면 표기와 같은 값)."""
    version_file = Path(__file__).resolve().parent.parent / "config" / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


__version__ = _read_version()
__author__ = "UCB Analytics"
__description__ = "SAV to Dashboard Converter for PsO H-Biologics Tracker"

from src.metrics.calc_metrics import calc_metrics, load_spec, load_settings
from src.dashboard.build_dashboard import build_dashboard
from src.utils.read_sav import read_sav_files
from src.utils.banner import filter_banner_data, validate_banner_configs
from src.utils.logger import get_logger

__all__ = [
    "calc_metrics",
    "load_spec",
    "load_settings",
    "build_dashboard",
    "read_sav_files",
    "filter_banner_data",
    "validate_banner_configs",
    "get_logger",
]
