# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

Auto Paper Digest (APD) 是一个自动化系统，它从 Hugging Face 获取 AI 论文，从 arXiv 下载 PDF，通过 NotebookLM 生成视频讲解，并将视频发布到 HuggingFace Spaces 和抖音。该系统包含一个基于 Gradio 的门户网站，用于浏览论文和观看视频。

## 开发命令

### 安装与设置
```bash
# 以可编辑模式安装包
pip install -e .

# 安装用于自动化的浏览器
playwright install chromium

# 复制并配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 HF_TOKEN、HF_USERNAME、HF_DATASET_NAME
```

### 测试与运行

**没有正式的测试套件。** 通过手动运行命令进行测试：

```bash
# 测试获取论文
apd fetch --week 2026-01 --max 5

# 使用 headful 模式测试（可看到浏览器界面）
apd upload --week 2026-01 --headful --max 3

# 检查论文处理状态
apd status --week 2026-01

# 本地运行门户网站
cd portal && python app.py
```

### 常用 CLI 命令

```bash
# 内容获取
apd fetch --week 2026-01 --max 10              # HuggingFace 论文
apd fetch-news --date 2026-01-20 --source weibo --max 50  # 微博热搜
apd fetch-github --date 2026-01-20 --language python      # GitHub Trending

# 阶段 1：上传 PDF 并触发视频生成
apd upload --week 2026-01 --max 10 --headful

# 阶段 2：下载已生成的视频
apd download-video --week 2026-01 --headful

# 阶段 3：发布到 HuggingFace
apd publish --week 2026-01

# 阶段 3b：发布到抖音（半自动模式）
apd publish-douyin --week 2026-01 --headful

# 阶段 3c：发布到B站（半自动模式）
apd publish-bilibili --date 2026-01-20 --headful

# 一次性登录命令
apd login              # Google 登录用于 NotebookLM
apd douyin-login       # 抖音创作者平台登录
apd bilibili-login     # B站创作者平台登录（二维码）
```

### 每日自动化脚本

```bash
# 交互式 shell 脚本用于每日论文处理
./daily.sh
```

## 架构

### 三阶段流水线

系统遵循带 SQLite 跟踪的状态化流水线：

```
阶段 1（上传）：
  HF 抓取 → PDF 下载 → NotebookLM 上传 → 触发视频
  状态：NEW → PDF_OK → NBLM_OK

阶段 2（下载）：
  检查 NotebookLM → 下载视频
  状态：NBLM_OK → VIDEO_OK

阶段 3（发布）：
  上传到 HuggingFace Dataset → 更新 metadata.json → 生成摘要
  （可选：发布到抖音）
```

### 状态流转

论文在 `apd.db` 中经历不同状态：
- `NEW`：从 HF 获取的论文（或从 GitHub/新闻站点获取的内容）
- `PDF_OK`：已从 arXiv 下载 PDF
- `NBLM_OK`：已上传到 NotebookLM，视频生成中
- `VIDEO_OK`：视频下载成功
- `ERROR`：处理失败（将根据 retry_count 重试）

### 内容类型

系统支持三种内容类型（`content_type` 字段）：
- `PAPER`：来自 HuggingFace 的学术论文（默认）
- `GITHUB`：GitHub Trending 热门项目
- `NEWS`：热榜新闻（微博/知乎/百度）

不同内容类型在数据库中有专用字段：
- GitHub：`github_stars`, `github_language`, `github_description`
- News：`news_source`, `news_url`
- 发布状态：`bilibili_published`, `douyin_published`

### 按周 vs 按日处理

系统支持两种模式：
- **按周处理**：`--week 2026-01`（处理 ISO 周的论文，使用 `/papers/week/2026-W01` URL）
- **按日处理**：`--date 2026-01-08`（处理特定日期的论文，使用 `/papers/date/2026-01-08` URL）

数据库查询智能匹配周 ID，包括该周内的所有每日日期（周一到周日）。

### 目录结构

