"""
Douyin Automation Bot for paper overview publishing.
"""

import json
import platform
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from .config import DATA_DIR
from .utils import get_logger

logger = get_logger()

# Path to save/load Douyin authentication session
DOUYIN_AUTH_PATH = DATA_DIR / ".douyin_auth.json"
CREATOR_HOME_URL = "https://creator.douyin.com/"
UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"


class DouyinBot:
    """
    Handles automation for Douyin Creator Studio.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        """Start the browser and context."""
        self.playwright = sync_playwright().start()
        
        # Grant geolocation permission to avoid the popup
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        
        # Load session if exists
        if DOUYIN_AUTH_PATH.exists():
            logger.info(f"Loading Douyin session from {DOUYIN_AUTH_PATH}")
            self.context = self.browser.new_context(
                storage_state=str(DOUYIN_AUTH_PATH),
                permissions=["geolocation"],  # Auto-grant location permission
            )
        else:
            logger.info("No Douyin session found, starting fresh")
            self.context = self.browser.new_context(
                permissions=["geolocation"],
            )
            
        self.page = self.context.new_page()

    def stop(self):
        """Stop the browser."""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def dismiss_popups(self):
        """
        Dismiss common popups that appear on Douyin Creator Studio.
        These include location permission, video preview info, co-creation center, etc.
        """
        popup_buttons = [
            '我知道了',  # Common "Got it" button - also for video preview feature popover
            '一律不允许',  # "Never allow" for location
            '仅这次访问时允许',  # "Allow this time"
            '关闭',  # "Close"
            '取消',  # "Cancel"
            '跳过',  # "Skip"
            '知道了',  # Another "Got it"
            '暂不开启',  # "Not now"
            '稍后再说',  # "Later"
        ]
        
        # Try multiple times to catch all popups
        for _ in range(3):
            for btn_text in popup_buttons:
                try:
                    btns = self.page.locator(f'text="{btn_text}"')
                    count = btns.count()
                    for i in range(count):
                        btn = btns.nth(i)
                        if btn.is_visible(timeout=200):
                            logger.info(f"Dismissing popup: clicking '{btn_text}'")
                            btn.click()
                            self.page.wait_for_timeout(300)
                except:
                    pass
            
            # Try to click semi-button primary buttons (common in popovers)
            try:
                semi_btns = self.page.locator('button.semi-button.semi-button-primary')
                count = semi_btns.count()
                for i in range(count):
                    btn = semi_btns.nth(i)
                    if btn.is_visible(timeout=200):
                        btn_text = btn.text_content()
                        if btn_text and ('知道' in btn_text or '确定' in btn_text or '好的' in btn_text):
                            logger.info(f"Dismissing semi-button popup: '{btn_text}'")
                            btn.click()
                            self.page.wait_for_timeout(300)
            except:
                pass
            
            # Also try to close any modal dialogs by pressing Escape
            try:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(200)
            except:
                pass

    def login(self):
        """
        Opens the Douyin Creator Studio for manual login and saves the session.
        This must be run in headful mode.
        """
        if self.headless:
            raise ValueError("Douyin login requires headful mode. Please run with --headful.")
            
        logger.info(f"Navigating to {CREATOR_HOME_URL} for manual login...")
        self.page.goto(CREATOR_HOME_URL)
        
        logger.info("Please complete the login manually in the browser...")
        
        # Wait for user to login - look for "发布视频" or similar text that indicates success
        try:
            # wait for specific element that appears after login
            self.page.wait_for_selector('text="发布视频"', timeout=300000) # 5 minutes timeout
            logger.info("Login detected!")
            
            # Dismiss any popups that might appear after login
            self.dismiss_popups()
            
            # Save session
            DOUYIN_AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=str(DOUYIN_AUTH_PATH))
            logger.info(f"Session saved to {DOUYIN_AUTH_PATH}")
            return True
        except Exception as e:
            logger.error(f"Login timeout or error: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check if we are logged into Douyin."""
        self.page.goto(CREATOR_HOME_URL)
        self.dismiss_popups()  # Dismiss any popups first
        try:
            # Check for "发布视频" or a profile element
            self.page.wait_for_selector('text="发布视频"', timeout=10000)
            return True
        except:
            return False

    def publish_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] = None,
        skip_login_check: bool = False,
        auto_publish: bool = False
    ):
        """
        Publishes a video to Douyin (semi-automatic mode by default).

        Args:
            video_path: Path to the video file
            title: Video title (max 30 chars for Douyin)
            description: Video description
            tags: List of hashtags
            skip_login_check: Skip login verification (useful for batch publishing)
            auto_publish: Auto-click publish button (default False, requires manual click)

        Returns:
            True if video info filled successfully, False otherwise
        """
        if not skip_login_check and not self.is_logged_in():
            logger.error("Not logged into Douyin. Run 'apd douyin-login' first.")
            return False
            
        logger.info(f"Navigating to upload page: {UPLOAD_URL}")
        self.page.goto(UPLOAD_URL)
        
        # Wait for page to load and dismiss any popups
        self.page.wait_for_timeout(2000)
        self.dismiss_popups()
        
        # 1. Upload video
        # Douyin uses a hidden input[type=file]
        logger.info(f"Uploading video: {video_path}")
        try:
            self.page.wait_for_selector('input[type="file"]', timeout=10000)
            self.page.set_input_files('input[type="file"]', str(video_path))
        except Exception as e:
            logger.error(f"Could not find file input: {e}")
            return False
        
        # 2. Wait for upload to complete - this redirects to the edit page
        logger.info("Waiting for upload to process...")
        
        # Keep dismissing popups while waiting
        for _ in range(30):  # Wait up to 30 seconds
            self.dismiss_popups()
            self.page.wait_for_timeout(1000)
            
            # Check if we're on the post page now (URL contains "post")
            if "post" in self.page.url:
                logger.info("Detected redirect to post page.")
                break
                
            # Check if title field is visible
            try:
                if self.page.locator('text="填写作品标题"').is_visible():
                    logger.info("Title field found.")
                    break
            except:
                pass
        
        # Final popup dismissal
        self.page.wait_for_timeout(1000)
        self.dismiss_popups()
        
        # 3. Fill title (the smaller input at the top with 0/30 counter)
        logger.info(f"Filling title: {title}")
        title_filled = False
        try:
            # The title input is an input element with class semi-input
            # Try multiple selectors to find the title input (prioritize the correct one)
            title_selectors = [
                'input.semi-input[placeholder*="填写作品标题"]',  # Primary selector - the actual input
                'input[placeholder*="填写作品标题"]',
                'input.semi-input.semi-input-default',
                'div[data-placeholder="填写作品标题，为作品获得更多流量"]',
                'div.zone-container input',
                'div.title-input', 
                'div[class*="title"] div[contenteditable="true"]',
                'div.notranslate[contenteditable="true"]',
            ]
            
            for selector in title_selectors:
                try:
                    title_input = self.page.locator(selector).first
                    if title_input.is_visible(timeout=1000):
                        logger.info(f"Found title input with selector: {selector}")
                        title_input.click()
                        self.page.wait_for_timeout(300)
                        # Clear any existing content first (use Meta+a for macOS, Control+a for others)
                        select_all_key = "Meta+a" if platform.system() == "Darwin" else "Control+a"
                        self.page.keyboard.press(select_all_key)
                        self.page.wait_for_timeout(100)
                        # For input elements, we can use fill() which is more reliable
                        if selector.startswith('input'):
                            title_input.fill(title)
                        else:
                            self.page.keyboard.type(title)
                        title_filled = True
                        logger.info(f"Title filled successfully: {title}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not title_filled:
                # Try clicking directly on the placeholder text
                logger.info("Trying to click on placeholder text for title...")
                placeholder = self.page.locator('text="填写作品标题，为作品获得更多流量"').first
                if placeholder.is_visible(timeout=2000):
                    placeholder.click()
                    self.page.wait_for_timeout(300)
                    self.page.keyboard.type(title)
                    title_filled = True
                    logger.info(f"Title filled via placeholder click: {title}")
        except Exception as e:
            logger.error(f"Failed to fill title: {e}")
        
        if not title_filled:
            logger.warning("Could not fill title field - continuing anyway")
        
        # 4. Dismiss popups again before filling description
        self.dismiss_popups()
        
        # 5. Fill description in the main text area (the area with #添加话题 @好友)
        # Douyin's description is entered in the same area as tags, before the hashtags
        logger.info("Filling description...")
        if description:
            try:
                # Click on the description/tag area first
                desc_area = self.page.locator('text="#添加话题"').first
                if desc_area.is_visible(timeout=3000):
                    desc_area.click()
                    self.page.wait_for_timeout(300)
                    
                    # Type the description (limit to reasonable length for Douyin)
                    truncated_desc = description[:800] if len(description) > 800 else description
                    self.page.keyboard.type(truncated_desc)
                    self.page.wait_for_timeout(300)
                    
                    # Add a newline before tags
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_timeout(200)
                    
                    logger.info(f"Description filled ({len(truncated_desc)} chars)")
                else:
                    logger.warning("Description area not found")
            except Exception as e:
                logger.warning(f"Could not fill description: {e}")
        
        # 6. Fill hashtags/tags
        logger.info("Filling tags...")
        if tags:
            try:
                # Tags are added after description in the same area
                for tag in tags:
                    self.page.keyboard.type(f"#{tag} ")
                    self.page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(f"Could not fill tags: {e}")

        # 5. Wait for video processing (indicated by cover generation)
        logger.info("Waiting for video covers to generate...")
        self.page.wait_for_timeout(5000)
        
        # Check if video is still transcoding
        try:
            transcoding = self.page.locator('text="预览转码中"')
            if transcoding.is_visible():
                logger.info("Video is still transcoding, waiting...")
                # Wait up to 60 seconds for transcoding
                for _ in range(12):
                    self.page.wait_for_timeout(5000)
                    if not transcoding.is_visible():
                        break
        except:
            pass
        
        # 6. Click Publish or wait for manual publish
        if auto_publish:
            logger.info("Auto-publish mode: Clicking Publish button...")
            publish_clicked = False

            # Scroll down to make sure publish button is visible
            logger.info("Scrolling down to find publish button...")
            try:
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self.page.wait_for_timeout(500)
            except:
                pass

            # Dismiss any popups that might have appeared
            self.dismiss_popups()

            try:
                # Try multiple selectors for the publish button (prioritize more specific ones)
                publish_selectors = [
                    'button[class*="primary-"]:has-text("发布")',  # Primary styled button
                    'button.button-dhlUZE.primary-cECiOJ',  # Specific class from browser inspection
                    'button:has-text("发布")',
                    'button.primary:has-text("发布")',
                    'div[class*="publish"] button',
                    'button[class*="primary"]',
                ]

                for selector in publish_selectors:
                    try:
                        publish_btn = self.page.locator(selector).first

                        # Wait for it to be visible
                        if publish_btn.is_visible(timeout=3000):
                            # Scroll the button into view
                            publish_btn.scroll_into_view_if_needed()
                            self.page.wait_for_timeout(300)

                            # Wait for button to be enabled
                            max_wait = 30  # Wait up to 30 seconds
                            for i in range(max_wait):
                                if not publish_btn.is_disabled():
                                    break
                                logger.info(f"Publish button is disabled, waiting... ({i+1}/{max_wait}s)")
                                self.page.wait_for_timeout(1000)

                            # Click the button
                            publish_btn.click()
                            publish_clicked = True
                            logger.info(f"Publish button clicked using selector: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue

                if not publish_clicked:
                    # Last resort: try to find any button with "发布" text
                    logger.info("Trying to find any button with 发布 text...")
                    all_buttons = self.page.locator('button').all()
                    for btn in all_buttons:
                        try:
                            btn_text = btn.text_content()
                            if btn_text and '发布' in btn_text:
                                btn.click()
                                publish_clicked = True
                            logger.info(f"Clicked button with text: {btn_text}")
                            break
                        except:
                            continue

            except Exception as e:
                logger.error(f"Error while trying to click publish: {e}")

            if not publish_clicked:
                logger.error("Failed to click publish button")
                # Take screenshot for debugging
                try:
                    self.page.screenshot(path="douyin_publish_error.png")
                    logger.info("Screenshot saved to douyin_publish_error.png")
                except:
                    pass
                return False

            # 7. Wait for success message or redirect
            logger.info("Waiting for publish confirmation...")
            try:
                # Success indicator often has "发布成功"
                self.page.wait_for_selector('text="发布成功"', timeout=30000)
                logger.info("Successfully published to Douyin!")
                # Wait a bit before processing next video
                self.page.wait_for_timeout(3000)
                return True
            except:
                # Check for redirect to manage page
                self.page.wait_for_timeout(5000)
                current_url = self.page.url
                if "manage" in current_url or "video" in current_url or "content" in current_url:
                    logger.info(f"Detected redirect to {current_url}, assuming publish success.")
                    # Wait a bit before processing next video
                    self.page.wait_for_timeout(2000)
                    return True
                logger.warning("Could not confirm publish success.")
                return False

        else:
            # Semi-automatic mode: wait for user to manually click publish
            logger.info("=" * 60)
            logger.info("✅ 视频信息已填写完成！")
            logger.info("📌 请在浏览器中检查视频信息，确认无误后手动点击【发布】按钮")
            logger.info("⏸️  脚本已暂停，浏览器保持打开状态...")
            logger.info("=" * 60)

            # Wait for user confirmation
            input("\n按回车键继续（发布完成后）...")
            logger.info("✅ User confirmed publish")

            return True
