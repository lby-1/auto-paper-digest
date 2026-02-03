"""
质量控制系统单元测试
"""

import sys
import io

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.quality_filter import QualityFilter, QualityScore


def test_evaluate_paper_basic():
    """测试基础论文评分"""
    filter = QualityFilter()

    score = filter.evaluate_paper(
        title="Attention Is All You Need",
        pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
        hf_url="https://huggingface.co/papers/1706.03762"
    )

    assert score.total_score > 0
    assert score.total_score <= 100
    assert len(score.reasons) > 0
    print(f"✓ Paper score: {score.total_score:.2f}")


def test_evaluate_paper_short_title():
    """测试标题过短的论文"""
    filter = QualityFilter()

    score = filter.evaluate_paper(
        title="Test",
        pdf_url="https://arxiv.org/pdf/2601.03252.pdf"
    )

    assert score.total_score == 0.0
    assert not score.passed
    print(f"✓ Short title rejected: {score.reasons}")


def test_evaluate_github_high_stars():
    """测试高Stars项目"""
    filter = QualityFilter()

    score = filter.evaluate_github_project(
        name="pytorch",
        stars=50000,
        language="Python",
        description="Deep learning framework"
    )

    assert score.passed is True
    assert score.total_score >= 60
    print(f"✓ High-star project passed: {score.total_score:.2f}")


def test_evaluate_github_low_stars():
    """测试低Stars项目"""
    filter = QualityFilter()

    score = filter.evaluate_github_project(
        name="small-project",
        stars=50,  # Below MIN_GITHUB_STARS (100)
        language="Python",
        description="A small project"
    )

    assert score.passed is False
    assert score.total_score == 0.0
    print(f"✓ Low-star project rejected: {score.reasons}")


def test_evaluate_news_top_rank():
    """测试热榜Top 10新闻"""
    filter = QualityFilter()

    score = filter.evaluate_news(
        title="重大科技突破",
        rank=5,
        source="zhihu",
        hot_value="100万"
    )

    assert score.passed is True
    assert score.total_score >= 80
    print(f"✓ Top 10 news passed: {score.total_score:.2f}")


def test_evaluate_news_low_rank():
    """测试排名较低的新闻"""
    filter = QualityFilter()

    score = filter.evaluate_news(
        title="普通新闻",
        rank=60,
        source="weibo",
        hot_value="1000"
    )

    # 排名60，来源微博(0.8权重)
    # rank_score = 100 - 60 = 40
    # source_score = 0.8 * 100 = 80
    # total = 40 * 0.6 + 80 * 0.4 = 24 + 32 = 56
    assert score.total_score < 60
    assert not score.passed
    print(f"✓ Low-rank news rejected: {score.total_score:.2f}")


def test_evaluate_content_unified_interface():
    """测试统一评分接口"""
    filter = QualityFilter()

    # Test PAPER type
    paper_score = filter.evaluate_content(
        content_type="PAPER",
        title="Test Paper",
        pdf_url="https://arxiv.org/pdf/2601.03252.pdf"
    )
    assert paper_score.total_score > 0

    # Test GITHUB type
    github_score = filter.evaluate_content(
        content_type="GITHUB",
        name="test-repo",
        stars=1000,
        language="Python"
    )
    assert github_score.total_score > 0

    # Test NEWS type
    news_score = filter.evaluate_content(
        content_type="NEWS",
        title="Test News",
        rank=10,
        source="zhihu"
    )
    assert news_score.total_score > 0

    print(f"✓ Unified interface works for all content types")


def test_quality_score_dataclass():
    """测试QualityScore数据类"""
    score = QualityScore(
        total_score=75.5,
        citation_score=80.0,
        venue_score=70.0,
        recency_score=76.0,
        reasons=["Test reason 1", "Test reason 2"],
        passed=True
    )

    assert score.total_score == 75.5
    assert score.passed is True
    assert len(score.reasons) == 2
    print(f"✓ QualityScore dataclass working correctly")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("质量控制系统单元测试")
    print("=" * 60 + "\n")

    test_evaluate_paper_basic()
    test_evaluate_paper_short_title()
    test_evaluate_github_high_stars()
    test_evaluate_github_low_stars()
    test_evaluate_news_top_rank()
    test_evaluate_news_low_rank()
    test_evaluate_content_unified_interface()
    test_quality_score_dataclass()

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60 + "\n")