```
data/
├── apd.db                     # SQLite 数据库（状态跟踪）
├── .douyin_auth.json          # 抖音登录会话（持久化）
├── .bilibili_auth.json        # B站登录会话（持久化）
├── profiles/
│   ├── default/               # Chromium 配置文件（Google 登录会话）
│   └── bilibili/              # B站浏览器配置文件
├── pdfs/
│   ├── weekly/2026-01/        # 2026-01 周的 PDF
│   └── daily/2026-01-08/      # 2026-01-08 日期的 PDF
├── videos/
│   ├── weekly/2026-01/        # 2026-01 周的视频
│   └── daily/2026-01-08/      # 2026-01-08 日期的视频
└── digests/                   # 生成的 markdown 摘要
```

### 核心模块

#### `apd/cli.py`
主 CLI 入口点。所有命令都在此使用 Click 框架定义。每个命令协调对专用模块的调用。

#### `apd/db.py`
SQLite 数据库层，包含 Paper 数据类。关键特性：
- 灵活的 `_build_week_id_clause()`：匹配周 ID 格式（YYYY-WW），包括该周的所有每日日期
- `upsert_paper()`：仅更新非 None 字段（部分更新）
- `get_papers_for_processing()`：返回准备进入下一流水线阶段的论文

#### `apd/nblm_bot.py`
NotebookLM 的 Playwright 自动化。使用 `data/profiles/default/` 的持久化浏览器上下文来维护跨运行的 Google 登录。关键流程：
1. 导航到 NotebookLM
2. 使用命名约定创建笔记本：`{period_id}_{paper_id}`
3. 上传 PDF，等待内容摄取
4. 触发 Audio Overview 生成（不等待完成）
5. 稍后：通过名称前缀查找笔记本并下载完成的视频

#### `apd/douyin_bot.py`
抖音创作者工作室的 Playwright 自动化。将登录状态保存到 `data/.douyin_auth.json`。处理：
- 二维码登录（手动，headful）
- 视频上传
- 表单填写（标题、描述、标签）
- 支持半自动模式：填写信息后暂停，等待用户手动点击发布

#### `apd/bilibili_bot.py`
B站创作者平台的 Playwright 自动化。使用持久化浏览器上下文（`data/profiles/bilibili/`）。处理：
- 二维码扫码登录（手动，headful）
- 视频上传到创作者中心
- 表单填写（标题最多80字符、简介、标签）
- 支持半自动模式（默认）：填写完成后暂停，等待用户手动点击「立即投稿」

#### `apd/github_fetcher.py`
GitHub Trending 爬虫。使用 BeautifulSoup 解析 HTML：
- 支持按编程语言过滤（`--language python`）
- 支持时间范围：daily, weekly, monthly
- 提取项目信息：名称、stars、语言、描述、forks
- 生成唯一 ID：`github-{owner}-{repo}`
- 直接存入数据库，`content_type='GITHUB'`

#### `apd/news_fetcher.py`
热榜新闻爬虫。支持多个新闻源：
- **微博热搜**：`https://s.weibo.com/top/summary`
- **知乎热榜**：`https://www.zhihu.com/hot`
- **百度热搜**：`https://top.baidu.com/board?tab=realtime`

每个源都有独立的解析函数 `_fetch_weibo_hot()`, `_fetch_zhihu_hot()`, `_fetch_baidu_hot()`。
提取信息：标题、URL、热度值、排名。
生成唯一 ID：`{source}-{hash(title)}`

#### `apd/hf_fetcher.py`
使用 BeautifulSoup 抓取 HuggingFace 论文。两种 URL 策略：
- 按周：`https://huggingface.co/papers/week/2026-W01`
- 按日：`https://huggingface.co/papers/date/2026-01-08`

检测重定向（周末/节假日无论文）并抛出 ValueError。

#### `apd/publisher.py`
使用 `huggingface_hub` 将视频上传到 HuggingFace Dataset。维护 `metadata.json`，结构如下：
```json
{
  "weeks": {
    "2026-01": [
      {"paper_id": "...", "title": "...", "video_url": "...", ...}
    ]
  }
}
```

#### `portal/app.py`
托管在 HuggingFace Spaces 的 Gradio Web 应用。使用 `gr.Blocks` 实现动态 UI：
- 每 5 分钟自动刷新周下拉列表
- 从数据集获取 `metadata.json`（force_download=True 保证新鲜度）
- 将 `/blob/` URL 转换为 `/resolve/` 用于视频流
- 嵌入 `<video>` 标签实现浏览器内播放

