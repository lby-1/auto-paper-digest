# APD 项目扩展规划 - GitHub/B站功能

**创建日期：** 2026-01-20
**目标：** 扩展 APD 项目以支持 GitHub 热门项目、国内热点新闻，以及 B站视频发布

---

## 一、需求概述

### 1.1 功能需求

1. **GitHub 热门项目获取**
   - 获取指定周的热门 GitHub 项目
   - 支持通过日期控制是哪一周的项目
   - 生成项目相关的视频内容

2. **国内热点新闻获取**
   - 获取指定日期的国内热点新闻（如 "2026-01-20"）
   - 支持按周或按日查询
   - 生成新闻相关的视频内容

3. **B站视频发布**
   - 支持发布视频到 B站
   - 支持配置文件配置 B站账号或通过命令登录
   - **半自动发布**：脚本负责上传视频和填写信息，用户手动点击发布按钮
   - 抖音发布也采用相同的半自动方式

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI 命令层 (cli.py)              │
│                                                          │
│  fetch-github | fetch-news | bilibili-login |          │
│  publish-bilibili | publish-douyin                    │
└─────────────────────────┬───────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼────────┐            ┌─────────▼──────────┐
│  数据获取层      │            │  发布层              │
├───────────────┤            ├─────────────────────┤
│ hf_fetcher.py  │            │ douyin_bot.py      │
│ github_fetcher.py │            │ bilibili_bot.py     │
│ news_fetcher.py │            │ publisher.py         │
└───────┬────────┘            └─────────▲──────────┘
        │                              │
┌───────▼──────────────────────────────▼──────────┐
│        数据层 (db.py)                          │
│                                                  │
│  papers 表扩展：content_type, source_url         │
└───────────────────────────────────────────────────┘
```

### 2.2 内容类型枚举

```python
class ContentType:
    PAPER = "PAPER"      # 论文（原有）
    GITHUB = "GITHUB"    # GitHub 项目（新增）
    NEWS = "NEWS"        # 新闻（新增）
```

---

## 三、数据库设计

### 3.1 现有 papers 表结构

```sql
CREATE TABLE papers (
    paper_id TEXT PRIMARY KEY,
    week_id TEXT NOT NULL,
    title TEXT,
    hf_url TEXT,
    pdf_url TEXT,
    pdf_path TEXT,
    pdf_sha256 TEXT,
    notebooklm_note_name TEXT,
    video_path TEXT,
    slides_path TEXT,
    summary TEXT,
    status TEXT DEFAULT 'NEW',
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    updated_at TEXT
)
```

### 3.2 新增字段（数据库迁移）

```sql
-- 新增字段
ALTER TABLE papers ADD COLUMN content_type TEXT DEFAULT 'PAPER';
ALTER TABLE papers ADD COLUMN source_url TEXT;
ALTER TABLE papers ADD COLUMN github_stars INTEGER;
ALTER TABLE papers ADD COLUMN github_language TEXT;
ALTER TABLE papers ADD COLUMN github_description TEXT;
ALTER TABLE papers ADD COLUMN news_source TEXT;
ALTER TABLE papers ADD COLUMN news_url TEXT;
ALTER TABLE papers ADD COLUMN bilibili_published INTEGER DEFAULT 0;
ALTER TABLE papers ADD COLUMN douyin_published INTEGER DEFAULT 0;
```

### 3.3 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `content_type` | TEXT | 内容类型：PAPER/GITHUB/NEWS |
| `source_url` | TEXT | 通用源 URL（替换/补充 hf_url） |
| `github_stars` | INTEGER | GitHub 项目星标数 |
| `github_language` | TEXT | GitHub 项目主要语言 |
| `github_description` | TEXT | GitHub 项目描述 |
| `news_source` | TEXT | 新闻来源（如：微博、知乎等） |
| `news_url` | TEXT | 新闻原文链接 |
| `bilibili_published` | INTEGER | 是否已发布到 B站（0/1） |
| `douyin_published` | INTEGER | 是否已发布到抖音（0/1） |

---

## 四、模块设计

### 4.1 GitHub 获取模块 (`github_fetcher.py`)

**功能：**
- 获取 GitHub Trending 列表
- 支持按日期/周获取
- 解析项目信息（名称、描述、星标数、语言）

**接口设计：**

```python
def fetch_weekly_github_trending(week_id: str, max_projects: int = 50) -> list[dict]:
    """
    获取指定周的 GitHub Trending 项目

    Args:
        week_id: 周 ID（如 "2026-03"）
        max_projects: 最大获取数量

    Returns:
        项目信息列表
    """

