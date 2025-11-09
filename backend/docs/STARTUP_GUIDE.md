# 后端服务启动指南

本指南说明如何正式运行 LeoBrain 后端服务。

## 📋 前置要求

1. **Python 3.11+** 已安装
2. **Docker 和 Docker Compose** 已安装
3. **PostgreSQL、MinIO、Redis** 等服务（通过 Docker Compose 运行）

## 🚀 启动步骤

### 1. 启动基础设施服务

```bash
# 在项目根目录
cd /Users/chuang/dev/leobrain

# 启动所有 Docker 服务（PostgreSQL, MinIO, Redis, Prefect 等）
docker compose up -d

# 检查服务状态
docker compose ps

# 查看服务日志（可选）
docker compose logs -f
```

### 2. 安装 Python 依赖

```bash
# 进入 backend 目录
cd backend

# 创建虚拟环境（推荐）
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 spaCy 语言模型（如果需要）
python -m spacy download en_core_web_sm
```

### 3. 配置环境变量（可选）

创建 `.env` 文件（如果不存在）：

```bash
cd backend
touch .env
```

编辑 `.env` 文件，添加以下配置（如果需要覆盖默认值）：

```env
# 数据库配置
DATABASE_URL=postgresql://leobrain:leobrain_dev@localhost:5432/leobrain

# MinIO 配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=leobrain-content
MINIO_SECURE=false

# Prefect 配置
PREFECT_API_URL=http://localhost:4200/api

# 日志配置（可选）
LOG_DIR=./logs
LOG_LEVEL=INFO
```

**注意**: 如果不创建 `.env` 文件，系统会使用代码中的默认值。

### 4. 运行数据库迁移

```bash
# 在 backend 目录
cd backend

# 运行数据库迁移
alembic upgrade head

# 如果需要创建新的迁移
# alembic revision --autogenerate -m "描述"
# alembic upgrade head
```

### 5. 启动后端服务

#### 方式 1: 使用 uvicorn（开发模式）

```bash
# 在 backend 目录
cd backend

# 确保虚拟环境已激活
source venv/bin/activate  # macOS/Linux

# 启动服务（开发模式，支持热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式 2: 使用启动脚本（推荐）

```bash
# 使用提供的启动脚本
./scripts/start_backend.sh
```

### 6. 验证服务运行

打开浏览器访问：

- **API 根路径**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **Prometheus 指标**: http://localhost:8000/metrics

## 🔍 检查服务状态

### 检查 Docker 服务

```bash
# 查看所有服务状态
docker compose ps

# 查看特定服务日志
docker compose logs postgres
docker compose logs minio
docker compose logs prefect-server
```

### 检查后端服务

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 检查 API 文档
curl http://localhost:8000/docs
```

### 检查数据库连接

```bash
# 使用 psql 连接（如果已安装）
psql -h localhost -U leobrain -d leobrain
# 密码: leobrain_dev

# 或使用 pgAdmin
# 访问 http://localhost:8081
```

## 🛠️ 常见问题

### 问题 1: 数据库连接失败

**错误**: `could not connect to server`

**解决方案**:
1. 确保 PostgreSQL 容器正在运行: `docker compose ps postgres`
2. 检查端口 5432 是否被占用
3. 验证 `DATABASE_URL` 配置是否正确

### 问题 2: MinIO 连接失败

**错误**: `Failed to connect to MinIO`

**解决方案**:
1. 确保 MinIO 容器正在运行: `docker compose ps minio`
2. 检查 MinIO Console: http://localhost:9001
3. 验证 MinIO 配置是否正确

### 问题 3: 端口已被占用

**错误**: `Address already in use`

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000  # macOS/Linux
# 或
netstat -ano | findstr :8000  # Windows

# 停止占用端口的进程，或修改启动端口
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 问题 4: 依赖安装失败

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像源（如果需要）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 5: 数据库迁移失败

**解决方案**:
```bash
# 检查当前迁移状态
alembic current

# 查看迁移历史
alembic history

# 如果需要回滚
alembic downgrade -1

# 重新运行迁移
alembic upgrade head
```

## 📊 服务端点

启动后，以下端点可用：

| 端点 | 说明 |
|------|------|
| `GET /` | API 根路径 |
| `GET /health` | 健康检查 |
| `GET /docs` | Swagger API 文档 |
| `GET /redoc` | ReDoc API 文档 |
| `GET /metrics` | Prometheus 指标 |
| `GET /api/v1/crawlers/sites` | 获取所有站点 |
| `GET /api/v1/jobs` | 获取所有任务 |
| `POST /api/v1/crawlers/sites/{site_name}/trigger` | 触发爬虫任务 |

## 🔄 生产环境部署

生产环境建议使用：

1. **Gunicorn + Uvicorn Workers**:
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **使用进程管理器** (如 systemd, supervisor)

3. **使用反向代理** (如 Nginx)

4. **配置日志轮转**

5. **设置环境变量**（不要使用默认值）

## 📝 下一步

- 查看 [Prefect WebUI 使用指南](./PREFECT_WEBUI_GUIDE.md) 了解如何管理任务
- 查看 [API 文档](http://localhost:8000/docs) 了解所有可用端点
- 配置前端服务连接到后端 API

