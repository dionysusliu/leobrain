# Prefect WebUI 使用指南

本指南说明如何在 Prefect WebUI 中查看已注册的部署（Deployments）和正在进行的任务（Flow Runs）。

## 1. 启动 Prefect 服务器

确保 Prefect 服务器正在运行：

```bash
# 在项目根目录
docker compose up -d prefect-server

# 检查服务状态
docker compose ps prefect-server

# 查看日志
docker compose logs -f prefect-server
```

## 2. 访问 Prefect WebUI

Prefect WebUI 运行在以下地址：

- **WebUI URL**: http://localhost:4200
- **API URL**: http://localhost:4200/api

在浏览器中打开 http://localhost:4200 即可访问 Prefect WebUI。

## 3. 在 WebUI 中查看部署（Deployments）

### 3.1 部署 Flow 到 Prefect 服务器

在查看部署之前，需要先将 Flow 部署到 Prefect 服务器。有两种方式：

#### 方式 1: 使用 Prefect CLI（推荐）

```bash
# 进入 backend 目录
cd backend

# 设置 Prefect API URL
export PREFECT_API_URL="http://localhost:4200/api"

# 部署所有站点（需要创建部署脚本，见下方）
# 或者手动部署单个 flow
prefect deploy workers/prefect_manager.py:crawl_site_flow \
  --name crawl-bbc \
  --work-queue-name default \
  --tags crawler,bbc
```

#### 方式 2: 使用 Python 脚本部署

创建一个部署脚本（见下方"部署脚本"部分）。

### 3.2 在 WebUI 中查看部署

1. 打开 http://localhost:4200
2. 在左侧导航栏，点击 **"Deployments"** 或 **"部署"**
3. 您将看到所有已注册的部署列表，包括：
   - 部署名称（如 `crawl-bbc`, `crawl-reuters`）
   - 关联的 Flow 名称（`crawl_site_flow`）
   - 调度计划（Schedule）
   - 标签（Tags）
   - 工作队列（Work Queue）
   - 是否启用调度（Schedule Active）

### 3.3 部署详情

点击任意部署名称，可以查看：
- 部署配置详情
- 参数设置
- 调度计划详情
- 关联的 Flow Runs 历史

## 4. 在 WebUI 中查看 Flow Runs（正在进行的任务）

### 4.1 查看所有 Flow Runs

1. 在左侧导航栏，点击 **"Flow Runs"** 或 **"运行"**
2. 您将看到所有 Flow Runs 的列表，包括：
   - Flow Run ID
   - Flow 名称
   - 状态（Running, Completed, Failed, Pending 等）
   - 开始时间
   - 结束时间
   - 持续时间
   - 标签（Tags）

### 4.2 筛选 Flow Runs

可以使用以下方式筛选：
- **按状态筛选**：Running, Completed, Failed, Pending 等
- **按标签筛选**：例如 `crawler`, `bbc`, `reuters`
- **按时间范围筛选**：选择开始和结束时间
- **按 Flow 名称筛选**：例如 `crawl_site_flow`

### 4.3 Flow Run 详情

点击任意 Flow Run，可以查看：
- **概览**：状态、时间、持续时间
- **日志**：任务执行日志
- **任务详情**：每个 Task 的执行状态和结果
- **时间线**：任务执行的时间线视图
- **参数**：Flow 运行时的参数

## 5. 实时监控

### 5.1 查看正在运行的任务

1. 在 Flow Runs 页面
2. 使用状态筛选器选择 **"Running"**
3. 实时查看当前正在执行的任务

### 5.2 查看任务日志

1. 点击正在运行的 Flow Run
2. 在详情页面查看实时日志
3. 日志会自动更新，显示任务执行进度

## 6. 通过 API 查询（程序化访问）

除了 WebUI，也可以通过代码查询部署和运行：

```python
from workers.prefect_manager import get_deployments, get_flow_runs

# 获取所有部署
deployments = await get_deployments()

# 获取最近的 Flow Runs
runs = await get_flow_runs(limit=20)

# 获取特定站点的 Flow Runs
runs = await get_flow_runs(site_name="bbc", limit=10)
```

## 7. 常见问题

### Q: WebUI 显示 "No deployments found"

**A**: 需要先将 Flow 部署到 Prefect 服务器。使用部署脚本或 CLI 命令部署。

### Q: 看不到正在运行的任务

**A**: 检查：
1. Prefect Worker 是否在运行（需要运行 worker 来执行任务）
2. 任务是否真的被触发
3. 使用状态筛选器查看不同状态的任务

### Q: 如何启动 Prefect Worker

**A**: Worker 负责执行任务。启动方式：

```bash
# 设置 API URL
export PREFECT_API_URL="http://localhost:4200/api"

# 启动 worker
prefect worker start --pool default --type process
```

### Q: 如何手动触发任务

**A**: 
1. 在 WebUI 的 Deployments 页面，点击部署名称
2. 点击 "Run" 按钮手动触发
3. 或通过 API：`POST /api/v1/crawlers/sites/{site_name}/trigger`

## 8. 快速检查清单

- [ ] Prefect 服务器运行中（`docker compose ps prefect-server`）
- [ ] WebUI 可访问（http://localhost:4200）
- [ ] Flow 已部署到服务器
- [ ] Prefect Worker 正在运行（用于执行任务）
- [ ] 任务已触发（手动或通过调度）

## 9. 相关 API 端点

项目中的 FastAPI 也提供了查询接口：

- `GET /api/v1/jobs` - 获取所有部署
- `GET /api/v1/jobs/{job_id}` - 获取特定部署及其运行历史
- `GET /api/v1/crawlers/sites/{site_name}` - 获取站点配置和 Prefect 运行状态