def fetch_daily_github_trending(date: str, max_projects: int = 50) -> list[dict]:
    """
    获取指定日期的 GitHub Trending 项目

    Args:
        date: 日期（如 "2026-01-08"）
        max_projects: 最大获取数量

    Returns:
        项目信息列表
    """
```

**实现要点：**
1. 使用 GitHub Trending API 或爬虫（`https://github.com/trending/{language}?since={date}`）
2. 解析 HTML 获取项目信息（使用 BeautifulSoup）
3. 生成唯一 ID：`github-{owner}-{repo}`（如 `github-openai-gpt`）
4. 调用 `upsert_paper()` 存入数据库

**依赖：**
- `requests`
- `beautifulsoup4`

### 4.2 热点新闻获取模块 (`news_fetcher.py`)

**功能：**
- 获取国内热点新闻
- 支持按日期/周获取
- 支持多新闻源（微博、知乎、百度等）

**接口设计：**

```python
def fetch_weekly_news(week_id: str, max_news: int = 50) -> list[dict]:
    """
    获取指定周的国内热点新闻

    Args:
        week_id: 周 ID（如 "2026-03"）
        max_news: 最大获取数量

    Returns:
        新闻信息列表
    """

def fetch_daily_news(date: str, max_news: int = 50) -> list[dict]:
    """
    获取指定日期的国内热点新闻

    Args:
        date: 日期（如 "2026-01-08"）
        max_news: 最大获取数量

    Returns:
        新闻信息列表
    """
```

**新闻源选项：**
- 微博热搜（`https://s.weibo.com/top/summary`）
- 知乎热榜（`https://www.zhihu.com/hot`）
- 百度热搜（`https://top.baidu.com/board?tab=realtime`）

**实现要点：**
1. 支持配置多个新闻源，可切换
2. 解析热搜列表获取标题、链接、热度
3. 生成唯一 ID：`news-{source}-{hash(title)}`（如 `news-weibo-abc123`）
4. 调用 `upsert_paper()` 存入数据库

### 4.3 B站发布模块 (`bilibili_bot.py`)

**功能：**
- 模拟 B站创作者平台登录
- 上传视频
- 填写视频信息（标题、简介、标签）
- 发布视频

**接口设计：**

```python
class BilibiliBot:
    """B站创作者平台自动化"""

    def __init__(self, headless: bool = True):
        ...

    def __enter__(self):
        """上下文管理器入口"""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        ...

    def login(self) -> bool:
        """
        登录 B站

        Returns:
            是否登录成功
        """

    def publish_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        skip_login_check: bool = False,
        auto_publish: bool = False  # 新增参数：是否自动点击发布
    ) -> bool:
        """
        发布视频到 B站（半自动模式）

        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频简介
            tags: 视频标签
            skip_login_check: 跳过登录检查（批量发布时使用）
            auto_publish: 是否自动点击发布按钮（默认 False，需要用户手动点击）

        Returns:
            是否完成视频信息填写（不包含发布操作）

        流程：
            1. 上传视频文件
            2. 填写标题、描述、标签
            3. 如果 auto_publish=False（默认）：
               - 打印提示信息，等待用户手动点击发布
               - 脚本保持浏览器窗口打开
            4. 如果 auto_publish=True：
               - 自动点击发布按钮
        """
```

**会话持久化：**
- B站登录状态保存到：`data/.bilibili_auth.json`

**URL 常量：**
- 创作者中心：`https://member.bilibili.com/platform/upload/video/frame`
- 登录页：`https://passport.bilibili.com/login`

