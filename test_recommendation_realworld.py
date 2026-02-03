"""
推荐系统真实场景测试

使用真实数据库中的论文测试推荐功能
"""

import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.recommender import Recommender
from apd.db import get_connection, upsert_paper
from apd.utils import now_iso


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_with_real_data():
    """测试真实数据库中的论文"""
    print_header("场景1: 使用真实论文数据测试")

    # 获取真实论文
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paper_id, title, quality_score, filtered_out
            FROM papers
            WHERE week_id LIKE '%2026-05%'
            LIMIT 10
        """)
        real_papers = cursor.fetchall()

    print(f"\n📊 数据库中的论文状态:")
    print(f"  总论文数: {len(real_papers)}")

    filtered_count = sum(1 for p in real_papers if p['filtered_out'])
    print(f"  已过滤: {filtered_count}")
    print(f"  可推荐: {len(real_papers) - filtered_count}")

    if filtered_count == len(real_papers):
        print(f"\n⚠️ 所有论文都被质量控制系统过滤了")
        print(f"  原因: 质量评分 < 60.0（默认阈值）")
        print(f"  解决方案:")
        print(f"    1. 降低质量阈值: 修改 .env 中的 MIN_QUALITY_SCORE")
        print(f"    2. 重新评分: 使用更好的质量评估策略")
        print(f"    3. 测试用被过滤论文: 修改推荐查询条件")


def test_create_high_quality_papers():
    """创建一些高质量论文用于测试"""
    print_header("场景2: 创建高质量测试论文")

    week_id = "2026-05"

    test_papers = [
        {
            'paper_id': 'test_real_1',
            'title': 'Multimodal Large Language Models: A Survey',
            'summary': 'A comprehensive survey of multimodal large language models.',
            'quality_score': 92.0,
            'recency_score': 95.0,
            'citation_score': 88.0,
        },
        {
            'paper_id': 'test_real_2',
            'title': 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models',
            'summary': 'We explore how generating a chain of thought can improve reasoning.',
            'quality_score': 95.0,
            'recency_score': 90.0,
            'citation_score': 100.0,
        },
        {
            'paper_id': 'test_real_3',
            'title': 'LLaMA: Open and Efficient Foundation Language Models',
            'summary': 'We introduce LLaMA, a collection of foundation language models.',
            'quality_score': 90.0,
            'recency_score': 85.0,
            'citation_score': 95.0,
        },
        {
            'paper_id': 'test_real_4',
            'title': 'Diffusion Models Beat GANs on Image Synthesis',
            'summary': 'We show that diffusion models can achieve better image generation quality.',
            'quality_score': 88.0,
            'recency_score': 80.0,
            'citation_score': 90.0,
        },
        {
            'paper_id': 'test_real_5',
            'title': 'InstructGPT: Training language models to follow instructions',
            'summary': 'We fine-tune GPT-3 to follow instructions better.',
            'quality_score': 93.0,
            'recency_score': 88.0,
            'citation_score': 92.0,
        },
    ]

    for paper in test_papers:
        upsert_paper(
            paper_id=paper['paper_id'],
            week_id=week_id,
            title=paper['title'],
            summary=paper.get('summary'),
            quality_score=paper['quality_score'],
            recency_score=paper['recency_score'],
            citation_score=paper['citation_score'],
            filtered_out=0,  # 不过滤
            content_type="PAPER"
        )

    print(f"\n✅ 创建了 {len(test_papers)} 篇高质量测试论文")
    for i, paper in enumerate(test_papers, 1):
        print(f"  {i}. {paper['title'][:50]}... (质量: {paper['quality_score']:.0f})")


def test_popular_recommendation():
    """测试热门推荐"""
    print_header("场景3: 热门推荐测试")

    recommender = Recommender(user_id="test_real_user")
    results = recommender.recommend_popular(week_id="2026-05", limit=5)

    if results:
        print(f"\n✨ 找到 {len(results)} 条热门推荐:")
        print(f"\n{'#':<3} {'评分':<6} {'标题':<55}")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.title[:52] + "..." if len(result.title) > 55 else result.title
            print(f"{i:<3} {result.score:<6.1f} {title}")
            if result.reasons:
                print(f"     💡 {' | '.join(result.reasons)}")
    else:
        print("\n❌ 未找到推荐（可能所有论文都被过滤）")


def test_user_interactions():
    """测试用户交互"""
    print_header("场景4: 用户交互测试")

    user_id = "test_real_user"
    recommender = Recommender(user_id=user_id)

    # 模拟用户行为
    interactions = [
        ('test_real_2', 'view', "查看论文"),
        ('test_real_2', 'favorite', "收藏论文"),
        ('test_real_1', 'view', "查看论文"),
        ('test_real_3', 'view', "查看论文"),
        ('test_real_3', 'share', "分享论文"),
    ]

    print(f"\n📊 模拟用户行为:")
    for paper_id, action, desc in interactions:
        recommender.track_interaction(paper_id, action)

        # 获取论文标题
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT title FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            title = row['title'][:40] + "..." if row and len(row['title']) > 40 else (row['title'] if row else paper_id)

        action_icons = {'view': '👀', 'favorite': '⭐', 'share': '📤'}
        print(f"  {action_icons.get(action, '•')} {desc}: {title}")

    # 统计交互
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                action_type,
                COUNT(*) as cnt,
                SUM(interaction_score) as total_score
            FROM user_interactions
            WHERE user_id = ?
            GROUP BY action_type
        """, (user_id,))
        stats = cursor.fetchall()

    print(f"\n📈 交互统计:")
    for row in stats:
        print(f"  {row['action_type']}: {row['cnt']} 次 (总分: {row['total_score']:.1f})")


