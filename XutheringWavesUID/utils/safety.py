from gsuid_core.logger import logger

def generate_dynamic_version(*args, **kwargs):
    try:
        from .waves_build.safety import generate_dynamic_version as _func
        return _func(*args, **kwargs)
    except ImportError:
        logger.error("请等待下载完成")
        return ""


def safe_calc_damage(*args, **kwargs):
    try:
        from .waves_build.safety import safe_calc_damage as _func
        return _func(*args, **kwargs)
    except ImportError:
        logger.error("请等待下载完成")
        return "0", "0"
