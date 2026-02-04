# 🚀 Auto Paper Digest (APD)

<p align="center">
  <strong>自动获取学术论文 → 生成视频讲解 → 多平台发布</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/NotebookLM-Automation-orange.svg" alt="NotebookLM">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker">
</p>

---

## ✨ 功能概览

| 功能 | 说明 |
|------|------|
| 📚 **多源获取** | HuggingFace 论文、GitHub Trending、热榜新闻 |
| 🎬 **视频生成** | NotebookLM 自动生成视频讲解 |
| 📱 **多平台发布** | 抖音、B站、小红书、HuggingFace（半自动模式） |
| 🎯 **质量控制** | 智能评分、去重、推荐系统 |
| 🐳 **Docker支持** | 容器化部署，一键启动 |
| 🌐 **Web门户** | Gradio 在线浏览视频 |

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/brianxiadong/auto-paper-digest.git
cd auto-paper-digest

# 2. 配置环境
cp .env.example .env
# 编辑 .env，填入 HF_TOKEN 等配置

# 3. 启动服务
docker-compose up -d

# 4. 访问门户
# http://localhost:7860
```

### 方式二：本地安装

```bash
# 1. 安装依赖
pip install -e .
playwright install chromium

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件

# 3. 首次登录
apd login
```

---

## 📖 基本使用

### 完整工作流程

```bash
# 1. 获取论文
apd fetch --week 2026-05 --max 20

# 2. 生成视频
apd upload --week 2026-05 --headful

# 3. 下载视频
apd download-video --week 2026-05 --headful

# 4. 发布到平台
apd publish --week 2026-05                    # HuggingFace
apd publish-douyin --week 2026-05 --headful   # 抖音
apd publish-bilibili --week 2026-05 --headful # B站
apd publish-xiaohongshu --week 2026-05 --headful # 小红书
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `apd fetch` | 获取内容 |
| `apd upload` | 上传并生成视频 |
| `apd download-video` | 下载视频 |
| `apd publish` | 发布到 HuggingFace |
| `apd status` | 查看处理状态 |

**查看所有命令**: `apd --help`

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| **[用户操作手册](./用户操作手册.md)** | 📖 完整使用教程和最佳实践 |
| [Docker部署指南](./DOCKER_GUIDE.md) | 🐳 Docker容器化部署 |
| [小红书发布指南](./XIAOHONGSHU_GUIDE.md) | 📱 小红书发布详解 |
| [质量控制指南](./QUALITY_CONTROL_GUIDE.md) | 🎯 内容质量评分系统 |

---

## 🔑 核心特性

### 半自动发布模式

默认使用**半自动模式**，确保发布安全：

1. ✅ 脚本自动上传视频和填写信息
2. ⏸️ 暂停等待用户确认
3. ✅ 用户手动点击发布按钮

这种模式避免了自动化导致的误发布和内容违规。

### 智能内容管理

- **质量评分**: 多维度评估内容质量（引用数、会议等级、时效性）
- **智能去重**: 三层相似度检测，避免重复处理
- **个性化推荐**: 4种推荐策略，提升内容发现

### Docker 容器化

- 一键部署，无需配置环境
- 自动定时任务
- Web 管理界面
- 数据持久化

---

## 🛠️ 技术栈

- **Python 3.11+** - 核心语言
- **Playwright** - 浏览器自动化
- **SQLite** - 数据持久化
- **Docker** - 容器化部署
- **Gradio** - Web 门户
- **NotebookLM** - 视频生成

---

## 📊 支持平台

| 平台 | 功能 | 状态 |
|------|------|------|
| HuggingFace | 数据集存储 | ✅ |
| 抖音 | 视频发布 | ✅ |
| B站 | 视频发布 | ✅ |
| 小红书 | 视频发布 | ✅ |
| YouTube | 计划中 | 🔜 |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License © 2026

---

## 🔗 相关链接

- **原项目**: [auto-paper-digest](https://github.com/brianxiadong/auto-paper-digest)
- **文档中心**: [用户操作手册](./用户操作手册.md)
- **问题反馈**: [GitHub Issues](https://github.com/brianxiadong/auto-paper-digest/issues)

---

<p align="center">
  <i>让学术传播更简单</i>
</p>
