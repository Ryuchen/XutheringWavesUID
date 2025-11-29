from gsuid_core.logger import logger
try:
    from ..waves_build.damage import *
except ImportError:
    logger.warning("无法导入 damage，将尝试下载")    
