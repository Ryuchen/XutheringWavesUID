import re
from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img

from ..utils.name_convert import alias_to_char_name_optional
from ..utils.resource.RESOURCE_PATH import GUIDE_PATH
from ..wutheringwaves_config.wutheringwaves_config import WutheringWavesConfig

guide_map = {
    "金铃子攻略组": "JinLingZi",
    "丸子": "VanZi",
    "Moealkyne": "Moealkyne",
    "小沐XMu": "XMu",
    "小羊早睡不遭罪": "XiaoYang",
    "吃我无痕": "WuHen",
    "巡游天国FM": "XFM",
}

guide_author_map = {v: k for k, v in guide_map.items()}


async def get_guide(bot: Bot, ev: Event, char_name: str):
    char_name = alias_to_char_name_optional(char_name)
    
    if not char_name:
        msg = f"[鸣潮] 未找到指定角色, 请检查输入是否正确！"
        return await bot.send(msg)
    
    logger.info(f"[鸣潮] 开始获取{char_name}图鉴")

    config = WutheringWavesConfig.get_config("WavesGuide").data

    # 获取群组排除的攻略提供方
    excluded_providers = []
    if ev.group_id:
        from ..wutheringwaves_config.guide_config import get_excluded_providers

        excluded_providers = get_excluded_providers(ev.group_id)

    imgs_result = []
    pattern = re.compile(re.escape(char_name), re.IGNORECASE)
    if "all" in config:
        for guide_path in GUIDE_PATH.iterdir():
            # 检查是否被排除
            author_name = guide_author_map.get(guide_path.name, guide_path.name)
            if author_name in excluded_providers or any(excluded in author_name for excluded in excluded_providers):
                continue

            imgs = await get_guide_pic(
                guide_path,
                pattern,
                author_name,
            )
            if len(imgs) == 0:
                continue
            imgs_result.extend(imgs)
    else:
        for guide_name in config:
            if guide_name in excluded_providers:
                continue

            if guide_name in guide_map:
                guide_path = GUIDE_PATH / guide_map[guide_name]
            else:
                guide_path = GUIDE_PATH / guide_name

            author_name = guide_author_map.get(guide_path.name, guide_path.name)
            if author_name in excluded_providers or any(excluded in author_name for excluded in excluded_providers):
                continue

            imgs = await get_guide_pic(
                guide_path,
                pattern,
                author_name,
            )
            if len(imgs) == 0:
                continue
            imgs_result.extend(imgs)

    if len(imgs_result) == 0:
        msg = f"[鸣潮]【{char_name}】暂无攻略！"
        return await bot.send(msg)

    await send_guide(config, imgs_result, bot)


async def get_guide_pic(guide_path: Path, pattern: re.Pattern, guide_author: str):
    imgs = []
    if not guide_path.is_dir():
        logger.warning(f"[鸣潮] 攻略路径错误 {guide_path}")
        return imgs

    if not guide_path.exists():
        logger.warning(f"[鸣潮] 攻略路径不存在 {guide_path}")
        return imgs

    for file in guide_path.iterdir():
        if not pattern.search(file.name):
            continue
        imgs.extend(await process_images_new(file))

    if len(imgs) > 0:
        imgs.insert(0, f"攻略作者：{guide_author}")

    return imgs


async def process_images_new(_dir: Path):
    imgs = []
    try:
        img = await convert_img(_dir)
        imgs.append(img)
    except Exception as e:
        logger.warning(f"攻略图片读取失败 {_dir}: {e}")
    return imgs


async def send_guide(config, imgs: list, bot: Bot):
    # 处理发送逻辑
    if "all" in config:
        await bot.send(imgs)
    elif len(imgs) == 2:
        await bot.send(imgs[1])
    else:
        await bot.send(imgs)
