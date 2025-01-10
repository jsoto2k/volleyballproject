# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=['C:\\Users\\Julian\\Desktop\\VolleyballProjectCustom\\.venv\\Lib\\site-packages'],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('C:\\Users\\Julian\\Desktop\\VolleyballProjectCustom\\.venv\\Lib\\site-packages\\datavolley', 'datavolley')],
    hiddenimports=['flask', 'flask_sqlalchemy', 'matplotlib', 'matplotlib.pyplot', 'seaborn', 'pandas', 'numpy', 'datavolley'],
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
    name='app',
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
)
