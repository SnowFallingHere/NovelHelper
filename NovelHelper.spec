# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['NovelHelper.py'],
    pathex=[],
    binaries=[],
    datas=[('translations/*.json', 'translations')],
    hiddenimports=['core', 'core.config_manager', 'core.file_manager', 'core.language_manager',
                   'models', 'models.keyword_manager', 'models.novel_model', 'models.summary_generator',
                   'ui', 'ui.chapter_creator', 'ui.network_graph', 'ui.style_theme', 'ui.widget_factory',
                   'controllers', 'controllers.monitor_controller', 'cn2an'],
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
    name='NovelHelper',
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
