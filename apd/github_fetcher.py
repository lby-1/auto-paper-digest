"""
GitHub Trending 热门项目获取模块

功能：
- 获取 GitHub Trending 热门项目
- 支持按日期/周获取
- 支持按编程语言过滤
"""

from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .config import (
    GITHUB_TRENDING_URL,
    GITHUB_TRENDING_LANGUAGE_URL,
    ContentType,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from .db import upsert_paper
from .utils import get_logger

logger = get_logger()


def fetch_daily_github_trending(
    date: str,
    max_projects: int = 50,
    language: Optional[str] = None,
    since: str = "daily"
) -> List[dict]:
    """
    获取指定日期的 GitHub Trending 项目

    注意：GitHub Trending 是实时的，date 参数主要用于数据库存储标识

    Args:
        date: 日期 (YYYY-MM-DD)，如 "2026-01-20"
        max_projects: 最大项目数量
        language: 编程语言过滤（如 "python", "javascript"）
        since: 时间范围 (daily/weekly/monthly)

    Returns:
        项目信息列表
    """
    logger.info(f"Fetching GitHub Trending (language={language}, since={since}) for date {date}")

    # 获取项目列表
    projects = _fetch_github_trending(max_projects, language, since)

    # 存入数据库
    saved_count = 0
    for project in projects:
        try:
            upsert_paper(
                paper_id=project['id'],
                week_id=date,  # 使用日期作为 week_id
                title=project['name'],
                content_type=ContentType.GITHUB,
                source_url=project['url'],
                summary=project['description'],
                github_stars=project['stars'],
                github_language=project['language'],
                github_description=project['description']
            )
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save project {project['name']}: {e}")

    logger.info(f"Saved {saved_count}/{len(projects)} projects to database")
    return projects


def fetch_weekly_github_trending(
    week_id: str,
    max_projects: int = 50,
    language: Optional[str] = None
) -> List[dict]:
    """
    获取指定周的 GitHub Trending 项目

    实际获取的是当前时刻的 Trending，使用 week_id 作为标识存储

    Args:
        week_id: 周 ID (YYYY-WW)，如 "2026-03"
        max_projects: 最大项目数量
        language: 编程语言过滤

    Returns:
        项目信息列表
    """
    # 使用当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    return fetch_daily_github_trending(current_date, max_projects, language, since="weekly")


# ============================================================================
# GitHub Trending 爬虫
# ============================================================================

def _fetch_github_trending(
    max_projects: int,
    language: Optional[str] = None,
    since: str = "daily"
) -> List[dict]:
    """
    获取 GitHub Trending 项目

    Args:
        max_projects: 最大项目数量
        language: 编程语言过滤
        since: 时间范围 (daily/weekly/monthly)

    Returns:
        项目列表，每个项目包含: id, name, url, description, stars, stars_today, language, forks
    """
    # 构建 URL
    if language:
        url = GITHUB_TRENDING_LANGUAGE_URL.format(language=language)
    else:
        url = GITHUB_TRENDING_URL

    params = {"since": since}
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        logger.info(f"Fetching from: {url} (since={since})")
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        projects = []

        # GitHub Trending 使用 article 标签包裹每个项目
        articles = soup.find_all('article', class_='Box-row')

        for idx, article in enumerate(articles[:max_projects], 1):
            try:
                project_data = _parse_github_project(article, idx)
                if project_data:
                    projects.append(project_data)
            except Exception as e:
                logger.warning(f"Failed to parse GitHub project: {e}")
                continue

        logger.info(f"Fetched {len(projects)} GitHub projects")
        return projects

    except Exception as e:
        logger.error(f"Failed to fetch GitHub Trending: {e}")
        return []


def _parse_github_project(article, rank: int) -> Optional[dict]:
    """
    解析单个 GitHub 项目的 HTML

    Args:
        article: BeautifulSoup article 元素
        rank: 排名

    Returns:
        项目信息字典
    """
    try:
        # 1. 提取项目名称和 URL
        h2 = article.find('h2', class_='h3')
        if not h2:
            return None

        link = h2.find('a')
        if not link:
            return None

        # 项目完整路径，如 "owner/repo"
        repo_path = link.get('href', '').strip('/')
        if not repo_path:
            return None

        # 项目名称
        repo_name = repo_path.split('/')[-1]

        # 完整 URL
        repo_url = f"https://github.com/{repo_path}"

        # 生成唯一 ID
        project_id = f"github-{repo_path.replace('/', '-')}"

        # 2. 提取描述
        description_elem = article.find('p', class_='col-9')
        description = description_elem.text.strip() if description_elem else ""

        # 3. 提取编程语言
        language_elem = article.find('span', itemprop='programmingLanguage')
        language = language_elem.text.strip() if language_elem else None

        # 4. 提取星标数（总数）
        stars = 0
        star_link = article.find('a', class_='Link--muted', href=lambda x: x and '/stargazers' in x)
        if star_link:
            stars_text = star_link.text.strip().replace(',', '').replace('k', '000')
            try:
                stars = int(float(stars_text))
            except:
                pass

        # 5. 提取今日新增星标
        stars_today = 0
        stars_today_span = article.find('span', class_='d-inline-block')
        if stars_today_span and '今日' not in stars_today_span.text and 'today' in stars_today_span.text.lower():
            stars_today_text = stars_today_span.text.strip().split()[0].replace(',', '')
            try:
                stars_today = int(stars_today_text)
            except:
                pass

        # 6. 提取 Forks 数
        forks = 0
        fork_link = article.find('a', class_='Link--muted', href=lambda x: x and '/forks' in x)
        if fork_link:
            forks_text = fork_link.text.strip().replace(',', '')
            try:
                forks = int(forks_text)
            except:
                pass

        return {
            'id': project_id,
            'name': repo_name,
            'full_name': repo_path,
            'url': repo_url,
            'description': description,
            'language': language,
            'stars': stars,
            'stars_today': stars_today,
            'forks': forks,
            'rank': rank,
        }

    except Exception as e:
        logger.error(f"Error parsing GitHub project: {e}")
        return None
