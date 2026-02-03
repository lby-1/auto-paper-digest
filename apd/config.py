"""
Configuration module for Auto Paper Digest.

Centralizes all paths, URLs, and default settings.
"""

import os
from pathlib import Path

# =============================================================================
# Directory Paths
# =============================================================================

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"

# Data subdirectories
PDF_DIR = DATA_DIR / "pdfs"
VIDEO_DIR = DATA_DIR / "videos"
SLIDES_DIR = DATA_DIR / "slides"
DIGEST_DIR = DATA_DIR / "digests"
PROFILE_DIR = DATA_DIR / "profiles"

# Database
DB_PATH = DATA_DIR / "apd.db"

# Default browser profile name
DEFAULT_PROFILE = "default"

# =============================================================================
# URLs
# =============================================================================

# Hugging Face papers page (date-based and week-based)
HF_PAPERS_URL = "https://huggingface.co/papers"
HF_PAPERS_DATE_URL = "https://huggingface.co/papers?date={date}"
HF_PAPERS_DATE_PAGE_URL = "https://huggingface.co/papers/date/{date}"  # e.g., /date/2026-01-08
HF_PAPERS_WEEK_URL = "https://huggingface.co/papers/week/{week}"  # e.g., /week/2026-W01

# arXiv PDF download template
ARXIV_PDF_URL = "https://export.arxiv.org/pdf/{paper_id}.pdf"

# NotebookLM
NOTEBOOKLM_URL = "https://notebooklm.google.com"

# GitHub Trending
GITHUB_TRENDING_URL = "https://github.com/trending"
GITHUB_TRENDING_LANGUAGE_URL = "https://github.com/trending/{language}"
GITHUB_API_URL = "https://api.github.com"

# 新闻源 URLs
NEWS_SOURCES = {
    "weibo": "https://s.weibo.com/top/summary",
    "zhihu": "https://www.zhihu.com/hot",
    "baidu": "https://top.baidu.com/board?tab=realtime",
}

# B站
BILIBILI_LOGIN_URL = "https://passport.bilibili.com/login"
BILIBILI_CREATOR_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_AUTH_PATH = DATA_DIR / ".bilibili_auth.json"

# =============================================================================
# Defaults
# =============================================================================

# Maximum papers to fetch per week
DEFAULT_MAX_PAPERS = 50

# Maximum retry attempts for failed operations
MAX_RETRIES = 3

# Request timeout in seconds
REQUEST_TIMEOUT = 60

# Download chunk size
DOWNLOAD_CHUNK_SIZE = 8192

# Delay between downloads (seconds) to respect arXiv rate limits
DOWNLOAD_DELAY_SECONDS = 3

# Playwright timeouts (milliseconds)
PLAYWRIGHT_TIMEOUT = 60000  # 60 seconds for general operations
PLAYWRIGHT_NAVIGATION_TIMEOUT = 120000  # 120 seconds for page navigation
PLAYWRIGHT_VIDEO_TIMEOUT = 600000  # 10 minutes for video generation

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# =============================================================================
# Status Constants
# =============================================================================

class Status:
    """Paper processing status values."""
    NEW = "NEW"
    PDF_OK = "PDF_OK"
    NBLM_OK = "NBLM_OK"  # Notebook created, PDF uploaded
    VIDEO_OK = "VIDEO_OK"
    ERROR = "ERROR"


class ContentType:
    """Content type values."""
    PAPER = "PAPER"      # 学术论文
    GITHUB = "GITHUB"    # GitHub 项目
    NEWS = "NEWS"        # 新闻热点


def ensure_directories() -> None:
    """Create all required directories if they don't exist."""
    for directory in [PDF_DIR, VIDEO_DIR, SLIDES_DIR, DIGEST_DIR, PROFILE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Quality Control Configuration
# =============================================================================

class QualityConfig:
    """质量控制配置"""

    # 评分权重(总和为1.0)
    CITATION_WEIGHT = 0.35
    AUTHOR_WEIGHT = 0.25
    VENUE_WEIGHT = 0.30
    RECENCY_WEIGHT = 0.10

    # 质量阈值
    MIN_QUALITY_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "60.0"))

    # 论文特定配置
    MIN_CITATIONS = int(os.getenv("MIN_CITATIONS", "0"))  # 新论文可为0
    ACCEPTED_VENUE_RANKS = ["A", "B", "C"]  # CCF等级

    # GitHub项目配置
    MIN_GITHUB_STARS = int(os.getenv("MIN_GITHUB_STARS", "100"))
    GITHUB_STARS_WEIGHT = 0.40
    GITHUB_LANGUAGE_WEIGHT = 0.20
    GITHUB_ACTIVITY_WEIGHT = 0.40

    # 新闻配置
    NEWS_RANK_WEIGHT = 0.60
    NEWS_SOURCE_WEIGHT = 0.40

    # 源权重(不同来源的基础分)
    SOURCE_WEIGHTS = {
        "arxiv": 1.0,
        "huggingface": 1.0,
        "weibo": 0.8,
        "zhihu": 0.9,
        "baidu": 0.7,
    }

    # API配置(可选)
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("S2_API_KEY")
    ENABLE_SEMANTIC_SCHOLAR = os.getenv("ENABLE_S2", "false").lower() == "true"


# =============================================================================
# Deduplication Configuration
# =============================================================================

class DeduplicationConfig:
    """去重配置"""

    # 相似度阈值
    EXACT_MATCH_THRESHOLD = 1.0  # URL完全匹配
    TITLE_SIMILARITY_THRESHOLD = float(os.getenv("TITLE_SIMILARITY_THRESHOLD", "0.85"))
    ABSTRACT_SIMILARITY_THRESHOLD = float(os.getenv("ABSTRACT_SIMILARITY_THRESHOLD", "0.90"))

    # 合并策略
    MERGE_STRATEGY = os.getenv("DEDUP_MERGE_STRATEGY", "keep_first")
    # 可选值: keep_first | keep_highest_quality | manual

    # 嵌入模型
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    # 轻量级模型 (~90MB)
    # 可选: "all-mpnet-base-v2" (更高精度, ~420MB)

    # 性能配置
    ENABLE_SEMANTIC_DEDUP = os.getenv("ENABLE_SEMANTIC_DEDUP", "true").lower() == "true"
    BATCH_SIZE = int(os.getenv("DEDUP_BATCH_SIZE", "100"))  # 批处理大小


# =============================================================================
# Recommendation Configuration
# =============================================================================

class RecommendationConfig:
    """推荐系统配置"""

    # 默认用户ID
    DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default")

    # Embedding模型（复用去重系统的模型）
    EMBEDDING_MODEL = os.getenv("REC_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # 热门推荐权重
    POPULAR_QUALITY_WEIGHT = 0.6
    POPULAR_RECENCY_WEIGHT = 0.3
    POPULAR_CITATION_WEIGHT = 0.1

    # 相似度阈值
    CONTENT_SIMILARITY_THRESHOLD = float(os.getenv("CONTENT_SIMILARITY_THRESHOLD", "0.5"))

    # 推荐数量
    DEFAULT_RECOMMENDATION_COUNT = int(os.getenv("REC_COUNT", "10"))

    # 用户行为权重
    INTERACTION_WEIGHTS = {
        "view": 1.0,
        "favorite": 3.0,
        "share": 5.0,
        "download": 2.0,
    }

    # 用户分类阈值（交互次数）
    NEW_USER_THRESHOLD = 5       # 新用户：< 5次交互
    ACTIVE_USER_THRESHOLD = 20   # 活跃用户：>= 20次交互
