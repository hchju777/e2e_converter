"""Edge 헤드리스 + DevTools Protocol로 대시보드 HTML 화면을 캡처하는 유틸리티.

PDF/PPTX 리포트는 이 모듈로 대시보드의 각 장표(page-section)를 열어
차트를 이미지로 캡처하고, 제목/인사이트/표 텍스트를 DOM에서 그대로 읽어온다.
"""

import base64
import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


class BrowserCaptureError(RuntimeError):
    """헤드리스 브라우저 캡처 중 발생한 오류."""


_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge() -> str:
    """설치된 Microsoft Edge 실행 파일 경로를 찾는다."""
    for candidate in _EDGE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    found = shutil.which("msedge")
    if found:
        return found
    raise BrowserCaptureError(
        "Microsoft Edge를 찾을 수 없습니다. PDF/PPTX 리포트를 생성하려면 Edge가 설치되어 있어야 합니다."
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class DashboardCapture:
    """Edge 헤드리스 인스턴스 하나를 관리하며 대시보드 요소를 캡처하는 컨텍스트 매니저."""

    def __init__(self, timeout: float = 20.0):
        self._edge_path = find_edge()
        self._port = _free_port()
        self._timeout = timeout
        self._proc = None
        self._ws = None
        self._msg_id = 0
        self._user_data_dir = None

    def __enter__(self) -> "DashboardCapture":
        import websocket  # 지연 임포트: 이 모듈이 없어도 나머지 앱은 동작해야 함

        self._websocket = websocket
        self._user_data_dir = tempfile.mkdtemp(prefix="pso_edge_")
        self._proc = subprocess.Popen(
            [
                self._edge_path,
                "--headless=new",
                "--disable-gpu",
                f"--remote-debugging-port={self._port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={self._user_data_dir}",
                "--no-first-run",
                "--window-size=1600,1200",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self._wait_for_devtools()
            tab = self._pick_tab()
            self._ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=self._timeout)
            self._send("Page.enable")
            self._send("Runtime.enable")
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._ws is not None:
                self._ws.close()
        finally:
            self._ws = None
            if self._proc is not None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                self._proc = None
            if self._user_data_dir:
                shutil.rmtree(self._user_data_dir, ignore_errors=True)
                self._user_data_dir = None

    def _wait_for_devtools(self):
        deadline = time.time() + self._timeout
        last_error = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self._port}/json/version", timeout=1):
                    return
            except (OSError, urllib.error.URLError) as error:
                last_error = error
                time.sleep(0.2)
        raise BrowserCaptureError(f"Edge DevTools 포트({self._port})에 연결하지 못했습니다: {last_error}")

    def _pick_tab(self) -> dict:
        with urllib.request.urlopen(f"http://127.0.0.1:{self._port}/json/list", timeout=self._timeout) as resp:
            tabs = json.loads(resp.read())
        for tab in tabs:
            if tab.get("type") == "page":
                return tab
        raise BrowserCaptureError("사용 가능한 Edge 탭을 찾지 못했습니다.")

    def _send(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        mid = self._msg_id
        self._ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            response = json.loads(self._ws.recv())
            if response.get("id") == mid:
                if "error" in response:
                    raise BrowserCaptureError(f"{method} 실패: {response['error']}")
                return response.get("result", {})

    def navigate(self, html_path: str | Path, wait: float = 1.0) -> None:
        """대시보드 HTML을 열고, 표지 오버레이를 닫고, 차트 애니메이션을 끈다."""
        url = Path(html_path).resolve().as_uri()
        self._send("Page.navigate", {"url": url})
        time.sleep(wait)
        self.evaluate("window.Chart && (Chart.defaults.animation = false);")
        self.evaluate("var c=document.getElementById('coverPage'); if (c) c.style.display='none';")

    def evaluate(self, expression: str):
        """JS 표현식을 실행하고 값을 반환한다 (문자열/숫자/불리언 등 JSON 직렬화 가능한 값만)."""
        result = self._send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        value = result.get("result", {})
        if value.get("subtype") == "error":
            raise BrowserCaptureError(f"페이지 스크립트 오류: {value.get('description')}")
        return value.get("value")

    def evaluate_json(self, expression: str):
        """JS 표현식의 결과를 JSON.stringify로 감싸 파이썬 객체로 반환한다."""
        text = self.evaluate(f"JSON.stringify({expression})")
        return json.loads(text) if text is not None else None

    def click(self, selector: str, wait: float = 0.4) -> None:
        found = self.evaluate(
            "(function(){var el=document.querySelector(" + json.dumps(selector) + ");"
            "if(!el) return false; el.click(); return true;})()"
        )
        if not found:
            raise BrowserCaptureError(f"클릭할 요소를 찾지 못했습니다: {selector}")
        time.sleep(wait)

    def exists(self, selector: str) -> bool:
        return bool(self.evaluate("!!document.querySelector(" + json.dumps(selector) + ")"))

    def text_of(self, selector: str) -> str | None:
        return self.evaluate(
            "(function(){var el=document.querySelector(" + json.dumps(selector) + ");"
            "return el ? el.innerText : null;})()"
        )

    def screenshot_element(self, selector: str) -> bytes:
        """요소의 경계 상자만 크롭한 PNG 스크린샷을 반환한다."""
        rect = self.evaluate_json(
            "document.querySelector(" + json.dumps(selector) + ").getBoundingClientRect()"
        )
        if rect is None:
            raise BrowserCaptureError(f"요소를 찾지 못했습니다: {selector}")
        result = self._send(
            "Page.captureScreenshot",
            {
                "format": "png",
                "clip": {
                    "x": rect["x"],
                    "y": rect["y"],
                    "width": rect["width"],
                    "height": rect["height"],
                    "scale": 1,
                },
            },
        )
        return base64.b64decode(result["data"])

    def goto_page(self, page_id: str, wait: float = 0.6) -> None:
        """사이드바 내비게이션에서 특정 page-section으로 이동한다."""
        self.click(f'.nav-item[data-page="{page_id}"]', wait=wait)

    def select_banner(self, page_id: str, filter_value: str, wait: float = 0.8) -> None:
        """특정 page-section 안에서 배너 탭(전체/수도권/지방/T1/T2/T3)을 클릭한다."""
        self.click(f'#page-{page_id} .tab-btn[data-f="{filter_value}"]', wait=wait)
