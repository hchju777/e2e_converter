"""비개발자용 로컬 SAV → HTML/CSV 변환 웹 애플리케이션."""

import hashlib
import json
import os
import re
import signal
import tempfile
import threading
import time
import uuid
import webbrowser
import sys
from contextlib import contextmanager
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pyreadstat

from src.dashboard.build_dashboard import _period_label, build_dashboard
from src.dashboard.generate_pdf import generate_pdf
from src.dashboard.generate_pptx import generate_pptx
from src.metrics.calc_metrics import calc_metrics, load_settings, load_spec
from src.utils.banner import filter_banner_data, validate_banner_configs
from src.utils.logger import get_logger


logger = get_logger(__name__)
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

APP_HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PsO Dashboard Converter v{{APP_VERSION}}</title>
  <style>
    *{box-sizing:border-box} body{margin:0;background:#f3f6fb;color:#17233c;font-family:Arial,'Noto Sans KR',sans-serif}
    .wrap{max-width:760px;margin:48px auto;padding:0 20px}.card{background:white;border-radius:18px;padding:34px;box-shadow:0 12px 36px #1a31551a}
    h1{margin:0 0 8px;font-size:28px}.sub{margin:0 0 28px;color:#61708b;line-height:1.6}
    .drop{border:2px dashed #9eb0cc;border-radius:14px;padding:42px 20px;text-align:center;background:#f9fbff;cursor:pointer;transition:.2s}
    .drop.over{border-color:#008e4e;background:#effaf5}.drop strong{display:block;font-size:18px;margin-bottom:8px}.drop span{color:#71809a}
    input[type=file]{display:none}.field{margin-top:22px}.field label{display:block;font-weight:700;margin-bottom:8px}
    input[type=text]{width:100%;padding:13px 14px;border:1px solid #cbd5e5;border-radius:9px;font-size:16px}
    button,.download{display:inline-block;border:0;border-radius:9px;padding:13px 18px;font-weight:700;text-decoration:none;cursor:pointer}
    #convert{width:100%;margin-top:22px;background:#008e4e;color:white;font-size:16px}#convert:disabled{background:#9ba8b8;cursor:not-allowed}
    .status{display:none;margin-top:22px;padding:15px;border-radius:10px;line-height:1.6;white-space:pre-wrap}.status.show{display:block}
    .working{background:#edf5ff;color:#174f91}.error{background:#fff0f0;color:#a42525}.success{background:#edf9f3;color:#11633d}
    .downloads{display:none;margin-top:18px;gap:8px;flex-wrap:wrap}.downloads.show{display:flex}.download{background:#17233c;color:white;flex:1;min-width:150px;text-align:center}
    .warnings{display:none;margin-top:16px;padding:16px 18px;border:1px solid #f0cf7a;border-radius:10px;background:#fff9e8;color:#704b00;font-size:14px;line-height:1.7}
    .warnings.show{display:block}.warnings-title{font-weight:700;font-size:15px;margin-bottom:10px}.warning-item{padding:9px 0;border-top:1px solid #f2dfad;white-space:pre-wrap;overflow-wrap:anywhere}.warning-item:first-of-type{border-top:0}
    .privacy{margin-top:22px;color:#71809a;font-size:13px;text-align:center}
  </style>
</head>
<body><div class="wrap"><div class="card">
  <h1>📊 PsO Dashboard Converter</h1>
  <div style="margin:-2px 0 12px;color:#008e4e;font-weight:700">Version {{APP_VERSION}}</div>
  <p class="sub">SPSS SAV 파일을 선택하면 지표를 계산해 HTML 대시보드, CSV 결과, PDF 보고서, PPTX 프레젠테이션을 만듭니다.</p>
  <div id="drop" class="drop"><strong>📂 SAV 파일을 여기에 놓으세요</strong><span>또는 클릭해서 파일 선택 (.sav, 최대 100MB)</span></div>
  <input id="file" type="file" accept=".sav,.SAV">
  <div class="field"><label for="period">보고 차수</label><input id="period" type="text" value="26년 6차" placeholder="예: 26년 6차"></div>
  <button id="convert" disabled>🚀 대시보드 생성</button>
  <div id="status" class="status"></div>
  <div id="downloads" class="downloads"><a id="htmlDownload" class="download">🌐 HTML 다운로드</a><a id="csvDownload" class="download">📄 CSV 다운로드</a><a id="pdfDownload" class="download">📋 PDF 보고서</a><a id="pptxDownload" class="download">🎯 PPTX 발표</a></div>
  <div id="warnings" class="warnings"></div>
  <div class="privacy">🔒 파일은 이 PC 내부에서만 처리되며 외부 서버로 전송되지 않습니다.</div>
</div></div>
<script>
const drop=document.getElementById('drop'), fileInput=document.getElementById('file'), button=document.getElementById('convert');
const statusEl=document.getElementById('status'), downloads=document.getElementById('downloads'), warnings=document.getElementById('warnings');
let selectedFile=null;
function clearWarnings(){warnings.className='warnings';warnings.innerHTML='';}
function selectFile(file){
  if(!file || !file.name.toLowerCase().endsWith('.sav')){showStatus('error','❌ .sav 파일만 선택할 수 있습니다.');return;}
  selectedFile=file; drop.querySelector('strong').textContent='✅ '+file.name; drop.querySelector('span').textContent=(file.size/1024/1024).toFixed(2)+' MB'; button.disabled=false;
  downloads.classList.remove('show'); clearWarnings(); statusEl.className='status';
}
function showStatus(type,text){statusEl.className='status show '+type;statusEl.textContent=text;}
drop.onclick=()=>fileInput.click(); fileInput.onchange=e=>selectFile(e.target.files[0]);
for(const event of ['dragenter','dragover']) drop.addEventListener(event,e=>{e.preventDefault();drop.classList.add('over')});
for(const event of ['dragleave','drop']) drop.addEventListener(event,e=>{e.preventDefault();drop.classList.remove('over')});
drop.addEventListener('drop',e=>selectFile(e.dataTransfer.files[0]));
button.onclick=async()=>{
  if(!selectedFile)return; const period=document.getElementById('period').value.trim();
  button.disabled=true; downloads.classList.remove('show'); clearWarnings(); showStatus('working','⏳ SAV를 읽고 6개 배너의 지표를 계산하고 있습니다...');
  try{
    const response=await fetch('/convert?period='+encodeURIComponent(period),{method:'POST',headers:{'Content-Type':'application/octet-stream','X-File-Name':encodeURIComponent(selectedFile.name)},body:selectedFile});
    const data=await response.json(); if(!response.ok)throw new Error(data.error||'변환에 실패했습니다.');
    showStatus('success',`✅ 변환 완료\n응답자 ${data.respondents}명 · 지표 ${data.metrics}개 · 경고 ${data.warning_count}건`);
    document.getElementById('htmlDownload').href=data.html_url; document.getElementById('csvDownload').href=data.csv_url;
    document.getElementById('pdfDownload').href=data.pdf_url; document.getElementById('pptxDownload').href=data.pptx_url;
    downloads.classList.add('show');
    ['pdfDownload','pptxDownload'].forEach(id=>{
      const link=document.getElementById(id); let built=false;
      link.onclick=()=>{ if(!built){ built=true; showStatus('working','⏳ 처음 요청이라 PDF/PPTX를 새로 만들고 있습니다. 최대 30초 정도 걸릴 수 있어요...'); } };
    });
    if(data.warnings.length){
      warnings.className='warnings show';
      warnings.innerHTML='<div class="warnings-title">⚠️ 계산 경고 '+data.warning_count+'건</div>';
      data.warnings.slice(0,20).forEach((message,index)=>{
        const item=document.createElement('div'); item.className='warning-item';
        item.textContent=(index+1)+'. '+message.split(' | ').join('\n   '); warnings.appendChild(item);
      });
      if(data.warnings.length>20){const more=document.createElement('div');more.className='warning-item';more.textContent='외 '+(data.warnings.length-20)+'건은 CSV의 경고 컬럼에서 확인하세요.';warnings.appendChild(more)}
    }
  }catch(error){showStatus('error','❌ '+error.message)}finally{button.disabled=false}
};
</script></body></html>"""


def bundled_resource(relative_path: str) -> Path:
    """개발 환경 또는 PyInstaller EXE 내부의 리소스 경로를 반환한다."""
    base_dir = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return base_dir / relative_path


def get_app_version() -> str:
    version = bundled_resource("config/VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"VERSION은 x.y.z 형식이어야 합니다: {version}")
    return version


def load_web_settings() -> dict:
    settings = load_settings(str(bundled_resource("config/settings.json")))
    settings["spec_path"] = str(bundled_resource("config/metric_spec.csv"))
    settings["dashboard_template"] = str(bundled_resource("db/PsO_dashboard_v4 (2).html"))
    return settings


def convert_sav(sav_path: Path, period: str, settings: dict, output_dir: Path, sav_hash: str) -> dict:
    """업로드된 SAV를 계산하여 HTML/CSV 파일과 요약 정보를 반환한다.

    PDF/PPTX는 여기서 만들지 않는다 — 실제로 다운로드가 요청될 때 lazy하게 생성한다
    (ConverterServer.get_or_build_report 참고).
    """
    _period_label(period)  # 계산 전에 차수 형식을 먼저 검증한다.
    logger.info("📂 업로드 SAV 읽는 중: %s", sav_path.name)
    df, _meta = pyreadstat.read_sav(str(sav_path))
    logger.info("📊 SAV 로드 완료: 응답자 %d명, 변수 %d개", len(df), len(df.columns))

    specs = load_spec(settings["spec_path"], "전체")
    banner_configs = settings["dashboard_banners"]
    validate_banner_configs(banner_configs)
    banner_values = {}
    result_frames = []
    warning_messages = []

    for config in banner_configs:
        name = config["name"]
        banner_df = filter_banner_data(df, config)
        logger.info("🧮 %s 배너 계산 중 (%d명)", name, len(banner_df))
        result = calc_metrics(banner_df, specs, period)
        failures = result[result["오류"] != ""]
        if not failures.empty:
            first = failures.iloc[0]
            raise ValueError(f"{name} 배너 계산 실패: {first['문항']} - {first['오류']}")
        result["배너조건"] = name
        result_frames.append(result)
        banner_values[name] = [None if pd.isna(value) else value for value in result[period].tolist()]
        for row in result[result["경고"] != ""][["항목", "문항", "경고"]].to_dict("records"):
            warning_messages.append(f"{name} | {row['항목']} | {row['문항']} | {row['경고']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    result_df = pd.concat(result_frames, ignore_index=True)
    csv_path = output_dir / "metrics.csv"
    html_path = output_dir / "dashboard.html"

    result_df.to_csv(csv_path, index=False, encoding="utf-8-sig", na_rep="NaN")
    build_dashboard(settings["dashboard_template"], str(html_path), period, banner_values)

    logger.info("✅ 변환 완료: 지표 %d개, 경고 %d개", len(result_df), len(warning_messages))
    return {
        "html_path": html_path,
        "csv_path": csv_path,
        "period": period,
        # 같은 SAV(내용 동일) + 같은 차수는 항상 같은 결과이므로, 업로드 토큰이 달라도
        # PDF/PPTX 캐시를 공유할 수 있도록 내용 기반 키를 만든다.
        "cache_key": f"{sav_hash}:{period}",
        "respondents": len(df),
        "metrics": len(result_df),
        "warnings": warning_messages,
    }


class ConverterServer(ThreadingHTTPServer):
    def __init__(self, address, handler, settings):
        super().__init__(address, handler)
        self.settings = settings
        self.temp_dir = tempfile.TemporaryDirectory(prefix="pso_converter_")
        self.jobs: dict[str, dict] = {}
        self.jobs_lock = threading.Lock()
        self._active_jobs = 0
        self._active_jobs_lock = threading.Lock()

        # PDF/PPTX는 요청이 실제로 들어올 때 lazy하게 만들고, 같은 SAV+차수(cache_key)에
        # 대해서는 다시 만들지 않고 캐시된 파일을 그대로 돌려준다.
        self._report_cache_dir = Path(self.temp_dir.name) / "_report_cache"
        self._report_cache_dir.mkdir(exist_ok=True)
        self.report_cache: dict[str, dict[str, Path]] = {}
        self.report_cache_lock = threading.Lock()
        self._report_build_locks: dict[str, threading.Lock] = {}

    @property
    def active_job_count(self) -> int:
        with self._active_jobs_lock:
            return self._active_jobs

    @contextmanager
    def track_job(self):
        """/convert, /download 처리 구간을 표시한다. 종료 시 이 구간이 끝날 때까지 temp_dir을 지우지 않는다."""
        with self._active_jobs_lock:
            self._active_jobs += 1
        try:
            yield
        finally:
            with self._active_jobs_lock:
                self._active_jobs -= 1

    def _build_lock_for(self, cache_key: str, kind: str) -> threading.Lock:
        lock_key = f"{cache_key}:{kind}"
        with self.report_cache_lock:
            lock = self._report_build_locks.get(lock_key)
            if lock is None:
                lock = threading.Lock()
                self._report_build_locks[lock_key] = lock
            return lock

    def get_or_build_report(self, kind: str, cache_key: str, dashboard_html: Path, period: str) -> Path:
        """PDF/PPTX를 요청 시점에 만들고(lazy), 같은 cache_key로 이미 만든 게 있으면 그걸 재사용한다."""
        cached = self._cached_report_path(cache_key, kind)
        if cached is not None:
            logger.info("♻️ 캐시된 %s 재사용 (key=%s)", kind.upper(), cache_key[:16])
            return cached

        # 같은 키에 대한 생성은 한 번만: 동시에 두 요청이 들어와도 한쪽만 실제로 만든다.
        with self._build_lock_for(cache_key, kind):
            cached = self._cached_report_path(cache_key, kind)
            if cached is not None:
                logger.info("♻️ 캐시된 %s 재사용 (key=%s)", kind.upper(), cache_key[:16])
                return cached

            # cache_key(예: "<sha256>:26년 6차")에는 Windows 경로에 쓸 수 없는 문자(:)가
            # 섞여 있을 수 있으므로, 폴더명은 별도로 해시해서 만든다.
            safe_dir_name = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
            out_dir = self._report_cache_dir / safe_dir_name
            out_dir.mkdir(parents=True, exist_ok=True)
            extension = "pdf" if kind == "pdf" else "pptx"
            out_path = out_dir / f"report.{extension}"

            logger.info("🛠️ %s 최초 요청 — 생성 시작 (key=%s)", kind.upper(), cache_key[:16])
            if kind == "pdf":
                generate_pdf(str(out_path), str(dashboard_html), period)
            else:
                generate_pptx(str(out_path), str(dashboard_html), period)

            with self.report_cache_lock:
                self.report_cache.setdefault(cache_key, {})[kind] = out_path
            return out_path

    def _cached_report_path(self, cache_key: str, kind: str) -> Path | None:
        with self.report_cache_lock:
            path = self.report_cache.get(cache_key, {}).get(kind)
        if path is not None and path.exists():
            return path
        return None

    def server_close(self):
        super().server_close()
        self.temp_dir.cleanup()


class ConverterHandler(BaseHTTPRequestHandler):
    server: ConverterServer

    def log_message(self, format, *args):
        logger.debug(format, *args)

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = APP_HTML.replace("{{APP_VERSION}}", get_app_version()).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "download" and parts[2] in {"html", "csv", "pdf", "pptx"}:
            kind = parts[2]
            with self.server.jobs_lock:
                job = self.server.jobs.get(parts[1])
            if not job:
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            if kind in ("html", "csv"):
                file_path = job[f"{kind}_path"]
            else:
                try:
                    with self.server.track_job():
                        file_path = self.server.get_or_build_report(
                            kind, job["cache_key"], job["html_path"], job["period"]
                        )
                except Exception:
                    logger.exception("💥 %s 생성 실패", kind.upper())
                    self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{kind.upper()} 생성에 실패했습니다."})
                    return

            body = file_path.read_bytes()

            filename_map = {
                "html": "PsO_dashboard.html",
                "csv": "PsO_metrics.csv",
                "pdf": "PsO_report.pdf",
                "pptx": "PsO_presentation.pptx",
            }
            content_type_map = {
                "html": "text/html; charset=utf-8",
                "csv": "text/csv; charset=utf-8",
                "pdf": "application/pdf",
                "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            }
            
            filename = filename_map[kind]
            content_type = content_type_map[kind]
            
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/convert":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        with self.server.track_job():
            self._handle_convert(parsed)

    def _handle_convert(self, parsed):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ValueError("업로드된 파일이 비어 있습니다.")
            if length > MAX_UPLOAD_BYTES:
                raise ValueError("SAV 파일은 100MB 이하여야 합니다.")
            period = parse_qs(parsed.query).get("period", [""])[0].strip()
            if not period:
                raise ValueError("보고 차수를 입력해 주세요.")
            encoded_name = self.headers.get("X-File-Name", "uploaded.sav")
            filename = Path(encoded_name).name
            if not filename.lower().endswith(".sav"):
                raise ValueError(".sav 파일만 업로드할 수 있습니다.")

            token = uuid.uuid4().hex
            job_dir = Path(self.server.temp_dir.name) / token
            job_dir.mkdir()
            sav_path = job_dir / "input.sav"
            remaining = length
            hasher = hashlib.sha256()
            with sav_path.open("wb") as file:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("파일 업로드가 중간에 끊겼습니다.")
                    file.write(chunk)
                    hasher.update(chunk)
                    remaining -= len(chunk)

            result = convert_sav(sav_path, period, self.server.settings, job_dir, hasher.hexdigest())
            with self.server.jobs_lock:
                self.server.jobs[token] = result
            self._json(HTTPStatus.OK, {
                "version": get_app_version(),
                "respondents": result["respondents"], "metrics": result["metrics"],
                "warning_count": len(result["warnings"]), "warnings": result["warnings"],
                "html_url": f"/download/{token}/html", "csv_url": f"/download/{token}/csv",
                "pdf_url": f"/download/{token}/pdf", "pptx_url": f"/download/{token}/pptx",
            })
        except Exception as error:
            logger.exception("💥 SAV 변환 실패")
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def _install_shutdown_handlers(shutdown_event: threading.Event) -> None:
    """Ctrl+C(SIGINT), SIGTERM, Ctrl+Break(Windows SIGBREAK)를 받으면 종료 이벤트를 켠다."""

    def handle_signal(signum, _frame):
        logger.info("🛑 종료 신호를 받았습니다 (signal=%s)", signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)
    if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break
        signal.signal(signal.SIGBREAK, handle_signal)


def _graceful_shutdown(server: ConverterServer, timeout: float = 60.0) -> None:
    """새 요청을 막고, 진행 중인 변환 작업이 끝날 때까지 기다린 뒤 정리한다."""
    logger.info("⏹️ 새 요청 수신을 중단합니다")
    server.shutdown()  # serve_forever 루프 종료 (다른 스레드에서 호출해야 함)

    waited = 0.0
    interval = 1.0
    while server.active_job_count > 0 and waited < timeout:
        logger.info("⏳ 진행 중인 변환 작업 %d건이 끝나기를 기다리는 중... (%.0fs 경과)",
                    server.active_job_count, waited)
        time.sleep(interval)
        waited += interval

    if server.active_job_count > 0:
        logger.warning("⚠️ %d건의 작업이 끝나지 않았지만 종료를 진행합니다", server.active_job_count)

    server.server_close()
    logger.info("✅ 변환기를 안전하게 종료했습니다")


def main():
    settings = load_web_settings()
    server = ConverterServer((HOST, DEFAULT_PORT), ConverterHandler, settings)
    url = f"http://{HOST}:{server.server_port}/"
    logger.info("🚀 PsO 변환기 v%s 실행: %s", get_app_version(), url)
    logger.info("🔒 SAV 파일은 이 PC 안에서만 처리됩니다")
    if os.environ.get("PSO_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    shutdown_event = threading.Event()
    _install_shutdown_handlers(shutdown_event)

    server_thread = threading.Thread(target=server.serve_forever, name="pso-http-server", daemon=True)
    server_thread.start()

    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(0.5)
    except KeyboardInterrupt:
        # signal 핸들러가 걸리지 않는 환경을 위한 안전망
        logger.info("🛑 Ctrl+C를 감지했습니다")
    finally:
        _graceful_shutdown(server, timeout=60.0)
        server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
