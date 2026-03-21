from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .char_alias_ops import char_alias_list, action_char_alias
from ..utils.name_convert import load_alias_data
from ..utils.char_info_utils import PATTERN

sv_add_char_alias = SV("ww角色名别名", pm=0)
sv_list_char_alias = SV("ww角色名别名列表")


@sv_add_char_alias.on_regex(
    rf"^(?P<action>添加|删除)(?P<name>{PATTERN})别名(?P<aliases>.+)$",
    block=True,
)
async def handle_add_char_alias(bot: Bot, ev: Event):
    import re as _re
    action = ev.regex_dict.get("action")
    if action not in ["添加", "删除"]:
        return
    char_name = ev.regex_dict.get("name")
    raw = ev.regex_dict.get("aliases", "").strip()
    if not char_name or not raw:
        return await bot.send("角色名或别名不能为空")

    alias_list = [a.strip() for a in _re.split(r'[,，\s]+', raw) if a.strip()]
    if not alias_list:
        return await bot.send("别名不能为空")

    msgs = []
    need_reload = False
    for alias in alias_list:
        msg = await action_char_alias(action, char_name, alias)
        msgs.append(msg)
        if "成功" in msg:
            need_reload = True
    if need_reload:
        load_alias_data()
    await bot.send("\n".join(msgs))


@sv_list_char_alias.on_regex(rf"^(?P<name>{PATTERN})别名(列表)?$", block=True)
async def handle_list_char_alias(bot: Bot, ev: Event):
    char_name = ev.regex_dict.get("name")
    if not char_name:
        return await bot.send("角色名不能为空")
    char_name = char_name.strip()
    msg = await char_alias_list(char_name)
    await bot.send(msg)
