"""
新闻热点获取模块

支持从多个新闻源获取热榜：
- 微博热搜
- 知乎热榜
- 百度热搜
"""

import hashlib
import re
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .config import ContentType, NEWS_SOURCES, REQUEST_TIMEOUT, USER_AGENT
from .db import upsert_paper
from .utils import get_logger

logger = get_logger()


def fetch_daily_news(
    date: str,
    max_news: int = 50,
    source: str = "weibo"
) -> List[dict]:
    """
    获取指定日期的热榜新闻

    注意：由于热榜是实时的，date 参数主要用于数据库存储标识
    实际获取的是当前时刻的热榜

    Args:
        date: 日期 (YYYY-MM-DD)，如 "2026-01-20"
        max_news: 最大新闻数量
        source: 新闻源 (weibo/zhihu/baidu)

    Returns:
        新闻信息列表
    """
    if source not in NEWS_SOURCES:
        raise ValueError(f"Unknown news source: {source}. Available: {list(NEWS_SOURCES.keys())}")

    logger.info(f"Fetching news from {source} for date {date}")

    # 导入质量过滤器
    from .quality_filter import QualityFilter
    from .utils import now_iso
    import json

    quality_filter = QualityFilter()

    # 根据源选择不同的爬取函数
    if source == "weibo":
        news_list = _fetch_weibo_hot(max_news)
    elif source == "zhihu":
        news_list = _fetch_zhihu_hot(max_news)
    elif source == "baidu":
        news_list = _fetch_baidu_hot(max_news)
    else:
        logger.error(f"Source {source} not implemented yet")
        return []

    # 存入数据库
    saved_count = 0
    for news in news_list:
        try:
            # 评估质量
            score = quality_filter.evaluate_news(
                title=news.get('title', ''),
                rank=news.get('rank', 999),
                source=source,
                hot_value=news.get('hot_value')
            )

            upsert_paper(
                paper_id=news['id'],
                week_id=date,  # 使用日期作为 week_id
                title=news['title'],
                content_type=ContentType.NEWS,
                source_url=news['url'],
                summary=news.get('description', ''),
                news_source=source,
                news_url=news['url'],
                # 质量评分字段
                quality_score=score.total_score,
                citation_score=score.citation_score,
                venue_score=score.venue_score,
                recency_score=score.recency_score,
                quality_reasons=json.dumps(score.reasons, ensure_ascii=False),
                filtered_out=0 if score.passed else 1,
                filter_reason=None if score.passed else "质量评分低于阈值",
                evaluated_at=now_iso()
            )
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save news {news['title']}: {e}")

    logger.info(f"Saved {saved_count}/{len(news_list)} news to database")
    return news_list


def fetch_weekly_news(
    week_id: str,
    max_news: int = 50,
    source: str = "weibo"
) -> List[dict]:
    """
    获取指定周的热榜新闻

    由于热榜是实时的，这个函数实际上获取当前时刻的热榜
    并使用 week_id 作为标识存储

    Args:
        week_id: 周 ID (YYYY-WW)，如 "2026-03"
        max_news: 最大新闻数量
        source: 新闻源 (weibo/zhihu/baidu)

    Returns:
        新闻信息列表
    """
    # 使用当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    return fetch_daily_news(current_date, max_news, source)


# ============================================================================
# 微博热搜爬虫
# ============================================================================

def _fetch_weibo_hot(max_news: int) -> List[dict]:
    """
    获取微博热搜榜

    Args:
        max_news: 最大新闻数量

    Returns:
        新闻列表，每条新闻包含: id, title, url, hot_value, description
    """
    url = NEWS_SOURCES["weibo"]
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        news_list = []

        # 微博热搜的 HTML 结构（可能需要根据实际情况调整）
        items = soup.find_all('td', class_='td-02')

        for idx, item in enumerate(items[:max_news], 1):
            try:
                # 提取标题和链接
                link = item.find('a')
                if not link:
                    continue

                title = link.text.strip()
                href = link.get('href', '')

                # 完整 URL
                if href.startswith('//'):
                    full_url = 'https:' + href
                elif href.startswith('/'):
                    full_url = 'https://s.weibo.com' + href
                else:
                    full_url = href

                # 提取热度值
                hot_elem = item.find('span', class_='td-02-num')
                hot_value = hot_elem.text.strip() if hot_elem else "N/A"

                # 生成唯一 ID
                news_id = f"weibo-{_generate_news_id(title)}"

                news_list.append({
                    'id': news_id,
                    'title': title,
                    'url': full_url,
                    'hot_value': hot_value,
                    'rank': idx,
                    'description': f"微博热搜第{idx}名，热度: {hot_value}"
                })
            except Exception as e:
                logger.warning(f"Failed to parse weibo item: {e}")
                continue

        logger.info(f"Fetched {len(news_list)} news from Weibo")
        return news_list

    except Exception as e:
        logger.error(f"Failed to fetch Weibo hot search: {e}")
        return []


