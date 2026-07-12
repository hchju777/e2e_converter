# -*- mode: python ; coding: utf-8 -*-

import json
import os
from PyInstaller.utils.hooks import collect_all


pyreadstat_datas, pyreadstat_binaries, pyreadstat_hiddenimports = collect_all("pyreadstat")

# spec 파일이 scripts/ 디렉토리에 있으므로, 부모 디렉토리(프로젝트 루트)를 기준으로 경로 설정
project_root = os.path.dirname(SPECPATH)
settings_path = os.path.join(project_root, "config/settings.json")
app_version = open(os.path.join(project_root, "config/VERSION"), encoding="utf-8").read().strip()
with open(settings_path, encoding="utf-8") as settings_file:
    settings = json.load(settings_file)

# settings.json의 상대경로를 소스와 EXE 내부에서 동일하게 유지한다.
dashboard_template = settings["dashboard_template"]
if os.path.isabs(dashboard_template):
    raise ValueError("dashboard_template은 프로젝트 루트 기준 상대경로여야 합니다.")
dashboard_template_source = os.path.normpath(os.path.join(project_root, dashboard_template))
dashboard_template_dest = os.path.dirname(os.path.normpath(dashboard_template)) or "."
if not os.path.isfile(dashboard_template_source):
    raise FileNotFoundError(
        f"settings.json의 dashboard_template 파일을 찾을 수 없습니다: {dashboard_template_source}"
    )

a = Analysis(
    [os.path.join(project_root, "src/dashboard/web_app.py")],
    pathex=[project_root],
    binaries=pyreadstat_binaries,
    datas=pyreadstat_datas + [
        (settings_path, "config"),
        (os.path.join(project_root, "config/metric_spec.csv"), "config"),
        (os.path.join(project_root, "config/VERSION"), "config"),
        (dashboard_template_source, dashboard_template_dest),
        (os.path.join(project_root, "src/dashboard/report_assets/toc.html"), "src/dashboard/report_assets"),
    ],
    hiddenimports=pyreadstat_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"PsO_Dashboard_Converter_v{app_version}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
