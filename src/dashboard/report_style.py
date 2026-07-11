"""PDF/PPTX 리포트에서 공용으로 쓰는 색상·치수 상수.

대시보드 CSS(PsO_dashboard_v4.html)의 색상 값을 그대로 옮겨와, 화면과 리포트가
같은 톤을 유지하도록 한다.
"""

from pathlib import Path

_WINDOWS_FONTS = Path(r"C:\Windows\Fonts")
KOREAN_FONT_REGULAR_PATH = _WINDOWS_FONTS / "malgun.ttf"
KOREAN_FONT_BOLD_PATH = _WINDOWS_FONTS / "malgunbd.ttf"
KOREAN_FONT_NAME = "MalgunGothic"
KOREAN_FONT_BOLD_NAME = "MalgunGothic-Bold"

_fonts_registered = False


def register_korean_fonts() -> tuple[str, str]:
    """맑은 고딕을 reportlab에 등록하고 (일반, 굵게) 폰트 이름을 반환한다.

    reportlab 기본 폰트(Helvetica 등)는 한글 글리프가 없어 빈 사각형으로 나오므로,
    Windows에 기본 내장된 맑은 고딕 TTF를 직접 등록해서 사용한다.
    """
    global _fonts_registered
    if _fonts_registered:
        return KOREAN_FONT_NAME, KOREAN_FONT_BOLD_NAME

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if not KOREAN_FONT_REGULAR_PATH.exists():
        raise FileNotFoundError(
            f"한글 폰트를 찾을 수 없습니다: {KOREAN_FONT_REGULAR_PATH} "
            "(Windows 기본 맑은 고딕 폰트가 필요합니다)"
        )
    pdfmetrics.registerFont(TTFont(KOREAN_FONT_NAME, str(KOREAN_FONT_REGULAR_PATH)))
    bold_path = KOREAN_FONT_BOLD_PATH if KOREAN_FONT_BOLD_PATH.exists() else KOREAN_FONT_REGULAR_PATH
    pdfmetrics.registerFont(TTFont(KOREAN_FONT_BOLD_NAME, str(bold_path)))
    _fonts_registered = True
    return KOREAN_FONT_NAME, KOREAN_FONT_BOLD_NAME

# RGB 튜플 (0-255) — reportlab/pptx 양쪽에서 이 값으로 각자의 Color 객체를 만든다.
ACCENT_BAR = (0x1A, 0x3A, 0x7C)
TITLE_TEXT = (0x1A, 0x1A, 0x2E)
INSIGHT_TEXT = (0x33, 0x33, 0x33)
UNIT_NOTE_TEXT = (0x99, 0x99, 0x99)
FOOTNOTE_TEXT = (0x99, 0x99, 0x99)
PAGE_NUM_TEXT = (0xBB, 0xBB, 0xBB)

TABLE_HEADER_TOP_BG = (0x3D, 0x4A, 0x5C)
TABLE_HEADER_PER_BG = (0x4F, 0x5D, 0x72)
TABLE_HEADER_TEXT = (0xFF, 0xFF, 0xFF)
TABLE_HEADER_PER_TEXT = (0xDD, 0xE5, 0xF0)
TABLE_BOLD_ROW_BG = (0xF0, 0xF3, 0xF9)
TABLE_BOLD_ROW_LABEL_BG = (0xE8, 0xEC, 0xF5)
TABLE_BOLD_ROW_LABEL_TEXT = (0x1A, 0x3A, 0x7C)
TABLE_BODY_TEXT = (0x22, 0x22, 0x22)
TABLE_GRID_LINE = (0xE3, 0xE6, 0xEC)

TITLE_FONT_SIZE = 15
INSIGHT_FONT_SIZE = 10.5
UNIT_NOTE_FONT_SIZE = 8
FOOTNOTE_FONT_SIZE = 7.5
PAGE_NUM_FONT_SIZE = 9
TABLE_FONT_SIZE = 7.5
TABLE_HEADER_FONT_SIZE = 7.5

# 16:9 위젯 슬라이드 크기 (인치)
PAGE_WIDTH_IN = 13.333
PAGE_HEIGHT_IN = 7.5
MARGIN_IN = 0.45
