import os
import time
import random
import asyncio
from pathlib import Path

from gsuid_core.sv import SV
from gsuid_core.aps import scheduler
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.subscribe import gs_subscribe

from .ann_card_render import ann_list_card, ann_detail_card
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import WutheringWavesConfig
from ..utils.resource.RESOURCE_PATH import ANN_CARD_PATH, CALENDAR_PATH

sv_ann = SV("鸣潮公告")
sv_ann_sub = SV("订阅鸣潮公告", pm=3)

task_name_ann = "订阅鸣潮公告"
ann_minute_check: int = WutheringWavesConfig.get_config("AnnMinuteCheck").data


@sv_ann.on_command("公告")
async def ann_(bot: Bot, ev: Event):
    ann_id = ev.text
    if not ann_id:
        img = await ann_list_card()
        return await bot.send(img)

    ann_id = ann_id.replace("#", "")
    if not ann_id.isdigit():
        raise Exception("公告ID不正确")

    img = await ann_detail_card(int(ann_id))
    return await bot.send(img)  # type: ignore


@sv_ann_sub.on_fullmatch("订阅公告")
async def sub_ann_(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.debug(f"非onebot禁止订阅鸣潮公告 【{ev.bot_id}】")
        return

    if ev.group_id is None:
        return await bot.send("请在群聊中订阅")
    if not WutheringWavesConfig.get_config("WavesAnnOpen").data:
        return await bot.send("鸣潮公告推送功能已关闭")

    # 检查是否已订阅
    data = await gs_subscribe.get_subscribe(task_name_ann)
    is_resubscribe = False
    if data:
        for subscribe in data:
            if subscribe.group_id == ev.group_id:
                # 删除旧订阅
                await gs_subscribe.delete_subscribe("session", task_name_ann, ev)
                is_resubscribe = True
                logger.info(f"[鸣潮公告] 群 {ev.group_id} 重新订阅，已删除旧订阅")
                break

    # 添加新订阅
    await gs_subscribe.add_subscribe(
        "session",
        task_name=task_name_ann,
        event=ev,
        extra_message="",
    )

    if is_resubscribe:
        await bot.send("已重新订阅鸣潮公告！")
    else:
        await bot.send("成功订阅鸣潮公告!")


@sv_ann_sub.on_fullmatch(("取消订阅公告", "取消公告", "退订公告"))
async def unsub_ann_(bot: Bot, ev: Event):
    if ev.bot_id != "onebot":
        logger.debug(f"非onebot禁止订阅鸣潮公告 【{ev.bot_id}】")
        return

    if ev.group_id is None:
        return await bot.send("请在群聊中取消订阅")

    data = await gs_subscribe.get_subscribe(task_name_ann)
    if data:
        for subscribe in data:
            if subscribe.group_id == ev.group_id:
                await gs_subscribe.delete_subscribe("session", task_name_ann, ev)
                return await bot.send("成功取消订阅鸣潮公告!")
    else:
        if not WutheringWavesConfig.get_config("WavesAnnOpen").data:
            return await bot.send("鸣潮公告推送功能已关闭")

    return await bot.send("未曾订阅鸣潮公告！")


@scheduler.scheduled_job("interval", minutes=ann_minute_check)
async def check_waves_ann():
    if not WutheringWavesConfig.get_config("WavesAnnOpen").data:
        return
    await check_waves_ann_state()


async def check_waves_ann_state():
    logger.info("[鸣潮公告] 定时任务: 鸣潮公告查询..")
    datas = await gs_subscribe.get_subscribe(task_name_ann)
    if not datas:
        logger.info("[鸣潮公告] 暂无群订阅")
        return

    ids = WutheringWavesConfig.get_config("WavesAnnNewIds").data
    new_ann_list = await waves_api.get_ann_list()
    if not new_ann_list:
        return

    new_ann_ids = [x["id"] for x in new_ann_list]
    if not ids:
        WutheringWavesConfig.set_config("WavesAnnNewIds", new_ann_ids)
        logger.info("[鸣潮公告] 初始成功, 将在下个轮询中更新.")
        return

    new_ann_need_send = []
    for ann_id in new_ann_ids:
        if ann_id not in ids:
            new_ann_need_send.append(ann_id)

    if not new_ann_need_send:
        logger.info("[鸣潮公告] 没有最新公告")
        return

    logger.info(f"[鸣潮公告] 更新公告id: {new_ann_need_send}")
    # 这里先不删了，就是存
    save_ids = sorted(ids, reverse=True) + new_ann_ids
    WutheringWavesConfig.set_config("WavesAnnNewIds", list(set(save_ids)))

    for ann_id in new_ann_need_send:
        try:
            img = await ann_detail_card(ann_id, is_check_time=True)
            if isinstance(img, str):
                continue
            for subscribe in datas:
                await subscribe.send(img)  # type: ignore
                await asyncio.sleep(random.uniform(1, 3))
        except Exception as e:
            logger.exception(e)

    logger.info("[鸣潮公告] 推送完毕")


def clean_old_cache_files(directory: Path, days: int) -> tuple[int, float]:
    """
    清理指定目录下创建时间早于指定天数的文件

    Args:
        directory: 要清理的目录路径
        days: 保留天数，早于此天数的文件将被删除

    Returns:
        tuple[int, float]: (删除的文件数量, 释放的空间大小(MB))
    """
    if not directory.exists():
        logger.debug(f"目录不存在: {directory}")
        return 0, 0.0

    current_time = time.time()
    cutoff_time = current_time - (days * 86400)  # 转换为秒

    deleted_count = 0
    freed_space = 0.0

    try:
        for file_path in directory.iterdir():
            if not file_path.is_file():
                continue

            # 获取文件的创建时间（在某些系统上是修改时间）
            file_ctime = file_path.stat().st_ctime

            if file_ctime < cutoff_time:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    freed_space += file_size
                    logger.debug(f"删除过期缓存文件: {file_path.name}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path.name}: {e}")
    except Exception as e:
        logger.error(f"清理目录失败 {directory}: {e}")

    freed_space_mb = freed_space / (1024 * 1024)  # 转换为MB
    return deleted_count, freed_space_mb


async def clean_cache_directories(days: int) -> str:
    """
    清理公告和日历缓存目录

    Args:
        days: 保留天数

    Returns:
        str: 清理结果消息
    """
    results = []
    total_count = 0
    total_space = 0.0

    # 清理公告缓存
    ann_count, ann_space = clean_old_cache_files(ANN_CARD_PATH, days)
    if ann_count > 0:
        results.append(f"公告: {ann_count}个文件, {ann_space:.2f}MB")
        total_count += ann_count
        total_space += ann_space

    # 清理日历缓存
    cal_count, cal_space = clean_old_cache_files(CALENDAR_PATH, days)
    if cal_count > 0:
        results.append(f"日历: {cal_count}个文件, {cal_space:.2f}MB")
        total_count += cal_count
        total_space += cal_space

    if total_count == 0:
        return f"没有找到需要清理的过期缓存文件(保留{days}天内的文件)"

    result_msg = f"[鸣潮] 清理完成！共删除{total_count}个文件，{total_space:.2f}MB\n"
    result_msg += "\n".join(f" - {r}" for r in results)
    return result_msg


@sv_ann.on_fullmatch(("删除公告缓存", "删除日历缓存", "清理缓存", "删除缓存"))
async def clean_cache_(bot: Bot, ev: Event):
    """手动清理缓存指令"""
    days = WutheringWavesConfig.get_config("CacheDaysToKeep").data
    logger.info(f"[缓存清理] 手动触发清理，保留{days}天内的文件")

    result = await clean_cache_directories(days)
    await bot.send(result)


@scheduler.scheduled_job("cron", hour=3, minute=0)
async def auto_clean_cache_daily():
    """每天凌晨3点自动清理缓存"""
    days = WutheringWavesConfig.get_config("CacheDaysToKeep").data
    logger.info(f"[缓存清理] 定时任务: 开始清理缓存，保留{days}天内的文件")

    result = await clean_cache_directories(days)
    logger.info(f"[缓存清理] {result}")


# 启动时执行一次清理
@scheduler.scheduled_job("date")
async def clean_cache_on_startup():
    """启动时清理一次缓存"""
    # 延迟5秒执行，确保配置已加载
    await asyncio.sleep(5)

    days = WutheringWavesConfig.get_config("CacheDaysToKeep").data
    logger.info(f"[缓存清理] 启动时清理，保留{days}天内的文件")

    result = await clean_cache_directories(days)
    logger.info(f"[缓存清理] {result}")
