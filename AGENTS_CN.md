# 项目知识库

**生成时间：** 2026-01-20
**提交：** N/A (本地仓库)
**分支：** main

## 概述
Auto Paper Digest (APD) - Python CLI 工具，从 Hugging Face 获取 AI 论文，通过 NotebookLM 生成视频讲解，并发布到 HuggingFace Spaces/抖音。三阶段流水线，使用 SQLite 进行状态跟踪。

## 项目结构
```
auto-paper-digest/
├── apd/                    # 核心包（11 个模块，5414 行代码）
│   ├── cli.py              # Click CLI - 12 个命令（fetch, upload, publish 等）
│   ├── config.py           # 中央配置（路径、URL、Status 常量）
│   ├── db.py               # SQLite 层，包含 Paper 数据类
│   ├── nblm_bot.py        # NotebookLM 自动化（1731 行代码 - 最大的模块）
│   ├── douyin_bot.py      # 抖音创作者平台自动化
│   ├── hf_fetcher.py      # HF 论文爬虫（周/日 URL 模式）
│   ├── pdf_downloader.py   # arXiv PDF 下载器（SHA256 缓存）
│   ├── publisher.py       # HF Dataset 上传器 + metadata.json
│   ├── digest.py          # 周报生成器
│   └── utils.py          # 日志、哈希、周工具函数
├── portal/                # Gradio Web 应用（HF Space）
│   ├── app.py            # 视频播放器，从 metadata.json 获取数据
│   └── requirements.txt  # gradio, huggingface_hub
├── data/                 # 运行时数据（已 gitignore）
│   ├── apd.db           # SQLite 数据库
│   ├── profiles/         # 浏览器会话（持久化上下文）
│   ├── pdfs/            # weekly/2026-01/ 和 daily/2026-01-08/
│   └── videos/          # weekly/2026-01/ 和 daily/2026-01-08/
├── daily.sh              # 交互式工作流脚本
├── pyproject.toml        # setuptools 构建，CLI 入口：apd = "apd.cli:main"
└── README.md             # 完整文档（架构、命令）
```

## 去哪里找
| 任务 | 位置 | 说明 |
|------|----------|-------|
| **添加 CLI 命令** | `apd/cli.py` | 使用 `@main.command()` 装饰器，遵循 Click 模式 |
| **修改数据库** | `apd/db.py` | 在 `init_db()` 中添加迁移，使用 try/except，更新 Paper 数据类 |
| **修改自动化** | `apd/nblm_bot.py` 或 `apd/douyin_bot.py` | Playwright 选择器脆弱，使用 `--headful` 调试 |
| **HF 爬取** | `apd/hf_fetcher.py` | 两种 URL 模式：`/week/YYYY-WXX` 和 `/date/YYYY-MM-DD` |
| **Portal 修改** | `portal/app.py` | Gradio 应用，自动刷新周列表，将 /blob/ 转换为 /resolve/ |
| **配置常量** | `apd/config.py` | 所有路径、URL、超时、Status 类 |
| **周报生成** | `apd/digest.py` | Markdown + JSON 输出 |
| **发布** | `apd/publisher.py` | 上传到 HF Dataset，更新 metadata.json |

## 约定（与标准的不同之处）

**CLI 模式：**
- Click 框架，所有命令在 `cli.py` 中
- 始终调用 `ensure_directories()` 和 `init_db()`（在 main() 组中处理）
- 使用 utils.py 中的 `get_logger()` 进行日志记录
- 所有自动化命令都有 `--headful` 标志用于可视化调试

**周与日期处理：**
- 内部周 ID：`YYYY-WW`（例如 "2026-01"）
- URL 的 ISO 周：`YYYY-WXX`（例如 "2026-W01"）
- 数据库查询匹配周 ID 以包含该周的所有日期
- `--week` 和 `--date` 是互斥的

