"""
日志管理器 - 提供轮转、归档和清理功能
"""
import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from .config_manager import ConfigManager
from .file_manager import get_base_dir

def get_log_dir():
    """获取日志目录"""
    log_dir = os.path.join(get_base_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logging(
    log_name='NovelHelper',
    max_bytes=5*1024*1024,  # 5MB per file
    backup_count=10,       # 保留最多10个文件
    log_level=logging.INFO,
    use_timed_rotation=False,
    when='midnight',
    interval=1,
    backup_days=30
):
    """
    配置日志系统

    Args:
        log_name: 日志文件名前缀
        max_bytes: 单个日志文件最大字节数（仅在 size 轮转模式下）
        backup_count: 保留文件数量
        log_level: 日志级别
        use_timed_rotation: 是否使用时间轮转（默认按大小）
        when: 时间轮转触发点 ('S'-秒, 'M'-分, 'H'-时, 'D'-天, 'midnight'-午夜)
        interval: 时间间隔
        backup_days: 保留天数（仅用于清理）
    """
    log_dir = get_log_dir()
    log_file = os.path.join(log_dir, f"{log_name}.log")

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有的 handlers，防止重复输出
    if root_logger.handlers:
        for h in root_logger.handlers:
            h.close()
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件 handler
    if use_timed_rotation:
        # 时间轮转
        file_handler = TimedRotatingFileHandler(
            log_file,
            when=when,
            interval=interval,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        # 大小轮转
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )

    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 清理旧日志
    clean_old_logs(log_dir, backup_days)

    return root_logger

def clean_old_logs(log_dir, keep_days=30):
    """
    清理过期的日志文件

    Args:
        log_dir: 日志目录
        keep_days: 保留天数

    Returns:
        删除的文件数量
    """
    if not os.path.exists(log_dir):
        return 0

    deleted_count = 0
    now = datetime.now().timestamp()
    cutoff = now - (keep_days * 24 * 60 * 60)

    try:
        for filename in os.listdir(log_dir):
            if not (filename.endswith('.log') or '.log.' in filename):
                continue

            file_path = os.path.join(log_dir, filename)
            if not os.path.isfile(file_path):
                continue

            try:
                if os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
                    deleted_count += 1
                    logging.debug(f"删除旧日志: {filename}")
            except Exception as e:
                logging.warning(f"清理日志 {filename} 失败: {e}")
    except Exception as e:
        logging.error(f"清理旧日志过程出错: {e}")

    return deleted_count

def get_log_size():
    """获取当前日志目录大小（字节）"""
    log_dir = get_log_dir()
    total = 0
    try:
        for filename in os.listdir(log_dir):
            filepath = os.path.join(log_dir, filename)
            if os.path.isfile(filepath):
                total += os.path.getsize(filepath)
    except Exception:
        pass
    return total

def archive_logs():
    """归档当前日志到 zip 文件"""
    log_dir = get_log_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_name = os.path.join(log_dir, f"NovelHelper_logs_{timestamp}.zip")

    try:
        import zipfile
        with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(log_dir):
                for f in files:
                    if f.endswith('.log') and not f.endswith('.zip'):
                        filepath = os.path.join(root, f)
                        arcname = os.path.relpath(filepath, log_dir)
                        zf.write(filepath, arcname)
        return archive_name
    except Exception as e:
        logging.error(f"归档失败: {e}")
        return None
