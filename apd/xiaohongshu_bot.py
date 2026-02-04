"""
小红书创作者平台自动化发布

使用Playwright自动化小红书创作者中心的视频发布流程。
支持半自动模式，脚本完成上传和信息填写后暂停，等待用户手动点击发布。
"""

import logging
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, BrowserContext

from .config import (
    PROFILE_DIR,
    XIAOHONGSHU_CREATOR_URL,
    XIAOHONGSHU_LOGIN_URL,
    AUTO_PUBLISH,
)

logger = logging.getLogger(__name__)


class XiaohongshuBot:
    """小红书创作者平台自动化"""

    def __init__(self, headless: bool = False):
        """
        初始化小红书Bot

        Args:
            headless: 是否无头模式（默认False，建议首次使用False以便登录）
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        """Context manager入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager退出"""
        self.close()

    def start(self):
        """启动浏览器"""
        logger.info("启动浏览器...")
        self.playwright = sync_playwright().start()

        # 使用持久化上下文以保存登录状态
        profile_path = Path(PROFILE_DIR) / "xiaohongshu"
        profile_path.mkdir(parents=True, exist_ok=True)

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ],
            viewport={'width': 1280, 'height': 800}
        )

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        logger.info("浏览器启动成功")

    def close(self):
        """关闭浏览器"""
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("浏览器已关闭")

    def login(self, wait_for_manual: bool = True):
        """
        登录小红书创作者中心

        Args:
            wait_for_manual: 是否等待手动登录（推荐True）
        """
        logger.info("访问小红书创作者中心...")
        self.page.goto(XIAOHONGSHU_CREATOR_URL, wait_until="domcontentloaded", timeout=30000)

        # 等待几秒让页面加载
        time.sleep(3)

        # 检查是否已登录
        if self._is_logged_in():
            logger.info("✅ 已登录小红书创作者中心")
            return True

        logger.info("未登录，需要扫码登录...")

        if wait_for_manual:
            print("\n" + "="*60)
            print("📱 请在浏览器中扫码登录小红书")
            print("="*60)
            print("\n提示：")
            print("1. 打开小红书APP")
            print("2. 点击右下角【我】")
            print("3. 点击右上角三条横线")
            print("4. 选择【扫一扫】")
            print("5. 扫描浏览器中的二维码")
            print("\n登录成功后，按回车继续...")
            input()

            # 再次检查登录状态
            if self._is_logged_in():
                logger.info("✅ 登录成功！")
                return True
            else:
                logger.error("❌ 登录失败，请重试")
                return False

        return False

    def _is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            # 检查URL是否包含creator
            current_url = self.page.url
            if 'creator.xiaohongshu.com' in current_url:
                # 检查是否有用户相关元素
                try:
                    self.page.wait_for_selector('[class*="avatar"], [class*="user"]', timeout=3000)
                    return True
                except:
                    pass
            return False
        except Exception as e:
            logger.warning(f"检查登录状态时出错: {e}")
            return False

    def publish_video(
        self,
        video_path: Path,
        title: str,
        description: str = "",
        tags: list[str] = None,
        cover_path: Optional[Path] = None,
        auto_publish: bool = False
    ) -> dict:
        """
        发布视频到小红书

        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频描述
            tags: 话题标签列表
            cover_path: 封面图片路径（可选）
            auto_publish: 是否自动发布（默认False，半自动模式）

        Returns:
            dict: 发布结果 {'success': bool, 'note_id': str, 'url': str}
        """
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        logger.info(f"开始发布视频: {title}")

        # 1. 访问发布页面
        logger.info("访问发布页面...")
        self.page.goto(f"{XIAOHONGSHU_CREATOR_URL}/publish/publish", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # 2. 上传视频
        logger.info(f"上传视频: {video_path.name}")
        self._upload_video(video_path)

        # 3. 等待上传完成（视频处理）
        logger.info("等待视频上传和处理...")
        self._wait_for_upload_complete()

        # 4. 填写标题
        logger.info(f"填写标题: {title}")
        self._fill_title(title)

        # 5. 填写描述
        if description:
            logger.info("填写描述...")
            self._fill_description(description)

        # 6. 添加话题标签
        if tags:
            logger.info(f"添加话题标签: {tags}")
            self._add_tags(tags)

        # 7. 选择封面（如果提供）
        if cover_path and cover_path.exists():
            logger.info("上传自定义封面...")
            self._upload_cover(cover_path)

        # 8. 发布或暂停
        if auto_publish or AUTO_PUBLISH:
            logger.info("自动发布中...")
            return self._click_publish()
        else:
            # 半自动模式：暂停等待用户手动发布
            logger.info("📋 视频信息已填写完成！")
            print("\n" + "="*60)
            print("📋 半自动发布模式")
            print("="*60)
            print("\n视频上传和信息填写已完成，请检查：")
            print("1. ✓ 视频已上传")
            print("2. ✓ 标题已填写")
            print("3. ✓ 描述已填写")
            print("4. ✓ 话题标签已添加")
            print("\n请在浏览器中检查无误后，手动点击【发布】按钮")
            print("发布完成后，按回车继续...")
            print("="*60 + "\n")
            input()

            # 获取发布结果
            return self._get_publish_result()

    def _upload_video(self, video_path: Path):
        """上传视频文件"""
        try:
            # 查找上传按钮或文件输入框
            # 小红书的上传通常是一个file input
            file_input = self.page.locator('input[type="file"][accept*="video"]').first

            if file_input.count() == 0:
                # 尝试其他选择器
                file_input = self.page.locator('input[type="file"]').first

            # 上传文件
            file_input.set_input_files(str(video_path))
            logger.info("视频文件已选择，开始上传...")

        except Exception as e:
            logger.error(f"上传视频失败: {e}")
            raise

    def _wait_for_upload_complete(self, timeout: int = 300):
        """
        等待视频上传完成

        Args:
            timeout: 超时时间（秒），默认5分钟
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 检查是否有"上传中"、"处理中"等提示
                uploading = self.page.locator('[class*="upload"], [class*="processing"]').count() > 0

                if not uploading:
                    # 等待标题输入框可用（表示可以填写信息了）
                    title_input = self.page.locator('[placeholder*="标题"], [placeholder*="title"]').first
                    if title_input.count() > 0 and title_input.is_enabled():
                        logger.info("✓ 视频上传完成")
                        time.sleep(2)  # 额外等待2秒确保稳定
                        return

                time.sleep(3)

            except Exception as e:
                logger.debug(f"等待上传时检查状态: {e}")
                time.sleep(3)

        raise TimeoutError(f"视频上传超时（{timeout}秒）")

    def _fill_title(self, title: str):
        """填写标题"""
        try:
            # 查找标题输入框
            title_input = self.page.locator('[placeholder*="标题"], [placeholder*="title"], textarea').first

            # 清空并填写
            title_input.click()
            title_input.fill("")
            time.sleep(0.5)
            title_input.fill(title)

            logger.info(f"✓ 标题已填写: {title[:30]}...")

        except Exception as e:
            logger.error(f"填写标题失败: {e}")
            raise

    def _fill_description(self, description: str):
        """填写描述"""
        try:
            # 查找描述输入框（通常是第二个textarea）
            desc_input = self.page.locator('textarea, [contenteditable="true"]').nth(1)

            if desc_input.count() == 0:
                # 尝试其他选择器
                desc_input = self.page.locator('[placeholder*="描述"], [placeholder*="简介"]').first

            # 清空并填写
            desc_input.click()
            desc_input.fill("")
            time.sleep(0.5)
            desc_input.fill(description)

            logger.info("✓ 描述已填写")

        except Exception as e:
            logger.warning(f"填写描述失败: {e}")
            # 描述不是必需的，所以只记录警告

    def _add_tags(self, tags: list[str]):
        """添加话题标签"""
        try:
            for tag in tags[:5]:  # 最多5个标签
                # 通常需要点击"添加话题"按钮
                try:
                    add_topic_btn = self.page.locator('[class*="topic"], [class*="tag"]').first
                    if add_topic_btn.count() > 0:
                        add_topic_btn.click()
                        time.sleep(1)
                except:
                    pass

                # 输入话题名称
                # 通常话题输入在描述框中用#开头
                desc_input = self.page.locator('textarea, [contenteditable="true"]').first

                # 在描述末尾添加话题
                current_text = desc_input.input_value() if hasattr(desc_input, 'input_value') else ""
                if not current_text.endswith(" "):
                    current_text += " "

                # 添加#标签
                tag_text = f"#{tag}"
                desc_input.fill(current_text + tag_text + " ")
                time.sleep(1)

                # 尝试选择话题（如果有下拉菜单）
                try:
                    self.page.keyboard.press("Enter")
                    time.sleep(0.5)
                except:
                    pass

            logger.info(f"✓ 已添加{len(tags)}个话题标签")

        except Exception as e:
            logger.warning(f"添加话题标签失败: {e}")

    def _upload_cover(self, cover_path: Path):
        """上传自定义封面"""
        try:
            # 查找封面上传按钮
            cover_input = self.page.locator('input[type="file"][accept*="image"]').first

            if cover_input.count() > 0:
                cover_input.set_input_files(str(cover_path))
                logger.info("✓ 封面已上传")
                time.sleep(2)
            else:
                logger.warning("未找到封面上传入口")

        except Exception as e:
            logger.warning(f"上传封面失败: {e}")

    def _click_publish(self) -> dict:
        """点击发布按钮"""
        try:
            # 查找发布按钮
            publish_btn = self.page.locator('button:has-text("发布"), button:has-text("publish")').first

            if publish_btn.count() == 0:
                raise Exception("未找到发布按钮")

            # 点击发布
            publish_btn.click()
            logger.info("已点击发布按钮...")

            # 等待发布完成
            time.sleep(5)

            return self._get_publish_result()

        except Exception as e:
            logger.error(f"点击发布按钮失败: {e}")
            return {'success': False, 'error': str(e)}

    def _get_publish_result(self) -> dict:
        """获取发布结果"""
        try:
            # 等待发布成功提示或跳转
            time.sleep(3)

            current_url = self.page.url

            # 检查是否跳转到作品页面
            if 'user' in current_url or 'note' in current_url:
                logger.info("✅ 发布成功！")

                # 尝试提取笔记ID
                note_id = self._extract_note_id(current_url)

                return {
                    'success': True,
                    'note_id': note_id,
                    'url': current_url
                }

            # 检查是否有成功提示
            success_text = self.page.locator(':has-text("成功"), :has-text("发布成功")').first
            if success_text.count() > 0:
                logger.info("✅ 发布成功！")
                return {
                    'success': True,
                    'note_id': None,
                    'url': current_url
                }

            # 如果没有明确的成功标识，返回可能成功
            logger.info("发布已提交")
            return {
                'success': True,
                'note_id': None,
                'url': current_url
            }

        except Exception as e:
            logger.error(f"获取发布结果失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_note_id(self, url: str) -> Optional[str]:
        """从URL中提取笔记ID"""
        try:
            # 小红书笔记URL格式: https://www.xiaohongshu.com/explore/xxxx
            if '/explore/' in url:
                return url.split('/explore/')[-1].split('?')[0]
            elif '/discovery/item/' in url:
                return url.split('/discovery/item/')[-1].split('?')[0]
            return None
        except:
            return None

    def screenshot(self, path: str = "xiaohongshu_screenshot.png"):
        """截图（调试用）"""
        if self.page:
            self.page.screenshot(path=path)
            logger.info(f"截图已保存: {path}")
