import base64
import json
import os
import socket
import tempfile
import unittest
import webbrowser
from pathlib import Path
from unittest import mock

from src.dashboard import web_app
from src.dashboard.web_app import (
    APP_HTML,
    _open_browser,
    _port_in_use,
    format_fieldwork,
    get_app_version,
    load_web_settings,
    parse_overview_input,
    render_app_html,
)


class AppVersionTests(unittest.TestCase):
    def test_version_uses_semantic_version_format(self):
        self.assertRegex(get_app_version(), r"^\d+\.\d+\.\d+$")

    def test_version_placeholder_exists_in_web_page(self):
        self.assertIn("{{APP_VERSION}}", APP_HTML)
        rendered = APP_HTML.replace("{{APP_VERSION}}", get_app_version())
        self.assertNotIn("{{APP_VERSION}}", rendered)
        self.assertIn(f"Version {get_app_version()}", rendered)


class WebSettingsTests(unittest.TestCase):
    def test_dashboard_template_comes_from_settings(self):
        settings = load_web_settings()

        self.assertEqual(Path(settings["dashboard_template"]).name, "PsO_dashboard_v4.html")
        self.assertTrue(Path(settings["dashboard_template"]).is_file())

    def test_resources_are_found_from_any_working_directory(self):
        """어느 폴더에서 python main.py web을 실행해도 설정을 찾아야 한다."""
        original = os.getcwd()
        os.chdir(tempfile.gettempdir())
        try:
            settings = load_web_settings()
            self.assertTrue(Path(settings["dashboard_template"]).is_file())
            self.assertRegex(get_app_version(), r"^\d+\.\d+\.\d+$")
        finally:
            os.chdir(original)


class StartupGuardTests(unittest.TestCase):
    def test_detects_a_port_already_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]

            self.assertTrue(_port_in_use("127.0.0.1", port))

        self.assertFalse(_port_in_use("127.0.0.1", port))

    def test_tells_the_user_where_to_go_when_the_browser_fails(self):
        messages = []
        with mock.patch.object(webbrowser, "open", return_value=False), \
             mock.patch.object(web_app.logger, "warning", lambda msg, *a: messages.append(msg % a if a else msg)):
            _open_browser("http://127.0.0.1:8765/")

        self.assertTrue(any("자동으로 열지 못했" in m for m in messages))
        self.assertTrue(any("http://127.0.0.1:8765/" in m for m in messages))

    def test_browser_errors_do_not_crash_startup(self):
        with mock.patch.object(webbrowser, "open", side_effect=RuntimeError("no browser")):
            _open_browser("http://127.0.0.1:8765/")   # 예외가 밖으로 나오면 실패


class FieldworkFormatTests(unittest.TestCase):
    def test_same_day_shows_year_on_both_sides(self):
        self.assertEqual(
            format_fieldwork("2026-07-25", "2026-07-25"), "2026년 7월 25일 ~ 2026년 7월 25일"
        )

    def test_range_within_one_year(self):
        self.assertEqual(
            format_fieldwork("2026-05-04", "2026-05-12"), "2026년 5월 4일 ~ 2026년 5월 12일"
        )

    def test_range_spanning_years_is_unambiguous(self):
        # 실사 기간이 해를 넘겨도 종료일 연도가 드러나야 한다.
        self.assertEqual(
            format_fieldwork("2025-01-01", "2026-07-26"), "2025년 1월 1일 ~ 2026년 7월 26일"
        )

    def test_rejects_reversed_range(self):
        with self.assertRaisesRegex(ValueError, "빠를 수 없"):
            format_fieldwork("2026-05-12", "2026-05-04")

    def test_rejects_invalid_format(self):
        with self.assertRaisesRegex(ValueError, "형식"):
            format_fieldwork("2026/05/12", "2026-05-13")


class OverviewInputTests(unittest.TestCase):
    def _encode(self, obj):
        return base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8")).decode("ascii")

    def test_parses_trims_and_formats(self):
        header = self._encode(
            {
                "target": ["A", "", "  B "],
                "sample": " N = 1 ",
                "region": "서울",
                "method": "온라인",
                "fieldwork_start": "2026-07-25",
                "fieldwork_end": "2026-07-30",
            }
        )
        result = parse_overview_input(header)
        self.assertEqual(result["target"], ["A", "B"])
        self.assertEqual(result["sample"], "N = 1")
        self.assertEqual(result["fieldwork"], "2026년 7월 25일 ~ 2026년 7월 30일")

    def test_none_header_returns_none(self):
        self.assertIsNone(parse_overview_input(None))


class ExcelUploadUiTests(unittest.TestCase):
    def test_excel_upload_elements_exist(self):
        for marker in ("excelDrop", "excelFile", "X-Excel-Bytes", "X-Excel-Name"):
            self.assertIn(marker, APP_HTML)

    def test_convert_requires_both_files(self):
        # 두 파일이 모두 선택되어야만 변환 버튼이 열린다.
        self.assertIn("button.disabled = !(selectedFile && selectedExcel)", APP_HTML)
        self.assertIn("과거 데이터 엑셀을 선택해 주세요", APP_HTML)

    def test_excel_download_is_offered(self):
        self.assertIn("xlsxDownload", APP_HTML)
        self.assertIn("PsO_history", APP_HTML)

    def test_excel_button_breaks_where_intended(self):
        # '엑셀' 다음에서 줄을 나누고, 낱말이 중간에서 끊기지 않게 한다.
        self.assertIn("📗 엑셀<br>(다음 차수용)", APP_HTML)
        self.assertIn("word-break:keep-all", APP_HTML)

    def test_button_labels_are_vertically_centered(self):
        # 한 줄짜리 버튼도 두 줄짜리와 같은 높이에서 글자가 가운데에 와야 한다.
        self.assertIn("display:flex;align-items:center;justify-content:center", APP_HTML)


