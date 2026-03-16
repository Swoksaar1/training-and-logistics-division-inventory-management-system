# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    *collect_submodules("inventory_app"),
    *collect_submodules("inventory_management_system"),
    "inventory_app",
    "inventory_app.apps",
    "inventory_app.urls",
    "inventory_app.views",
    "inventory_app.models",
    "inventory_app.serializers",
    "inventory_app.signals",
    "inventory_app.admin",
    "inventory_management_system",
    "inventory_management_system.settings",
    "inventory_management_system.urls",
    "inventory_management_system.wsgi",
    "inventory_management_system.asgi",
]

datas = [
    ("db.sqlite3", "."),
]

a = Analysis(
    ["run.backend.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="inventory_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
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
    name="inventory_backend",
)