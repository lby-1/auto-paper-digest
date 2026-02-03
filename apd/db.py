"""
Database module for Auto Paper Digest.

Provides SQLite-based paper tracking with status management.
"""

import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from .config import DB_PATH, Status
from .utils import get_logger, now_iso

logger = get_logger()


def _is_week_format(period_id: str) -> bool:
    """Check if period_id is week format (YYYY-WW) vs date format (YYYY-MM-DD)."""
    # Week format: 2026-03 (4 digits, dash, 2 digits)
    # Date format: 2026-01-15 (4 digits, dash, 2 digits, dash, 2 digits)
    return bool(re.match(r'^\d{4}-\d{2}$', period_id))


def _get_dates_for_week(week_id: str) -> list[str]:
    """
    Get all dates (YYYY-MM-DD) for a given week.
    
    Args:
        week_id: Week identifier (e.g., "2026-03")
        
    Returns:
        List of date strings for that week (Monday to Sunday)
    """
    parts = week_id.split("-")
    if len(parts) != 2:
        return []
    
    year, week = int(parts[0]), int(parts[1])
    
    # Get the Monday of the given ISO week
    jan4 = datetime(year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())
    monday = start_of_week1 + timedelta(weeks=week - 1)
    
    # Generate all 7 days of the week
    dates = []
    for i in range(7):
        day = monday + timedelta(days=i)
        dates.append(day.strftime("%Y-%m-%d"))
    
    return dates


def _build_week_id_clause(week_id: str) -> tuple[str, list]:
    """
    Build SQL clause for week_id matching.
    
    If week_id is in week format (YYYY-WW), matches both the week format
    and all daily dates within that week.
    
    Args:
        week_id: Week or date identifier
        
    Returns:
        Tuple of (SQL clause, parameters list)
    """
    if _is_week_format(week_id):
        # Match both week format and all daily dates in that week
        dates = _get_dates_for_week(week_id)
        all_ids = [week_id] + dates
        placeholders = ",".join("?" * len(all_ids))
        return f"week_id IN ({placeholders})", all_ids
    else:
        # Just match the exact value
        return "week_id = ?", [week_id]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Paper:
    """Represents a paper/content record in the database."""
    paper_id: str
    week_id: str

    # 基础字段
    title: Optional[str] = None
    hf_url: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_sha256: Optional[str] = None
    notebooklm_note_name: Optional[str] = None
    video_path: Optional[str] = None
    slides_path: Optional[str] = None
    summary: Optional[str] = None

    # 新增：内容类型和源
    content_type: str = "PAPER"  # PAPER/GITHUB/NEWS
    source_url: Optional[str] = None  # 通用源 URL

    # 新增：GitHub 相关字段
    github_stars: Optional[int] = None
    github_language: Optional[str] = None
    github_description: Optional[str] = None

    # 新增：新闻相关字段
    news_source: Optional[str] = None  # weibo/zhihu/baidu
    news_url: Optional[str] = None

    # 新增：发布状态
    bilibili_published: int = 0  # 0=未发布, 1=已发布
    douyin_published: int = 0    # 0=未发布, 1=已发布

    # 质量控制字段（新增）
    quality_score: Optional[float] = None        # 综合质量评分 0-100
    citation_score: Optional[float] = None       # 引用数评分
    venue_score: Optional[float] = None          # 会议/期刊评分
    recency_score: Optional[float] = None        # 时效性评分
    quality_reasons: Optional[str] = None        # JSON字符串：评分详情
    filtered_out: int = 0                        # 是否被过滤 0/1
    filter_reason: Optional[str] = None          # 过滤原因
    evaluated_at: Optional[str] = None           # 评估时间戳

    # 状态字段
    status: str = Status.NEW
    retry_count: int = 0
    last_error: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# Database Management