def test_similar_recommendation():
    """测试相似推荐"""
    print_header("场景5: 相似论文推荐测试")

    recommender = Recommender(user_id="test_real_user")

    base_paper = "test_real_2"
    print(f"\n🔍 查找与论文 {base_paper} 相似的论文...")

    # 获取基准论文标题
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM papers WHERE paper_id = ?", (base_paper,))
        row = cursor.fetchone()
        if row:
            print(f"   基准论文: {row['title']}")

    results = recommender.recommend_similar(
        paper_id=base_paper,
        limit=3,
        min_similarity=0.0
    )

    if results:
        print(f"\n✨ 找到 {len(results)} 条相似推荐:")
        print(f"\n{'#':<3} {'相似度':<8} {'标题':<55}")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.title[:52] + "..." if len(result.title) > 55 else result.title
            print(f"{i:<3} {result.score:<8.2f} {title}")
    else:
        print(f"\n⚠️ 未找到相似论文")
        print(f"   提示: 安装 sentence-transformers 可启用语义相似度")


def test_hybrid_recommendation():
    """测试混合推荐"""
    print_header("场景6: 混合推荐测试")

    # 新用户
    print(f"\n🆕 新用户 (无交互记录):")
    new_user = Recommender(user_id="new_test_user")
    results = new_user.recommend_hybrid(week_id="2026-05", limit=3)

    if results:
        print(f"   策略: {results[0].strategy}")
        for i, result in enumerate(results, 1):
            title = result.title[:50] + "..." if len(result.title) > 50 else result.title
            print(f"   {i}. {title}")

    # 活跃用户
    print(f"\n👤 活跃用户 (有交互记录):")
    active_user = Recommender(user_id="test_real_user")
    results = active_user.recommend_hybrid(week_id="2026-05", limit=3)

    if results:
        strategies = set(r.strategy for r in results)
        print(f"   策略: {', '.join(strategies)}")
        for i, result in enumerate(results, 1):
            title = result.title[:50] + "..." if len(result.title) > 50 else result.title
            print(f"   {i}. {title}")


def test_recommendation_stats():
    """测试推荐统计"""
    print_header("场景7: 推荐系统统计")

    with get_connection() as conn:
        cursor = conn.cursor()

        # 交互统计
        cursor.execute("""
            SELECT COUNT(*) as cnt, COUNT(DISTINCT user_id) as users
            FROM user_interactions
            WHERE user_id LIKE 'test_real%' OR user_id = 'new_test_user'
        """)
        interaction_stats = cursor.fetchone()

        # 推荐统计
        cursor.execute("""
            SELECT COUNT(*) as cnt, COUNT(DISTINCT strategy) as strategies
            FROM recommendations
            WHERE user_id LIKE 'test_real%' OR user_id = 'new_test_user'
        """)
        rec_stats = cursor.fetchone()

        # 热门论文
        cursor.execute("""
            SELECT p.paper_id, p.title, COUNT(*) as interactions
            FROM user_interactions ui
            JOIN papers p ON ui.paper_id = p.paper_id
            WHERE ui.user_id LIKE 'test_real%'
            GROUP BY p.paper_id
            ORDER BY interactions DESC
            LIMIT 3
        """)
        hot_papers = cursor.fetchall()

    print(f"\n📊 总体统计:")
    print(f"  用户数: {interaction_stats['users']}")
    print(f"  交互次数: {interaction_stats['cnt']}")
    print(f"  推荐次数: {rec_stats['cnt']}")

    if hot_papers:
        print(f"\n🔥 最热门论文:")
        for i, row in enumerate(hot_papers, 1):
            title = row['title'][:50] + "..." if len(row['title']) > 50 else row['title']
            print(f"  {i}. {title} ({row['interactions']} 次交互)")


def cleanup():
    """清理测试数据"""
    print_header("清理测试数据")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM papers WHERE paper_id LIKE 'test_real_%'")
        papers_deleted = cursor.rowcount

        cursor.execute("DELETE FROM user_interactions WHERE user_id LIKE 'test_real%' OR user_id = 'new_test_user'")
        interactions_deleted = cursor.rowcount

        cursor.execute("DELETE FROM recommendations WHERE user_id LIKE 'test_real%' OR user_id = 'new_test_user'")
        recommendations_deleted = cursor.rowcount

        conn.commit()

    print(f"\n✅ 清理完成:")
    print(f"  删除论文: {papers_deleted}")
    print(f"  删除交互: {interactions_deleted}")
    print(f"  删除推荐: {recommendations_deleted}")


def main():
    print("\n" + "=" * 70)
    print("  推荐系统真实场景测试")
    print("=" * 70)

    try:
        # 测试真实数据
        test_with_real_data()

        # 创建高质量测试数据
        test_create_high_quality_papers()

        # 测试各种推荐策略
        test_popular_recommendation()
        test_user_interactions()
        test_similar_recommendation()
        test_hybrid_recommendation()
        test_recommendation_stats()

    finally:
        # 清理
        cleanup()

    print("\n" + "=" * 70)
    print("  测试完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