**实现要点：**
1. 使用 Playwright 模拟浏览器操作
2. 支持二维码登录（首次使用）
3. 支持会话持久化（后续使用）
4. 处理常见弹窗（登录提示、审核提示等）
5. **半自动发布模式**（默认）：
   - 上传视频并填写所有信息后
   - 打印提示信息：`"✅ 视频信息已填写完成！请在浏览器中检查并手动点击【发布】按钮"`
   - 使用 `page.pause()` 或 `input("按回车键继续...")` 等待用户操作
   - 保持浏览器窗口打开，不自动关闭
6. 参考 `douyin_bot.py` 的实现模式，但移除自动点击发布的逻辑

**依赖：**
- `playwright`

---

## 五、配置扩展

### 5.1 `.env.example` 新增配置

```bash
# HuggingFace（已有）
HF_TOKEN=hf_xxx
HF_USERNAME=your-username
HF_DATASET_NAME=paper-digest-videos

# GitHub（新增）
GITHUB_TOKEN=ghp_xxx  # 可选，用于 API 访问
GITHUB_SINCE=daily  # daily/weekly/monthly

# 新闻源配置（新增）
NEWS_SOURCE=weibo  # weibo/zhihu/baidu/multiple

# B站（新增）
BILIBILI_USERNAME=your-bilibili-username
BILIBILI_COOKIE=  # 可选，手动获取的 Cookie
```

### 5.2 `config.py` 新增常量

```python
# GitHub
GITHUB_TRENDING_URL = "https://github.com/trending/{language}?since={since}"
GITHUB_DEFAULT_SINCE = "daily"

# 新闻源
NEWS_SOURCES = {
    "weibo": "https://s.weibo.com/top/summary",
    "zhihu": "https://www.zhihu.com/hot",
    "baidu": "https://top.baidu.com/board?tab=realtime",
}

# B站
BILIBILI_AUTH_PATH = DATA_DIR / ".bilibili_auth.json"
BILIBILI_CREATOR_URL = "https://member.bilibili.com/platform/upload/video/frame"
BILIBILI_LOGIN_URL = "https://passport.bilibili.com/login"

# 内容类型
class ContentType:
    PAPER = "PAPER"
    GITHUB = "GITHUB"
    NEWS = "NEWS"
```

---

## 六、CLI 命令设计

### 6.1 新增命令

#### 1. GitHub 获取命令

```bash
# 获取指定周的热门 GitHub 项目
apd fetch-github --week 2026-03 --max 20

# 获取指定日期的热门 GitHub 项目
apd fetch-github --date 2026-01-08 --max 20
```

#### 2. 热点新闻获取命令

```bash
# 获取指定日期的国内热点新闻（推荐）
apd fetch-news --date 2026-01-20 --max 20 --source weibo

# 获取今天的热榜新闻
apd fetch-news --max 20 --source weibo

# 获取指定周的国内热点新闻（获取该周所有日期的新闻）
apd fetch-news --week 2026-03 --max 20 --source zhihu

# 支持的新闻源：weibo（微博热搜）、zhihu（知乎热榜）、baidu（百度热搜）
apd fetch-news --date 2026-01-20 --source baidu
```

#### 3. B站登录命令

```bash
# 打开浏览器进行 B站登录（首次使用）
apd bilibili-login
```

#### 4. B站发布命令（半自动：填写信息，手动发布）

```bash
# 发布指定周的视频到 B站
# 脚本会上传视频、填写标题/描述/标签，然后暂停等待你手动点击发布按钮
apd publish-bilibili --week 2026-03 --headful

# 发布指定日期的视频到 B站
apd publish-bilibili --date 2026-01-20 --headful

# 发布指定 ID 的内容到 B站
apd publish-bilibili --paper-id github-openai-gpt --headful
```

#### 5. 抖音发布命令（半自动：填写信息，手动发布）

```bash
# 发布指定周的视频到抖音
# 脚本会上传视频、填写标题/描述/标签，然后暂停等待你手动点击发布按钮
apd publish-douyin --week 2026-03 --headful

# 发布指定日期的视频到抖音
apd publish-douyin --date 2026-01-20 --headful

# 发布指定 ID 的内容到抖音
apd publish-douyin --paper-id news-weibo-abc123 --headful
```

