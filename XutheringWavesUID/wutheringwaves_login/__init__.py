import re

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .email_login import email_login_entry
from .login import code_login, page_login
from ..wutheringwaves_config import PREFIX

sv_kuro_login = SV("库洛登录")
# sv_kuro_login_help = SV("库洛登录帮助", pm=0, priority=4)
sv_email_login = SV("国际服登录")


@sv_kuro_login.on_command(("登录", "登陆", "登入", "登龙", "login", "dl"), block=True)
async def get_login_msg(bot: Bot, ev: Event):
    game_title = "[鸣潮]"

    # uid_list = await WavesBind.get_uid_list_by_game(ev.user_id, ev.bot_id)
    # if uid_list is None:
    #     return await bot.send(ERROR_CODE[WAVES_CODE_103])

    text = re.sub(r'["\n\t ]+', "", ev.text.strip())
    text = text.replace("，", ",")
    if text == "":
        return await page_login(bot, ev)

    elif "," in text:
        return await code_login(bot, ev, text)

    elif text.isdigit():
        return

    at_sender = True if ev.group_id else False
    msg = f"{game_title} 账号登录失败\n请重新输入命令【{PREFIX}登录】进行登录"
    return await bot.send(
        (" " if at_sender else "") + msg,
        at_sender=at_sender,
    )


@sv_email_login.on_fullmatch(("邮箱登录", "国际服登录"), block=True)
async def get_email_login_msg(bot: Bot, ev: Event):
    return await email_login_entry(bot, ev)
