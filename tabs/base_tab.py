"""
标签页基类
提供统一的标签页接口，支持延迟初始化、数据刷新和资源管理
"""

from PyQt5.QtWidgets import QWidget
import logging

logger = logging.getLogger(__name__)


class BaseTab(QWidget):
    """
    标签页基类
    
    功能：
    - 延迟初始化（首次显示时才构建UI）
    - 统一的数据加载/刷新机制
    - 资源清理支持
    """

    data_loaded = object()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initialized = False
        self._data = None
        self.tab_name = "未命名标签"
        logger.debug(f"[{self.__class__.__name__}] 初始化")

    def initialize(self):
        if self._initialized:
            return True
        try:
            logger.info(f"[{self.tab_name}] 开始延迟初始化...")
            self._build_ui()
            self._load_data()
            self._initialized = True
            logger.info(f"[{self.tab_name}] 初始化完成")
            return True
        except Exception as e:
            logger.error(f"[{self.tab_name}] 初始化失败: {str(e)}", exc_info=True)
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _build_ui(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} 必须实现 _build_ui() 方法"
        )

    def _load_data(self):
        pass

    def retranslate_ui(self):
        """语言切换时刷新所有控件文字。子类重写此方法。"""
        pass

    def refresh(self, force=False):
        if not self._initialized:
            self.initialize()
            return
        logger.debug(f"[{self.tab_name}] 刷新数据 (force={force})")
        self._load_data()

    def cleanup(self):
        logger.debug(f"[{self.tab_name}] 清理资源")
        self._data = None

    def get_status(self) -> dict:
        return {
            'tab_name': self.tab_name,
            'initialized': self._initialized,
            'has_data': self._data is not None,
        }

    def on_show(self):
        pass

    def on_hide(self):
        pass


def initialize_tab_if_needed(tab: BaseTab) -> bool:
    if isinstance(tab, BaseTab) and not tab.is_initialized:
        return tab.initialize()
    return False