**注意：** 发布命令都采用半自动模式，脚本会：
1. ✅ 打开浏览器（headful 模式）
2. ✅ 检查登录状态
3. ✅ 上传视频文件
4. ✅ 填写标题、描述、标签
5. ⏸️ **暂停并提示你手动点击"发布"按钮**
6. ⏹️ 你确认内容无误后，手动点击发布

### 6.2 命令实现框架

在 `cli.py` 中添加：

```python
@main.command()
@click.option("--week", "-w", default=None, help="周 ID")
@click.option("--date", "-d", default=None, help="日期")
@click.option("--max", "-m", "max_projects", default=50, type=int, help="最大数量")
def fetch_github(week, date, max_projects):
    """获取 GitHub 热门项目"""
    ...

@main.command()
@click.option("--week", "-w", default=None, help="周 ID")
@click.option("--date", "-d", default=None, help="日期")
@click.option("--max", "-m", "max_news", default=50, type=int, help="最大数量")
@click.option("--source", "-s", default="weibo", help="新闻源：weibo/zhihu/baidu")
def fetch_news(week, date, max_news, source):
    """获取国内热点新闻"""
    ...

@main.command()
def bilibili_login():
    """B站登录"""
    ...

@main.command()
@click.option("--week", "-w", default=None, help="周 ID")
@click.option("--date", "-d", default=None, help="日期（YYYY-MM-DD）")
@click.option("--paper-id", "-p", default=None, help="指定内容 ID")
@click.option("--headful", is_flag=True, help="显示浏览器（必需，用于手动发布）")
@click.option("--auto-publish", is_flag=True, help="自动点击发布按钮（默认关闭）")
def publish_bilibili(week, date, paper_id, headful, auto_publish):
    """
    发布视频到 B站（半自动模式）

    默认行为：
    - 上传视频并填写信息
    - 等待用户手动点击发布按钮

    使用 --auto-publish 可以自动点击发布（不推荐）
    """
    ...

@main.command()
@click.option("--week", "-w", default=None, help="周 ID")
@click.option("--date", "-d", default=None, help="日期（YYYY-MM-DD）")
@click.option("--paper-id", "-p", default=None, help="指定内容 ID")
@click.option("--headful", is_flag=True, help="显示浏览器（必需，用于手动发布）")
@click.option("--auto-publish", is_flag=True, help="自动点击发布按钮（默认关闭）")
def publish_douyin(week, date, paper_id, headful, auto_publish):
    """
    发布视频到抖音（半自动模式）

    默认行为：
    - 上传视频并填写信息
    - 等待用户手动点击发布按钮

    使用 --auto-publish 可以自动点击发布（不推荐）
    """
    ...
```

---

## 七、实现步骤

### 阶段一：数据库扩展（优先级：高）

**任务：**
1. 修改 `db.py` 的 `init_db()` 添加数据库迁移
2. 修改 `Paper` 数据类，添加新字段
3. 修改 `upsert_paper()` 函数支持新字段
4. 测试数据库迁移

**预期时间：** 1-2 小时

### 阶段二：GitHub 获取模块（优先级：高）

**任务：**
1. 创建 `github_fetcher.py`
2. 实现 `fetch_weekly_github_trending()` 和 `fetch_daily_github_trending()`
3. 添加 CLI 命令 `fetch-github`
4. 测试 GitHub 热门项目获取

**预期时间：** 3-4 小时

### 阶段三：热点新闻获取模块（优先级：中）

**任务：**
1. 创建 `news_fetcher.py`
2. 实现 `fetch_weekly_news()` 和 `fetch_daily_news()`
3. 支持多新闻源（微博、知乎）
4. 添加 CLI 命令 `fetch-news`
5. 测试新闻获取

**预期时间：** 3-4 小时

### 阶段四：B站发布模块（优先级：高）

**任务：**
1. 创建 `bilibili_bot.py`
2. 实现 `BilibiliBot` 类（半自动发布模式）
3. 实现登录和视频上传功能
4. **关键实现**：填写信息后暂停，等待用户手动点击发布
5. 添加 CLI 命令 `bilibili-login` 和 `publish-bilibili`
6. 测试 B站半自动发布流程

**预期时间：** 4-6 小时

### 阶段五：抖音发布改造和优化（优先级：高）

