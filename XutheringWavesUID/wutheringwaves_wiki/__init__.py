from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .guide import get_guide
from .draw_char import draw_char_wiki
from .draw_echo import draw_wiki_echo
from .draw_list import draw_sonata_list, draw_weapon_list
from .draw_tower import draw_slash_challenge_img, draw_tower_challenge_img
from .draw_weapon import draw_wiki_weapon
from ..utils.name_convert import char_name_to_char_id
from ..utils.char_info_utils import PATTERN
from ..wutheringwaves_abyss.period import (
    get_tower_period_number,
    get_slash_period_number,
)

sv_waves_guide = SV("鸣潮攻略")
sv_waves_tower = SV("waves查询深塔信息", priority=4)
sv_waves_slash_info = SV("waves查询海墟信息", priority=4)


@sv_waves_guide.on_regex(
    rf"^(?P<wiki_name>{PATTERN})(?P<wiki_type>共鸣链|命座|天赋|技能|图鉴|wiki|介绍|回路|操作|机制)$",
    block=True,
)
async def send_waves_wiki(bot: Bot, ev: Event):
    wiki_name = ev.regex_dict.get("wiki_name", "")
    wiki_type = ev.regex_dict.get("wiki_type", "")

    at_sender = True if ev.group_id else False
    if wiki_type in ("共鸣链", "命座", "天赋", "技能", "回路", "操作", "机制"):
        char_name = wiki_name
        char_id = char_name_to_char_id(char_name)
        if not char_id:
            msg = f"[鸣潮] wiki【{char_name}】无法找到, 可能暂未适配, 请先检查输入是否正确！\n"
            return await bot.send(msg, at_sender)

        if wiki_type in ("技能", "天赋"):
            query_role_type = "天赋"
        elif wiki_type in ("共鸣链", "命座"):
            query_role_type = "命座"
        else:
            query_role_type = wiki_type

        img = await draw_char_wiki(char_id, query_role_type)
        if isinstance(img, str):
            msg = f"[鸣潮] wiki【{wiki_name}】无法找到, 可能暂未适配, 请先检查输入是否正确！\n"
            return await bot.send(msg, at_sender)
        await bot.send(img)
    else:
        img = await draw_wiki_weapon(wiki_name)
        if isinstance(img, str) or not img:
            echo_name = wiki_name
            await bot.logger.info(f"[鸣潮] 开始获取{echo_name}wiki")
            img = await draw_wiki_echo(echo_name)

        if isinstance(img, str) or not img:
            msg = f"[鸣潮] wiki【{wiki_name}】无法找到, 可能暂未适配, 请先检查输入是否正确！\n"
            return await bot.send(msg, at_sender)

        await bot.send(img)


@sv_waves_guide.on_regex(rf"^(?P<char>{PATTERN})攻略$", block=True)
async def send_role_guide_pic(bot: Bot, ev: Event):
    char_name = ev.regex_dict.get("char", "")

    char_id = char_name_to_char_id(char_name)
    at_sender = True if ev.group_id else False
    if not char_id:
        msg = f"[鸣潮] 角色名【{char_name}】无法找到, 可能暂未适配, 请先检查输入是否正确！\n"
        return await bot.send(msg, at_sender)

    await get_guide(bot, ev, char_name)


@sv_waves_guide.on_regex(rf"^(?P<type>{PATTERN})?武器(?:列表)?$", block=True)
async def send_weapon_list(bot: Bot, ev: Event):
    weapon_type = ev.regex_dict.get("type", "")
    img = await draw_weapon_list(weapon_type)
    await bot.send(img)


@sv_waves_guide.on_regex(r".*套装(列表)?$", block=True)
async def send_sonata_list(bot: Bot, ev: Event):
    await bot.send(await draw_sonata_list())


@sv_waves_tower.on_regex(
    r"^深塔(?:(?:信息(?:第)?|第)(?P<period>\d+|下(?:一)?期|下下期|上(?:一)?期|上上期)?|(?P<period_force>\d+|下(?:一)?期|下下期|上(?:一)?期|上上期))期?$",
    block=True,
)
async def send_tower_challenge_info(bot: Bot, ev: Event):
    """查询深塔挑战信息"""
    period_val = ev.regex_dict.get("period", "") or ev.regex_dict.get("period_force", "")
    
    current_period = get_tower_period_number()
    target_period = current_period
    
    if period_val:
        if period_val.isdigit():
            target_period = int(period_val)
        elif period_val in ("下一期", "下期"):
            target_period = current_period + 1
        elif period_val == "下下期":
            target_period = current_period + 2
        elif period_val in ("上一期", "上期"):
            target_period = current_period - 1
        elif period_val == "上上期":
            target_period = current_period - 2
    # If period_val is empty, target_period remains current_period, which is the desired default.

    im = await draw_tower_challenge_img(ev, target_period)
    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    else:
        await bot.send(im)

@sv_waves_slash_info.on_regex(
    r"^(?:海墟|冥海|无尽)(?:(?:信息(?:第)?|第)(?P<period>\d+|下(?:一)?期|下下期|上(?:一)?期|上上期)?|(?P<period_force>\d+|下(?:一)?期|下下期|上(?:一)?期|上上期))期?$",
    block=True,
)
async def send_slash_challenge_info(bot: Bot, ev: Event):
    """查询海墟挑战信息"""
    period_val = ev.regex_dict.get("period", "") or ev.regex_dict.get("period_force", "")
    
    current_period = get_slash_period_number()
    target_period = current_period
    
    if period_val:
        if period_val.isdigit():
            target_period = int(period_val)
        elif period_val in ("下一期", "下期"):
            target_period = current_period + 1
        elif period_val == "下下期":
            target_period = current_period + 2
        elif period_val in ("上一期", "上期"):
            target_period = current_period - 1
        elif period_val == "上上期":
            target_period = current_period - 2

    im = await draw_slash_challenge_img(ev, target_period)
    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    else:
        await bot.send(im)
