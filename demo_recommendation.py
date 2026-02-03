"""
推荐系统演示脚本

展示推荐系统的各种功能
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.recommender import Recommender
from apd.db import get_connection, upsert_paper, init_db
from apd.utils import now_iso


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def setup_demo_data():
    """设置演示数据"""
    week_id = "2026-05"

    # 创建更丰富的测试数据
    papers = [
        {
            'paper_id': 'demo_paper_1',
            'title': 'Attention Is All You Need',
            'summary': 'We propose the Transformer, a new simple network architecture based solely on attention mechanisms.',
            'quality_score': 95.0,
            'recency_score': 85.0,
            'citation_score': 100.0,
        },
        {
            'paper_id': 'demo_paper_2',
            'title': 'BERT: Pre-training of Deep Bidirectional Transformers',
            'summary': 'We introduce BERT, which stands for Bidirectional Encoder Representations from Transformers.',
            'quality_score': 92.0,
            'recency_score': 80.0,
            'citation_score': 95.0,
        },
        {
            'paper_id': 'demo_paper_3',
            'title': 'GPT-3: Language Models are Few-Shot Learners',
            'summary': 'We show that scaling up language models greatly improves task-agnostic, few-shot performance.',
            'quality_score': 90.0,
            'recency_score': 90.0,
            'citation_score': 90.0,
        },
        {
            'paper_id': 'demo_paper_4',
            'title': 'ResNet: Deep Residual Learning for Image Recognition',
            'summary': 'We present a residual learning framework to ease the training of networks that are substantially deeper.',
            'quality_score': 88.0,
            'recency_score': 70.0,
            'citation_score': 100.0,
        },
        {
            'paper_id': 'demo_paper_5',
            'title': 'Transformer-XL: Attentive Language Models Beyond a Fixed-Length Context',
            'summary': 'We propose Transformer-XL, a Transformer architecture that learns dependency beyond a fixed length.',
            'quality_score': 85.0,
            'recency_score': 75.0,
            'citation_score': 80.0,
        },
        {
            'paper_id': 'demo_paper_6',
            'title': 'EfficientNet: Rethinking Model Scaling for CNNs',
            'summary': 'We systematically study model scaling and propose a new scaling method called compound scaling.',
            'quality_score': 82.0,
            'recency_score': 75.0,
            'citation_score': 85.0,
        },
        {
            'paper_id': 'demo_paper_7',
            'title': 'CLIP: Learning Transferable Visual Models From Natural Language Supervision',
            'summary': 'We demonstrate that the simple pre-training task of predicting which caption goes with which image.',
            'quality_score': 88.0,
            'recency_score': 85.0,
            'citation_score': 88.0,
        },
        {
            'paper_id': 'demo_paper_8',
            'title': 'AlphaFold: Improved protein structure prediction',
            'summary': 'AlphaFold produces protein structure predictions that are accurate enough for practical use.',
            'quality_score': 98.0,
            'recency_score': 80.0,
            'citation_score': 95.0,
        },
    ]

    for paper in papers:
        upsert_paper(
            paper_id=paper['paper_id'],
            week_id=week_id,
            title=paper['title'],
            summary=paper.get('summary'),
            quality_score=paper['quality_score'],
            recency_score=paper['recency_score'],
            citation_score=paper['citation_score'],
            filtered_out=0,
            content_type="PAPER"
        )

    print(f"✓ 创建了 {len(papers)} 篇演示论文")


def demo_popular_recommendation():
    """演示1: 热门推荐"""
    print_header("Demo 1: 热门推荐")

    recommender = Recommender(user_id="demo_user")
    results = recommender.recommend_popular(limit=5)

    print(f"\n📈 基于质量评分、时效性和引用数的热门推荐:")
    print(f"\n{'#':<3} {'评分':<6} {'标题':<50}")
    print("-" * 70)

    for i, result in enumerate(results, 1):
        title = result.title[:47] + "..." if len(result.title) > 50 else result.title
        print(f"{i:<3} {result.score:<6.2f} {title}")
        if result.reasons:
            print(f"     💡 {' | '.join(result.reasons)}")


def demo_similar_recommendation():
    """演示2: 相似推荐"""
    print_header("Demo 2: 相似论文推荐")

    base_paper_title = "Attention Is All You Need"
    print(f"\n🔍 寻找与《{base_paper_title}》相似的论文:\n")

    recommender = Recommender(user_id="demo_user")
    try:
        results = recommender.recommend_similar(
            paper_id="demo_paper_1",
            limit=3,
            min_similarity=0.0  # 降低阈值以便演示
        )

        if results:
            print(f"{'#':<3} {'相似度':<8} {'标题':<50}")
            print("-" * 70)

            for i, result in enumerate(results, 1):
                title = result.title[:47] + "..." if len(result.title) > 50 else result.title
                print(f"{i:<3} {result.score:<8.2f} {title}")
                if result.reasons:
                    print(f"     💡 {' | '.join(result.reasons)}")
        else:
            print("⚠ 未找到相似论文（可能是因为缺少 sentence-transformers 库）")
            print("  可以通过以下命令安装: pip install sentence-transformers")
    except Exception as e:
        print(f"⚠ 相似度计算失败: {e}")
        print("  提示: 安装 sentence-transformers 以启用语义相似度功能")


def demo_user_interactions():
    """演示3: 用户交互追踪"""
    print_header("Demo 3: 用户交互追踪")

    recommender = Recommender(user_id="alice")

    print("\n📊 模拟用户 Alice 的行为:\n")

    # Alice 查看了几篇论文
    papers_viewed = [
        ("demo_paper_1", "Attention Is All You Need"),
        ("demo_paper_2", "BERT: Pre-training of Deep Bidirectional Transformers"),
        ("demo_paper_3", "GPT-3: Language Models are Few-Shot Learners"),
    ]

    for paper_id, title in papers_viewed:
        recommender.track_interaction(paper_id, "view")
        print(f"  👀 查看: {title[:50]}...")

    # Alice 收藏了一些论文
    papers_favorited = [
        ("demo_paper_1", "Attention Is All You Need"),
        ("demo_paper_3", "GPT-3: Language Models are Few-Shot Learners"),
    ]

    print()
    for paper_id, title in papers_favorited:
        recommender.track_interaction(paper_id, "favorite")
        print(f"  ⭐ 收藏: {title[:50]}...")

    # Alice 分享了一篇论文
    print()
    recommender.track_interaction("demo_paper_3", "share")
    print(f"  📤 分享: GPT-3: Language Models are Few-Shot Learners")

    # 统计交互数据
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT action_type, COUNT(*) as cnt, SUM(interaction_score) as total_score
            FROM user_interactions
            WHERE user_id = 'alice'
            GROUP BY action_type
        """, ())
        stats = cursor.fetchall()

    print("\n📈 Alice 的交互统计:")
    for row in stats:
        print(f"  - {row['action_type']}: {row['cnt']} 次 (总分: {row['total_score']:.1f})")