**任务：**
1. 修改 `douyin_bot.py` 的 `publish_video()` 函数
2. 添加 `auto_publish` 参数，默认为 False
3. 实现半自动发布模式（填写信息后暂停）
4. 更新 CLI 命令 `publish-douyin`，添加 `--auto-publish` 选项
5. 更新文档（README.md, CLAUDE.md）
6. 添加使用示例和注意事项

**预期时间：** 2-3 小时

---

## 八、注意事项和风险

### 8.1 反爬虫机制
- GitHub 可能有访问频率限制
- 微博、知乎等新闻源可能有反爬虫（验证码、登录限制）
- 需要设置合理的请求间隔，模拟真实用户行为

### 8.2 内容过滤
- GitHub 项目和新闻可能包含敏感内容
- 建议添加内容过滤机制
- 或提供人工审核选项

### 8.3 B站/抖音发布限制
- B站和抖音对视频都有审核机制，发布后需要等待审核通过
- 每日发布数量可能有上限
- **半自动发布的优势**：
  - 用户可以在发布前最后检查视频信息
  - 避免因自动化错误导致发布不当内容
  - 符合平台对自动化行为的限制
  - 用户可以根据需要调整标签、封面等细节

### 8.4 数据兼容性
- 数据库迁移需要确保向后兼容
- 现有论文记录不受影响
- 新字段使用 DEFAULT 值

### 8.5 错误处理
- 网络请求失败重试
- 视频上传失败重试
- 记录详细的错误信息

---

## 九、测试策略

### 9.1 单元测试
- 测试数据库迁移
- 测试 GitHub 项目解析
- 测试新闻获取逻辑

### 9.2 集成测试
- 端到端测试 GitHub 获取流程
- 端到端测试新闻获取流程（按日期）
- 测试 B站半自动发布流程（使用测试账号）
- 测试抖音半自动发布流程

### 9.3 手动测试
- 使用 `--headful` 模式观察发布过程（必需）
- **验证半自动发布流程**：
  1. 确认视频上传成功
  2. 确认标题、描述、标签填写正确
  3. 确认脚本在填写完信息后暂停
  4. 手动点击发布按钮
  5. 确认发布成功
- 测试指定日期获取新闻：`apd fetch-news --date 2026-01-20`

---

## 十、后续优化建议

1. **内容模板系统**
   - 为不同类型的内容生成不同的视频脚本
   - GitHub 项目：项目介绍、功能特点、使用场景
   - 新闻：事件概述、影响分析、相关评论

2. **多账号支持**
   - 支持配置多个 B站/抖音账号
   - 轮换账号发布以避免限制

3. **内容推荐算法**
   - 根据历史发布数据推荐内容
   - 分析热门标签和发布时机

4. **批量半自动发布优化**
   - 在批量发布时，可以一次性准备多个视频
   - 用户可以依次检查并发布，无需每次重新运行命令
   - 添加 `--prepare-only` 选项，只准备不打开浏览器

5. **数据分析面板**
   - 展示发布数据统计
   - 分析视频播放量、点赞数等

6. **新闻源扩展**
   - 支持更多新闻源（头条、36氪、虎嗅等）
   - 支持自定义新闻源配置
   - 按话题分类新闻（科技、财经、娱乐等）

---

## 总结

本规划详细设计了 APD 项目扩展所需的数据库模式、模块架构、CLI 命令和实现步骤。核心亮点：

1. **向后兼容**：数据库迁移确保现有功能不受影响
2. **模块化设计**：各模块职责清晰，易于维护
3. **半自动发布流程**：脚本负责填写信息，用户手动点击发布，安全可控
4. **灵活的内容获取**：支持按日期获取新闻（如 `--date 2026-01-20`）
5. **独立的平台命令**：B站和抖音分别使用不同命令，互不干扰

**关键特性：**
- ✅ 支持获取指定日期的热榜新闻
- ✅ B站和抖音使用独立的发布命令
- ✅ 默认半自动模式，手动点击发布按钮
- ✅ 可选的 `--auto-publish` 参数用于完全自动化（不推荐）

**预计总开发时间：** 15-20 小时

**建议开发顺序：** 数据库扩展 → 新闻获取（按日期） → B站半自动发布 → 抖音改造（半自动） → GitHub 获取
