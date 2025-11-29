from gsuid_core.logger import logger
try:
    from .waves_build.calculate import *
except ImportError:
    logger.warning("无法导入 calculate，将尝试下载")
        