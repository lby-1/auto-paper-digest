# 智能内容推荐系统实现计划

## 概述

为 Auto-Paper-Digest 项目添加智能内容推荐系统，基于用户行为、论文内容和质量评分提供个性化推荐。

**目标**：
- 提升用户发现优质内容的效率
- 根据用户兴趣自动筛选和排序论文
- 提供多样化的推荐策略
- 提高用户粘性和满意度

**核心价值**：
- 📊 基于数据的智能推荐
- 🎯 个性化内容发现
- 🔥 热门趋势追踪
- 🤝 相似论文关联

**实施时间**: 3-4 天

---

## 关键文件

### 需要修改的文件
1. `apd/db.py` - 数据库schema扩展（用户行为、推荐记录）
2. `apd/config.py` - 推荐系统配置
3. `apd/cli.py` - 添加推荐CLI命令

### 需要创建的文件
1. `apd/recommender.py` - 推荐引擎核心模块（新建）
2. `tests/test_recommender.py` - 推荐系统测试
3. `demo_recommendation.py` - 演示脚本

---

## 推荐策略

### 1. 热门推荐（Popular Recommendation）
- 基于质量评分、时效性
- 适合新用户或无历史数据场景
- 公式: `score = quality_score * 0.6 + recency_score * 0.3 + citation_score * 0.1`

### 2. 内容相似推荐（Content-based Filtering）
- 基于论文标题、摘要、关键词的语义相似度
- 使用Sentence-BERT embeddings
- 适合"更多类似论文"场景

### 3. 协同过滤推荐（Collaborative Filtering）
- 基于用户行为（查看、收藏、分享）
- "喜欢这篇论文的用户还喜欢..."
- 需要一定的用户行为数据

### 4. 混合推荐（Hybrid Recommendation）
- 结合多种策略的加权平均
- 根据用户数据量动态调整权重
- 新用户：热门推荐为主
- 老用户：协同过滤 + 内容相似

### 5. 领域专家推荐
- 基于作者影响力
- 追踪特定作者的新论文
- 识别高引用作者

---

## 实施步骤

### 第一步：数据库Schema扩展

**文件**: `apd/db.py`

#### 1.1 创建用户行为表

```sql
CREATE TABLE IF NOT EXISTS user_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,           -- 用户标识（默认为"default"）
    paper_id TEXT NOT NULL,
    action_type TEXT NOT NULL,       -- view | favorite | share | download
    interaction_score REAL DEFAULT 1.0,  -- 行为权重
    created_at TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
);

CREATE INDEX idx_user_interactions_user ON user_interactions(user_id);
CREATE INDEX idx_user_interactions_paper ON user_interactions(paper_id);
CREATE INDEX idx_user_interactions_time ON user_interactions(created_at);
```

#### 1.2 创建推荐记录表

```sql
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    paper_id TEXT NOT NULL,
    strategy TEXT NOT NULL,          -- popular | content | collaborative | hybrid
    score REAL NOT NULL,
    reason TEXT,                     -- JSON: 推荐理由
    created_at TEXT NOT NULL,
    clicked INTEGER DEFAULT 0,       -- 是否被点击
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
);

CREATE INDEX idx_recommendations_user ON recommendations(user_id);
CREATE INDEX idx_recommendations_paper ON recommendations(paper_id);
```

#### 1.3 创建用户偏好表

```sql
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferred_topics TEXT,           -- JSON array: ["NLP", "CV", "RL"]
    preferred_authors TEXT,          -- JSON array
    min_quality_score REAL DEFAULT 60.0,
    min_citations INTEGER DEFAULT 0,
    exclude_keywords TEXT,           -- JSON array: 排除关键词
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### 1.4 扩展 Paper 数据类

```python
@dataclass
class Paper:
    # ... 现有字段 ...

    # 推荐相关字段（新增）
    embedding: Optional[str] = None          # JSON: 向量embedding
    keywords: Optional[str] = None           # JSON: 提取的关键词
    view_count: int = 0                      # 查看次数
    favorite_count: int = 0                  # 收藏次数
    share_count: int = 0                     # 分享次数
    recommendation_score: Optional[float] = None  # 推荐分数