# =============================================================================

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    Context manager for database connections.
    
    Yields:
        SQLite connection with row factory enabled
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                week_id TEXT NOT NULL,
                title TEXT,
                hf_url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,
                pdf_sha256 TEXT,
                notebooklm_note_name TEXT,
                video_path TEXT,
                slides_path TEXT,
                summary TEXT,
                status TEXT DEFAULT 'NEW',
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT
            )
        """)
        
        # Add slides_path column if it doesn't exist (migration for existing databases)
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN slides_path TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add summary column if it doesn't exist (migration for existing databases)
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN summary TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # === 新增字段迁移 ===

        # 内容类型和源
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN content_type TEXT DEFAULT 'PAPER'")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN source_url TEXT")
        except sqlite3.OperationalError:
            pass

        # GitHub 相关字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN github_stars INTEGER")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN github_language TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN github_description TEXT")
        except sqlite3.OperationalError:
            pass

        # 新闻相关字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN news_source TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN news_url TEXT")
        except sqlite3.OperationalError:
            pass

        # 发布状态字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN bilibili_published INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN douyin_published INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 质量控制字段迁移
        quality_fields = [
            ("quality_score", "REAL DEFAULT 0.0"),
            ("citation_score", "REAL DEFAULT 0.0"),
            ("venue_score", "REAL DEFAULT 0.0"),
            ("recency_score", "REAL DEFAULT 0.0"),
            ("quality_reasons", "TEXT"),
            ("filtered_out", "INTEGER DEFAULT 0"),
            ("filter_reason", "TEXT"),
            ("evaluated_at", "TEXT"),
        ]

        for field_name, field_type in quality_fields:
            try:
                cursor.execute(f"ALTER TABLE papers ADD COLUMN {field_name} {field_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_week 
            ON papers(week_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_status 
            ON papers(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_week_status 
            ON papers(week_id, status)
        """)
        
        logger.debug("Database initialized")


# =============================================================================
# CRUD Operations
# =============================================================================