### 浏览器自动化模式

1. **持久化上下文**：NotebookLM 和抖音 bot 都使用 Playwright 的 `launch_persistent_context()` 在运行之间保存 cookies/会话
2. **首次运行登录**：必须首次使用 `--headful` 运行 `apd login` 或 `apd douyin-login` 进行手动认证
3. **无头运行**：登录后，自动化默认无头运行（使用 `--headful` 进行调试）
4. **会话验证**：bot 在继续之前检查登录指示器
5. **半自动发布模式**（新增）：
   - 默认模式：脚本上传视频并填写所有信息，然后使用 `input()` 暂停
   - 用户在浏览器中手动检查信息并点击发布按钮
   - 避免自动发布可能导致的错误或违规
   - 使用 `--auto-publish` 标志恢复全自动模式（不推荐）

### 缓存与幂等性

- **PDF 下载**：SHA256 哈希存储在数据库中，如存在匹配文件则跳过
- **视频下载**：检查目标目录中是否存在 `{paper_id}_*.mp4`（使用 `--force` 覆盖）
- **发布**：检查 `metadata.json` 以跳过已发布的论文

### 错误处理

- 处理失败的论文移至 `ERROR` 状态
- `retry_count` 跟踪尝试次数（默认最多 3 次）
- 使用 `apd status --status ERROR` 查找失败的论文
- NotebookLM 错误时截图保存到 `data/profiles/screenshots/`

## 重要实现注意事项

### 添加新命令时
- 在 `apd/cli.py` 中使用 `@main.command()` 装饰器添加
- 对参数使用 Click 选项（遵循现有模式）
- 始终调用 `ensure_directories()` 和 `init_db()`（在 `main()` 组中处理）
- 使用 `utils.py` 的 `get_logger()` 记录日志

### 修改自动化时
- Playwright 选择器很脆弱（UI 更改会破坏 bot）
- 始终为 `wait_for_*()` 调用添加超时
- 为调试截图：`page.screenshot(path="debug.png")`
- 开发期间使用 `slow_mo` 参数查看操作

### 更改数据库模式时
- 在 `init_db()` 中使用 `ALTER TABLE` 配合 try/except 添加迁移
- 永远不要破坏现有列名（仅添加新列）
- 更新 `db.py` 中的 `Paper` 数据类

### 周 ID 格式
- 内部格式：`YYYY-WW`（例如 "2026-01"）
- ISO 周格式：`YYYY-WXX`（例如 "2026-W01"）用于 HF URL
- 转换：`hf_fetcher.py` 中的 `week_id_to_iso_week()`

### 视频命名约定
- NotebookLM 生成文件名：`{paper_id}_{video_title}.mp4`
- 代码按前缀匹配：`{paper_id}_*.mp4`
- 笔记本命名：`{period_id}_{paper_id}`（例如 "2026-01_2401.12345"）

### 必需的环境变量
```bash
HF_TOKEN=hf_...              # HuggingFace 写入令牌
HF_USERNAME=your-username    # HuggingFace 用户名
HF_DATASET_NAME=paper-digest-videos  # 数据集名称
```

## 配置

所有路径、URL 和默认值集中在 `apd/config.py` 中：
- `PROJECT_ROOT`、`DATA_DIR`、子目录
- `PLAYWRIGHT_TIMEOUT`、`PLAYWRIGHT_VIDEO_TIMEOUT`（针对慢速网络调整）
- `DOWNLOAD_DELAY_SECONDS`（arXiv 速率限制）
- `Status` 类包含所有状态常量
- `ContentType` 类：PAPER, GITHUB, NEWS（新增）
- `NEWS_SOURCES` 字典：微博、知乎、百度 URL（新增）
- `GITHUB_TRENDING_URL` 和相关配置（新增）
- `BILIBILI_*` 常量：B站创作者平台 URL（新增）

## 门户部署

`portal/` 目录是一个独立的 HuggingFace Space：
- `app.py`：Gradio 应用
- `requirements.txt`：仅 gradio + huggingface_hub
- `README.md`：Space 元数据（emoji、SDK 版本等）

通过将 `portal/` 内容推送到 HuggingFace Space 仓库来部署。