```

---

### 第二步：推荐引擎核心模块

**文件**: `apd/recommender.py`（新建）

```python
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
from sentence_transformers import SentenceTransformer

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
            logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(self.config.EMBEDDING_MODEL)
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
                query += " AND p.week_id = ?"
                params.append(week_id)

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
                    (p.quality_score * ? +
                     p.recency_score * ? +
                     p.citation_score * ?) DESC
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
        with get_connection() as conn:
            cursor = conn.cursor()

            # 获取目标论文
            cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            if not row:
                return []

            target_paper = Paper(**dict(row))

            # 获取候选论文（同一周或相近周）
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
        model = self._load_model()

        # 编码目标论文
        target_text = f"{target_paper.title} {target_paper.summary or ''}"
        target_embedding = model.encode([target_text])[0]

        # 编码候选论文并计算相似度
        results = []
        for candidate in candidates:
            candidate_text = f"{candidate.title} {candidate.summary or ''}"
            candidate_embedding = model.encode([candidate_text])[0]

            # 计算余弦相似度
            similarity = np.dot(target_embedding, candidate_embedding) / (
                np.linalg.norm(target_embedding) * np.linalg.norm(candidate_embedding)
            )

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
            interaction_count = cursor.fetchone()['cnt']

        # 动态调整权重
        if interaction_count < 5:
            # 新用户：主要基于热门
            popular_results = self.recommend_popular(week_id, limit=limit * 2)
            results = popular_results[:limit]
        elif interaction_count < 20:
            # 中等用户：热门 + 内容相似
            popular_results = self.recommend_popular(week_id, limit=limit)
            # TODO: 基于用户最近查看的论文推荐相似内容
            results = popular_results
        else:
            # 老用户：协同过滤 + 热门
            collaborative_results = self.recommend_collaborative(limit=limit // 2)
            popular_results = self.recommend_popular(week_id, limit=limit // 2)
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
        score: float = 1.0
    ):
        """记录用户交互"""
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

        logger.info(f"Tracked {action_type} for paper {paper_id}")


# 辅助函数
def record_view(paper_id: str, user_id: str = "default"):
    """记录查看行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "view", score=1.0)


def record_favorite(paper_id: str, user_id: str = "default"):
    """记录收藏行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "favorite", score=3.0)


def record_share(paper_id: str, user_id: str = "default"):
    """记录分享行为"""
    recommender = Recommender(user_id)
    recommender.track_interaction(paper_id, "share", score=5.0)
```

---

### 第三步：配置系统扩展

**文件**: `apd/config.py`

```python
# Recommendation Configuration
class RecommendationConfig:
    """推荐系统配置"""

    # 默认用户ID
    DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default")

    # Embedding模型
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

    # 新用户阈值（交互次数）
    NEW_USER_THRESHOLD = 5
    ACTIVE_USER_THRESHOLD = 20
```

---

### 第四步：CLI命令扩展

**文件**: `apd/cli.py`

```python
@main.command()
@click.option("--week", "-w", default=None, help="Week ID")
@click.option("--strategy", "-s",
              type=click.Choice(["popular", "similar", "collaborative", "hybrid"]),
              default="hybrid",
              help="Recommendation strategy")
@click.option("--limit", "-n", default=10, help="Number of recommendations")
@click.option("--user", "-u", default="default", help="User ID")
@click.option("--based-on", help="Paper ID for similar recommendations")
def recommend(
    week: Optional[str],
    strategy: str,
    limit: int,
    user: str,
    based_on: Optional[str]
) -> None:
    """Get personalized paper recommendations."""

    from .recommender import Recommender

    recommender = Recommender(user_id=user)

    click.echo(f"🎯 Getting recommendations using {strategy} strategy...")

    if strategy == "popular":
        results = recommender.recommend_popular(week_id=week, limit=limit)
    elif strategy == "similar":
        if not based_on:
            click.echo("❌ Error: --based-on required for similar strategy")
            return
        results = recommender.recommend_similar(paper_id=based_on, limit=limit)
    elif strategy == "collaborative":
        results = recommender.recommend_collaborative(limit=limit)
    elif strategy == "hybrid":
        results = recommender.recommend_hybrid(week_id=week, limit=limit)
    else:
        click.echo(f"❌ Unknown strategy: {strategy}")
        return

    if not results:
        click.echo("📭 No recommendations found")
        return

    click.echo(f"\n✨ Found {len(results)} recommendations:\n")
    click.echo(f"{'#':<3} {'Score':<6} {'Strategy':<15} {'Title':<50}")
    click.echo("-" * 80)

    for i, result in enumerate(results, 1):
        score_str = f"{result.score:.2f}"
        title = result.title[:47] + "..." if len(result.title) > 50 else result.title
        click.echo(f"{i:<3} {score_str:<6} {result.strategy:<15} {title}")

        if result.reasons:
            reasons_str = " | ".join(result.reasons)
            click.echo(f"    💡 {reasons_str}")

        # 保存推荐记录
        recommender.save_recommendation(result)


