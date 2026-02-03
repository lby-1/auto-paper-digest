"""
去重系统演示脚本

展示去重系统的各种功能
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.deduplicator import Deduplicator


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def main():
    dedup = Deduplicator()

    print_header("智能去重系统演示")

    # Demo 1: arXiv ID标准化
    print_header("Demo 1: arXiv ID标准化")

    urls = [
        "https://arxiv.org/abs/2601.03252",
        "https://arxiv.org/pdf/2601.03252.pdf",
        "https://export.arxiv.org/pdf/2601.03252.pdf",
    ]

    print("\n不同格式的arXiv URL:")
    for url in urls:
        normalized = dedup.normalize_arxiv_id(url)
        print(f"  {url}")
        print(f"    → {normalized}\n")

    # Demo 2: 标题相似度
    print_header("Demo 2: 标题相似度计算")

    title_pairs = [
        ("Attention Is All You Need", "Attention Is All You Need"),
        ("Attention Is All You Need", "Attention is all you need"),
        ("Attention Is All You Need", "Transformer: Attention Is All You Need"),
        ("Attention Is All You Need", "BERT: Pre-training Transformers"),
    ]

    print()
    for t1, t2 in title_pairs:
        similarity = dedup.compute_title_similarity(t1, t2)
        status = "✅ 相似" if similarity >= 0.85 else "❌ 不同"
        print(f"标题1: {t1}")
        print(f"标题2: {t2}")
        print(f"相似度: {similarity:.2f} {status}\n")

    # Demo 3: 完整去重流程
    print_header("Demo 3: 完整去重流程")

    # 模拟论文数据
    papers = [
        {
            'paper_id': 'arxiv:2601.03252_hf',
            'title': 'Attention Is All You Need',
            'pdf_url': 'https://arxiv.org/pdf/2601.03252.pdf',
            'hf_url': 'https://huggingface.co/papers/2601.03252',
            'abstract': 'The dominant sequence transduction models...'
        },
        {
            'paper_id': 'arxiv:2601.03252_direct',
            'title': 'Attention Mechanism Research',
            'pdf_url': 'https://export.arxiv.org/pdf/2601.03252.pdf',  # 同一arXiv ID
            'hf_url': '',
            'abstract': 'Research on attention mechanisms...'
        },
        {
            'paper_id': 'paper_similar_title',
            'title': 'attention is all you need',  # 相同标题，不同大小写
            'pdf_url': '',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper_unique_1',
            'title': 'BERT: Pre-training of Deep Bidirectional Transformers',
            'pdf_url': 'https://arxiv.org/pdf/1810.04805.pdf',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper_unique_2',
            'title': 'GPT-3: Language Models are Few-Shot Learners',
            'pdf_url': 'https://arxiv.org/pdf/2005.14165.pdf',
            'hf_url': '',
            'abstract': ''
        },
    ]

    print(f"\n输入: {len(papers)} 篇论文")
    for paper in papers:
        print(f"  - {paper['paper_id']}: {paper['title'][:50]}")

    print("\n\n🔍 运行去重检测...")
    result = dedup.find_duplicates(papers, use_semantic=False)

    print(f"\n📊 去重结果:")
    print(f"  总论文数: {result.total_papers}")
    print(f"  唯一论文: {result.unique_papers}")
    print(f"  重复组数: {len(result.duplicate_groups)}")
    print(f"  去除重复: {result.duplicates_removed}")
    print(f"  去重率: {result.duplicates_removed/result.total_papers*100:.1f}%")

    if result.duplicate_groups:
        print(f"\n📋 重复组详情:")
        for i, group in enumerate(result.duplicate_groups, 1):
            print(f"\n  组 {i}: 检测方法={group.detection_method}")
            print(f"    主论文: {group.canonical_paper_id}")
            print(f"    重复项:")
            for dup_id in group.duplicate_paper_ids:
                score = group.similarity_scores.get(dup_id, 0.0)
                print(f"      - {dup_id} (相似度: {score:.2f})")

    # Demo 4: 统计信息
    print_header("Demo 4: 统计信息")

    stats = dedup.get_deduplication_stats(result)

    print(f"\n总体统计:")
    print(f"  总论文数: {stats['total_papers']}")
    print(f"  唯一论文: {stats['unique_papers']}")
    print(f"  重复组数: {stats['duplicate_groups']}")
    print(f"  去除重复: {stats['duplicates_removed']}")
    print(f"  去重率: {stats['deduplication_rate']*100:.1f}%")

    print(f"\n检测方法分布:")
    print(f"  精确URL匹配: {stats['detection_methods']['exact_url']}")
    print(f"  标题相似度: {stats['detection_methods']['title_similarity']}")
    print(f"  语义相似度: {stats['detection_methods']['semantic_similarity']}")

    # 总结
    print_header("资源节省估算")

    saved_papers = result.duplicates_removed
    time_per_paper = 15  # 分钟
    cost_per_paper = 0.5  # 美元

    print(f"\n如果每篇论文处理需要:")
    print(f"  - 时间: {time_per_paper} 分钟")
    print(f"  - 成本: ${cost_per_paper}")

    print(f"\n通过去重节省:")
    print(f"  - 时间: {saved_papers * time_per_paper} 分钟 = {saved_papers * time_per_paper / 60:.1f} 小时")
    print(f"  - 成本: ${saved_papers * cost_per_paper}")
    print(f"  - 存储空间: ~{saved_papers * 100} MB")

    print("\n" + "=" * 70)
    print("  演示完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
