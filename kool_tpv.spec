# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Definir los archivos y carpetas extra que queremos incluir en el EXE
# Formato: (ruta_origen, ruta_destino_dentro_del_exe)
added_files = [
    ('kool_tpv/assets', 'kool_tpv/assets'),
    ('kool_tpv/config', 'kool_tpv/config'),
    ('kool_tpv/base_datos/migraciones', 'kool_tpv/base_datos/migraciones'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PIL.Image',
        'customtkinter',
        'reportlab',
        'barcode',
        'googleapiclient',
        'google_auth_oauthlib',
        'win32print',
        'win32api',
        'win32con',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KoolTPV',
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
    # icon='kool_tpv/assets/logo/logo.ico' 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KoolTPV',
)
