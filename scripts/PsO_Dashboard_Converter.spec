# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all


pyreadstat_datas, pyreadstat_binaries, pyreadstat_hiddenimports = collect_all("pyreadstat")

# spec 파일이 scripts/ 디렉토리에 있으므로, 부모 디렉토리(프로젝트 루트)를 기준으로 경로 설정
project_root = os.path.dirname(SPECPATH)
app_version = open(os.path.join(project_root, "config/VERSION"), encoding="utf-8").read().strip()

a = Analysis(
    [os.path.join(project_root, "src/dashboard/web_app.py")],
    pathex=[project_root],
    binaries=pyreadstat_binaries,
    datas=pyreadstat_datas + [
        (os.path.join(project_root, "config/settings.json"), "config"),
        (os.path.join(project_root, "config/metric_spec.csv"), "config"),
        (os.path.join(project_root, "config/VERSION"), "config"),
        (os.path.join(project_root, "db/PsO_dashboard_v4 (2).html"), "db"),
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
