"""
检查数据库中论文的质量评分
"""

import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.db import get_connection

with get_connection() as conn:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT paper_id, title, quality_score, recency_score, citation_score, filtered_out
        FROM papers
        WHERE week_id LIKE '%2026-05%'
        LIMIT 10
    """)

    rows = cursor.fetchall()

    print(f"\n找到 {len(rows)} 篇论文:")
    print(f"\n{'Paper ID':<15} {'Quality':<8} {'Recency':<8} {'Citation':<8} {'Filtered':<8} {'Title':<50}")
    print("-" * 110)

    for row in rows:
        paper_id = row['paper_id']
        title = (row['title'][:47] + "...") if row['title'] and len(row['title']) > 50 else (row['title'] or "N/A")
        quality = f"{row['quality_score']:.1f}" if row['quality_score'] else "N/A"
        recency = f"{row['recency_score']:.1f}" if row['recency_score'] else "N/A"
        citation = f"{row['citation_score']:.1f}" if row['citation_score'] else "N/A"
        filtered = "Yes" if row['filtered_out'] else "No"

        print(f"{paper_id:<15} {quality:<8} {recency:<8} {citation:<8} {filtered:<8} {title}")
