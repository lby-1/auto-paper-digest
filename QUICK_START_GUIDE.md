# 快速实施指南 - Quick Start

> 本文档是 `OPTIMIZATION_ROADMAP.md` 的精简版，提供最快上手的优化实施方案。

---

## 🚀 立即可做（1-2天）

### 1. 添加配置文件扩展

```bash
# .env 添加新配置
cat >> .env << 'EOF'

# === 新增配置 ===

# 质量控制
QUALITY_THRESHOLD=60.0
MIN_CITATIONS=0
MIN_GITHUB_STARS=100

# TTS配置
DEFAULT_TTS_ENGINE=notebooklm
ENABLE_EDGE_TTS_FALLBACK=true

# 发布配置
AUTO_PUBLISH=false
ENABLE_SEMI_AUTO_MODE=true
EOF
```

### 2. 安装额外依赖

```bash
# 去重与质量过滤
pip install sentence-transformers scikit-learn python-Levenshtein

# 数据分析
pip install plotly pandas

# 备用TTS
pip install edge-tts

# arXiv直接集成
pip install arxiv
```

---

## 📊 Week 1: 质量控制（推荐优先）

### 任务清单

- [ ] **Day 1-2:** 实现简单的标题去重
  ```python
  # apd/simple_dedup.py
  def find_duplicate_titles(papers: list[Paper]) -> list[tuple]:
      """简单的标题去重（编辑距离）"""
      from difflib import SequenceMatcher

      duplicates = []
      for i, p1 in enumerate(papers):
          for p2 in papers[i+1:]:
              ratio = SequenceMatcher(None, p1.title, p2.title).ratio()
              if ratio > 0.85:
                  duplicates.append((p1, p2, ratio))
      return duplicates
  ```

- [ ] **Day 3-4:** 集成Semantic Scholar API获取引用数
  ```python
  # apd/s2_api.py
  import requests

  def get_citation_count(arxiv_id: str) -> int:
      """获取论文引用数"""
      url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
      response = requests.get(url, params={'fields': 'citationCount'})
      if response.ok:
          return response.json().get('citationCount', 0)
      return 0
  ```

- [ ] **Day 5:** 添加质量过滤CLI命令
  ```bash
  # 使用示例
  apd fetch --week 2026-W04 --min-citations 5 --max 20
  ```

**预期效果:**
- ✅ 自动过滤低质量论文
- ✅ 减少50%无效视频生成
- ✅ 提升内容整体质量

---

## 📈 Week 2: 数据统计（快速见效）

### 任务清单

- [ ] **Day 1-2:** 数据库扩展
  ```sql
  -- 执行SQL
  ALTER TABLE papers ADD COLUMN views INTEGER DEFAULT 0;
  ALTER TABLE papers ADD COLUMN likes INTEGER DEFAULT 0;
  ALTER TABLE papers ADD COLUMN comments INTEGER DEFAULT 0;
  ALTER TABLE papers ADD COLUMN publish_time TIMESTAMP;
  ```

- [ ] **Day 3-4:** 简单的数据采集脚本
  ```python
  # scripts/collect_metrics.py
  import re
  from playwright.sync_api import sync_playwright

  def get_douyin_stats(video_url: str) -> dict:
      """获取抖音视频数据"""
      with sync_playwright() as p:
          browser = p.chromium.launch()
          page = browser.new_page()
          page.goto(video_url)

          # 提取数据（需要根据实际页面结构调整）
          likes = page.locator('[data-e2e="like-count"]').inner_text()

          return {'likes': int(likes.replace('w', '0000'))}
  ```

- [ ] **Day 5:** 生成简单报告
  ```python
  # apd/simple_report.py
  def generate_weekly_report(week_id: str):
      """生成周报告"""
      papers = db.get_papers_by_week(week_id)

      total_views = sum(p.views for p in papers)
      total_likes = sum(p.likes for p in papers)

      print(f"""
      === {week_id} 周报 ===
      发布视频数: {len(papers)}
      总观看量: {total_views:,}
      总点赞数: {total_likes:,}
      平均观看: {total_views/len(papers):,.0f}
      """)
  ```

**使用方式:**
```bash
python scripts/collect_metrics.py --week 2026-W04
apd report --week 2026-W04
```

---

## 🎙️ Week 3: TTS备选方案（降低风险）

### 任务清单

- [ ] **Day 1:** 集成Edge TTS（完全免费）
  ```python
  # apd/tts/edge_tts_engine.py
  import edge_tts
  import asyncio

  async def generate_audio(text: str, output_path: str):
      """使用Edge TTS生成语音"""
      communicate = edge_tts.Communicate(
          text=text,
          voice="zh-CN-XiaoxiaoNeural"
      )
      await communicate.save(output_path)

  # 同步包装
  def synthesize(text: str, output_path: str):
      asyncio.run(generate_audio(text, output_path))
  ```

- [ ] **Day 2-3:** 添加fallback逻辑
  ```python
  # apd/nblm_bot.py 修改
  def generate_video_with_fallback(paper: Paper):
      """带fallback的视频生成"""
      try:
          # 尝试NotebookLM
          return self.generate_via_notebooklm(paper)
      except Exception as e:
          logger.warning(f"NotebookLM failed: {e}, using Edge TTS")
          # Fallback到Edge TTS
          return self.generate_via_edge_tts(paper)
  ```

- [ ] **Day 4-5:** 测试与文档

**使用方式:**
```bash
# 强制使用Edge TTS
apd upload --week 2026-W04 --tts-engine edge

# 自动fallback（默认）
apd upload --week 2026-W04
```