class UploadFeedbackTests(unittest.TestCase):
    def test_reports_wrong_extension_clearly(self):
        self.assertIn("xlsx 형식의 파일을 업로드하세요", APP_HTML)
        self.assertIn("sav 형식의 파일을 업로드하세요", APP_HTML)

    def test_error_is_shown_inside_the_drop_zone(self):
        """화면 아래 상태창만으로는 스크롤 밖이라 보이지 않는다."""
        self.assertIn("function markDropInvalid(", APP_HTML)
        self.assertIn(".drop.invalid{border-color:#d94a4a", APP_HTML)
        self.assertIn("markDropInvalid(drop,'❌ sav 형식의 파일을 업로드하세요.',file)", APP_HTML)
        self.assertIn("markDropInvalid(excelDrop,'❌ xlsx 형식의 파일을 업로드하세요.',file)", APP_HTML)

    def test_wrong_file_can_actually_be_selected(self):
        # accept 필터가 있으면 잘못된 파일이 선택 대화상자에 아예 안 보여 오류를 낼 수 없다.
        self.assertIn('<input id="excelFile" type="file">', APP_HTML)
        self.assertIn('<input id="file" type="file">', APP_HTML)

    def test_wrong_file_clears_previous_selection(self):
        self.assertIn("selectedFile=null; refreshConvertButton();", APP_HTML)
        self.assertIn("selectedExcel=null; refreshConvertButton();", APP_HTML)

    def test_file_errors_do_not_break_the_page(self):
        # 잘못된 파일을 골라도 예외가 화면 밖으로 튀지 않도록 두 선택 함수를 모두 감싼다.
        self.assertEqual(APP_HTML.count("markDropInvalid(drop,'❌ 파일을 읽지 못했습니다: '"), 1)
        self.assertEqual(APP_HTML.count("markDropInvalid(excelDrop,'❌ 파일을 읽지 못했습니다: '"), 1)


class PeriodSelectorTests(unittest.TestCase):
    def test_uses_numeric_year_and_wave_inputs(self):
        for marker in ('id="periodYear"', 'id="periodWave"', 'type="number"'):
            self.assertIn(marker, APP_HTML)
        self.assertNotIn('id="period" type="text"', APP_HTML)

    def test_defaults_to_this_year_and_first_wave(self):
        self.assertIn("periodYear.value=String(new Date().getFullYear()).slice(-2)", APP_HTML)
        self.assertIn("periodWave.value='1'", APP_HTML)


class FieldworkDefaultTests(unittest.TestCase):
    def test_start_comes_from_uploaded_excel(self):
        # 시작일은 엑셀의 첫 차수에서 읽고, 종료일은 오늘로 맞춘다.
        self.assertIn("/excel-info", APP_HTML)
        self.assertIn("ovStart.value=info.fieldwork_start", APP_HTML)
        self.assertIn("ovEnd.value=todayISO()", APP_HTML)

    def test_reporting_wave_no_longer_drives_dates(self):
        self.assertNotIn("fieldworkStartFor", APP_HTML)
        self.assertIn("function refreshPeriod(){ periodPreview.textContent=periodText(); }", APP_HTML)

    def test_reporting_wave_follows_the_excel(self):
        # 보고 차수는 엑셀에 아직 없는 바로 다음 차수로 채워진다.
        self.assertIn("periodYear.value=String(info.next_year)", APP_HTML)
        self.assertIn("periodWave.value=String(info.next_number)", APP_HTML)


class SaveDialogOrderTests(unittest.TestCase):
    def test_picks_destination_before_generating(self):
        """PDF/PPTX는 생성이 오래 걸려, 만든 뒤에 물으면 저장 대화상자 권한이 만료된다."""
        picker = APP_HTML.index("const target=await pickSaveTarget(")
        fetch = APP_HTML.index("const fileResponse=await fetch(data[cfg.key")
        self.assertLess(picker, fetch, "저장 위치를 먼저 물어야 합니다")

    def test_split_helpers_exist(self):
        self.assertIn("async function pickSaveTarget(", APP_HTML)
        self.assertIn("async function writeToTarget(", APP_HTML)


class ProgressEmphasisTests(unittest.TestCase):
    def test_working_status_is_animated(self):
        self.assertIn("@keyframes pulse", APP_HTML)
        self.assertIn(".status.working{border:2px solid", APP_HTML)

    def test_respects_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", APP_HTML)


class AppHtmlOverviewTests(unittest.TestCase):
    def test_overview_placeholders_present(self):
        for placeholder in ("{{OV_TARGET}}", "{{OV_SAMPLE}}", "{{OV_REGION}}", "{{OV_METHOD}}"):
            self.assertIn(placeholder, APP_HTML)

    def test_render_fills_template_defaults(self):
        page = render_app_html(load_web_settings())
        self.assertNotIn("{{OV_", page)
        self.assertIn("N = 35", page)
        self.assertIn("전국", page)