def get_paper(paper_id: str) -> Optional[Paper]:
    """
    Get a paper by its ID.
    
    Args:
        paper_id: The paper ID (arXiv ID)
        
    Returns:
        Paper object or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()
        
        if row:
            return Paper(**dict(row))
        return None


def upsert_paper(
    paper_id: str,
    week_id: str,
    title: Optional[str] = None,
    hf_url: Optional[str] = None,
    pdf_url: Optional[str] = None,
    pdf_path: Optional[str] = None,
    pdf_sha256: Optional[str] = None,
    notebooklm_note_name: Optional[str] = None,
    video_path: Optional[str] = None,
    slides_path: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
    last_error: Optional[str] = None,
    # 新增参数
    content_type: Optional[str] = None,
    source_url: Optional[str] = None,
    github_stars: Optional[int] = None,
    github_language: Optional[str] = None,
    github_description: Optional[str] = None,
    news_source: Optional[str] = None,
    news_url: Optional[str] = None,
    bilibili_published: Optional[int] = None,
    douyin_published: Optional[int] = None,
    # 质量控制参数
    quality_score: Optional[float] = None,
    citation_score: Optional[float] = None,
    venue_score: Optional[float] = None,
    recency_score: Optional[float] = None,
    quality_reasons: Optional[str] = None,
    filtered_out: Optional[int] = None,
    filter_reason: Optional[str] = None,
    evaluated_at: Optional[str] = None,
) -> Paper:
    """
    Insert or update a paper/content record.

    Only updates fields that are explicitly provided (not None).

    Args:
        paper_id: The content ID (arXiv ID, GitHub repo, news ID, etc.)
        week_id: Week/date identifier
        content_type: Content type (PAPER/GITHUB/NEWS)
        Other args: Optional fields to set/update

    Returns:
        The updated Paper object
    """
    existing = get_paper(paper_id)
    now = now_iso()

    with get_connection() as conn:
        cursor = conn.cursor()

        if existing:
            # Build UPDATE query dynamically for non-None fields
            updates = []
            values = []

            if title is not None:
                updates.append("title = ?")
                values.append(title)
            if hf_url is not None:
                updates.append("hf_url = ?")
                values.append(hf_url)
            if pdf_url is not None:
                updates.append("pdf_url = ?")
                values.append(pdf_url)
            if pdf_path is not None:
                updates.append("pdf_path = ?")
                values.append(pdf_path)
            if pdf_sha256 is not None:
                updates.append("pdf_sha256 = ?")
                values.append(pdf_sha256)
            if notebooklm_note_name is not None:
                updates.append("notebooklm_note_name = ?")
                values.append(notebooklm_note_name)
            if video_path is not None:
                updates.append("video_path = ?")
                values.append(video_path)
            if slides_path is not None:
                updates.append("slides_path = ?")
                values.append(slides_path)
            if summary is not None:
                updates.append("summary = ?")
                values.append(summary)
            if status is not None:
                updates.append("status = ?")
                values.append(status)
            if last_error is not None:
                updates.append("last_error = ?")
                values.append(last_error)

            # 新增字段更新
            if content_type is not None:
                updates.append("content_type = ?")
                values.append(content_type)
            if source_url is not None:
                updates.append("source_url = ?")
                values.append(source_url)
            if github_stars is not None:
                updates.append("github_stars = ?")
                values.append(github_stars)
            if github_language is not None:
                updates.append("github_language = ?")
                values.append(github_language)
            if github_description is not None:
                updates.append("github_description = ?")
                values.append(github_description)
            if news_source is not None:
                updates.append("news_source = ?")
                values.append(news_source)
            if news_url is not None:
                updates.append("news_url = ?")
                values.append(news_url)
            if bilibili_published is not None:
                updates.append("bilibili_published = ?")
                values.append(bilibili_published)
            if douyin_published is not None:
                updates.append("douyin_published = ?")
                values.append(douyin_published)

            # 质量控制字段更新
            if quality_score is not None:
                updates.append("quality_score = ?")
                values.append(quality_score)
            if citation_score is not None:
                updates.append("citation_score = ?")
                values.append(citation_score)
            if venue_score is not None:
                updates.append("venue_score = ?")
                values.append(venue_score)
            if recency_score is not None:
                updates.append("recency_score = ?")
                values.append(recency_score)
            if quality_reasons is not None:
                updates.append("quality_reasons = ?")
                values.append(quality_reasons)
            if filtered_out is not None:
                updates.append("filtered_out = ?")
                values.append(filtered_out)
            if filter_reason is not None:
                updates.append("filter_reason = ?")
                values.append(filter_reason)
            if evaluated_at is not None:
                updates.append("evaluated_at = ?")
                values.append(evaluated_at)

            updates.append("updated_at = ?")
            values.append(now)
            values.append(paper_id)

            if updates:
                query = f"UPDATE papers SET {', '.join(updates)} WHERE paper_id = ?"
                cursor.execute(query, values)

            logger.debug(f"Updated paper: {paper_id}")
        else:
            # INSERT new record
            cursor.execute("""
                INSERT INTO papers (
                    paper_id, week_id, title, hf_url, pdf_url, pdf_path,
                    pdf_sha256, notebooklm_note_name, video_path, slides_path, summary, status,
                    retry_count, last_error, updated_at,
                    content_type, source_url, github_stars, github_language, github_description,
                    news_source, news_url, bilibili_published, douyin_published,
                    quality_score, citation_score, venue_score, recency_score, quality_reasons,
                    filtered_out, filter_reason, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id, week_id, title, hf_url, pdf_url, pdf_path,
                pdf_sha256, notebooklm_note_name, video_path, slides_path, summary,
                status or Status.NEW, 0, last_error, now,
                content_type or "PAPER", source_url, github_stars, github_language, github_description,
                news_source, news_url, bilibili_published or 0, douyin_published or 0,
                quality_score, citation_score, venue_score, recency_score, quality_reasons,
                filtered_out or 0, filter_reason, evaluated_at
            ))
            logger.debug(f"Inserted paper: {paper_id}")

    return get_paper(paper_id)  # type: ignore



