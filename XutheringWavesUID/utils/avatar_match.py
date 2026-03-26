"""通过opencv直方图相似度将角色头像URL匹配到角色ID"""

from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image
from gsuid_core.logger import logger

from .resource.RESOURCE_PATH import AVATAR_PATH


def _try_import_cv2():
    try:
        import cv2  # type: ignore

        return cv2
    except Exception:
        logger.warning(
            "[鸣潮] 未安装opencv-python，矩阵排行将无法解析角色ID。"
        )
        return None


def _try_import_np():
    try:
        import numpy as np  # type: ignore

        return np
    except Exception:
        return None


_cv2 = _try_import_cv2()
_np = _try_import_np()

# 匹配尺寸
_MATCH_SIZE = (64, 64)
# 相似度阈值
_MATCH_THRESHOLD = 0.3

# 缓存: char_id_str -> histogram
_ref_hist_cache: Dict[str, object] = {}


def _compute_hist(img_bgr):
    """计算HSV直方图"""
    hsv = _cv2.cvtColor(img_bgr, _cv2.COLOR_BGR2HSV)
    hist = _cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
    _cv2.normalize(hist, hist, 0, 1, _cv2.NORM_MINMAX)
    return hist


def _pil_to_cv2_bgr(pil_img: Image.Image):
    """PIL Image -> cv2 BGR array"""
    rgb = _np.array(pil_img.convert("RGB"))
    return _cv2.cvtColor(rgb, _cv2.COLOR_RGB2BGR)


def _load_reference_histograms() -> Dict[str, object]:
    """加载本地头像并计算直方图（带内存缓存）"""
    if _ref_hist_cache:
        return _ref_hist_cache

    if not AVATAR_PATH.exists():
        logger.warning(f"[鸣潮] 头像目录不存在: {AVATAR_PATH}")
        return {}

    for avatar_file in AVATAR_PATH.glob("role_head_*.png"):
        char_id_str = avatar_file.stem.replace("role_head_", "")
        try:
            img = _cv2.imread(str(avatar_file))
            if img is None:
                continue
            img = _cv2.resize(img, _MATCH_SIZE)
            hist = _compute_hist(img)
            if hist is not None:
                _ref_hist_cache[char_id_str] = hist
        except Exception as e:
            logger.debug(f"[鸣潮] 加载头像失败 {avatar_file}: {e}")

    logger.info(f"[鸣潮] 加载了 {len(_ref_hist_cache)} 个参考头像用于矩阵匹配")
    return _ref_hist_cache


def match_avatar_image(pil_img: Image.Image) -> Optional[int]:
    """将一个头像PIL Image匹配到角色ID

    Returns:
        匹配到的角色ID (int), 未匹配到返回 None
    """
    if _cv2 is None or _np is None:
        return None

    try:
        bgr = _pil_to_cv2_bgr(pil_img)
        bgr = _cv2.resize(bgr, _MATCH_SIZE)
        query_hist = _compute_hist(bgr)

        ref_hists = _load_reference_histograms()
        if not ref_hists:
            return None

        best_score = -1.0
        best_char_id = None
        for char_id_str, ref_hist in ref_hists.items():
            score = _cv2.compareHist(
                query_hist, ref_hist, _cv2.HISTCMP_CORREL
            )
            if score > best_score:
                best_score = score
                best_char_id = char_id_str

        if best_char_id and best_score >= _MATCH_THRESHOLD:
            return int(best_char_id)

        logger.debug(f"[鸣潮] 头像匹配分数过低: {best_score:.3f}")
        return None

    except Exception as e:
        logger.warning(f"[鸣潮] 头像匹配失败: {e}")
        return None


async def match_role_icons_to_char_ids(
    role_icons: List[str],
    cache_path: Path,
) -> List[int]:
    """批量将角色头像URL匹配到角色ID列表

    Args:
        role_icons: 角色头像URL列表
        cache_path: 图片下载缓存目录

    Returns:
        匹配到的角色ID列表（长度可能小于输入）
    """
    if _cv2 is None or _np is None:
        return []

    from .image import pic_download_from_url

    char_ids: List[int] = []
    for icon_url in role_icons:
        if not icon_url:
            continue
        try:
            pil_img = await pic_download_from_url(cache_path, icon_url)
            char_id = match_avatar_image(pil_img)
            if char_id is not None:
                char_ids.append(char_id)
        except Exception as e:
            logger.warning(f"[鸣潮] 下载/匹配角色头像失败: {e}")

    return char_ids
