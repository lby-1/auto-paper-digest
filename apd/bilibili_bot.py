"""
B站创作者平台自动化模块

功能：
- B站登录（二维码扫码）
- 视频上传
- 信息填写（标题、描述、标签）
- 半自动发布：填写完成后等待用户手动点击发布
"""

import json
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

from .config import (
    BILIBILI_AUTH_PATH,
    BILIBILI_CREATOR_URL,
    BILIBILI_LOGIN_URL,
    DEFAULT_PROFILE,
    PLAYWRIGHT_NAVIGATION_TIMEOUT,
    PLAYWRIGHT_TIMEOUT,
    PROFILE_DIR,
)
from .utils import ensure_dir, get_logger

logger = get_logger()


class BilibiliBot:
    """
    B站创作者平台自动化

    使用 Playwright 持久化上下文维护登录状态
    """

    def __init__(
        self,
        headless: bool = True,
        profile_name: str = "bilibili",
        slow_mo: int = 0
    ):
        """
        初始化 B站 Bot

        Args:
            headless: 是否无头模式（首次登录必须 False）
            profile_name: 浏览器配置文件名
            slow_mo: 操作延迟（毫秒）
        """
        self.headless = headless
        self.profile_path = ensure_dir(PROFILE_DIR / profile_name)
        self.slow_mo = slow_mo

        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "BilibiliBot":
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.stop()

    def start(self) -> None:
        """启动浏览器"""
        logger.info(f"Starting Bilibili browser (headless={self.headless})")

        self._playwright = sync_playwright().start()

        # 使用持久化上下文保存登录状态
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_path),
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # 设置默认超时
        self._context.set_default_timeout(PLAYWRIGHT_TIMEOUT)
        self._context.set_default_navigation_timeout(PLAYWRIGHT_NAVIGATION_TIMEOUT)

        # 获取第一个页面
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        logger.info("Browser started successfully")

    def stop(self) -> None:
        """关闭浏览器"""
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser stopped")

    @property
    def page(self) -> Page:
        """获取当前页面"""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    def login(self) -> bool:
        """
        登录 B站

        打开登录页面，用户扫码登录
        登录状态会自动保存到浏览器配置文件

        Returns:
            是否登录成功
        """
        logger.info("Opening Bilibili login page...")

        try:
            # 打开登录页
            self.page.goto(BILIBILI_LOGIN_URL, wait_until="networkidle")

            # 等待用户扫码登录
            logger.info("请使用 B站 APP 扫描二维码登录...")
            logger.info("等待登录完成...")

            # 等待登录成功的标志（跳转到首页或其他页面）
            # 可以通过检查 URL 变化或特定元素出现来判断
            try:
                # 等待最多 5 分钟
                self.page.wait_for_url(
                    lambda url: "passport.bilibili.com/login" not in url,
                    timeout=300000  # 5 minutes
                )
                logger.info("✅ Login successful!")

                # 保存认证信息（可选）
                self._save_auth_info()

                return True
            except PlaywrightTimeout:
                logger.error("❌ Login timeout (5 minutes)")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def is_logged_in(self) -> bool:
        """
        检查是否已登录

        Returns:
            是否已登录
        """
        try:
            # 访问创作者中心，如果未登录会跳转到登录页
            self.page.goto(BILIBILI_CREATOR_URL, wait_until="domcontentloaded")

            # 检查是否在创作者中心页面
            current_url = self.page.url
            if "member.bilibili.com" in current_url:
                logger.info("✅ Already logged in to Bilibili")
                return True
            else:
                logger.warning("⚠️ Not logged in to Bilibili")
                return False

        except Exception as e:
            logger.error(f"Failed to check login status: {e}")
            return False

    def publish_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        skip_login_check: bool = False,
        auto_publish: bool = False
    ) -> bool:
        """
        发布视频到 B站（半自动模式）

        Args:
            video_path: 视频文件路径
            title: 视频标题（B站标题限制80字符）
            description: 视频简介
            tags: 视频标签（最多12个）
            skip_login_check: 是否跳过登录检查
            auto_publish: 是否自动点击发布（默认 False，需要用户手动点击）

        Returns:
            是否完成视频信息填写
        """
        try:
            # 检查登录状态
            if not skip_login_check and not self.is_logged_in():
                logger.error("Not logged in. Please run 'apd bilibili-login' first.")
                return False

            logger.info(f"Publishing video: {video_path.name}")

            # 1. 访问上传页面
            logger.info("Navigating to upload page...")
            self.page.goto(BILIBILI_CREATOR_URL, wait_until="domcontentloaded")
            time.sleep(2)

            # 2. 上传视频文件
            logger.info("Uploading video file...")
            upload_success = self._upload_video_file(video_path)
            if not upload_success:
                logger.error("Failed to upload video file")
                return False

            # 3. 填写视频信息
            logger.info("Filling video information...")
            self._fill_video_info(title, description, tags)

            # 4. 等待用户手动发布或自动发布
            if auto_publish:
                logger.info("Auto-publishing video...")
                self._click_publish_button()
                logger.info("✅ Video published automatically")
            else:
                # 半自动模式：等待用户手动点击发布
                logger.info("=" * 60)
                logger.info("✅ 视频信息已填写完成！")
                logger.info("📌 请在浏览器中检查视频信息，确认无误后手动点击【立即投稿】按钮")
                logger.info("⏸️  脚本已暂停，浏览器保持打开状态...")
                logger.info("=" * 60)

                # 等待用户操作
                input("\n按回车键继续（发布完成后）...")
                logger.info("✅ User confirmed publish")

            return True

        except Exception as e:
            logger.error(f"Failed to publish video: {e}")
            # 截图保存错误现场
            try:
                screenshot_path = self.profile_path / "screenshots"
                screenshot_path.mkdir(exist_ok=True)
                self.page.screenshot(
                    path=str(screenshot_path / f"error_{int(time.time())}.png")
                )
            except:
                pass
            return False

    def _upload_video_file(self, video_path: Path) -> bool:
        """
        上传视频文件

        Args:
            video_path: 视频文件路径

        Returns:
            是否上传成功
        """
        try:
            # 查找文件上传输入框
            # B站的上传通常使用 input[type="file"]
            file_input = self.page.locator('input[type="file"]').first

            if not file_input:
                logger.error("Cannot find file upload input")
                return False

            # 设置文件
            file_input.set_input_files(str(video_path))
            logger.info(f"Video file set: {video_path.name}")

            # 等待上传完成
            # 检查上传进度或等待特定元素出现
            logger.info("Waiting for upload to complete...")

            # 等待上传完成的标志（例如：封面选择区域出现）
            # 这里需要根据B站实际页面结构调整选择器
            try:
                self.page.wait_for_selector(
                    'text=选择封面',  # 或其他上传完成后出现的元素
                    timeout=300000  # 5分钟超时
                )
                logger.info("✅ Video upload completed")
                return True
            except PlaywrightTimeout:
                logger.warning("Upload timeout, but may still be processing...")
                return True  # 即使超时也继续，因为上传可能在后台继续

        except Exception as e:
            logger.error(f"Failed to upload video file: {e}")
            return False

    def _fill_video_info(
        self,
        title: str,
        description: str,
        tags: list[str]
    ) -> None:
        """
        填写视频信息

        Args:
            title: 视频标题
            description: 视频简介
            tags: 视频标签
        """
        try:
            # 填写标题（B站标题限制80字符）
            title = title[:80]
            logger.info(f"Filling title: {title}")

            title_input = self.page.locator('input[placeholder*="标题"]').first
            if title_input:
                title_input.fill(title)
                time.sleep(0.5)

            # 填写简介
            logger.info("Filling description...")
            desc_textarea = self.page.locator('textarea[placeholder*="简介"]').first
            if desc_textarea:
                desc_textarea.fill(description[:2000])  # B站简介限制2000字
                time.sleep(0.5)

            # 添加标签
            logger.info(f"Adding {len(tags)} tags...")
            for tag in tags[:12]:  # B站最多12个标签
                try:
                    tag_input = self.page.locator('input[placeholder*="标签"]').first
                    if tag_input:
                        tag_input.fill(tag)
                        time.sleep(0.3)
                        # 按回车确认标签
                        tag_input.press("Enter")
                        time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"Failed to add tag '{tag}': {e}")

            logger.info("✅ Video information filled")

        except Exception as e:
            logger.error(f"Failed to fill video info: {e}")

    def _click_publish_button(self) -> None:
        """点击发布按钮"""
        try:
            # 查找并点击发布按钮
            # B站的发布按钮通常是"立即投稿"
            publish_button = self.page.locator('text=立即投稿').first

            if publish_button:
                publish_button.click()
                logger.info("Clicked publish button")
                time.sleep(2)
            else:
                logger.warning("Cannot find publish button")

        except Exception as e:
            logger.error(f"Failed to click publish button: {e}")

    def _save_auth_info(self) -> None:
        """保存认证信息到文件（可选）"""
        try:
            # 获取 cookies
            cookies = self._context.cookies()

            auth_data = {
                "cookies": cookies,
                "timestamp": time.time()
            }

            BILIBILI_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BILIBILI_AUTH_PATH, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f, indent=2)

            logger.info(f"Auth info saved to {BILIBILI_AUTH_PATH}")

        except Exception as e:
            logger.warning(f"Failed to save auth info: {e}")
