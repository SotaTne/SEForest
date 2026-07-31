# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

app_dir = Path(SPECPATH).resolve()


def collect_directory(directory_name: str) -> list[tuple[str, str]]:
    """アプリケーションへ同梱するディレクトリ内のファイルを収集する。"""

    source_dir = app_dir / directory_name
    if not source_dir.exists():
        return []

    datas: list[tuple[str, str]] = []
    for source_path in source_dir.rglob("*"):
        if source_path.is_file():
            relative_path = source_path.relative_to(source_dir)
            target_dir = Path(directory_name) / relative_path.parent
            datas.append((str(source_path), str(target_dir)))
    return datas


datas = []
datas += collect_directory("assets")
datas += collect_directory("THIRD_PARTY_LICENSES")
datas.append((str(app_dir / "LICENSE"), "."))

a = Analysis(
    [str(app_dir / "main.py")],
    pathex=[str(app_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name="Forest",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Forest",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Forest.app",
        icon=None,
        bundle_identifier="jp.seforest.forest",
    )