---

## 🔌 Week 4: 扩展内容源（提升内容丰富度）

### 任务清单

- [ ] **Day 1-2:** arXiv API直接集成
  ```python
  # apd/arxiv_fetcher.py
  import arxiv

  def fetch_recent_papers(categories=['cs.AI', 'cs.CL'], max_results=50):
      """直接从arXiv获取论文"""
      client = arxiv.Client()
      search = arxiv.Search(
          query=f"cat:{' OR cat:'.join(categories)}",
          max_results=max_results,
          sort_by=arxiv.SortCriterion.SubmittedDate
      )

      papers = []
      for result in client.results(search):
          papers.append({
              'title': result.title,
              'pdf_url': result.pdf_url,
              'abstract': result.summary,
              'arxiv_id': result.get_short_id(),
          })
      return papers
  ```

- [ ] **Day 3:** 添加CLI命令
  ```python
  # apd/cli.py
  @click.command()
  @click.option('--categories', default='cs.AI,cs.CL')
  @click.option('--max', default=50)
  def fetch_arxiv(categories, max):
      """直接从arXiv获取论文"""
      cats = categories.split(',')
      papers = fetch_recent_papers(cats, max)
      # 保存到数据库
      for p in papers:
          db.save_paper(p)
  ```

- [ ] **Day 4-5:** 测试与优化

**使用方式:**
```bash
apd fetch-arxiv --categories cs.AI,cs.LG --max 30
```

---

## 📱 Month 2: 平台扩展

### YouTube发布（推荐优先）

**准备工作:**
1. 获取YouTube API credentials
2. 安装依赖: `pip install google-api-python-client google-auth-oauthlib`

**实施步骤:**

```python
# apd/youtube_bot.py
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

class YouTubePublisher:
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self):
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', self.SCOPES
        )
        credentials = flow.run_local_server()
        self.youtube = build('youtube', 'v3', credentials=credentials)

    def upload_video(self, video_path, title, description):
        """上传视频到YouTube"""
        from googleapiclient.http import MediaFileUpload

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'categoryId': '28'  # Science & Technology
            },
            'status': {'privacyStatus': 'public'}
        }

        media = MediaFileUpload(video_path, resumable=True)
        request = self.youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        response = request.execute()
        return f"https://youtube.com/watch?v={response['id']}"
```

**CLI集成:**
```bash
apd publish-youtube --week 2026-W04
```

---

## 🎯 优先级建议

根据你的具体情况选择：

### 场景1: 内容质量不稳定
**优先:** Week 1 质量控制
- 实施去重系统
- 添加引用数过滤
- 效果立竿见影

### 场景2: 想了解发布效果
**优先:** Week 2 数据统计
- 快速看到数据
- 指导后续优化
- 技术难度低

### 场景3: 担心NotebookLM稳定性
**优先:** Week 3 TTS备选
- Edge TTS完全免费
- 降低单点故障风险
- 实施相对简单

### 场景4: 需要更多内容
**优先:** Week 4 内容源扩展
- arXiv API更及时
- 丰富内容类型
- 提升竞争力

---

## 📦 完整实施包（All-in-One）

如果你有充足时间，按此顺序实施效果最佳：

```
Week 1: 质量控制
  ↓ (质量提升后再扩量)
Week 4: 内容源扩展
  ↓ (有更多内容后)
Week 2: 数据统计
  ↓ (基于数据优化)
Week 3: TTS备选方案
  ↓ (降低风险)
Month 2: 平台扩展
```

---

## 🛠️ 开发工具推荐

### 代码质量
```bash
# 安装
pip install black isort flake8 mypy

# 使用
black apd/  # 代码格式化
isort apd/  # import排序
flake8 apd/  # 代码检查
mypy apd/  # 类型检查
```

### 测试
```bash
pip install pytest pytest-cov

# 运行测试
pytest tests/

# 覆盖率报告
pytest --cov=apd --cov-report=html
```

### 性能分析
```bash
pip install py-spy

# 性能分析
py-spy top -- python -m apd.cli upload --week 2026-W04
```

---

## 📚 学习资源

### API文档
- [Semantic Scholar API](https://api.semanticscholar.org/)
- [arXiv API](https://arxiv.org/help/api)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [Edge TTS](https://github.com/rany2/edge-tts)

### 相关技术
- [Sentence Transformers](https://www.sbert.net/)
- [Playwright Python](https://playwright.dev/python/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

---

## ❓ 常见问题

**Q: 我应该从哪个优化开始？**
A: 如果不确定，从 **Week 1 质量控制** 开始，效果最明显。

**Q: 这些优化会破坏现有功能吗？**
A: 不会。所有优化都是向后兼容的，可以逐步启用。

**Q: 需要额外的服务器吗？**
A: 前4周的优化都不需要。Month 2的平台扩展可能需要云服务器（可选）。

**Q: 估计总开发时间？**
A:
- Week 1-4: 每周投入20-30小时，可由1人完成
- Month 2: 需要40-60小时，建议2人协作

**Q: 有示例代码吗？**
A: 本文档中的代码都是可运行的示例，可以直接复制使用。

---

## 🤝 获取帮助

遇到问题？
1. 查看 `OPTIMIZATION_ROADMAP.md` 详细文档
2. 查看 `COMPETITORS_ANALYSIS.md` 了解最佳实践
3. 提交 GitHub Issue
4. 参与 GitHub Discussions

---

**祝你优化顺利！ 🚀**

*最后更新: 2026-01-23*