# ============================================================================
# 知乎热榜爬虫
# ============================================================================

def _fetch_zhihu_hot(max_news: int) -> List[dict]:
    """
    获取知乎热榜

    Args:
        max_news: 最大新闻数量

    Returns:
        新闻列表
    """
    url = NEWS_SOURCES["zhihu"]
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.zhihu.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        news_list = []

        # 知乎热榜的 HTML 结构（可能需要根据实际情况调整）
        # 由于知乎使用了大量 JavaScript 渲染，这里提供一个基础实现
        sections = soup.find_all('section', class_='HotItem')

        for idx, section in enumerate(sections[:max_news], 1):
            try:
                # 提取标题
                title_elem = section.find('h2', class_='HotItem-title')
                if not title_elem:
                    continue

                title = title_elem.text.strip()

                # 提取链接
                link_elem = section.find('a', class_='HotItem-content')
                href = link_elem.get('href', '') if link_elem else ''

                if href and not href.startswith('http'):
                    href = 'https://www.zhihu.com' + href

                # 提取热度
                hot_elem = section.find('div', class_='HotItem-metrics')
                hot_value = hot_elem.text.strip() if hot_elem else "N/A"

                # 提取摘要
                excerpt_elem = section.find('p', class_='HotItem-excerpt')
                excerpt = excerpt_elem.text.strip() if excerpt_elem else ""

                # 生成唯一 ID
                news_id = f"zhihu-{_generate_news_id(title)}"

                news_list.append({
                    'id': news_id,
                    'title': title,
                    'url': href,
                    'hot_value': hot_value,
                    'rank': idx,
                    'description': f"知乎热榜第{idx}名，热度: {hot_value}\n{excerpt}"
                })
            except Exception as e:
                logger.warning(f"Failed to parse zhihu item: {e}")
                continue

        logger.info(f"Fetched {len(news_list)} news from Zhihu")
        return news_list

    except Exception as e:
        logger.error(f"Failed to fetch Zhihu hot list: {e}")
        return []


# ============================================================================
# 百度热搜爬虫
# ============================================================================

def _fetch_baidu_hot(max_news: int) -> List[dict]:
    """
    获取百度热搜榜

    Args:
        max_news: 最大新闻数量

    Returns:
        新闻列表
    """
    url = NEWS_SOURCES["baidu"]
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        news_list = []

        # 百度热搜的 HTML 结构
        items = soup.find_all('div', class_='category-wrap_iQLoo')

        for idx, item in enumerate(items[:max_news], 1):
            try:
                # 提取标题
                title_elem = item.find('div', class_='c-single-text-ellipsis')
                if not title_elem:
                    continue

                title = title_elem.text.strip()

                # 提取链接
                link_elem = item.find('a')
                href = link_elem.get('href', '') if link_elem else ''

                # 提取热度
                hot_elem = item.find('div', class_='hot-index_1Bl1a')
                hot_value = hot_elem.text.strip() if hot_elem else "N/A"

                # 提取描述
                desc_elem = item.find('div', class_='hot-desc_1m_jR')
                description = desc_elem.text.strip() if desc_elem else ""

                # 生成唯一 ID
                news_id = f"baidu-{_generate_news_id(title)}"

                news_list.append({
                    'id': news_id,
                    'title': title,
                    'url': href,
                    'hot_value': hot_value,
                    'rank': idx,
                    'description': f"百度热搜第{idx}名，热度: {hot_value}\n{description}"
                })
            except Exception as e:
                logger.warning(f"Failed to parse baidu item: {e}")
                continue

        logger.info(f"Fetched {len(news_list)} news from Baidu")
        return news_list

    except Exception as e:
        logger.error(f"Failed to fetch Baidu hot search: {e}")
        return []


# ============================================================================
# 工具函数
# ============================================================================

def _generate_news_id(title: str) -> str:
    """
    根据标题生成唯一 ID

    Args:
        title: 新闻标题

    Returns:
        8位哈希字符串
    """
    # 使用 MD5 生成短哈希
    hash_obj = hashlib.md5(title.encode('utf-8'))
    return hash_obj.hexdigest()[:8]