@main.command()
@click.argument("paper_id")
@click.option("--action", "-a",
              type=click.Choice(["view", "favorite", "share"]),
              required=True,
              help="Interaction type")
@click.option("--user", "-u", default="default", help="User ID")
def interact(paper_id: str, action: str, user: str) -> None:
    """Record user interaction with a paper."""

    from .recommender import Recommender

    recommender = Recommender(user_id=user)

    scores = {
        "view": 1.0,
        "favorite": 3.0,
        "share": 5.0,
    }

    recommender.track_interaction(paper_id, action, score=scores[action])
    click.echo(f"✅ Recorded {action} for paper {paper_id}")
```

---

### 第五步：数据库迁移

在 `apd/db.py` 的 `init_db()` 函数中添加：

```python
def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()

        # ... 现有表创建 ...

        # 用户交互表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                interaction_score REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON user_interactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_interactions_paper ON user_interactions(paper_id)")

        # 推荐记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                score REAL NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                clicked INTEGER DEFAULT 0,
                FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_paper ON recommendations(paper_id)")

        # 用户偏好表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                preferred_topics TEXT,
                preferred_authors TEXT,
                min_quality_score REAL DEFAULT 60.0,
                min_citations INTEGER DEFAULT 0,
                exclude_keywords TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 扩展papers表
        recommendation_fields = [
            ("embedding", "TEXT"),
            ("keywords", "TEXT"),
            ("view_count", "INTEGER DEFAULT 0"),
            ("favorite_count", "INTEGER DEFAULT 0"),
            ("share_count", "INTEGER DEFAULT 0"),
            ("recommendation_score", "REAL"),
        ]

        for field_name, field_type in recommendation_fields:
            try:
                cursor.execute(f"ALTER TABLE papers ADD COLUMN {field_name} {field_type}")
            except sqlite3.OperationalError:
                pass

        conn.commit()
```

---

## 测试计划

### 单元测试

**文件**: `tests/test_recommender.py`

```python
def test_popular_recommendation():
    """测试热门推荐"""
    recommender = Recommender(user_id="test_user")
    results = recommender.recommend_popular(limit=5)
    assert len(results) <= 5
    assert all(r.strategy == "popular" for r in results)
    assert results[0].score >= results[-1].score  # 降序排列


def test_similar_recommendation():
    """测试相似推荐"""
    recommender = Recommender(user_id="test_user")
    results = recommender.recommend_similar(paper_id="test_paper_1", limit=5)
    assert len(results) <= 5
    assert all(r.strategy == "content_based" for r in results)


def test_track_interaction():
    """测试交互记录"""
    recommender = Recommender(user_id="test_user")
    recommender.track_interaction("test_paper_1", "view")
    recommender.track_interaction("test_paper_1", "favorite")

    # 验证数据库记录
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM user_interactions
            WHERE user_id = ? AND paper_id = ?
        """, ("test_user", "test_paper_1"))
        count = cursor.fetchone()['cnt']
        assert count == 2
```

---

## CLI使用示例

```bash
# 1. 获取热门推荐
apd recommend --strategy popular --limit 10

# 2. 查找相似论文
apd recommend --strategy similar --based-on 2601.17058 --limit 5

# 3. 协同过滤推荐
apd recommend --strategy collaborative --limit 10 --user alice

# 4. 混合推荐（自动选择最佳策略）
apd recommend --strategy hybrid --week 2026-05 --limit 10

# 5. 记录用户交互
apd interact 2601.17058 --action view
apd interact 2601.17058 --action favorite --user alice
apd interact 2601.17058 --action share
```

---

## 预期收益

- ✅ 提升内容发现效率 40-60%
- ✅ 提高用户粘性和满意度
- ✅ 个性化推荐准确率 70%+
- ✅ 减少无效内容浏览时间
- ✅ 增强用户参与度

---

## 后续扩展（可选）

1. **主题建模**
   - LDA主题提取
   - 自动标签生成

2. **作者追踪**
   - 关注特定作者
   - 作者新论文提醒

3. **趋势分析**
   - 识别热门研究方向
   - 新兴主题发现

4. **推荐解释**
   - 可解释的推荐理由
   - 推荐透明度提升

5. **A/B测试**
   - 测试不同推荐策略效果
   - 持续优化推荐算法