def demo_collaborative_filtering():
    """演示4: 协同过滤"""
    print_header("Demo 4: 协同过滤推荐")

    # 创建另一个用户 Bob，他和 Alice 有相似的兴趣
    bob = Recommender(user_id="bob")
    bob.track_interaction("demo_paper_1", "favorite")  # 和 Alice 共同喜欢
    bob.track_interaction("demo_paper_3", "favorite")  # 和 Alice 共同喜欢
    bob.track_interaction("demo_paper_5", "favorite")  # Bob 喜欢但 Alice 还没看过

    print("\n👥 用户 Bob 也喜欢:")
    print("  ⭐ Attention Is All You Need")
    print("  ⭐ GPT-3: Language Models are Few-Shot Learners")
    print("  ⭐ Transformer-XL (Alice 还没看过)")

    print("\n🎯 为 Alice 生成协同过滤推荐:")

    alice = Recommender(user_id="alice")
    results = alice.recommend_collaborative(limit=3)

    if results:
        print(f"\n{'#':<3} {'评分':<6} {'标题':<50}")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            print(f"{i:<3} {result.score:<6.2f} {title}")
            if result.reasons:
                print(f"     💡 {' | '.join(result.reasons)}")
    else:
        print("  ⚠ 暂无协同过滤推荐（需要更多用户行为数据）")


