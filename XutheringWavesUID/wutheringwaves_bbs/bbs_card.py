from typing import Union
from pathlib import Path

from gsuid_core.logger import logger
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import WutheringWavesConfig
from ..utils.resource.RESOURCE_PATH import waves_templates, BBS_PATH
from ..utils.render_utils import (
    PLAYWRIGHT_AVAILABLE,
    get_footer_b64,
    image_to_base64,
    get_image_b64_with_cache,
    render_html,
)


async def kuro_coin_card(cookie: str) -> Union[bytes, str]:
    """生成库洛币信息卡片"""
    try:
        logger.debug("[鸣潮] 正在获取库洛币信息...")

        res = await waves_api.get_user_mine_v2(cookie)

        if not res.success:
            error_msg = f"获取库洛币信息失败: {res.retmsg}"
            logger.warning(f"[鸣潮] {error_msg}")
            return error_msg

        data = res.model_dump()
        mine_data = data.get("data", {}).get("mine", {})

        if not mine_data:
            return "获取库洛币信息失败，请检查账号是否绑定"

        user_name = mine_data.get("userName", "未知")
        user_id = mine_data.get("userId", "")
        head_url = mine_data.get("headUrl", "")
        head_frame_url = mine_data.get("headFrameUrl", "")
        gold_num = mine_data.get("goldNum", 0)
        signature = mine_data.get("signature", "")

        use_html_render = WutheringWavesConfig.get_config("UseHtmlRender").data
        if not PLAYWRIGHT_AVAILABLE or not use_html_render:
            # 返回纯文本格式
            text = f"用户名: {user_name}\n"
            if user_id:
                text += f"库街区ID: {user_id}\n"
            text += f"库洛币余额: {gold_num}"
            return text

        # 获取 coin.png 的 base64
        coin_path = Path(__file__).parent / "texture2d" / "coin.png"
        coin_b64 = image_to_base64(coin_path) if coin_path.exists() else ""

        # 获取头像和头像框，使用缓存
        head_url_b64 = ""
        if head_url:
            head_url_b64 = await get_image_b64_with_cache(head_url, BBS_PATH, quality=None)

        head_frame_url_b64 = ""
        if head_frame_url:
            head_frame_url_b64 = await get_image_b64_with_cache(head_frame_url, BBS_PATH, quality=None)

        context = {
            "footer_b64": get_footer_b64(),
            "user_name": user_name,
            "user_id": user_id,
            "head_url": head_url_b64,
            "head_frame_url": head_frame_url_b64,
            "gold_num": gold_num,
            "signature": signature,
            "coin_b64": coin_b64,
        }

        logger.debug(f"[鸣潮] 正在渲染库洛币卡片: {user_name}, 库洛币: {gold_num}")
        img = await render_html(waves_templates, "bbs_coin.html", context)

        if img is None:
            # 渲染失败，回退到纯文本
            logger.warning("[鸣潮] 库洛币卡片渲染失败，回退到纯文本")
            text = f"用户名: {user_name}\n"
            if user_id:
                text += f"库街区ID: {user_id}\n"
            text += f"库洛币余额: {gold_num}"
            return text

        logger.info(f"[鸣潮] 库洛币卡片生成成功: {user_name}")
        return img

    except Exception as e:
        logger.exception(f"[鸣潮] 生成库洛币卡片时出错: {e}")
        return f"生成库洛币卡片失败: {str(e)}"
