"""
去重系统单元测试
"""

import sys
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from apd.deduplicator import Deduplicator, DuplicateGroup


def test_normalize_arxiv_id():
    """测试arXiv ID标准化"""
    dedup = Deduplicator()

    # 测试不同格式的arXiv URL
    test_cases = [
        ("https://arxiv.org/abs/2601.03252", "2601.03252"),
        ("https://arxiv.org/pdf/2601.03252.pdf", "2601.03252"),
        ("https://export.arxiv.org/pdf/2601.03252.pdf", "2601.03252"),
        ("https://arxiv.org/abs/1706.03762", "1706.03762"),
        ("invalid_url", None),
    ]

    for url, expected in test_cases:
        result = dedup.normalize_arxiv_id(url)
        assert result == expected, f"Failed for {url}: got {result}, expected {expected}"

    print("✓ arXiv ID normalization tests passed")


def test_normalize_title():
    """测试标题标准化"""
    dedup = Deduplicator()

    test_cases = [
        ("Attention Is All You Need", "attention is all you need"),
        ("BERT: Pre-training of Deep Bidirectional Transformers", "bert pre training of deep bidirectional transformers"),
        ("GPT-3: Language Models are Few-Shot Learners", "gpt 3 language models are few shot learners"),
    ]

    for original, expected in test_cases:
        result = dedup.normalize_title(original)
        assert result == expected, f"Failed for '{original}': got '{result}'"

    print("✓ Title normalization tests passed")


def test_title_similarity():
    """测试标题相似度计算"""
    dedup = Deduplicator()

    # 完全相同
    sim = dedup.compute_title_similarity(
        "Attention Is All You Need",
        "Attention Is All You Need"
    )
    assert sim == 1.0, f"Expected 1.0, got {sim}"

    # 高度相似
    sim = dedup.compute_title_similarity(
        "Attention Is All You Need",
        "Attention is all you need"  # 大小写不同
    )
    assert sim == 1.0, f"Expected 1.0, got {sim}"

    # 中等相似
    sim = dedup.compute_title_similarity(
        "Attention Is All You Need",
        "Transformer: Attention Is All You Need"
    )
    assert sim > 0.7, f"Expected > 0.7, got {sim}"
    print(f"  Similar titles score: {sim:.2f}")

    # 低相似度
    sim = dedup.compute_title_similarity(
        "Attention Is All You Need",
        "BERT: Pre-training of Deep Bidirectional Transformers"
    )
    assert sim < 0.5, f"Expected < 0.5, got {sim}"
    print(f"  Different titles score: {sim:.2f}")

    print("✓ Title similarity tests passed")


def test_find_duplicates_exact_url():
    """测试URL精确匹配"""
    dedup = Deduplicator()

    papers = [
        {
            'paper_id': 'paper1',
            'title': 'Attention Is All You Need',
            'pdf_url': 'https://arxiv.org/pdf/2601.03252.pdf',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper2',
            'title': 'Attention Mechanism Research',
            'pdf_url': 'https://export.arxiv.org/pdf/2601.03252.pdf',  # 同一arXiv ID
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper3',
            'title': 'Different Paper',
            'pdf_url': 'https://arxiv.org/pdf/2601.99999.pdf',
            'hf_url': '',
            'abstract': ''
        },
    ]

    result = dedup.find_duplicates(papers, use_semantic=False)

    assert result.total_papers == 3
    assert len(result.duplicate_groups) == 1
    assert result.duplicates_removed == 1
    assert result.unique_papers == 2

    group = result.duplicate_groups[0]
    assert group.detection_method == 'exact_url'
    assert group.canonical_paper_id in ['paper1', 'paper2']
    assert len(group.duplicate_paper_ids) == 1

    print("✓ Exact URL matching tests passed")


def test_find_duplicates_title_similarity():
    """测试标题相似度匹配"""
    dedup = Deduplicator()

    papers = [
        {
            'paper_id': 'paper1',
            'title': 'Attention Is All You Need',
            'pdf_url': '',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper2',
            'title': 'Attention is all you need',  # 完全相同（忽略大小写）
            'pdf_url': '',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper3',
            'title': 'Completely Different Paper',
            'pdf_url': '',
            'hf_url': '',
            'abstract': ''
        },
    ]

    result = dedup.find_duplicates(papers, use_semantic=False)

    assert result.total_papers == 3
    assert len(result.duplicate_groups) == 1
    assert result.duplicates_removed == 1

    group = result.duplicate_groups[0]
    assert group.detection_method == 'title_similarity'

    print("✓ Title similarity matching tests passed")


def test_no_duplicates():
    """测试无重复情况"""
    dedup = Deduplicator()

    papers = [
        {
            'paper_id': 'paper1',
            'title': 'First Paper',
            'pdf_url': 'https://arxiv.org/pdf/2601.00001.pdf',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper2',
            'title': 'Second Paper',
            'pdf_url': 'https://arxiv.org/pdf/2601.00002.pdf',
            'hf_url': '',
            'abstract': ''
        },
        {
            'paper_id': 'paper3',
            'title': 'Third Paper',
            'pdf_url': 'https://arxiv.org/pdf/2601.00003.pdf',
            'hf_url': '',
            'abstract': ''
        },
    ]

    result = dedup.find_duplicates(papers, use_semantic=False)

    assert result.total_papers == 3
    assert len(result.duplicate_groups) == 0
    assert result.duplicates_removed == 0
    assert result.unique_papers == 3

    print("✓ No duplicates tests passed")


def test_deduplication_stats():
    """测试统计信息"""
    dedup = Deduplicator()

    papers = [
        {'paper_id': 'p1', 'title': 'Same Title', 'pdf_url': '', 'hf_url': '', 'abstract': ''},
        {'paper_id': 'p2', 'title': 'Same Title', 'pdf_url': '', 'hf_url': '', 'abstract': ''},
        {'paper_id': 'p3', 'title': 'Different', 'pdf_url': '', 'hf_url': '', 'abstract': ''},
    ]

    result = dedup.find_duplicates(papers, use_semantic=False)
    stats = dedup.get_deduplication_stats(result)

    assert stats['total_papers'] == 3
    assert stats['unique_papers'] == 2
    assert stats['duplicate_groups'] == 1
    assert stats['duplicates_removed'] == 1
    assert 0 < stats['deduplication_rate'] <= 1

    print("✓ Statistics tests passed")
    print(f"  Deduplication rate: {stats['deduplication_rate']*100:.1f}%")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("去重系统单元测试")
    print("=" * 60 + "\n")

    test_normalize_arxiv_id()
    test_normalize_title()
    test_title_similarity()
    test_find_duplicates_exact_url()
    test_find_duplicates_title_similarity()
    test_no_duplicates()
    test_deduplication_stats()

    print("\n" + "=" * 60)
    print("所有测试通过! ✅")
    print("=" * 60 + "\n")
