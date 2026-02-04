# 小红书发布使用指南

> 本指南介绍如何使用Auto-Paper-Digest将视频自动发布到小红书创作者中心

---

## 📋 目录

- [功能特点](#功能特点)
- [首次配置](#首次配置)
- [发布流程](#发布流程)
- [命令参考](#命令参考)
- [常见问题](#常见问题)

---

## ✨ 功能特点

### 半自动发布模式（推荐）

小红书发布默认使用**半自动模式**，确保发布安全：

1. ✅ 自动上传视频文件
2. ✅ 自动填写标题
3. ✅ 自动填写描述
4. ✅ 自动添加话题标签
5. ⏸️ **暂停等待用户手动点击发布按钮**

这种模式可以在发布前进行最后检查，避免误发布或内容违规。

### 支持的功能

- ✅ 视频上传（MP4格式）
- ✅ 标题自动填写（最多100字符）
- ✅ 描述自动填写（最多1000字符）
- ✅ 话题标签添加（最多5个）
- ✅ 自定义封面上传（可选）
- ✅ 登录状态持久化
- ✅ 批量发布支持

---

## 🚀 首次配置

### 1. 登录小红书创作者中心

首次使用需要扫码登录：

```bash
apd xiaohongshu-login
```

**操作步骤**:

1. 命令执行后会打开浏览器
2. 浏览器显示小红书登录页面和二维码
3. 使用小红书APP扫描二维码：
   - 打开小红书APP
   - 点击右下角【我】
   - 点击右上角三条横线
   - 选择【扫一扫】
   - 扫描浏览器中的二维码
4. 扫码成功后在APP中确认登录
5. 浏览器显示登录成功，按回车继续
6. 登录状态自动保存在 `data/.xiaohongshu_auth.json`

### 2. 验证登录

登录成功后，你可以尝试发布一个视频来验证：

```bash
apd publish-xiaohongshu --paper-id <某个已有视频的ID> --headful
```

---

## 📤 发布流程

### 基本发布流程

完整的视频发布流程如下：

```bash
# 1. 获取内容（论文/GitHub项目等）
apd fetch --week 2026-05

# 2. 下载PDF（如果是论文）
apd download --week 2026-05

# 3. 生成视频
apd upload --week 2026-05 --headful

# 4. 下载生成的视频
apd download-video --week 2026-05 --headful

# 5. 发布到小红书
apd publish-xiaohongshu --week 2026-05 --headful
```

### 发布选项

#### 按周发布

```bash
# 发布本周内容
apd publish-xiaohongshu --headful

# 发布指定周的内容
apd publish-xiaohongshu --week 2026-05 --headful
```

#### 按日发布

```bash
# 发布指定日期的内容
apd publish-xiaohongshu --date 2026-02-04 --headful
```

#### 发布单个视频

```bash
# 发布指定ID的视频
apd publish-xiaohongshu --paper-id arxiv:2601.12345 --headful
```

#### 强制重新发布

```bash
# 即使已发布也重新发布
apd publish-xiaohongshu --week 2026-05 --force --headful
```

#### 自动发布模式（不推荐）

```bash
# 自动点击发布按钮（跳过人工确认）
apd publish-xiaohongshu --week 2026-05 --headful --auto-publish
```

⚠️ **注意**：自动发布模式会跳过人工确认，可能导致误发布。仅在充分测试后使用。

---

## 📋 命令参考

### xiaohongshu-login

登录小红书创作者中心

```bash
apd xiaohongshu-login
```

**说明**:
- 打开浏览器显示登录页面
- 需要使用小红书APP扫码登录
- 登录状态会自动保存

---

### publish-xiaohongshu

发布视频到小红书

```bash
apd publish-xiaohongshu [OPTIONS]
```

**选项**:

| 选项 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--week` | `-w` | TEXT | 周ID（如2026-05） |
| `--date` | `-d` | TEXT | 日期（如2026-02-04） |
| `--paper-id` | `-p` | TEXT | 指定内容ID |
| `--force` | `-f` | FLAG | 强制重新发布 |
| `--headful` | - | FLAG | 显示浏览器窗口 |
| `--auto-publish` | - | FLAG | 自动点击发布按钮 |

**示例**:

```bash
# 基础用法
apd publish-xiaohongshu --week 2026-05 --headful

# 按日期发布
apd publish-xiaohongshu --date 2026-02-04 --headful

# 发布单个视频
apd publish-xiaohongshu --paper-id arxiv:2601.12345 --headful

# 强制重新发布
apd publish-xiaohongshu --week 2026-05 --force --headful

# 自动发布（不推荐）
apd publish-xiaohongshu --week 2026-05 --headful --auto-publish
```

---

## 🎯 半自动模式详解

### 工作流程

1. **自动阶段**（脚本执行）:
   - 打开小红书创作者中心
   - 上传视频文件
   - 等待视频处理完成
   - 填写标题
   - 填写描述
   - 添加话题标签
   - 上传封面（如果有）

2. **手动阶段**（用户操作）:
   - 脚本暂停，显示提示信息
   - 用户在浏览器中检查：
     - ✓ 视频上传是否成功
     - ✓ 标题是否正确
     - ✓ 描述是否完整
     - ✓ 话题标签是否合适
     - ✓ 封面是否合适
   - 用户手动点击【发布】按钮
   - 用户按回车继续

3. **完成阶段**:
   - 脚本获取发布结果
   - 更新数据库状态
   - 显示发布统计

### 示例输出

```
🚀 Publishing 3 videos to Xiaohongshu...
📌 Semi-automatic mode: You will manually click publish button

============================================================
📹 Processing video 1/3
📤 Uploading arxiv:2601.12345: Attention Is All You Need
✓ 视频已上传
✓ 标题已填写: Attention Is All You Need
✓ 描述已填写
✓ 已添加5个话题标签

============================================================
📋 半自动发布模式
============================================================

视频上传和信息填写已完成，请检查：
1. ✓ 视频已上传
2. ✓ 标题已填写
3. ✓ 描述已填写
4. ✓ 话题标签已添加

请在浏览器中检查无误后，手动点击【发布】按钮
发布完成后，按回车继续...
============================================================

[用户按回车后]
✅ Successfully published arxiv:2601.12345!

...

🎉 Xiaohongshu publish complete: 3/3 successful.
```

---

## 📊 内容自动适配

### 标题处理

- 自动截取前100字符（小红书标题限制）
- 保持标题完整性，避免截断单词

### 描述生成

根据内容类型自动生成描述：

**论文类内容**:
```
[论文摘要]

📚 arXiv: 2601.12345
PDF: https://arxiv.org/pdf/2601.12345.pdf

🤖 由 Auto-Paper-Digest 自动生成
```

**GitHub项目**:
```
[项目描述]

GitHub: https://github.com/user/repo
⭐ Stars: 50000
Language: Python

🤖 由 Auto-Paper-Digest 自动生成
```

**新闻内容**:
```
[新闻摘要]

来源: 知乎
原文: https://www.zhihu.com/...

🤖 由 Auto-Paper-Digest 自动生成
```

### 话题标签

根据内容类型自动添加标签：

- **论文**: #AI #论文解读 #学术 #科技
- **GitHub项目**: #GitHub #开源项目 #编程 #技术分享
- **新闻**: #热点 #新闻 #资讯

---

## ❓ 常见问题

### Q1: 登录后重启电脑，是否需要重新登录？

**A**: 不需要。登录状态保存在 `data/.xiaohongshu_auth.json` 和浏览器配置文件中，只要这些文件不被删除，登录状态就会保持。

---

### Q2: 视频上传失败怎么办？

**A**: 可能的原因和解决方案：

1. **视频格式不支持**
   - 确保视频是MP4格式
   - 使用NotebookLM生成的视频通常是支持的格式

2. **视频文件太大**
   - 小红书有视频大小限制（通常500MB以内）
   - 考虑压缩视频

3. **网络问题**
   - 检查网络连接
   - 尝试使用 `--headful` 模式观察上传过程
   - 增加超时时间

---

### Q3: 如何修改标题和描述？

**A**: 有两种方式：

1. **使用半自动模式**（推荐）
   - 脚本填写完信息后会暂停
   - 在浏览器中手动修改标题和描述
   - 然后点击发布

2. **修改源代码**
   - 编辑 `apd/xiaohongshu_bot.py`
   - 修改标题和描述生成逻辑
   - 或在 `apd/config.py` 中修改模板

---

### Q4: 可以自定义封面吗？

**A**: 目前支持自定义封面上传功能，但需要在代码中指定封面路径。未来版本会添加自动生成封面的功能。

---

### Q5: 发布频率有限制吗？

**A**: 小红书对发布频率有一定限制，建议：

- 每小时不超过5个视频
- 每天不超过20个视频
- 避免短时间内大量发布相同内容

脚本会自动在每个视频发布间隔添加延迟。

---

### Q6: 如何查看已发布的视频？

**A**: 可以通过以下方式查看：

1. **数据库查询**:
   ```bash
   apd status --week 2026-05
   ```

2. **小红书创作者中心**:
   - 登录 https://creator.xiaohongshu.com
   - 查看【内容管理】

---

### Q7: 半自动模式下，如果不想发布某个视频怎么办？

**A**: 在浏览器中可以：

1. 关闭当前标签页（取消发布）
2. 在终端按Ctrl+C中断脚本
3. 该视频的发布状态不会更新，下次运行时会跳过

---

### Q8: 自动发布模式和半自动模式有什么区别？

**A**:

| 特性 | 半自动模式（默认） | 自动发布模式 |
|------|------------------|-------------|
| 视频上传 | ✅ 自动 | ✅ 自动 |
| 信息填写 | ✅ 自动 | ✅ 自动 |
| 点击发布按钮 | ❌ 需要手动 | ✅ 自动 |
| 人工确认 | ✅ 需要 | ❌ 不需要 |
| 安全性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 推荐使用 | ✅ 是 | ❌ 否 |

---

### Q9: 如何处理小红书界面变化？

**A**: 小红书可能会更新网页界面，导致脚本失效。遇到问题时：

1. **查看截图**:
   ```bash
   ls data/profiles/screenshots/
   ```

2. **调试模式**:
   ```bash
   apd publish-xiaohongshu --headful --debug
   ```

3. **提交Issue**:
   - 访问 GitHub Issues
   - 提供错误信息和截图
   - 描述复现步骤

---

### Q10: 可以同时发布到多个平台吗？

**A**: 可以！依次执行多个发布命令：

```bash
# 发布到所有平台
apd publish --week 2026-05                      # HuggingFace
apd publish-douyin --week 2026-05 --headful    # 抖音
apd publish-bilibili --week 2026-05 --headful  # B站
apd publish-xiaohongshu --week 2026-05 --headful  # 小红书
```

或创建一个脚本批量发布：

```bash
#!/bin/bash
WEEK="2026-05"

echo "Publishing to all platforms..."
apd publish --week $WEEK
apd publish-douyin --week $WEEK --headful
apd publish-bilibili --week $WEEK --headful
apd publish-xiaohongshu --week $WEEK --headful
echo "All platforms published!"
```

---

## 🔒 隐私和安全

### 登录信息存储

- 登录状态保存在本地 `data/` 目录
- 不会上传到任何服务器
- 建议定期备份 `data/` 目录

### 安全建议

1. ✅ 使用半自动模式进行人工确认
2. ✅ 定期检查已发布内容
3. ✅ 不要分享 `data/` 目录中的认证文件
4. ✅ 在公共电脑使用后清除浏览器数据
5. ❌ 不要将 `AUTO_PUBLISH=true` 设置为默认

---

## 📚 相关文档

- [主文档](./README.md) - 项目总览和快速开始
- [Docker部署指南](./DOCKER_GUIDE.md) - 使用Docker部署
- [质量控制指南](./QUALITY_CONTROL_GUIDE.md) - 内容质量评分
- [优化路线图](./OPTIMIZATION_ROADMAP.md) - 未来规划

---

## 🤝 反馈和支持

遇到问题或有建议？

- **GitHub Issues**: https://github.com/brianxiadong/auto-paper-digest/issues
- **讨论区**: GitHub Discussions
- **邮件支持**: [提供你的邮箱]

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
**适用版本**: Auto-Paper-Digest v2.1+
