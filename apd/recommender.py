"""
智能推荐引擎

提供多种推荐策略：热门推荐、内容相似、协同过滤、混合推荐
"""

import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from .config import RecommendationConfig
from .db import get_connection, Paper
from .utils import now_iso

logger = logging.getLogger(__name__)


@dataclass
class RecommendationResult:
    """推荐结果"""
    paper_id: str
    title: str
    score: float
    strategy: str
    reasons: List[str]
    paper: Optional[Paper] = None


class Recommender:
    """推荐引擎"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.config = RecommendationConfig
        self.model = None  # 延迟加载

    def _load_model(self):
        """延迟加载Sentence-BERT模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
                self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
            except ImportError:
                logger.warning("sentence-transformers not installed, semantic features disabled")
                self.model = None
        return self.model

    def recommend_popular(
        self,
        week_id: Optional[str] = None,
        limit: int = 10,
        exclude_seen: bool = True
    ) -> List[RecommendationResult]:
        """
        热门推荐

        基于质量评分、时效性、引用数的综合排序
        """
        with get_connection() as conn:
            cursor = conn.cursor()

            # 构建查询
            query = """
                SELECT p.*
                FROM papers p
                WHERE p.filtered_out = 0
                  AND p.quality_score IS NOT NULL
            """
            params = []

            if week_id:
                clause, clause_params = self._build_week_id_clause(week_id)
                query += f" AND {clause}"
                params.extend(clause_params)

            if exclude_seen:
                # 排除已经交互过的论文
                query += """
                    AND p.paper_id NOT IN (
                        SELECT paper_id FROM user_interactions
                        WHERE user_id = ?
                    )
                """
                params.append(self.user_id)

            # 综合评分排序
            query += """
                ORDER BY
                    (COALESCE(p.quality_score, 0) * ? +
                     COALESCE(p.recency_score, 0) * ? +
                     COALESCE(p.citation_score, 0) * ?) DESC
                LIMIT ?
            """
            params.extend([
                self.config.POPULAR_QUALITY_WEIGHT,
                self.config.POPULAR_RECENCY_WEIGHT,
                self.config.POPULAR_CITATION_WEIGHT,
                limit
            ])

            cursor.execute(query, params)
            rows = cursor.fetchall()

        results = []
        for row in rows:
            paper = Paper(**dict(row))
            score = (
                (paper.quality_score or 0) * self.config.POPULAR_QUALITY_WEIGHT +
                (paper.recency_score or 0) * self.config.POPULAR_RECENCY_WEIGHT +
                (paper.citation_score or 0) * self.config.POPULAR_CITATION_WEIGHT
            )

            reasons = []
            if paper.quality_score and paper.quality_score >= 80:
                reasons.append(f"高质量论文（{paper.quality_score:.0f}分）")
            if paper.recency_score and paper.recency_score >= 80:
                reasons.append("最新发布")
            if paper.citation_score and paper.citation_score >= 80:
                reasons.append("高引用")

            results.append(RecommendationResult(
                paper_id=paper.paper_id,
                title=paper.title,
                score=score,
                strategy="popular",
                reasons=reasons if reasons else ["综合推荐"],
                paper=paper
            ))

        return results

    def _build_week_id_clause(self, week_id: str) -> Tuple[str, List]:
        """构建week_id查询条件（支持YYYY-WNN和YYYY-MM-DD格式）"""
        if "W" in week_id.upper():
            # YYYY-WNN format
            return "week_id = ?", [week_id]
        else:
            # YYYY-MM-DD format
            return "week_id LIKE ?", [f"%{week_id}%"]

    def recommend_similar(
        self,
        paper_id: str,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> List[RecommendationResult]:
        """
        基于内容相似度的推荐

        找到与给定论文相似的其他论文
        """
        model = self._load_model()
        if model is None:
            logger.warning("Semantic model not available, using title-only similarity")
            return self._recommend_similar_title_only(paper_id, limit)

        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取目标论文
            cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            if not row:
                return []

            target_paper = Paper(**dict(row))

            # 获取候选论文
            cursor.execute("""
                SELECT * FROM papers
                WHERE paper_id != ?
                  AND filtered_out = 0
                  AND title IS NOT NULL
                LIMIT 100
            """, (paper_id,))
            candidates = [Paper(**dict(row)) for row in cursor.fetchall()]

        if not candidates:
            return []

        # 计算相似度
        # 编码目标论文
        target_text = f"{target_paper.title} {target_paper.summary or ''}"
        target_embedding = model.encode([target_text])[0]

        # 编码候选论文并计算相似度
        results = []
        for candidate in candidates:
            candidate_text = f"{candidate.title} {candidate.summary or ''}"
            candidate_embedding = model.encode([candidate_text])[0]

            # 计算余弦相似度
            similarity = float(np.dot(target_embedding, candidate_embedding) / (
                np.linalg.norm(target_embedding) * np.linalg.norm(candidate_embedding)
            ))

            if similarity >= min_similarity:
                reasons = [f"与《{target_paper.title[:30]}...》相似（{similarity:.0%}）"]

                results.append(RecommendationResult(
                    paper_id=candidate.paper_id,
                    title=candidate.title,
                    score=similarity,
                    strategy="content_based",
                    reasons=reasons,
                    paper=candidate
                ))

        # 按相似度排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _recommend_similar_title_only(
        self,
        paper_id: str,
        limit: int
    ) -> List[RecommendationResult]:
        """基于标题的简单相似推荐（fallback）"""
        from .deduplicator import Deduplicator

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            if not row:
                return []

            target_paper = Paper(**dict(row))

            cursor.execute("""
                SELECT * FROM papers
                WHERE paper_id != ?
                  AND filtered_out = 0
                  AND title IS NOT NULL
                LIMIT 50
            """, (paper_id,))
            candidates = [Paper(**dict(row)) for row in cursor.fetchall()]

        dedup = Deduplicator()
        results = []

        for candidate in candidates:
            similarity = dedup.compute_title_similarity(target_paper.title, candidate.title)

            if similarity >= 0.3:  # 较低阈值
                results.append(RecommendationResult(
                    paper_id=candidate.paper_id,
                    title=candidate.title,
                    score=similarity,
                    strategy="content_based",
                    reasons=[f"标题相似（{similarity:.0%}）"],
                    paper=candidate
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def recommend_collaborative(
        self,
        limit: int = 10
    ) -> List[RecommendationResult]:
        """
        协同过滤推荐

        "喜欢你看过论文的用户还喜欢..."
        """
        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取当前用户喜欢的论文
            cursor.execute("""
                SELECT paper_id, MAX(interaction_score) as score
                FROM user_interactions
                WHERE user_id = ?
                  AND action_type IN ('favorite', 'share')
                GROUP BY paper_id
                ORDER BY score DESC
                LIMIT 10
            """, (self.user_id,))
            liked_papers = [row['paper_id'] for row in cursor.fetchall()]

            if not liked_papers:
                logger.info("No user history for collaborative filtering")
                return []

            # 找到喜欢相同论文的其他用户
            placeholders = ','.join(['?'] * len(liked_papers))
            cursor.execute(f"""
                SELECT DISTINCT user_id
                FROM user_interactions
                WHERE paper_id IN ({placeholders})
                  AND user_id != ?
                  AND action_type IN ('favorite', 'share')
            """, [*liked_papers, self.user_id])
            similar_users = [row['user_id'] for row in cursor.fetchall()]

            if not similar_users:
                logger.info("No similar users found")
                return []

            # 获取这些用户喜欢的其他论文
            user_placeholders = ','.join(['?'] * len(similar_users))
            paper_placeholders = ','.join(['?'] * len(liked_papers))
            cursor.execute(f"""
                SELECT
                    ui.paper_id,
                    p.title,
                    COUNT(*) as user_count,
                    AVG(ui.interaction_score) as avg_score
                FROM user_interactions ui
                JOIN papers p ON ui.paper_id = p.paper_id
                WHERE ui.user_id IN ({user_placeholders})
                  AND ui.paper_id NOT IN ({paper_placeholders})
                  AND ui.action_type IN ('favorite', 'share')
                  AND p.filtered_out = 0
                GROUP BY ui.paper_id
                ORDER BY user_count DESC, avg_score DESC
                LIMIT ?
            """, [*similar_users, *liked_papers, limit])

            results = []
            for row in cursor.fetchall():
                user_count = row['user_count']
                reasons = [f"{user_count}位相似用户也喜欢"]

                results.append(RecommendationResult(
                    paper_id=row['paper_id'],
                    title=row['title'],
                    score=row['avg_score'],
                    strategy="collaborative",
                    reasons=reasons
                ))

        return results

    def recommend_hybrid(
        self,
        week_id: Optional[str] = None,
        limit: int = 10
    ) -> List[RecommendationResult]:
        """
        混合推荐

        结合热门推荐、内容相似、协同过滤
        """
        # 获取用户交互数量
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM user_interactions
                WHERE user_id = ?
            """, (self.user_id,))
            row = cursor.fetchone()
            interaction_count = row['cnt'] if row else 0

        # 动态调整权重
        if interaction_count < self.config.NEW_USER_THRESHOLD:
            # 新用户：主要基于热门
            logger.info(f"New user ({interaction_count} interactions), using popular strategy")
            popular_results = self.recommend_popular(week_id, limit=limit * 2, exclude_seen=False)
            results = popular_results[:limit]
        elif interaction_count < self.config.ACTIVE_USER_THRESHOLD:
            # 中等用户：热门为主
            logger.info(f"Medium user ({interaction_count} interactions), using popular strategy")
            popular_results = self.recommend_popular(week_id, limit=limit, exclude_seen=True)
            results = popular_results
        else:
            # 老用户：协同过滤 + 热门
            logger.info(f"Active user ({interaction_count} interactions), using hybrid strategy")
            collaborative_results = self.recommend_collaborative(limit=limit // 2)
            popular_results = self.recommend_popular(week_id, limit=limit - len(collaborative_results), exclude_seen=True)
            results = collaborative_results + popular_results

        # 去重并按分数排序
        seen = set()
        unique_results = []
        for r in results:
            if r.paper_id not in seen:
                seen.add(r.paper_id)
                unique_results.append(r)

        unique_results.sort(key=lambda x: x.score, reverse=True)
        return unique_results[:limit]

    def save_recommendation(self, result: RecommendationResult):
        """保存推荐记录"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recommendations
                (user_id, paper_id, strategy, score, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.user_id,
                result.paper_id,
                result.strategy,
                result.score,
                json.dumps(result.reasons, ensure_ascii=False),
                now_iso()
            ))
            conn.commit()

    def track_interaction(
        self,
        paper_id: str,
        action_type: str,
        score: Optional[float] = None
    ):
        """记录用户交互"""
        if score is None:
            score = self.config.INTERACTION_WEIGHTS.get(action_type, 1.0)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_interactions
                (user_id, paper_id, action_type, interaction_score, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                self.user_id,
                paper_id,
                action_type,
                score,
                now_iso()
            ))
            conn.commit()

        logger.info(f"Tracked {action_type} for paper {paper_id} (score: {score})")


# 辅助函数
def record_view(paper_id: str, user_id: str = "default"):
    """记录查看行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "view")


def record_favorite(paper_id: str, user_id: str = "default"):
    """记录收藏行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "favorite")


def record_share(paper_id: str, user_id: str = "default"):
    """记录分享行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "share")
