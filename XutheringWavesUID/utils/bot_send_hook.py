from typing import Callable, Optional
from gsuid_core.bot import Bot
from gsuid_core.logger import logger


_send_hooks: list[Callable] = []
_target_send_hooks: list[Callable] = []
_original_target_send = None  # 保存原始方法


def register_send_hook(func: Callable):
    """注册 send 方法 hook"""
    if func not in _send_hooks:
        _send_hooks.append(func)
        logger.info(f"[BotHook] 注册 send hook: {func.__name__}")


def register_target_send_hook(func: Callable):
    """注册 target_send 方法 hook"""
    if func not in _target_send_hooks:
        _target_send_hooks.append(func)
        logger.info(f"[BotHook] 注册 target_send hook: {func.__name__}")


async def _call_send_hooks(bot: Bot, group_id: Optional[str], bot_id: str):
    """调用所有注册的 send hooks"""
    for hook in _send_hooks:
        try:
            await hook(group_id, bot_id)
        except Exception as e:
            logger.warning(f"[BotHook] send hook {hook.__name__} 执行失败: {e}")


async def _call_target_send_hooks(
    bot: Bot,
    target_type: str,
    target_id: Optional[str],
    bot_id: str,
    bot_self_id: str,
):
    """调用所有注册的 target_send hooks"""
    group_id = target_id if target_type == "group" else None

    logger.debug(f"[BotHook] 调用 {_target_send_hooks.__len__()} 个 target_send hooks, target_type={target_type}, group_id={group_id}, bot_self_id={bot_self_id}")

    for hook in _target_send_hooks:
        try:
            logger.debug(f"[BotHook] 执行 hook: {hook.__name__}, group_id={group_id}, bot_self_id={bot_self_id}")
            await hook(group_id, bot_self_id)
        except Exception as e:
            logger.warning(f"[BotHook] target_send hook {hook.__name__} 执行失败: {e}")


def install_bot_hooks():
    """安装 Bot 类的 hooks

    通过 Monkey Patch 的方式拦截 Bot.send 和 Bot.target_send 方法

    注意：此函数可以安全地多次调用，不会重复安装
    """
    global _original_target_send

    if hasattr(Bot, "_gs_hooked"):
        logger.debug("[BotHook] Bot hooks 已经安装，跳过")
        return  # 已经安装过了

    # 保存原始方法
    original_send = Bot.send
    original_target_send = Bot.target_send

    # 包装 send 方法
    async def hooked_send(self, *args, **kwargs):
        # 调用 hooks
        group_id = getattr(self.ev, "group_id", None) if hasattr(self, "ev") else None
        bot_self_id = getattr(self, "bot_self_id", "") if hasattr(self, "bot_self_id") else ""

        logger.debug(f"[BotHook] send 被调用: bot_self_id={bot_self_id}, group_id={group_id}")

        if group_id:
            await _call_send_hooks(self, group_id, bot_self_id)

        # 调用原始方法
        return await original_send(self, *args, **kwargs)

    # 包装 target_send 方法
    async def hooked_target_send(self, *args, **kwargs):
        if len(args) >= 5:
            target_type = args[1]
            target_id = args[2]
            bot_id = args[3]
            bot_self_id = args[4]

            logger.debug(f"[BotHook] target_send 被调用: target_type={target_type}, target_id={target_id}, bot_id={bot_id}, bot_self_id={bot_self_id}")

            if target_type == "group":
                await _call_target_send_hooks(self, target_type, target_id, bot_id, bot_self_id)

        # 调用原始方法
        return await original_target_send(self, *args, **kwargs)

    # 替换方法
    Bot.send = hooked_send
    Bot.target_send = hooked_target_send
    Bot._gs_hooked = True

    logger.info("[BotHook] Bot hooks 已安装")

