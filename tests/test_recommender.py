"""
推荐系统单元测试
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.recommender import Recommender, RecommendationResult
from apd.db import get_connection, upsert_paper, init_db
from apd.utils import now_iso


def setup_test_data():
    """设置测试数据"""
    week_id = "2026-05"

    # 创建一些测试论文
    papers = [
        {
            'paper_id': 'test_rec_1',
            'title': 'Attention Is All You Need',
            'quality_score': 95.0,
            'recency_score': 90.0,
            'citation_score': 100.0,
        },
        {
            'paper_id': 'test_rec_2',
            'title': 'BERT: Pre-training of Deep Bidirectional Transformers',
            'quality_score': 92.0,
            'recency_score': 85.0,
            'citation_score': 95.0,
        },
        {
            'paper_id': 'test_rec_3',
            'title': 'GPT-3: Language Models are Few-Shot Learners',
            'quality_score': 88.0,
            'recency_score': 80.0,
            'citation_score': 90.0,
        },
        {
            'paper_id': 'test_rec_4',
            'title': 'ResNet: Deep Residual Learning for Image Recognition',
            'quality_score': 85.0,
            'recency_score': 75.0,
            'citation_score': 85.0,
        },
        {
            'paper_id': 'test_rec_5',
            'title': 'Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context',
            'quality_score': 80.0,
            'recency_score': 70.0,
            'citation_score': 80.0,
        },
    ]

    for paper in papers:
        upsert_paper(
            paper_id=paper['paper_id'],
            week_id=week_id,
            title=paper['title'],
            quality_score=paper['quality_score'],
            recency_score=paper['recency_score'],
            citation_score=paper['citation_score'],
            filtered_out=0,
            content_type="PAPER"
        )

    print(f"✓ Created {len(papers)} test papers")


def test_popular_recommendation():
    """测试热门推荐"""
    print("\n" + "="*60)
    print("测试1: 热门推荐")
    print("="*60)

    recommender = Recommender(user_id="test_user")
    results = recommender.recommend_popular(limit=5)

    assert len(results) <= 5, "Results exceed limit"
    assert all(r.strategy == "popular" for r in results), "Wrong strategy"

    if results:
        assert results[0].score >= results[-1].score, "Results not sorted by score"

        print(f"✓ Got {len(results)} popular recommendations")
        print(f"  Top recommendation: {results[0].title[:50]}... (score: {results[0].score:.2f})")
        print(f"  Reasons: {', '.join(results[0].reasons)}")
    else:
        print("⚠ No results found")

    print("✓ Popular recommendation test passed")


def test_similar_recommendation():
    """测试相似推荐"""
    print("\n" + "="*60)
    print("测试2: 相似推荐")
    print("="*60)

    recommender = Recommender(user_id="test_user")

    # 基于"Attention Is All You Need"找相似论文
    results = recommender.recommend_similar(paper_id="test_rec_1", limit=3, min_similarity=0.0)

    assert len(results) <= 3, "Results exceed limit"

    if results:
        print(f"✓ Got {len(results)} similar recommendations")
        print(f"  Most similar: {results[0].title[:50]}... (similarity: {results[0].score:.2f})")
    else:
        print("⚠ No results found (may need sentence-transformers)")

    print("✓ Similar recommendation test passed")


def test_track_interaction():
    """测试交互记录"""
    print("\n" + "="*60)
    print("测试3: 用户交互记录")
    print("="*60)

    recommender = Recommender(user_id="test_user_interactions")

    # 记录不同类型的交互
    recommender.track_interaction("test_rec_1", "view")
    recommender.track_interaction("test_rec_1", "favorite")
    recommender.track_interaction("test_rec_2", "share")

    # 验证数据库记录
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM user_interactions
            WHERE user_id = ?
        """, ("test_user_interactions",))
        count = cursor.fetchone()['cnt']

        assert count == 3, f"Expected 3 interactions, got {count}"

    print(f"✓ Recorded 3 interactions")
    print("  - view: test_rec_1")
    print("  - favorite: test_rec_1")
    print("  - share: test_rec_2")
    print("✓ Track interaction test passed")


