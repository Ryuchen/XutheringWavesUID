"""init"""

import re
import shutil
from pathlib import Path

from gsuid_core.sv import Plugins
from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

Plugins(name="XutheringWavesUID", force_prefix=["ww"], allow_empty_prefix=False)

# 安装 Bot 消息发送 Hook
from .utils.bot_send_hook import install_bot_hooks
from .utils.database.waves_subscribe import WavesSubscribe

# 注册 WavesSubscribe 的 hook
async def waves_bot_check_hook(group_id: str, bot_self_id: str):
    """XutheringWavesUID 的 bot 检测 hook"""
    logger.debug(f"[XutheringWavesUID Hook] bot_check_hook 被调用: group_id={group_id}, bot_self_id={bot_self_id}")

    if group_id:
        try:
            await WavesSubscribe.check_and_update_bot(group_id, bot_self_id)
        except Exception as e:
            logger.warning(f"[XutheringWavesUID] Bot检测失败: {e}")

# 安装 hooks 并注册
install_bot_hooks()
from .utils.bot_send_hook import register_target_send_hook, register_send_hook
register_target_send_hook(waves_bot_check_hook)
register_send_hook(waves_bot_check_hook)

logger.info("[XutheringWavesUID] Bot 消息发送 hook 已注册")


# 迁移部分
MAIN_PATH = get_res_path()
PLAYERS_PATH = MAIN_PATH / "XutheringWavesUID" / "players"
cfg_path = MAIN_PATH / "config.json"
show_cfg_path = MAIN_PATH / "XutheringWavesUID" / "show_config.json"
BACKUP_PATH = MAIN_PATH / "backup"

# 此次迁移是为了删除错误的资源
if (MAIN_PATH / "XutheringWavesUID" / "resuorce" / "map" / "detail_json" / "sonata" / "15.json").exists():
    shutil.rmtree(MAIN_PATH / "XutheringWavesUID" / "resuorce" / "map" / "detail_json" / "sonata" / "15.json")
    logger.info("[XutheringWavesUID] 资源已更新，已删除错误资源 15.json")

# 此次迁移是更改JieXing为VanZi
if (MAIN_PATH / "XutheringWavesUID" / "guide_new" / "JieXing").exists():
    shutil.rmtree(MAIN_PATH / "XutheringWavesUID" / "guide_new" / "JieXing")
    logger.info("[XutheringWavesUID] 资源已更新，已删除旧资源")

# 此次迁移是删除错误的背景id
TO_DEL = MAIN_PATH / "XutheringWavesUID" / "resuorce" / "role_bg" / "1402.webp"
if TO_DEL.exists():
    TO_DEL.unlink()
    logger.info("[XutheringWavesUID] 已删除错误的背景图片 1402.webp")

# 此次迁移是直接把显示配置改为上传内容配置
BG_PATH = MAIN_PATH / "XutheringWavesUID" / "bg"
if BG_PATH.exists():
    shutil.move(str(BG_PATH), str(BG_PATH.parent / "show"))
    logger.info("[XutheringWavesUID] 已将bg重命名为show以适应新配置")

if show_cfg_path.exists():
    with open(show_cfg_path, "r", encoding="utf-8") as f:
        show_cfg_text = f.read()
    if "bg" in show_cfg_text:
        logger.info("正在更新显示配置文件中的背景路径...")
        shutil.copyfile(show_cfg_path, MAIN_PATH / "show_config_back.json")
        show_cfg_text = show_cfg_text.replace("/bg", "/show")
        with open(show_cfg_path, "w", encoding="utf-8") as f:
            f.write(show_cfg_text)
        Path(MAIN_PATH / "show_config_back.json").unlink()

# 此次迁移是因为初次实现抽卡排行时，uid字段拿错导致的下划线连接多uid
if PLAYERS_PATH.exists():
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"^\d+_\d+")
    for item in PLAYERS_PATH.iterdir():
        if item.is_dir() and pattern.match(item.name):
            try:
                backup_item = BACKUP_PATH / item.name
                if backup_item.exists():
                    shutil.rmtree(backup_item)
                shutil.move(str(item), str(backup_item))
                logger.info(f"[XutheringWavesUID] 已移动错误的players文件夹到备份: {item.name}")
            except Exception as e:
                logger.warning(f"[XutheringWavesUID] 移动players文件夹失败 {item.name}: {e}")


# 此次迁移是因为从WWUID改名为XutheringWavesUID
if "WutheringWavesUID" in str(Path(__file__)):
    logger.error("请修改插件文件夹名称为 XutheringWavesUID 以支持后续指令更新")

if not Path(MAIN_PATH / "XutheringWavesUID").exists() and Path(MAIN_PATH / "WutheringWavesUID").exists():
    logger.info("存在旧版插件资源，正在进行重命名...")
    shutil.copytree(MAIN_PATH / "WutheringWavesUID", MAIN_PATH / "XutheringWavesUID")

if Path(MAIN_PATH / "WutheringWavesUID").exists():
    logger.warning("检测到旧版资源 WutheringWavesUID，建议删除以节省空间")

with open(cfg_path, "r", encoding="utf-8") as f:
    cfg_text = f.read()
if "WutheringWavesUID" in cfg_text and "XutheringWavesUID" not in cfg_text:
    logger.info("正在更新配置文件中的插件名称...")
    shutil.copyfile(cfg_path, MAIN_PATH / "config_backup.json")
    cfg_text = cfg_text.replace("WutheringWavesUID", "XutheringWavesUID")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(cfg_text)
    Path(MAIN_PATH / "config_backup.json").unlink()
elif "WutheringWavesUID" in cfg_text and "XutheringWavesUID" in cfg_text:
    logger.warning(
        "同时存在 WutheringWavesUID 和 XutheringWavesUID 配置，可保留老的配置文件后重启，请自己编辑 gsuid_core/data/config.json 删除冗余配置（将 XutheringWavesUID 条目删除后将 WutheringWavesUID 改名为 XutheringWavesUID）"
    )

if Path(show_cfg_path).exists():
    with open(show_cfg_path, "r", encoding="utf-8") as f:
        show_cfg_text = f.read()
    if "WutheringWavesUID" in show_cfg_text:
        logger.info("正在更新显示配置文件中的插件名称...")
        shutil.copyfile(show_cfg_path, MAIN_PATH / "show_config_back.json")
        show_cfg_text = show_cfg_text.replace("WutheringWavesUID", "XutheringWavesUID")
        with open(show_cfg_path, "w", encoding="utf-8") as f:
            f.write(show_cfg_text)
        Path(MAIN_PATH / "show_config_back.json").unlink()
