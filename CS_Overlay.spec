# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['CS_Overlay.py'],
    pathex=[],
    binaries=[
        ('C:/Users/Andrew/miniforge3/envs/overlay/Library/bin/ffi-8.dll', '.'),
        ('C:/Users/Andrew/miniforge3/envs/overlay/Library/bin/libbz2.dll', '.'),
        ('C:/Users/Andrew/miniforge3/envs/overlay/Library/bin/liblzma.dll', '.'),
        ('C:/Users/Andrew/miniforge3/envs/overlay/Library/bin/libmpdec-4.dll', '.'),
        ('C:/Users/Andrew/miniforge3/envs/overlay/Library/bin/zstd.dll', '.'),
    ],
    datas=[('draw.ico', '.')],
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
    name='CS Overlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['draw.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CS Overlay',
)
