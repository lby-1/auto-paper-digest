"""
真实场景去重测试

模拟实际使用中可能遇到的重复场景
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.db import upsert_paper, get_connection
from apd.deduplicator import Deduplicator
from apd.utils import now_iso

def setup_test_data():
    """设置测试数据：创建一些具有重复特征的论文"""

    week_id = "2026-05"

    # 场景1: 同一篇论文从不同来源获取（arXiv vs HuggingFace）
    print("📝 场景1: 同一论文的不同来源")
    upsert_paper(
        paper_id="test_dup_arxiv_1",
        week_id=week_id,
        title="Attention Is All You Need",
        pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
        hf_url="",
        content_type="PAPER",
        summary="The dominant sequence transduction models..."
    )

    upsert_paper(
        paper_id="test_dup_hf_1",
        week_id=week_id,
        title="Attention Is All You Need",
        pdf_url="https://export.arxiv.org/pdf/1706.03762.pdf",  # 同一arXiv ID，不同域名
        hf_url="https://huggingface.co/papers/1706.03762",
        content_type="PAPER",
        summary="The dominant sequence transduction models..."
    )
    print("  ✓ 添加了2篇相同论文（不同URL格式）")

    # 场景2: 标题略有不同但实际是同一论文
    print("\n📝 场景2: 标题大小写和标点差异")
    upsert_paper(
        paper_id="test_dup_case_1",
        week_id=week_id,
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        pdf_url="https://arxiv.org/pdf/1810.04805.pdf",
        hf_url="",
        content_type="PAPER",
        summary="We introduce BERT..."
    )

    upsert_paper(
        paper_id="test_dup_case_2",
        week_id=week_id,
        title="bert pre-training of deep bidirectional transformers",  # 全小写
        pdf_url="",
        hf_url="https://huggingface.co/papers/1810.04805",
        content_type="PAPER",
        summary="We introduce BERT..."
    )
    print("  ✓ 添加了2篇相同论文（不同大小写）")

    # 场景3: 标题有前缀/后缀的重复
    print("\n📝 场景3: 标题有额外前缀")
    upsert_paper(
        paper_id="test_dup_prefix_1",
        week_id=week_id,
        title="GPT-3: Language Models are Few-Shot Learners",
        pdf_url="https://arxiv.org/pdf/2005.14165.pdf",
        hf_url="",
        content_type="PAPER",
        summary="Recent work has demonstrated..."
    )

    upsert_paper(
        paper_id="test_dup_prefix_2",
        week_id=week_id,
        title="[2020] GPT-3: Language Models are Few-Shot Learners",  # 带年份前缀
        pdf_url="",
        hf_url="https://huggingface.co/papers/2005.14165",
        content_type="PAPER",
        summary="Recent work has demonstrated..."
    )
    print("  ✓ 添加了2篇相同论文（一个有年份前缀）")

    # 场景4: 完全不同的论文（不应该被标记为重复）
    print("\n📝 场景4: 不同的论文（对照组）")
    upsert_paper(
        paper_id="test_unique_1",
        week_id=week_id,
        title="ResNet: Deep Residual Learning for Image Recognition",
        pdf_url="https://arxiv.org/pdf/1512.03385.pdf",
        hf_url="",
        content_type="PAPER",
        summary="Deeper neural networks are more difficult to train..."
    )

    upsert_paper(
        paper_id="test_unique_2",
        week_id=week_id,
        title="AlexNet: ImageNet Classification with Deep CNNs",
        pdf_url="https://arxiv.org/pdf/1404.5997.pdf",
        hf_url="",
        content_type="PAPER",
        summary="We trained a large, deep convolutional neural network..."
    )
    print("  ✓ 添加了2篇不同的论文")

    print(f"\n✅ 测试数据准备完成：共8篇论文，预期检测到3组重复（6篇重复论文）")


def run_dedup_test():
    """运行去重测试"""

    print("\n" + "="*70)
    print("  开始去重检测")
    print("="*70)

    # 获取所有测试论文
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT paper_id, title, pdf_url, hf_url, summary
            FROM papers
            WHERE paper_id LIKE 'test_%'
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
        papers = [dict(row) for row in rows]

    print(f"\n📊 输入数据：{len(papers)} 篇论文")
    for i, paper in enumerate(papers, 1):
        print(f"  {i}. {paper['paper_id']}: {paper['title'][:60]}...")

    # 运行去重
    dedup = Deduplicator()
    result = dedup.find_duplicates(papers, use_semantic=False)

    print(f"\n" + "="*70)
    print("  去重结果")
    print("="*70)

    print(f"\n📈 统计数据：")
    print(f"  总论文数：{result.total_papers}")
    print(f"  唯一论文：{result.unique_papers}")
    print(f"  重复组数：{len(result.duplicate_groups)}")
    print(f"  检测到的重复：{result.duplicates_removed}")
    print(f"  去重率：{result.duplicates_removed/result.total_papers*100:.1f}%")

    if result.duplicate_groups:
        print(f"\n📋 重复组详情：")
        for i, group in enumerate(result.duplicate_groups, 1):
            print(f"\n  组 {i}: 检测方法={group.detection_method}")
            print(f"    主论文：{group.canonical_paper_id}")
            print(f"    标题：", end="")
            # 获取主论文标题
            main_paper = next((p for p in papers if p['paper_id'] == group.canonical_paper_id), None)
            if main_paper:
                print(f"{main_paper['title']}")
            print(f"    重复项：")
            for dup_id in group.duplicate_paper_ids:
                score = group.similarity_scores.get(dup_id, 0.0)
                dup_paper = next((p for p in papers if p['paper_id'] == dup_id), None)
                if dup_paper:
                    print(f"      - {dup_id} (相似度: {score:.2f})")
                    print(f"        {dup_paper['title']}")

    # 计算资源节省
    print(f"\n" + "="*70)
    print("  资源节省估算")
    print("="*70)

    saved_papers = result.duplicates_removed
    time_per_paper = 15  # 分钟
    cost_per_paper = 0.5  # 美元
    storage_per_paper = 100  # MB

    print(f"\n💰 通过去重节省：")
    print(f"  ⏱️  处理时间：{saved_papers * time_per_paper} 分钟 = {saved_papers * time_per_paper / 60:.1f} 小时")
    print(f"  💵 处理成本：${saved_papers * cost_per_paper:.2f}")
    print(f"  💾 存储空间：~{saved_papers * storage_per_paper} MB")

    if result.total_papers > 0:
        print(f"\n📊 效率提升：")
        print(f"  处理效率提升：{(1 - result.unique_papers/result.total_papers)*100:.1f}%")
        print(f"  成本降低：{(saved_papers * cost_per_paper) / (result.total_papers * cost_per_paper) * 100:.1f}%")


def cleanup_test_data():
    """清理测试数据"""
    print(f"\n" + "="*70)
    print("  清理测试数据")
    print("="*70)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM papers WHERE paper_id LIKE 'test_%'")
        deleted = cursor.rowcount
        conn.commit()

    print(f"✅ 已删除 {deleted} 条测试记录")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  真实场景去重系统测试")
    print("="*70 + "\n")

    try:
        # 设置测试数据
        setup_test_data()

        # 运行去重测试
        run_dedup_test()

    finally:
        # 清理测试数据
        cleanup_test_data()

    print("\n" + "="*70)
    print("  测试完成！")
    print("="*70 + "\n")
