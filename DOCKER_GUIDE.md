# Docker部署指南

本指南介绍如何使用Docker部署和运行Auto-Paper-Digest项目。

---

## 📋 目录

- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [部署模式](#部署模式)
- [配置说明](#配置说明)
- [常用命令](#常用命令)
- [云平台部署](#云平台部署)
- [故障排除](#故障排除)

---

## 前置要求

### 必需软件

- **Docker** >= 20.10
- **Docker Compose** >= 2.0

### 安装Docker

**Windows/Mac:**
- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)

**Linux:**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### 验证安装

```bash
docker --version
docker-compose --version
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/brianxiadong/auto-paper-digest.git
cd auto-paper-digest
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

**必需配置项**:
```bash
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
HF_USERNAME=your-username
HF_DATASET_NAME=paper-digest-videos
```

### 3. 启动服务

**方式A: 使用Docker Compose**
```bash
docker-compose up -d
```

**方式B: 使用脚本**
```bash
# Linux/Mac
./deploy/deploy_local.sh prod

# Windows
deploy\deploy_local.bat prod
```

**方式C: 使用Makefile**
```bash
make up
```

### 4. 访问服务

- **门户网站**: http://localhost:7860
- **查看日志**: `docker-compose logs -f`
- **进入容器**: `docker-compose exec apd bash`

---

## 部署模式

### 生产模式 (Production)

适用于正式运行环境。

**启动**:
```bash
docker-compose up -d
```

**特点**:
- 所有服务在后台运行
- 自动重启策略
- 数据持久化
- 定时任务自动执行

**服务列表**:
- `apd`: 主服务容器
- `scheduler`: 定时任务容器（每周自动运行）
- `portal`: Web门户容器

### 开发模式 (Development)

适用于开发和调试。

**启动**:
```bash
docker-compose -f docker-compose.dev.yml up -d
# 或
make dev-up
```

**特点**:
- 源代码热重载
- 交互式Shell
- 调试器支持
- 详细日志输出

**进入开发容器**:
```bash
docker-compose -f docker-compose.dev.yml exec apd-dev bash
# 或
make dev-shell
```

---

## 配置说明

### 环境变量

编辑 `.env` 文件配置项目参数。

#### 必需配置

```bash
# HuggingFace配置
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
HF_USERNAME=your-username
HF_DATASET_NAME=paper-digest-videos
```

#### 可选配置

```bash
# 质量控制
MIN_QUALITY_SCORE=60.0
MIN_CITATIONS=0
MIN_GITHUB_STARS=100

# Azure TTS (可选)
AZURE_TTS_KEY=your-azure-key
AZURE_TTS_REGION=eastus

# Semantic Scholar (可选)
S2_API_KEY=your-s2-api-key

# 端口配置
PORTAL_PORT=7860
```

### 数据卷

项目使用以下数据卷持久化数据：

| 卷名称 | 宿主机路径 | 容器路径 | 用途 |
|--------|-----------|---------|------|
| data | `./data` | `/app/data` | 数据库、PDF、视频 |
| config | `./config` | `/app/config` | 配置文件 |
| profiles | `apd-profiles` | `/app/data/profiles` | 浏览器配置 |

**查看数据卷**:
```bash
docker volume ls
docker volume inspect apd-browser-profiles
```

---

## 常用命令

### 使用Makefile（推荐）

```bash
# 查看所有命令
make help

# 生产环境
make up          # 启动服务
make down        # 停止服务
make logs        # 查看日志
make shell       # 进入Shell
make restart     # 重启服务
make rebuild     # 重新构建

# 开发环境
make dev-up      # 启动开发环境
make dev-down    # 停止开发环境
make dev-shell   # 进入开发Shell

# 维护
make test        # 运行测试
make clean       # 清理资源
make ps          # 查看状态
```

### 使用Docker Compose

#### 启动/停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 停止并删除数据卷
docker-compose down -v
```

#### 查看状态

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f apd
docker-compose logs -f scheduler
docker-compose logs -f portal
```

#### 执行命令

```bash
# 进入容器Shell
docker-compose exec apd bash

# 运行APD命令
docker-compose exec apd apd status --show-scores
docker-compose exec apd apd fetch --week 2026-05
docker-compose exec apd apd upload --week 2026-05 --max 10

# 运行Python脚本
docker-compose exec apd python tests/test_quality_filter.py
```

### 手动运行工作流

在容器内执行完整工作流：

```bash
# 进入容器
docker-compose exec apd bash

# 执行工作流
WEEK=$(date +%Y-W%V)
apd fetch --week $WEEK --max 20
apd upload --week $WEEK --headful
apd download-video --week $WEEK --headful
apd publish --week $WEEK
```

---

## 云平台部署

### Railway部署

1. 安装Railway CLI:
```bash
npm install -g @railway/cli
```

2. 登录并初始化:
```bash
railway login
railway init
```

3. 配置环境变量:
```bash
railway variables set HF_TOKEN=hf_xxx
railway variables set HF_USERNAME=your-username
```

4. 部署:
```bash
railway up
```

### AWS EC2部署

使用提供的部署脚本：

```bash
cd deploy
chmod +x deploy_aws.sh

# 执行部署
./deploy_aws.sh t3.medium your-key-pair
```

**部署后**:
```bash
# SSH登录
ssh -i your-key-pair.pem ec2-user@<PUBLIC_IP>

# 配置环境变量
cd auto-paper-digest
nano .env

# 重启服务
docker-compose restart
```

### 其他云平台

**Google Cloud Run**:
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/apd
gcloud run deploy apd --image gcr.io/PROJECT-ID/apd
```

**Azure Container Instances**:
```bash
az container create \
  --resource-group myResourceGroup \
  --name apd \
  --image your-registry/apd:latest
```

---

## 故障排除

### 问题1: 容器无法启动

**症状**: `docker-compose up` 失败

**检查**:
```bash
# 查看详细日志
docker-compose logs apd

# 检查配置
docker-compose config
```

**解决方案**:
- 检查 `.env` 文件是否存在且配置正确
- 确认Docker有足够的资源（内存、磁盘空间）
- 检查端口是否被占用

### 问题2: Playwright浏览器错误

**症状**: `Executable doesn't exist` 或浏览器启动失败

**解决方案**:
```bash
# 重新安装浏览器
docker-compose exec apd playwright install chromium
docker-compose exec apd playwright install-deps chromium

# 或重新构建镜像
docker-compose build --no-cache apd
```

### 问题3: 数据丢失

**症状**: 重启后数据消失

**原因**: 数据卷未正确挂载

**解决方案**:
```bash
# 检查卷挂载
docker-compose config | grep volumes

# 确保数据目录存在
mkdir -p ./data
```

### 问题4: 内存不足

**症状**: 容器被OOM Killer杀死

**解决方案**:
```bash
# 增加Docker内存限制
# Docker Desktop: Settings -> Resources -> Memory

# 或在docker-compose.yml中限制内存
services:
  apd:
    mem_limit: 2g
```

### 问题5: 端口冲突

**症状**: `Error: Port 7860 is already in use`

**解决方案**:
```bash
# 修改.env中的端口
PORTAL_PORT=8080

# 或修改docker-compose.yml
ports:
  - "8080:7860"
```

### 查看容器资源使用

```bash
# 实时监控
docker stats

# 查看特定容器
docker stats apd
```

### 清理Docker资源

```bash
# 停止并删除所有容器
docker-compose down -v

# 清理未使用的镜像
docker system prune -a

# 清理所有资源（危险！）
docker system prune -a --volumes
```

---

## 性能优化

### 镜像大小优化

当前镜像使用多阶段构建，大小约 **1.5GB**。

**进一步优化**:
1. 使用Alpine基础镜像（需要额外配置）
2. 清理不必要的依赖
3. 使用 `.dockerignore` 排除文件

### 构建缓存

```bash
# 使用BuildKit加速构建
DOCKER_BUILDKIT=1 docker-compose build

# 启用构建缓存
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

### 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  apd:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          memory: 2G
```

---

## 监控和日志

### 日志管理

**查看日志**:
```bash
# 所有服务
docker-compose logs -f

# 指定行数
docker-compose logs --tail=100 apd

# 带时间戳
docker-compose logs -f -t
```

**日志持久化**:

在 `docker-compose.yml` 中配置日志驱动：

```yaml
services:
  apd:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 健康检查

容器已配置健康检查：

```bash
# 查看健康状态
docker-compose ps
docker inspect --format='{{.State.Health.Status}}' apd
```

---

## 备份和恢复

### 备份数据

```bash
# 备份数据目录
tar -czf apd-backup-$(date +%Y%m%d).tar.gz data/

# 备份数据库
docker-compose exec apd sqlite3 /app/data/apd.db .dump > backup.sql
```

### 恢复数据

```bash
# 恢复数据目录
tar -xzf apd-backup-20260203.tar.gz

# 恢复数据库
docker-compose exec -T apd sqlite3 /app/data/apd.db < backup.sql
```

---

## 高级配置

### 自定义Dockerfile

如需修改Dockerfile：

```bash
# 修改Dockerfile后重新构建
docker-compose build --no-cache

# 使用特定Dockerfile
docker build -f Dockerfile.custom -t apd:custom .
```

### 多环境部署

创建多个compose文件：

```bash
# 开发环境
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 测试环境
docker-compose -f docker-compose.yml -f docker-compose.test.yml up

# 生产环境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

### 网络配置

**使用自定义网络**:

```yaml
networks:
  apd-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

**连接外部网络**:

```yaml
networks:
  external-network:
    external: true
    name: my-network
```

---

## 安全建议

1. **不要在镜像中包含敏感信息**
   - 使用环境变量
   - 使用Docker Secrets（Swarm模式）

2. **定期更新基础镜像**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

3. **使用非root用户**
   在Dockerfile中添加：
   ```dockerfile
   RUN useradd -m appuser
   USER appuser
   ```

4. **限制容器权限**
   ```yaml
   services:
     apd:
       security_opt:
         - no-new-privileges:true
   ```

---

## 参考资料

- [Docker官方文档](https://docs.docker.com/)
- [Docker Compose文档](https://docs.docker.com/compose/)
- [Playwright Docker文档](https://playwright.dev/docs/docker)

---

## 技术支持

遇到问题？

- GitHub Issues: https://github.com/brianxiadong/auto-paper-digest/issues
- 查看日志: `docker-compose logs -f`
- 健康检查: `docker-compose ps`

---

**文档版本**: v1.0
**最后更新**: 2026-02-04
