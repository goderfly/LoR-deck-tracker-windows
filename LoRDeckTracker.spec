# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/LoR-deck-tracker-windows/main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/LoR-deck-tracker-windows/data/cards_cache_ru.json', 'data'), ('C:/LoR-deck-tracker-windows/data/cards_cache_ru_ru.json', 'data'), ('C:/LoR-deck-tracker-windows/data/globals_ru.json', 'data'), ('C:/LoR-deck-tracker-windows/data/globals_ru_ru.json', 'data'), ('C:/LoR-deck-tracker-windows/data/settings.json', 'data'), ('C:/LoR-deck-tracker-windows/data/icons', 'data/icons'), ('C:/LoR-deck-tracker-windows/lor', 'lor')],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'urllib3', 'win32service', 'win32gui', 'win32con', 'win32process', 'PIL', 'lor', 'lor.manager', 'lor.panels', 'lor.advisor', 'lor.preview', 'lor.settings', 'lor.theme', 'lor.widgets', 'lor.win32ext', 'lor.card_db', 'lor.tracker_engine', 'lor.advisor_engine'],
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
    name='LoRDeckTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='C:/LoR-deck-tracker-windows/scripts/file_version_info.txt',
    icon=['C:/LoR-deck-tracker-windows/data/icons/app_icon.ico'],
)
