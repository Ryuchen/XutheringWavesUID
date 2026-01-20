import json
import re
from typing import Dict, Optional

from gsuid_core.logger import logger

from ..utils.resource.RESOURCE_PATH import GACHA_CONFIG_PATH


def load_gacha_config() -> Dict[str, int]:
    if not GACHA_CONFIG_PATH.exists():
        return {}

    try:
        with open(GACHA_CONFIG_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception as e:
        logger.exception(f"加载抽卡配置失败: {e}")
        return {}


def save_gacha_config(config: Dict[str, int]) -> bool:
    try:
        with open(GACHA_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.exception(f"保存抽卡配置失败: {e}")
        return False


def parse_gacha_min_value(text: str) -> Optional[int]:
    match = re.search(r"\d+", text or "")
    if not match:
        return None
    try:
        value = int(match.group(0))
    except ValueError:
        return None
    return value if value > 0 else None


def get_group_gacha_min(group_id: Optional[str]) -> Optional[int]:
    if not group_id:
        return None
    config = load_gacha_config()
    value = config.get(str(group_id))
    if value is None:
        return None
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        return None
    return value_int if value_int > 0 else None
