"""
智能去重系统

多层级相似度检测：
- Level 1: URL精确匹配（arXiv ID标准化）
- Level 2: 标题相似度（Levenshtein距离 + Jaccard）
- Level 3: 语义相似度（Sentence-BERT embeddings）
"""

import re
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """重复组"""
    group_id: str
    canonical_paper_id: str  # 主论文ID
    duplicate_paper_ids: List[str]  # 重复论文ID列表
    similarity_scores: Dict[str, float]  # {paper_id: score}
    detection_method: str  # exact_url | title_similarity | semantic_similarity
    created_at: str


@dataclass
class DeduplicationResult:
    """去重结果"""
    total_papers: int
    duplicate_groups: List[DuplicateGroup]
    unique_papers: int
    duplicates_removed: int

    def __post_init__(self):
        self.unique_papers = self.total_papers - self.duplicates_removed


class Deduplicator:
    """内容去重器"""

    def __init__(self, config=None):
        if config is None:
            from .config import DeduplicationConfig
            config = DeduplicationConfig

        self.config = config
        self.sentence_model = None  # 延迟加载

    def _load_sentence_model(self):
        """延迟加载Sentence-BERT模型"""
        if self.sentence_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.config.EMBEDDING_MODEL}")
                self.sentence_model = SentenceTransformer(self.config.EMBEDDING_MODEL)
                logger.info("Model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers not installed. Semantic similarity disabled.")
                logger.info("Install with: pip install sentence-transformers")
                self.sentence_model = None
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.sentence_model = None

    def normalize_arxiv_id(self, url: str) -> Optional[str]:
        """
        标准化arXiv ID

        输入:
        - https://arxiv.org/abs/2601.03252
        - https://arxiv.org/pdf/2601.03252.pdf
        - https://export.arxiv.org/pdf/2601.03252.pdf

        输出: 2601.03252
        """
        if not url:
            return None

        # 匹配arXiv ID模式
        patterns = [
            r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})',
            r'export\.arxiv\.org/pdf/(\d{4}\.\d{4,5})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def normalize_title(self, title: str) -> str:
        """
        标题标准化

        - 转小写
        - 移除特殊字符
        - 移除多余空格
        """
        if not title:
            return ""

        # 转小写
        title = title.lower()

        # 移除特殊字符，保留字母数字和空格
        title = re.sub(r'[^a-z0-9\s]', ' ', title)

        # 移除多余空格
        title = ' '.join(title.split())

        return title

    def compute_title_hash(self, title: str) -> str:
        """计算标题哈希值（用于快速查找）"""
        normalized = self.normalize_title(title)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def compute_title_similarity(self, title1: str, title2: str) -> float:
        """
        计算标题相似度（结合多种方法）

        返回: 0.0-1.0的相似度分数
        """
        if not title1 or not title2:
            return 0.0

        # 标准化
        t1 = self.normalize_title(title1)
        t2 = self.normalize_title(title2)

        # 完全相同
        if t1 == t2:
            return 1.0

        # 方法1: SequenceMatcher（基于编辑距离）
        seq_ratio = SequenceMatcher(None, t1, t2).ratio()

        # 方法2: Jaccard相似度（基于词集合）
        words1 = set(t1.split())
        words2 = set(t2.split())

        if not words1 or not words2:
            return seq_ratio

        intersection = words1 & words2
        union = words1 | words2
        jaccard_ratio = len(intersection) / len(union)

        # 加权平均
        similarity = (seq_ratio * 0.6 + jaccard_ratio * 0.4)

        return similarity

    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算语义相似度（使用Sentence-BERT）

        返回: 0.0-1.0的相似度分数
        """
        if not text1 or not text2:
            return 0.0

        # 加载模型
        if self.sentence_model is None:
            self._load_sentence_model()

        if self.sentence_model is None:
            logger.warning("Sentence model not available, using title similarity instead")
            return self.compute_title_similarity(text1, text2)

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # 生成embeddings
            embeddings = self.sentence_model.encode([text1, text2])

            # 计算余弦相似度
            similarity = cosine_similarity(
                embeddings[0].reshape(1, -1),
                embeddings[1].reshape(1, -1)
            )[0][0]

            return float(similarity)

        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0

    def find_duplicates(
        self,
        papers: List[dict],
        use_semantic: bool = True
    ) -> DeduplicationResult:
        """
        查找重复内容

        Args:
            papers: 论文列表，每项包含 {paper_id, title, pdf_url, hf_url, abstract}
            use_semantic: 是否使用语义相似度（较慢但更准确）

        Returns:
            DeduplicationResult对象
        """
        from .utils import now_iso

        duplicate_groups = []
        processed_ids = set()

        logger.info(f"Starting deduplication for {len(papers)} papers")

        for i, paper1 in enumerate(papers):
            paper1_id = paper1.get('paper_id')

            # 跳过已处理的
            if paper1_id in processed_ids:
                continue

            duplicates = []
            scores = {}
            detection_method = None

            # 与后续论文比较
            for j in range(i + 1, len(papers)):
                paper2 = papers[j]
                paper2_id = paper2.get('paper_id')

                if paper2_id in processed_ids:
                    continue

                # Level 1: URL精确匹配
                arxiv1 = self.normalize_arxiv_id(paper1.get('pdf_url', ''))
                arxiv2 = self.normalize_arxiv_id(paper2.get('pdf_url', ''))

                if arxiv1 and arxiv2 and arxiv1 == arxiv2:
                    duplicates.append(paper2_id)
                    scores[paper2_id] = 1.0
                    detection_method = 'exact_url'
                    logger.info(f"Found exact URL match: {paper1_id} <-> {paper2_id}")
                    continue

                # Level 2: 标题相似度
                title_sim = self.compute_title_similarity(
                    paper1.get('title', ''),
                    paper2.get('title', '')
                )

                if title_sim >= self.config.TITLE_SIMILARITY_THRESHOLD:
                    duplicates.append(paper2_id)
                    scores[paper2_id] = title_sim
                    detection_method = 'title_similarity'
                    logger.info(
                        f"Found title similarity match: {paper1_id} <-> {paper2_id} "
                        f"(score: {title_sim:.2f})"
                    )
                    continue

                # Level 3: 语义相似度（可选）
                if use_semantic and paper1.get('abstract') and paper2.get('abstract'):
                    semantic_sim = self.compute_semantic_similarity(
                        paper1.get('abstract', ''),
                        paper2.get('abstract', '')
                    )

                    if semantic_sim >= self.config.ABSTRACT_SIMILARITY_THRESHOLD:
                        duplicates.append(paper2_id)
                        scores[paper2_id] = semantic_sim
                        detection_method = 'semantic_similarity'
                        logger.info(
                            f"Found semantic similarity match: {paper1_id} <-> {paper2_id} "
                            f"(score: {semantic_sim:.2f})"
                        )

            # 如果找到重复，创建重复组
            if duplicates:
                group = DuplicateGroup(
                    group_id=f"dup_{hashlib.md5(paper1_id.encode()).hexdigest()[:8]}",
                    canonical_paper_id=paper1_id,
                    duplicate_paper_ids=duplicates,
                    similarity_scores=scores,
                    detection_method=detection_method or 'unknown',
                    created_at=now_iso()
                )
                duplicate_groups.append(group)

                # 标记为已处理
                processed_ids.add(paper1_id)
                for dup_id in duplicates:
                    processed_ids.add(dup_id)

        # 计算统计
        total_papers = len(papers)
        duplicates_removed = sum(len(g.duplicate_paper_ids) for g in duplicate_groups)

        result = DeduplicationResult(
            total_papers=total_papers,
            duplicate_groups=duplicate_groups,
            unique_papers=0,  # 会在__post_init__中计算
            duplicates_removed=duplicates_removed
        )

        logger.info(
            f"Deduplication complete: {total_papers} papers, "
            f"{len(duplicate_groups)} groups, "
            f"{duplicates_removed} duplicates removed"
        )

        return result

    def merge_duplicates(
        self,
        papers: List[dict],
        duplicate_group: DuplicateGroup,
        strategy: str = None
    ) -> dict:
        """
        合并重复论文

        Args:
            papers: 所有论文列表
            duplicate_group: 重复组
            strategy: 合并策略 (keep_first | keep_highest_quality | manual)

        Returns:
            合并后的论文dict
        """
        if strategy is None:
            strategy = self.config.MERGE_STRATEGY

        # 获取所有相关论文
        all_ids = [duplicate_group.canonical_paper_id] + duplicate_group.duplicate_paper_ids
        related_papers = [p for p in papers if p.get('paper_id') in all_ids]

        if not related_papers:
            return None

        if strategy == 'keep_first':
            # 保留第一个（canonical）
            canonical = next(
                (p for p in related_papers if p.get('paper_id') == duplicate_group.canonical_paper_id),
                related_papers[0]
            )
            return canonical

        elif strategy == 'keep_highest_quality':
            # 保留质量最高的
            best_paper = max(
                related_papers,
                key=lambda p: p.get('quality_score', 0.0)
            )
            return best_paper

        else:
            # 默认返回第一个
            return related_papers[0]

    def get_deduplication_stats(self, result: DeduplicationResult) -> dict:
        """获取去重统计信息"""
        return {
            'total_papers': result.total_papers,
            'unique_papers': result.unique_papers,
            'duplicate_groups': len(result.duplicate_groups),
            'duplicates_removed': result.duplicates_removed,
            'deduplication_rate': result.duplicates_removed / result.total_papers if result.total_papers > 0 else 0,
            'detection_methods': {
                'exact_url': sum(1 for g in result.duplicate_groups if g.detection_method == 'exact_url'),
                'title_similarity': sum(1 for g in result.duplicate_groups if g.detection_method == 'title_similarity'),
                'semantic_similarity': sum(1 for g in result.duplicate_groups if g.detection_method == 'semantic_similarity'),
            }
        }
