# 质量控制系统 - 使用指南

## 概述

质量控制系统为 Auto-Paper-Digest 项目添加了智能内容筛选功能,支持论文、GitHub项目和新闻内容的质量评分与过滤。

## 功能特性

- **多维度评分**: 基于引用数、会议等级、时效性等维度综合评分
- **自动过滤**: 自动过滤低质量内容,减少无效视频生成
- **灵活配置**: 通过环境变量调整质量阈值
- **数据驱动**: 提供详细的评分理由,便于分析优化

## 快速开始

### 1. 配置环境变量

在 `.env` 文件中添加:

```bash
# 质量控制配置
MIN_QUALITY_SCORE=60.0      # 最低质量评分 (0-100)
MIN_CITATIONS=0             # 论文最低引用数
MIN_GITHUB_STARS=100        # GitHub项目最低星标数

# 可选: Semantic Scholar API
# S2_API_KEY=your-api-key
# ENABLE_S2=false
```

### 2. 获取内容并自动评分

```bash
# 获取本周论文并自动评分
apd fetch --week 2026-05

# 获取GitHub项目并自动评分
apd fetch-github --date 2026-02-03

# 获取新闻热点并自动评分
apd fetch-news --date 2026-02-03 --source zhihu
```

### 3. 查看质量评分

```bash
# 显示所有内容及其质量评分
apd status --show-scores

# 只显示高质量内容 (评分 >= 70)
apd status --min-quality 70 --show-scores

# 查看被过滤的内容
apd status --min-quality 0 --show-scores | grep 🚫
```

## 评分维度

### 论文评分 (Paper)

| 维度 | 权重 | 说明 |
|------|------|------|
| 引用数 | 35% | 基于Semantic Scholar API (可选) |
| 作者 | 25% | 作者H-index和影响力 (暂用默认值) |
| 会议/期刊 | 30% | CCF等级、影响因子 (暂用URL完整性) |
| 时效性 | 10% | 发表时间距今 (基于arXiv ID) |

**示例:**

```python
from apd.quality_filter import QualityFilter

filter = QualityFilter()
score = filter.evaluate_paper(
    title="Attention Is All You Need",
    pdf_url="https://arxiv.org/pdf/2601.03252.pdf",
    hf_url="https://huggingface.co/papers/2601.03252"
)

print(f"质量评分: {score.total_score:.2f}")
print(f"是否通过: {score.passed}")
print(f"评分理由: {score.reasons}")
```

### GitHub项目评分

| 维度 | 权重 | 说明 |
|------|------|------|
| Stars数量 | 40% | 对数评分,100 stars=50分,10000 stars=100分 |
| 编程语言 | 20% | Python=100, JavaScript/TypeScript=95, 等 |
| 活跃度 | 40% | 描述完整性 (当前实现) |

**示例:**

```python
score = filter.evaluate_github_project(
    name="pytorch",
    stars=50000,
    language="Python",
    description="Deep learning framework"
)
# 预期: 90.80 分,通过
```

### 新闻评分

| 维度 | 权重 | 说明 |
|------|------|------|
| 排名 | 60% | Top 10=100分, Top 20=80分, Top 50=60分 |
| 来源 | 40% | 知乎=0.9, 微博=0.8, 百度=0.7 |

**示例:**

```python
score = filter.evaluate_news(
    title="重大科技突破",
    rank=5,
    source="zhihu",
    hot_value="100万"
)
# 预期: 96.00 分,通过
```

## 数据库Schema

质量控制系统为 `papers` 表添加了以下字段:

```sql
-- 评分字段
quality_score REAL          -- 综合质量评分 (0-100)
citation_score REAL         -- 引用数评分
venue_score REAL            -- 会议/期刊评分
recency_score REAL          -- 时效性评分
quality_reasons TEXT        -- JSON字符串: 评分详情

-- 过滤状态
filtered_out INTEGER        -- 是否被过滤 (0/1)
filter_reason TEXT          -- 过滤原因
evaluated_at TEXT           -- 评估时间戳
```

## 高级用法

### 1. 按质量过滤处理流程

```bash
# 只下载高质量论文 (评分 >= 70)
apd download --week 2026-05 --min-quality 70

# 只为高质量内容生成视频
apd download-video --week 2026-05 --min-quality 70
```

### 2. 质量分析

```python
from apd.db import list_papers_by_quality

# 获取所有高质量内容
high_quality = list_papers_by_quality(
    week_id="2026-05",
    min_quality_score=70.0,
    include_filtered=False
)

# 统计各评分段分布
score_ranges = {
    "优秀 (80-100)": 0,
    "良好 (70-80)": 0,
    "中等 (60-70)": 0,
    "较差 (<60)": 0
}

for paper in high_quality:
    if paper.quality_score >= 80:
        score_ranges["优秀 (80-100)"] += 1
    elif paper.quality_score >= 70:
        score_ranges["良好 (70-80)"] += 1
    elif paper.quality_score >= 60:
        score_ranges["中等 (60-70)"] += 1
    else:
        score_ranges["较差 (<60)"] += 1

print(score_ranges)
```

### 3. 自定义评分权重

修改 `apd/config.py` 中的 `QualityConfig` 类:

```python
class QualityConfig:
    # 调整评分权重 (总和必须为1.0)
    CITATION_WEIGHT = 0.40  # 增加引用权重
    AUTHOR_WEIGHT = 0.20    # 减少作者权重
    VENUE_WEIGHT = 0.30
    RECENCY_WEIGHT = 0.10

    # 调整质量阈值
    MIN_QUALITY_SCORE = 70.0  # 更严格的阈值
```

## 预期效果

实施质量控制系统后,预期可以达到:

- ✅ 内容质量提升 30-50%
- ✅ 减少 40% 无效视频生成
- ✅ 节省 30% 处理资源
- ✅ 提高观众留存率
- ✅ 降低人工审核负担

## 故障排查

### 问题1: 评分过低,大量内容被过滤

**解决方案**: 降低 `MIN_QUALITY_SCORE` 阈值

```bash
# .env
MIN_QUALITY_SCORE=50.0  # 从60降到50
```

### 问题2: 无法获取真实引用数

**解决方案**: 配置Semantic Scholar API

```bash
# .env
S2_API_KEY=your-semantic-scholar-api-key
ENABLE_S2=true
```

### 问题3: 某些高质量内容被误判

**解决方案**: 调整评分权重或白名单特定来源

```python
# 在 quality_filter.py 中添加白名单逻辑
if paper_id in WHITELIST:
    score.total_score = 100.0
    score.passed = True
```

## 后续扩展

### 计划中的功能

1. **Semantic Scholar集成**
   - 获取真实引用数和H-index
   - 识别会议等级 (CCF A/B/C)

2. **机器学习评分模型**
   - 基于历史播放数据训练模型
   - 预测视频播放量

3. **A/B测试框架**
   - 测试不同阈值的效果
   - 数据驱动优化参数

## 测试

运行单元测试:

```bash
python tests/test_quality_filter.py
```

预期输出:

```
============================================================
质量控制系统单元测试
============================================================

✓ Paper score: 30.50
✓ Short title rejected
✓ High-star project passed: 90.80
✓ Low-star project rejected
✓ Top 10 news passed: 96.00
✓ Low-rank news rejected: 56.00
✓ Unified interface works for all content types
✓ QualityScore dataclass working correctly

============================================================
所有测试通过!
============================================================
```

## 贡献

欢迎提交Issue和Pull Request来改进质量控制系统!

## 许可证

与主项目保持一致。
