# 智能去重系统实施计划

## 概述

实施多层级相似度检测系统，消除重复内容，节省50%+处理资源。

**实施时间**: 4-6天
**优先级**: ⭐⭐⭐⭐⭐

---

## 实施步骤

### 第一步：创建去重核心模块 (1天)

**文件**: `apd/deduplicator.py`

**功能**:
- Level 1: URL精确匹配（arXiv ID标准化）
- Level 2: 标题相似度（Levenshtein距离 + Jaccard相似度）
- Level 3: 语义相似度（Sentence-BERT embeddings）

**核心类**:
```python
class Deduplicator:
    - find_duplicates()         # 查找重复内容
    - normalize_arxiv_id()      # 标准化arXiv ID
    - compute_title_similarity() # 标题相似度
    - compute_semantic_similarity() # 语义相似度
    - merge_duplicates()        # 合并重复项
```

---

### 第二步：数据库Schema扩展 (0.5天)

**扩展 `apd/db.py`**:

1. 新增 `duplicate_groups` 表
2. Paper数据类添加字段：
   - `title_hash`: 标题哈希值
   - `arxiv_id_normalized`: 标准化的arXiv ID
3. 新增查询函数：
   - `get_duplicate_groups()`
   - `create_duplicate_group()`

---

### 第三步：配置系统扩展 (0.5天)

**扩展 `apd/config.py`**:

```python
class DeduplicationConfig:
    EXACT_MATCH_THRESHOLD = 1.0
    TITLE_SIMILARITY_THRESHOLD = 0.85
    ABSTRACT_SIMILARITY_THRESHOLD = 0.90
    MERGE_STRATEGY = "keep_first"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

---

### 第四步：CLI命令实现 (1天)

**扩展 `apd/cli.py`**:

```bash
# 检测重复
apd dedup --week 2026-05 --show-details

# 自动合并
apd dedup --week 2026-05 --auto-merge

# 查看去重组
apd dedup-groups --status pending
```

---

### 第五步：集成到Fetcher (1天)

**修改**:
- `apd/hf_fetcher.py`
- `apd/github_fetcher.py`
- `apd/news_fetcher.py`

在保存前自动去重检测。

---

### 第六步：测试与优化 (1-2天)

1. 单元测试
2. 集成测试
3. 性能测试
4. 文档编写

---

## 技术依赖

```bash
pip install sentence-transformers scikit-learn python-Levenshtein
```

---

## 预期收益

- ✅ 消除重复视频生成
- ✅ 节省50%+处理资源
- ✅ 提升平台发布质量
- ✅ 减少用户困惑

---

## 风险与缓解

**风险1**: Sentence-BERT模型下载慢
**缓解**: 使用轻量级模型 `all-MiniLM-L6-v2` (90MB)

**风险2**: 误判合法的相似论文
**缓解**: 可配置阈值，默认采用保守策略

**风险3**: 计算开销大
**缓解**: 增量计算，缓存embeddings

---

## 开始实施

准备好了吗？我将开始编写代码！