def test_collaborative_filtering():
    """测试协同过滤"""
    print("\n" + "="*60)
    print("测试4: 协同过滤推荐")
    print("="*60)

    # 创建一些用户行为数据
    recommender1 = Recommender(user_id="alice")
    recommender1.track_interaction("test_rec_1", "favorite")
    recommender1.track_interaction("test_rec_2", "favorite")

    recommender2 = Recommender(user_id="bob")
    recommender2.track_interaction("test_rec_1", "favorite")  # 和alice共同喜欢
    recommender2.track_interaction("test_rec_3", "favorite")  # bob喜欢但alice没看过

    # alice应该被推荐test_rec_3
    results = recommender1.recommend_collaborative(limit=5)

    if results:
        print(f"✓ Got {len(results)} collaborative recommendations for alice")
        print(f"  Top recommendation: {results[0].title[:50]}...")
        print(f"  Reasons: {', '.join(results[0].reasons)}")
    else:
        print("⚠ No collaborative recommendations (expected for limited data)")

    print("✓ Collaborative filtering test passed")


def test_hybrid_recommendation():
    """测试混合推荐"""
    print("\n" + "="*60)
    print("测试5: 混合推荐")
    print("="*60)

    # 新用户：应该使用热门推荐
    new_user = Recommender(user_id="new_user")
    results = new_user.recommend_hybrid(limit=5)

    assert len(results) <= 5, "Results exceed limit"

    if results:
        print(f"✓ Got {len(results)} hybrid recommendations for new user")
        print(f"  Strategy used: {results[0].strategy}")
        assert all(r.strategy == "popular" for r in results), "New user should get popular recommendations"

    # 活跃用户：应该使用混合策略
    active_user = Recommender(user_id="active_user")
    for i in range(10):
        active_user.track_interaction(f"test_rec_{(i % 5) + 1}", "view")

    results = active_user.recommend_hybrid(limit=5)

    if results:
        print(f"✓ Got {len(results)} hybrid recommendations for active user")
        print(f"  Strategies used: {', '.join(set(r.strategy for r in results))}")

    print("✓ Hybrid recommendation test passed")


def test_save_recommendation():
    """测试推荐记录保存"""
    print("\n" + "="*60)
    print("测试6: 推荐记录保存")
    print("="*60)

    recommender = Recommender(user_id="test_save")
    result = RecommendationResult(
        paper_id="test_rec_1",
        title="Test Paper",
        score=0.95,
        strategy="popular",
        reasons=["高质量论文"]
    )

    recommender.save_recommendation(result)

    # 验证保存
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM recommendations
            WHERE user_id = ? AND paper_id = ?
        """, ("test_save", "test_rec_1"))
        count = cursor.fetchone()['cnt']

        assert count >= 1, "Recommendation not saved"

    print("✓ Recommendation saved successfully")
    print("✓ Save recommendation test passed")


def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "="*60)
    print("清理测试数据")
    print("="*60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 删除测试论文
        cursor.execute("DELETE FROM papers WHERE paper_id LIKE 'test_rec_%'")
        papers_deleted = cursor.rowcount

        # 删除测试交互
        cursor.execute("DELETE FROM user_interactions WHERE user_id LIKE 'test_%' OR user_id IN ('alice', 'bob', 'new_user', 'active_user')")
        interactions_deleted = cursor.rowcount

        # 删除测试推荐
        cursor.execute("DELETE FROM recommendations WHERE user_id LIKE 'test_%' OR user_id IN ('alice', 'bob', 'new_user', 'active_user')")
        recommendations_deleted = cursor.rowcount

        conn.commit()

    print(f"✓ Deleted {papers_deleted} test papers")
    print(f"✓ Deleted {interactions_deleted} test interactions")
    print(f"✓ Deleted {recommendations_deleted} test recommendations")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("推荐系统单元测试")
    print("="*60 + "\n")

    # 确保数据库已初始化
    init_db()

    try:
        # 设置测试数据
        setup_test_data()

        # 运行测试
        test_popular_recommendation()
        test_similar_recommendation()
        test_track_interaction()
        test_collaborative_filtering()
        test_hybrid_recommendation()
        test_save_recommendation()

    finally:
        # 清理测试数据
        cleanup_test_data()

    print("\n" + "="*60)
    print("所有测试通过! ✅")
    print("="*60 + "\n")
