import base64
import asyncio
import time
import re
from typing import Union, Optional
from pathlib import Path

from gsuid_core.logger import logger
from gsuid_core.config import core_config, CONFIG_DEFAULT
from gsuid_core.app_life import app as fastapi_app
from fastapi.staticfiles import StaticFiles
from .resource.RESOURCE_PATH import TEMP_PATH

TEMPLATES_ABS_PATH = Path(__file__).parent.parent / "templates"

class CORSStaticFiles(StaticFiles):
    """Custom StaticFiles class to add CORS headers only for served files."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD"
        return response

def _import_playwright():
    try:
        from playwright.async_api import async_playwright
        return async_playwright
    except ImportError:
        logger.warning("[鸣潮] 未安装 playwright，无法使用渲染公告、wiki图等功能。")
        logger.info("[鸣潮] 安装方法 Linux/Mac: 在当前目录下执行 source .venv/bin/activate && uv pip install playwright && uv run playwright install chromium")
        logger.info("[鸣潮] 安装方法 Windows: 在当前目录下执行 .venv\\Scripts\\activate; uv pip install playwright; uv run playwright install chromium")
        return None


async_playwright = _import_playwright()
PLAYWRIGHT_AVAILABLE = async_playwright is not None

_playwright = None
_browser = None
_browser_lock = asyncio.Lock()
_browser_uses = 0
_last_used = 0.0
_active_contexts = 0

_MAX_BROWSER_USES = 1000
_BROWSER_IDLE_TTL = 3600

_FONT_CSS_NAME = "fonts.css"
_FONTS_DIR = TEMP_PATH / "fonts"


def _mount_fonts() -> None:
    try:
        for route in fastapi_app.routes:
            if getattr(route, "path", None) == "/waves/fonts":
                return
        if _FONTS_DIR.exists():
            fastapi_app.mount(
                "/waves/fonts",
                CORSStaticFiles(directory=_FONTS_DIR),
                name="wwuid_fonts",
            )
        logger.debug("[鸣潮] 已挂载字体静态路由 (CORS Enabled)")
    except Exception as e:
        logger.warning(f"[鸣潮] 挂载字体静态路由失败: {e}")


def _get_local_base_url() -> str:
    host = core_config.get_config("HOST") or CONFIG_DEFAULT["HOST"]
    port = core_config.get_config("PORT") or CONFIG_DEFAULT["PORT"]
    if host in ("0.0.0.0", "0.0.0.0:"):
        host = "127.0.0.1"
    return f"http://{host}:{port}"


_mount_fonts()


async def _ensure_browser():
    """Get a reusable browser instance; restart periodically to bound memory."""
    global _playwright, _browser, _browser_uses, _last_used, _active_contexts

    if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
        return None

    async with _browser_lock:
        now = time.monotonic()

        if _browser is not None and not _browser.is_connected():
            try:
                await _browser.close()
            except Exception:
                pass
            _browser = None

        need_restart = (
            _browser is None
            or _browser_uses >= _MAX_BROWSER_USES
            or (_last_used > 0 and now - _last_used > _BROWSER_IDLE_TTL)
        )

        if need_restart and _browser is not None and _active_contexts > 0:
            need_restart = False

        if need_restart:
            if _browser is not None:
                try:
                    await _browser.close()
                except Exception:
                    pass
                _browser = None

            if _playwright is None:
                _playwright = await async_playwright().start()

            _browser = await _playwright.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            _browser_uses = 0

        _last_used = now
        return _browser


async def render_html(waves_templates, template_name: str, context: dict) -> Optional[bytes]:
    global _browser_uses, _last_used, _active_contexts

    if not PLAYWRIGHT_AVAILABLE or async_playwright is None:
        logger.warning("[鸣潮] Playwright 未安装，无法渲染，将回退到 PIL 渲染（如有）")
        return None

    try:
        logger.debug(f"[鸣潮] HTML渲染开始: {template_name}")
        logger.debug(f"[鸣潮] async_playwright type: {type(async_playwright)}")

        try:
            template = waves_templates.get_template(template_name)
            font_css_path = _FONTS_DIR / _FONT_CSS_NAME
            
            base_url = _get_local_base_url()
            
            if font_css_path.exists():
                context.setdefault(
                    "font_css_url",
                    f"{base_url}/waves/fonts/{_FONT_CSS_NAME}",
                )
            html_content = template.render(**context)
            logger.debug(f"[鸣潮] HTML渲染完成: {template_name}")
        except Exception as e:
            logger.error(f"[鸣潮] Template render failed: {e}")
            raise e

        font_css_path = _FONTS_DIR / _FONT_CSS_NAME
        if not font_css_path.exists():
            logger.warning("[鸣潮] fonts.css 不存在，继续使用原始字体链接。")

        try:
            logger.debug("[鸣潮] 获取复用浏览器实例...")
            browser = await _ensure_browser()
            if browser is None:
                return None

            context_obj = await browser.new_context(viewport={"width": 1200, "height": 1000})
            _active_contexts += 1
            try:
                page = await context_obj.new_page()
                logger.debug("[鸣潮] 加载HTML内容...")
                await page.set_content(html_content)

                try:
                    logger.debug("[鸣潮] 等待网络空闲...")
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception as e:
                    logger.debug(f"[鸣潮] 等待网络空闲超时 (可能部分资源加载缓慢): {e}")

                logger.debug("[鸣潮] 正在计算容器尺寸...")
                container = page.locator(".container")
                await page.wait_for_selector(".container", timeout=2000)
                size = await container.evaluate(
                    """(el) => {
                        const rect = el.getBoundingClientRect();
                        const width = Math.ceil(Math.max(rect.width, el.scrollWidth));
                        const height = Math.ceil(Math.max(rect.height, el.scrollHeight));
                        return { width, height };
                    }"""
                )

                if size and size.get("width") and size.get("height"):
                    await page.set_viewport_size(
                        {
                            "width": max(1, int(size["width"])),
                            "height": max(1, int(size["height"])),
                        }
                    )
                    await page.wait_for_timeout(50)

                logger.debug("[鸣潮] 正在截图...")
                screenshot = await container.screenshot(type='jpeg', quality=90)
                logger.debug(f"[鸣潮] HTML渲染成功, 图片大小: {len(screenshot)} bytes")
                return screenshot
            finally:
                try:
                    await context_obj.close()
                except Exception:
                    pass
                _active_contexts = max(0, _active_contexts - 1)
                _browser_uses += 1
                _last_used = time.monotonic()
        except Exception as e:
            logger.error(f"[鸣潮] Playwright execution failed: {e}")
            raise e

    except Exception as e:
        logger.error(f"[鸣潮] HTML渲染失败: {e}")
        return None


def image_to_base64(image_path: Union[str, Path]) -> str:
    if not isinstance(image_path, Path):
        image_path = Path(image_path)
    if not image_path.exists():
        return ""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        ext = image_path.suffix.lstrip(".").lower()
        if ext == "jpg":
            ext = "jpeg"
        return f"data:image/{ext};base64,{base64.b64encode(data).decode('utf-8')}"
    except Exception as e:
        logger.warning(f"[渲染工具] 图片转 base64 失败: {image_path}, {e}")
        return ""


def get_logo_b64() -> Optional[str]:
    try:
        logo_path = TEMP_PATH / "imgs" / "kurobbs.png"

        if not logo_path.exists():
            return None

        with open(logo_path, "rb") as f:
            data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"
    except Exception as e:
        logger.warning(f"[渲染工具] Logo loading failed: {e}")
        return None


def get_footer_b64(footer_type: str = "black") -> Optional[str]:
    try:
        from pathlib import Path

        current_file_path = Path(__file__).resolve()
        footer_path = current_file_path.parent / "texture2d" / f"footer_{footer_type}.png"

        if not footer_path.exists():
            if footer_type == "black":
                footer_path = current_file_path.parent / "texture2d" / "footer_white.png"
            else:
                footer_path = current_file_path.parent / "texture2d" / "footer_black.png"

        if not footer_path.exists():
            return None

        with open(footer_path, "rb") as f:
            data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"
    except Exception as e:
        logger.warning(f"[渲染工具] Footer loading failed: {e}")
        return None


async def get_image_b64_with_cache(url: str, cache_path: Path) -> str:
    if not url:
        return ""

    try:
        from .image import pic_download_from_url

        await pic_download_from_url(cache_path, url)

        filename = url.split("/")[-1]
        local_path = cache_path / filename

        return image_to_base64(local_path)
    except Exception as e:
        logger.warning(f"[渲染工具] 获取图片 base64 失败: {url}, {e}")
        return ""