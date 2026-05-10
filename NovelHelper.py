"""
NovelHelper 主应用程序启动入口
基于 qfluentwidgets / qframelesswindow 实现亚克力窗口
"""
import os
import sys
import logging
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt


def init_logging():
    from core.log_manager import setup_logging
    setup_logging(
        log_name=f"NovelHelper_{datetime.now().strftime('%Y%m%d')}",
        max_bytes=5 * 1024 * 1024,
        backup_count=10
    )


def setup_import_path():
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_script_dir)
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    os.chdir(_script_dir)


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("NovelHelper")
    app.setOrganizationName("NovelHelper")

    init_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("NovelHelper 启动中...")

    try:
        setup_import_path()

        from qfluentwidgets import setTheme, Theme
        from novelhelper.core.config_manager import ConfigManager

        theme_name = ConfigManager.get('UI', 'theme', fallback='fluent')
        if theme_name == 'matrix':
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)

        from novelhelper.main_window import NovelHelper as MainWindow
        window = MainWindow()
        window.show()

        logger.info("NovelHelper 启动成功！")
        return app.exec_()

    except Exception as e:
        logger.critical(f"启动失败: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())