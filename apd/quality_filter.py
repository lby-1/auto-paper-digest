"""
质量评分系统

为论文、GitHub项目和新闻内容提供质量评分。
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """质量评分结果"""
    total_score: float  # 0-100
    citation_score: float = 0.0
    venue_score: float = 0.0
    recency_score: float = 0.0
    reasons: list = field(default_factory=list)
    passed: bool = True


class QualityFilter:
    """内容质量评分器"""

    def __init__(self, config=None):
        # 延迟导入以避免循环依赖
        if config is None:
            from .config import QualityConfig
            config = QualityConfig
        self.config = config

    def evaluate_paper(
        self,
        title: str,
        pdf_url: Optional[str] = None,
        hf_url: Optional[str] = None,
        **kwargs
    ) -> QualityScore:
        """
        评估论文质量

        基于以下维度:
        - 标题长度和完整性(基础)
        - URL有效性
        - 时效性(基于arXiv ID中的日期)
        """
        reasons = []
        scores = {
            "citation": 0.0,
            "venue": 50.0,  # 默认中等分
            "recency": 0.0,
        }

        # 基础检查:标题
        if not title or len(title) < 10:
            reasons.append("标题过短或缺失")
            return QualityScore(
                total_score=0.0,
                reasons=reasons,
                passed=False
            )

        # URL有效性检查
        if not pdf_url and not hf_url:
            reasons.append("缺少PDF或HF链接")
            scores["venue"] = 30.0
        else:
            reasons.append("有效的论文链接")
            scores["venue"] = 60.0

        # 时效性评分(基于arXiv ID)
        if pdf_url and "arxiv.org" in pdf_url:
            try:
                # 提取arXiv ID中的年月信息 (YYMM.XXXXX)
                arxiv_id = pdf_url.split("/")[-1].replace(".pdf", "")
                year_month = arxiv_id.split(".")[0]

                # 计算距今的月数
                current_year = datetime.now().year % 100
                current_month = datetime.now().month

                paper_year = int(year_month[:2])
                paper_month = int(year_month[2:])

                months_ago = (current_year - paper_year) * 12 + (current_month - paper_month)

                # 时效性评分:0-6个月=100分,每月递减5分
                recency = max(0, 100 - months_ago * 5)
                scores["recency"] = recency

                if months_ago <= 6:
                    reasons.append(f"近期论文({months_ago}个月前)")
                else:
                    reasons.append(f"较早论文({months_ago}个月前)")
            except Exception as e:
                logger.debug(f"Failed to parse arXiv date: {e}")
                scores["recency"] = 50.0
        else:
            scores["recency"] = 50.0  # 默认分

        # 标题质量加分
        if len(title) > 50:
            scores["venue"] += 10
            reasons.append("详细的标题")

        # 综合评分
        total_score = (
            scores["citation"] * self.config.CITATION_WEIGHT +
            scores["venue"] * self.config.VENUE_WEIGHT +
            scores["recency"] * self.config.RECENCY_WEIGHT +
            50 * self.config.AUTHOR_WEIGHT  # 默认作者分
        )

        passed = total_score >= self.config.MIN_QUALITY_SCORE

        return QualityScore(
            total_score=total_score,
            citation_score=scores["citation"],
            venue_score=scores["venue"],
            recency_score=scores["recency"],
            reasons=reasons,
            passed=passed
        )

    def evaluate_github_project(
        self,
        name: str,
        stars: int,
        language: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> QualityScore:
        """
        评估GitHub项目质量

        基于:
        - Stars数量(主要指标)
        - 编程语言热度
        - 描述完整性
        """
        reasons = []

        # Stars评分(对数尺度)
        if stars < self.config.MIN_GITHUB_STARS:
            reasons.append(f"Stars过低({stars} < {self.config.MIN_GITHUB_STARS})")
            return QualityScore(
                total_score=0.0,
                reasons=reasons,
                passed=False
            )

        # 对数评分:100 stars=50分,10000 stars=100分
        import math
        stars_score = min(100, 50 + 10 * math.log10(max(stars / 100, 0.1)))
        reasons.append(f"Stars: {stars}(评分: {stars_score:.1f})")

        # 编程语言评分
        language_scores = {
            "Python": 100,
            "JavaScript": 95,
            "TypeScript": 95,
            "Go": 90,
            "Rust": 90,
            "Java": 85,
            "C++": 85,
            "C": 80,
        }
        language_score = language_scores.get(language, 70)
        reasons.append(f"语言: {language}(评分: {language_score})")

        # 描述完整性
        desc_score = 100 if (description and len(description) > 20) else 50
        if description and len(description) > 20:
            reasons.append("有详细描述")

        # 综合评分
        total_score = (
            stars_score * self.config.GITHUB_STARS_WEIGHT +
            language_score * self.config.GITHUB_LANGUAGE_WEIGHT +
            desc_score * self.config.GITHUB_ACTIVITY_WEIGHT
        )

        passed = total_score >= self.config.MIN_QUALITY_SCORE

        return QualityScore(
            total_score=total_score,
            citation_score=stars_score,
            venue_score=language_score,
            recency_score=desc_score,
            reasons=reasons,
            passed=passed
        )

    def evaluate_news(
        self,
        title: str,
        rank: int,
        source: str,
        hot_value: Optional[str] = None,
        **kwargs
    ) -> QualityScore:
        """
        评估新闻质量

        基于:
        - 排名(越靠前越好)
        - 来源可信度
        - 热度值
        """
        reasons = []

        # 排名评分:排名1-10=100分,11-20=80分,21-50=60分
        if rank <= 10:
            rank_score = 100
            reasons.append(f"热榜Top 10(第{rank}名)")
        elif rank <= 20:
            rank_score = 80
            reasons.append(f"热榜Top 20(第{rank}名)")
        elif rank <= 50:
            rank_score = 60
            reasons.append(f"热榜Top 50(第{rank}名)")
        else:
            rank_score = max(0, 100 - rank)
            reasons.append(f"热榜第{rank}名")

        # 来源评分
        source_score = self.config.SOURCE_WEIGHTS.get(source, 0.7) * 100
        reasons.append(f"来源: {source}(权重: {source_score/100:.1f})")

        # 综合评分
        total_score = (
            rank_score * self.config.NEWS_RANK_WEIGHT +
            source_score * self.config.NEWS_SOURCE_WEIGHT
        )

        passed = total_score >= self.config.MIN_QUALITY_SCORE

        return QualityScore(
            total_score=total_score,
            citation_score=rank_score,
            venue_score=source_score,
            recency_score=100.0,  # 新闻都是最新的
            reasons=reasons,
            passed=passed
        )

    def evaluate_content(
        self,
        content_type: str,
        **kwargs
    ) -> QualityScore:
        """
        统一评分接口

        根据content_type自动选择评分方法
        """
        if content_type == "PAPER":
            return self.evaluate_paper(**kwargs)
        elif content_type == "GITHUB":
            return self.evaluate_github_project(**kwargs)
        elif content_type == "NEWS":
            return self.evaluate_news(**kwargs)
        else:
            logger.warning(f"Unknown content_type: {content_type}")
            return QualityScore(total_score=50.0, reasons=["未知内容类型"])