**浏览器自动化：**
- 持久化上下文：`launch_persistent_context()` 保存登录状态
- 首次运行登录：必须是 `--headful` 进行手动认证
- 会话持久化：Google 登录在 `data/profiles/default/`，抖音在 `data/.douyin_auth.json`
- 开发期间使用 `slow_mo`，为 `wait_for_*()` 调用添加超时
- 错误时截图：`data/profiles/screenshots/`

**流水线状态流：**
```
NEW → PDF_OK → NBLM_OK → VIDEO_OK
 │                          │
 └──────── ERROR ◄──────────┘
```

**视频/Notebook 命名：**
- NotebookLM：`{paper_id}_{video_title}.mp4`
- Notebooks：`{period_id}_{paper_id}`（例如 "2026-01_2401.12345"）
- 按前缀匹配：`{paper_id}_*.mp4`

**缓存与幂等性：**
- PDF：SHA256 哈希存储在 DB 中，如果存在匹配文件则跳过
- 视频：检查 `{paper_id}_*.mp4` 是否存在，使用 `--force` 覆盖
- 发布：检查 `metadata.json` 以跳过已发布的论文

## 反模式（本项目）
- **没有测试套件**：仅通过 CLI 命令配合 `--headful` 标志进行手动测试
- **没有 CI/CD**：没有 .github/workflows，PR 上没有自动化测试
- **没有代码检查**：没有配置 ruff、flake8、mypy 或 pre-commit hooks
- **没有 LICENSE 文件**：pyproject.toml 声明 MIT 但不存在 LICENSE 文件
- **双重依赖文件**：主依赖在 pyproject.toml 中，portal 依赖在 portal/requirements.txt 中

## 独特风格
- **三阶段流水线**：Upload → Download-video → Publish-douyin（分离的命令，非原子操作）
- **交互式每日脚本**：`daily.sh` 带有菜单驱动的工作流，用于常规操作
- **手动操作优先**：强调开发者控制而非自动化（无 CI/CD）
- **内置浏览器调试**：所有 Playwright 命令都有 `--headful` 标志

## 命令
```bash
# 安装
pip install -e .
playwright install chromium
cp .env.example .env  # 配置 HF_TOKEN, HF_USERNAME, HF_DATASET_NAME

# 阶段 1：获取 + 上传 + 触发视频生成
apd upload --week 2026-01 --headful --max 10

# 阶段 2：下载生成的视频（先等待 5-10 分钟）
apd download-video --week 2026-01 --headful

# 阶段 3：发布到 HuggingFace
apd publish --week 2026-01

# 阶段 3b：发布到抖音（可选）
apd douyin-login  # 首次使用：扫码
apd publish-douyin --week 2026-01 --headful

# 状态检查
apd status --week 2026-01
apd status --week 2026-01 --status ERROR

# Portal 测试
cd portal && python app.py
```

## 注意事项
- **周末/节假日日期**：HF 论文页面会重定向，抛出 ValueError
- **视频生成时间**：每篇论文 5-10 分钟，不要在上传后立即运行
- **错误恢复**：论文移至 ERROR 状态，跟踪 retry_count（最多 3 次）
- **没有自动化测试**：使用 `--headful` 和 `apd status` 手动验证
- **Portal URL 转换**：`/blob/` URL 必须变为 `/resolve/` 才能流式传输视频
- **HF dataset 结构**：metadata.json 格式为 `{"weeks": {"2026-01": [...]}}`
- **需要的环境变量**：HF_TOKEN（写入令牌）、HF_USERNAME、HF_DATASET_NAME

---

**关键注意事项：**
- 当 NotebookLM/抖音 UI 变化时 Playwright 选择器会失效（使用截图调试）
- Daily.sh 是交互式的，非自动化（需要手动菜单选择）
- 数据库周查询包含所有日期（URL 使用 `week_id_to_iso_week()`）
- Portal Gradio 应用每 5 分钟自动刷新周下拉列表
