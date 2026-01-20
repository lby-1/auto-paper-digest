# 🚀 Auto Paper Digest (APD)

> **原项目地址**: [https://github.com/brianxiadong/auto-paper-digest](https://github.com/brianxiadong/auto-paper-digest)
> 本仓库为 Fork 版本，在原项目基础上扩展了多源内容获取和多平台发布功能。

<p align="center">
  <strong>自动获取多源内容 → 生成视频讲解 → 多平台发布 → 门户网站展示</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/NotebookLM-Automation-orange.svg" alt="NotebookLM">
  <img src="https://img.shields.io/badge/HuggingFace-Spaces-yellow.svg" alt="HuggingFace">
  <img src="https://img.shields.io/badge/Bilibili-Creator-00A1D6.svg" alt="Bilibili">
  <img src="https://img.shields.io/badge/Douyin-Creator-ff0050.svg" alt="Douyin">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

<br>

---

## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 📚 **多源内容获取** | 支持 HuggingFace 论文、GitHub Trending、热榜新闻（微博/知乎/百度） |
| 📄 **PDF 下载** | 从 arXiv 下载论文 PDF（幂等操作，SHA256 校验） |
| 🎬 **视频生成** | 通过 NotebookLM 自动生成视频讲解 |
| 📤 **自动发布** | 上传视频到 HuggingFace Dataset |
| 📱 **多平台发布** | 支持抖音和B站创作者平台（半自动发布模式） |
| 🌐 **门户网站** | Gradio 门户网站，在线播放视频 |
| 💾 **断点续传** | SQLite 状态追踪，支持中断后继续 |
| 🔐 **登录复用** | Google/抖音/B站登录状态持久化，一次登录长期使用 |

---

## 🆕 本次更新内容 (v2.0)

### 新增功能

#### 1️⃣ 多源内容获取
- ✅ **GitHub Trending**：获取热门开源项目，支持按编程语言过滤
- ✅ **热榜新闻**：支持微博热搜、知乎热榜、百度热搜
- ✅ **灵活日期处理**：所有命令支持 `--week` 和 `--date` 参数

#### 2️⃣ B站创作者平台集成
- ✅ 二维码扫码登录
- ✅ 视频自动上传和信息填写
- ✅ 半自动发布模式（默认）：填写完成后暂停，等待用户手动点击发布

#### 3️⃣ 半自动发布模式
- ✅ **安全发布**：脚本完成上传和信息填写后暂停
- ✅ **人工确认**：用户在浏览器中检查无误后手动点击发布按钮
- ✅ **避免误发**：防止自动化导致的错误或违规发布
- ✅ **双平台支持**：抖音和B站均支持半自动模式

#### 4️⃣ 数据库增强
- ✅ 内容类型：`PAPER` / `GITHUB` / `NEWS`
- ✅ 平台发布状态追踪：`bilibili_published` / `douyin_published`
- ✅ GitHub 项目信息：stars、language、description
- ✅ 新闻信息：source、url

### 新增命令

```bash
# 内容获取
apd fetch-news --date 2026-01-20 --source weibo    # 获取热榜新闻
apd fetch-github --date 2026-01-20 --language python  # 获取 GitHub Trending

# 平台登录
apd bilibili-login                                   # B站创作者登录

# 内容发布
apd publish-bilibili --date 2026-01-20 --headful   # B站发布（半自动）
apd publish-douyin --date 2026-01-20 --headful     # 抖音发布（半自动）
```

### 技术亮点

- 🎯 **模块化设计**：独立的爬虫模块（`github_fetcher.py`, `news_fetcher.py`）
- 🔒 **安全发布**：半自动模式避免自动化风险
- 📊 **类型系统**：ContentType 枚举支持多源内容
- 🗃️ **向后兼容**：数据库迁移保持现有数据完整性

---

## 📐 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Auto Paper Digest                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Phase 1: Upload            Phase 2: Download      Phase 3: Publish │
│   ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌──────────────┐ │
│   │   HF    │───▶│  arXiv  │───▶│ NotebookLM  │───▶│  HuggingFace │ │
│   │ Papers  │    │  PDFs   │    │   Videos    │    │   Dataset    │ │
│   └─────────┘    └─────────┘    └─────────────┘    └──────────────┘ │
│        │               │               │                   │         │
│        ▼               ▼               ▼                   ▼         │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    SQLite Database                           │   │
│   │      (status: NEW → PDF_OK → NBLM_OK → VIDEO_OK)            │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│              ┌───────────────┼───────────────┐                       │
│              ▼               ▼               ▼                       │
│   ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐               │
│   │ Portal Website  │ │   Douyin    │ │   Other     │               │
│   │  (HF Spaces)    │ │  Creator    │ │  Platforms  │               │
│   └─────────────────┘ └─────────────┘ └─────────────┘               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/brianxiadong/auto-paper-digest.git
cd auto-paper-digest

# 安装依赖
pip install -e .

# 安装浏览器
playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 填入 HuggingFace 配置
# HF_TOKEN=hf_xxx
# HF_USERNAME=your-username
# HF_DATASET_NAME=paper-digest-videos
```

### 3. 首次登录 Google

```bash
apd login
```

> 浏览器会打开 NotebookLM 登录页面，完成 Google 登录后，会话将被保存。

---

## 📖 三阶段工作流

### Phase 1: 上传并触发视频生成

```bash
apd upload --week 2026-01 --headful --max 10
```

该命令会：
- ✅ 获取 HuggingFace 本周论文（使用 `/week/YYYY-WXX` URL）
- ✅ 下载 arXiv PDF（支持缓存，已下载的跳过）
- ✅ 上传到 NotebookLM
- ✅ 触发视频生成（不等待完成）

### Phase 2: 下载生成的视频

等待几分钟后（视频生成需要时间），运行：

```bash
apd download-video --week 2026-01 --headful
```

支持缓存！已下载的视频会自动跳过，使用 `--force` 强制重新下载。

### Phase 3: 发布到 HuggingFace

```bash
apd publish --week 2026-01
```

该命令会：
- ✅ 上传视频到 HuggingFace Dataset
- ✅ 更新 metadata.json
- ✅ 生成 Markdown 摘要

### Phase 3b: 发布到抖音（可选）

首次使用需要先登录抖音：

```bash
apd douyin-login
```

> 浏览器会打开抖音创作者中心登录页面，使用抖音 APP 扫码登录，登录状态将被保存。

然后发布视频到抖音：

```bash
apd publish-douyin --week 2026-01 --headful
```

该命令会：
- ✅ 自动上传视频到抖音创作者平台
- ✅ 填写视频标题（论文标题）
- ✅ 添加话题标签（AI、论文解读等）
- ✅ 自动点击发布

> 💡 **提示**：首次使用建议添加 `--headful` 参数观察发布过程，确认无误后可去掉该参数。

---

## 📅 按日处理（可选）

除了按周处理外，也支持按日期处理论文：

```bash
# 获取指定日期的论文
apd fetch --date 2026-01-08 --max 10

# 上传并生成视频
apd upload --date 2026-01-08 --headful --max 10

# 下载视频
apd download-video --date 2026-01-08 --headful

# 发布到抖音
apd publish-douyin --date 2026-01-08 --headful
```

> ⚠️ **注意**：周末和节假日没有论文，系统会提示错误而非继续处理。

### 文件夹结构

按日和按周的数据分开存放：
- `data/pdfs/weekly/2026-01/` - 按周处理的 PDF
- `data/pdfs/daily/2026-01-08/` - 按日处理的 PDF
- `data/videos/weekly/2026-01/` - 按周处理的视频
- `data/videos/daily/2026-01-08/` - 按日处理的视频

---

### 🌐 门户网站

视频发布后，可在 HuggingFace Spaces 门户网站直接观看：

```
https://huggingface.co/spaces/your-username/paper-digest
```

---

## 📖 命令大全

### 登录命令
| 命令 | 说明 |
|------|------|
| `apd login` | 打开浏览器完成 Google 登录（NotebookLM） |
| `apd douyin-login` | 打开浏览器完成抖音登录 |
| `apd bilibili-login` | 打开浏览器完成B站创作者登录（扫码） |

### 内容获取命令
| 命令 | 说明 |
|------|------|
| `apd fetch` | 获取 HuggingFace 论文列表 |
| `apd fetch-news` | 获取热榜新闻（微博/知乎/百度） |
| `apd fetch-github` | 获取 GitHub Trending 项目 |

### 处理与发布命令
| 命令 | 说明 |
|------|------|
| `apd download` | 仅下载 PDF（支持缓存） |
| `apd upload` | **Phase 1**：获取 + 下载 + 上传 + 触发生成 |
| `apd download-video` | **Phase 2**：下载已生成的视频（支持缓存） |
| `apd publish` | **Phase 3**：发布到 HuggingFace |
| `apd publish-douyin` | **Phase 3b**：发布到抖音（半自动模式） |
| `apd publish-bilibili` | **Phase 3c**：发布到B站（半自动模式） |

### 其他命令
| 命令 | 说明 |
|------|------|
| `apd digest` | 生成本地周报 |
| `apd run` | 完整流程（一键执行，需等待视频生成） |
| `apd status` | 查看内容处理状态 |

### 常用参数

```bash
--week, -w        指定周 ID（如 2026-01），默认当前周
--date, -d        指定日期（如 2026-01-20），按日期处理
--max, -m         最大内容数量
--headful         显示浏览器窗口（调试时使用）
--force, -f       强制重新处理（忽略缓存）
--auto-publish    自动点击发布按钮（默认半自动模式）
--debug           开启调试日志
```

---

## 🌟 多源内容获取

### 获取 GitHub Trending

```bash
# 获取当日 GitHub Trending 项目
apd fetch-github --date 2026-01-20 --max 20

# 按周获取，指定编程语言
apd fetch-github --week 2026-03 --language python --since weekly

# 支持的时间范围：daily, weekly, monthly
apd fetch-github --date 2026-01-20 --since monthly --max 30
```

### 获取热榜新闻

```bash
# 获取微博热搜
apd fetch-news --date 2026-01-20 --source weibo --max 50

# 获取知乎热榜
apd fetch-news --date 2026-01-20 --source zhihu --max 30

# 获取百度热搜
apd fetch-news --date 2026-01-20 --source baidu --max 50

# 按周获取（使用当前日期标识）
apd fetch-news --week 2026-03 --source weibo
```

### 多平台发布

#### 发布到抖音（半自动模式）

```bash
# 首次登录
apd douyin-login

# 半自动发布：脚本填写信息，用户手动点击发布
apd publish-douyin --date 2026-01-20 --headful

# 自动发布（不推荐）
apd publish-douyin --date 2026-01-20 --headful --auto-publish
```

#### 发布到B站（半自动模式）

```bash
# 首次登录
apd bilibili-login

# 半自动发布：脚本上传并填写信息，暂停等待用户手动发布
apd publish-bilibili --date 2026-01-20 --headful

# 自动发布（不推荐）
apd publish-bilibili --date 2026-01-20 --headful --auto-publish
```

> 💡 **半自动模式说明**：默认情况下，脚本会完成视频上传和信息填写，然后暂停等待用户检查并手动点击发布按钮。这样可以在发布前进行最后确认，避免错误发布。

---

## 📁 目录结构

```
auto-paper-digest/
├── apd/                    # 主程序包
│   ├── cli.py              # 命令行入口
│   ├── config.py           # 配置常量
│   ├── db.py               # SQLite 数据库
│   ├── hf_fetcher.py       # HF 论文抓取
│   ├── github_fetcher.py   # GitHub Trending 爬虫（新增）
│   ├── news_fetcher.py     # 热榜新闻爬虫（新增）
│   ├── pdf_downloader.py   # PDF 下载器
│   ├── nblm_bot.py         # NotebookLM 自动化
│   ├── douyin_bot.py       # 抖音创作者平台自动化
│   ├── bilibili_bot.py     # B站创作者平台自动化（新增）
│   ├── publisher.py        # HuggingFace 发布
│   ├── digest.py           # 周报生成
│   └── utils.py            # 工具函数
├── portal/                 # HuggingFace Spaces 门户
│   ├── app.py              # Gradio 应用
│   ├── requirements.txt
│   └── README.md
├── data/
│   ├── apd.db              # SQLite 数据库
│   ├── .douyin_auth.json   # 抖音登录状态
│   ├── .bilibili_auth.json # B站登录状态（新增）
│   ├── pdfs/               # 下载的 PDF（按周/日期分目录）
│   ├── videos/             # 生成的视频（按周/日期分目录）
│   ├── digests/            # 周报文件
│   └── profiles/           # 浏览器配置（含登录态）
├── CLAUDE.md               # AI 助手开发文档
├── CLAUDE_CN.md            # AI 助手开发文档（中文）
├── EXTENSION_PLAN.md       # 扩展计划文档
├── .env.example            # 环境变量模板
└── pyproject.toml
```

---

## � 缓存机制

### PDF 缓存
- 已下载的 PDF 通过 SHA256 校验
- 相同文件自动跳过

### 视频缓存
- 使用文件名前缀匹配（`{paper_id}_*.mp4`）
- 支持新的命名格式：`{paper_id}_{video_title}.mp4`
- 使用 `--force` 强制重新下载

### 发布缓存
- metadata.json 中记录已发布的论文
- 重复发布自动跳过

---

## 📊 状态追踪

```
NEW → PDF_OK → NBLM_OK → VIDEO_OK
 │                          │
 └──────── ERROR ◄──────────┘
```

| 状态 | 含义 |
|------|------|
| `NEW` | 论文已抓取，待处理 |
| `PDF_OK` | PDF 已下载 |
| `NBLM_OK` | 已上传到 NotebookLM，视频生成中 |
| `VIDEO_OK` | 视频已下载 |
| `ERROR` | 处理失败（会自动重试） |

查看状态：

```bash
apd status --week 2026-01
apd status --week 2026-01 --status ERROR
```

---

## 🔧 故障排除

### 登录问题

```bash
apd login
```

### NotebookLM 界面变化

查看截图：

```bash
ls data/profiles/screenshots/
```

### 视频未生成

视频生成需要几分钟时间，请稍后重试：

```bash
apd download-video --week 2026-01 --headful
```

### HuggingFace Token 问题

确保 `.env` 文件配置正确：

```bash
cat .env
# 检查 HF_TOKEN 和 HF_USERNAME
```

---

## 🤝 技术栈

- **Python 3.11+** - 核心语言
- **Playwright** - 浏览器自动化
- **SQLite** - 状态持久化
- **Click** - CLI 框架
- **Requests + BeautifulSoup** - 网页抓取
- **huggingface_hub** - HF API
- **Gradio** - 门户网站
- **python-dotenv** - 环境变量管理

---

## 📄 License

MIT License © 2026