def update_status(
    paper_id: str,
    status: str,
    error: Optional[str] = None,
    increment_retry: bool = False
) -> Optional[Paper]:
    """
    Update the status of a paper.
    
    Args:
        paper_id: The paper ID
        status: New status value
        error: Optional error message
        increment_retry: Whether to increment retry_count
        
    Returns:
        Updated Paper object or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        now = now_iso()
        
        if increment_retry:
            cursor.execute("""
                UPDATE papers 
                SET status = ?, last_error = ?, retry_count = retry_count + 1, updated_at = ?
                WHERE paper_id = ?
            """, (status, error, now, paper_id))
        else:
            cursor.execute("""
                UPDATE papers 
                SET status = ?, last_error = ?, updated_at = ?
                WHERE paper_id = ?
            """, (status, error, now, paper_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"Paper not found for status update: {paper_id}")
            return None
            
        logger.debug(f"Updated status for {paper_id}: {status}")
    
    return get_paper(paper_id)


def list_papers(
    week_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None
) -> list[Paper]:
    """
    List papers with optional filtering.
    
    Args:
        week_id: Filter by week
        status: Filter by status
        limit: Maximum number of results
        
    Returns:
        List of Paper objects
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM papers WHERE 1=1"
        params: list = []
        
        if week_id:
            clause, clause_params = _build_week_id_clause(week_id)
            query += f" AND {clause}"
            params.extend(clause_params)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY updated_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [Paper(**dict(row)) for row in rows]


def count_papers(week_id: Optional[str] = None, status: Optional[str] = None) -> int:
    """
    Count papers with optional filtering.

    Args:
        week_id: Filter by week
        status: Filter by status

    Returns:
        Count of matching papers
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM papers WHERE 1=1"
        params: list = []

        if week_id:
            clause, clause_params = _build_week_id_clause(week_id)
            query += f" AND {clause}"
            params.extend(clause_params)
        if status:
            query += " AND status = ?"
            params.append(status)

        cursor.execute(query, params)
        return cursor.fetchone()[0]


def list_papers_by_quality(
    week_id: Optional[str] = None,
    min_quality_score: float = 0.0,
    include_filtered: bool = True,
    limit: Optional[int] = None
) -> list[Paper]:
    """列出符合质量要求的内容"""
    with get_connection() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM papers WHERE 1=1"
        params: list = []

        if min_quality_score > 0:
            query += " AND (quality_score >= ? OR quality_score IS NULL)"
            params.append(min_quality_score)

        if not include_filtered:
            query += " AND filtered_out = 0"

        if week_id:
            clause, clause_params = _build_week_id_clause(week_id)
            query += f" AND {clause}"
            params.extend(clause_params)

        query += " ORDER BY quality_score DESC, updated_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [Paper(**dict(row)) for row in rows]


def get_papers_for_processing(
    week_id: str,
    target_status: str,
    max_retries: int = 3,
    limit: Optional[int] = None
) -> list[Paper]:
    """
    Get papers that need processing to reach a target status.
    
    Args:
        week_id: Week to process
        target_status: The status we want papers to reach
        max_retries: Maximum retry attempts before skipping
        limit: Maximum papers to return
        
    Returns:
        List of papers that need processing
    """
    # Define status precedence
    status_order = [Status.NEW, Status.PDF_OK, Status.NBLM_OK, Status.VIDEO_OK]
    
    if target_status not in status_order:
        return []
    
    target_idx = status_order.index(target_status)
    needed_statuses = status_order[:target_idx]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Build week_id clause for smart matching
        week_clause, week_params = _build_week_id_clause(week_id)
        
        status_placeholders = ",".join("?" * len(needed_statuses))
        query = f"""
            SELECT * FROM papers 
            WHERE {week_clause}
            AND status IN ({status_placeholders})
            AND retry_count < ?
            ORDER BY paper_id
        """
        
        params = week_params + needed_statuses + [max_retries]
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [Paper(**dict(row)) for row in rows]
