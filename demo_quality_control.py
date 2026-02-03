#!/usr/bin/env python3
"""
质量控制系统演示脚本

展示质量评分系统的各种功能
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.quality_filter import QualityFilter


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_score(score, content_type="Content"):
    print(f"\n{content_type} Quality Score:")
    print(f"  ├─ Total Score:    {score.total_score:.2f} / 100.0")
    print(f"  ├─ Citation Score: {score.citation_score:.2f}")
    print(f"  ├─ Venue Score:    {score.venue_score:.2f}")
    print(f"  ├─ Recency Score:  {score.recency_score:.2f}")
    print(f"  ├─ Passed:         {'✅ YES' if score.passed else '❌ NO'}")
    print(f"  └─ Reasons:")
    for reason in score.reasons:
        print(f"      • {reason}")


def main():
    filter = QualityFilter()

    print_header("质量控制系统演示")

    # Demo 1: Paper Evaluation
    print_header("Demo 1: 论文质量评分")

    print("\n📄 评估论文: 'Attention Is All You Need'")
    paper_score = filter.evaluate_paper(
        title="Attention Is All You Need: Transformer Architecture",
        pdf_url="https://arxiv.org/pdf/2601.03252.pdf",
        hf_url="https://huggingface.co/papers/2601.03252"
    )
    print_score(paper_score, "Paper")

    print("\n📄 评估论文: 标题过短")
    short_paper_score = filter.evaluate_paper(
        title="Test",
        pdf_url="https://arxiv.org/pdf/1234.56789.pdf"
    )
    print_score(short_paper_score, "Paper")

    # Demo 2: GitHub Project Evaluation
    print_header("Demo 2: GitHub项目质量评分")

    print("\n⭐ 评估项目: PyTorch (50,000 stars)")
    github_score = filter.evaluate_github_project(
        name="pytorch",
        stars=50000,
        language="Python",
        description="Deep learning framework for research and production"
    )
    print_score(github_score, "GitHub Project")

    print("\n⭐ 评估项目: 小型项目 (50 stars)")
    small_github_score = filter.evaluate_github_project(
        name="small-project",
        stars=50,
        language="Python",
        description="A small utility library"
    )
    print_score(small_github_score, "GitHub Project")

    # Demo 3: News Evaluation
    print_header("Demo 3: 新闻热点质量评分")

    print("\n📰 评估新闻: 知乎热榜 Top 5")
    news_score = filter.evaluate_news(
        title="AI领域重大突破：新型神经网络架构",
        rank=5,
        source="zhihu",
        hot_value="100万热度"
    )
    print_score(news_score, "News")

    print("\n📰 评估新闻: 微博热搜 第60名")
    low_news_score = filter.evaluate_news(
        title="普通热点事件",
        rank=60,
        source="weibo",
        hot_value="1000热度"
    )
    print_score(low_news_score, "News")

    # Demo 4: Unified Interface
    print_header("Demo 4: 统一评分接口")

    print("\n使用 evaluate_content() 统一接口:")

    print("\n1. 评估论文:")
    unified_paper = filter.evaluate_content(
        content_type="PAPER",
        title="Deep Learning for Natural Language Processing",
        pdf_url="https://arxiv.org/pdf/2601.03252.pdf"
    )
    print(f"   Score: {unified_paper.total_score:.2f}, Passed: {unified_paper.passed}")

    print("\n2. 评估GitHub项目:")
    unified_github = filter.evaluate_content(
        content_type="GITHUB",
        name="tensorflow",
        stars=150000,
        language="Python"
    )
    print(f"   Score: {unified_github.total_score:.2f}, Passed: {unified_github.passed}")

    print("\n3. 评估新闻:")
    unified_news = filter.evaluate_content(
        content_type="NEWS",
        title="热点新闻",
        rank=8,
        source="zhihu"
    )
    print(f"   Score: {unified_news.total_score:.2f}, Passed: {unified_news.passed}")

    # Summary
    print_header("评分总结")

    scores = [
        ("高质量论文", paper_score.total_score, paper_score.passed),
        ("低质量论文", short_paper_score.total_score, short_paper_score.passed),
        ("高Stars项目", github_score.total_score, github_score.passed),
        ("低Stars项目", small_github_score.total_score, small_github_score.passed),
        ("热榜Top新闻", news_score.total_score, news_score.passed),
        ("低排名新闻", low_news_score.total_score, low_news_score.passed),
    ]

    print("\n内容类型          评分      是否通过")
    print("-" * 50)
    for name, score, passed in scores:
        status = "✅ YES" if passed else "❌ NO"
        print(f"{name:<15} {score:>6.2f}    {status}")

    passed_count = sum(1 for _, _, passed in scores if passed)
    print("-" * 50)
    print(f"通过率: {passed_count}/{len(scores)} ({passed_count/len(scores)*100:.1f}%)")

    print("\n" + "=" * 70)
    print("  演示完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