def demo_hybrid_recommendation():
    """演示5: 混合推荐"""
    print_header("Demo 5: 混合推荐策略")

    print("\n🆕 新用户 Charlie（无历史记录）:")
    charlie = Recommender(user_id="charlie")
    results = charlie.recommend_hybrid(limit=3)

    if results:
        print(f"\n策略: 热门推荐（新用户）")
        print(f"{'#':<3} {'评分':<6} {'标题':<50}")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.title[:47] + "..." if len(result.title) > 50 else result.title
            print(f"{i:<3} {result.score:<6.2f} {title}")

    print("\n\n👤 活跃用户 Alice（有丰富历史记录）:")
    alice = Recommender(user_id="alice")
    results = alice.recommend_hybrid(limit=3)

    if results:
        strategies = set(r.strategy for r in results)
        print(f"\n策略: {', '.join(strategies)} (活跃用户)")
        print(f"{'#':<3} {'评分':<6} {'策略':<15} {'标题':<40}")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.title[:37] + "..." if len(result.title) > 40 else result.title
            print(f"{i:<3} {result.score:<6.2f} {result.strategy:<15} {title}")


def demo_statistics():
    """演示6: 推荐系统统计"""
    print_header("Demo 6: 推荐系统统计")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 总交互数
        cursor.execute("SELECT COUNT(*) as cnt FROM user_interactions")
        total_interactions = cursor.fetchone()['cnt']

        # 独立用户数
        cursor.execute("SELECT COUNT(DISTINCT user_id) as cnt FROM user_interactions")
        unique_users = cursor.fetchone()['cnt']

        # 总推荐数
        cursor.execute("SELECT COUNT(*) as cnt FROM recommendations")
        total_recommendations = cursor.fetchone()['cnt']

        # 推荐策略分布
        cursor.execute("""
            SELECT strategy, COUNT(*) as cnt
            FROM recommendations
            GROUP BY strategy
        """)
        strategy_stats = cursor.fetchall()

        # 最热门的论文
        cursor.execute("""
            SELECT p.paper_id, p.title, COUNT(*) as interaction_count
            FROM user_interactions ui
            JOIN papers p ON ui.paper_id = p.paper_id
            GROUP BY p.paper_id
            ORDER BY interaction_count DESC
            LIMIT 3
        """)
        hot_papers = cursor.fetchall()

    print(f"\n📊 推荐系统总体统计:")
    print(f"  总交互数: {total_interactions}")
    print(f"  独立用户: {unique_users}")
    print(f"  总推荐数: {total_recommendations}")

    if strategy_stats:
        print(f"\n📈 推荐策略分布:")
        for row in strategy_stats:
            print(f"  - {row['strategy']}: {row['cnt']} 次")

    if hot_papers:
        print(f"\n🔥 最热门论文:")
        for i, row in enumerate(hot_papers, 1):
            title = row['title'][:50] + "..." if len(row['title']) > 50 else row['title']
            print(f"  {i}. {title} ({row['interaction_count']} 次交互)")


def cleanup_demo_data():
    """清理演示数据"""
    print_header("清理演示数据")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM papers WHERE paper_id LIKE 'demo_paper_%'")
        papers_deleted = cursor.rowcount

        cursor.execute("DELETE FROM user_interactions WHERE user_id IN ('demo_user', 'alice', 'bob', 'charlie')")
        interactions_deleted = cursor.rowcount

        cursor.execute("DELETE FROM recommendations WHERE user_id IN ('demo_user', 'alice', 'bob', 'charlie')")
        recommendations_deleted = cursor.rowcount

        conn.commit()

    print(f"\n✅ 已删除:")
    print(f"  - {papers_deleted} 篇演示论文")
    print(f"  - {interactions_deleted} 条交互记录")
    print(f"  - {recommendations_deleted} 条推荐记录")


def main():
    print("\n" + "=" * 70)
    print("  智能推荐系统演示")
    print("=" * 70)

    # 确保数据库已初始化
    init_db()

    try:
        # 设置演示数据
        setup_demo_data()

        # 运行各个演示
        demo_popular_recommendation()
        demo_similar_recommendation()
        demo_user_interactions()
        demo_collaborative_filtering()
        demo_hybrid_recommendation()
        demo_statistics()

    finally:
        # 清理演示数据
        cleanup_demo_data()

    print("\n" + "=" * 70)
    print("  演示完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
