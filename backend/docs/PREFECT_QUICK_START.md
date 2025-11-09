# Prefect WebUI 快速开始

## 快速访问

1. **启动 Prefect 服务器**
   ```bash
   docker compose up -d prefect-server
   ```

2. **访问 WebUI**
   - 打开浏览器访问: **http://localhost:4200**

## 查看已注册的部署（Deployments）

1. 在 WebUI 左侧导航栏，点击 **"Deployments"**
2. 查看所有已注册的部署列表
3. 每个部署显示：
   - 部署名称
   - Flow 名称
   - 调度计划
   - 标签
   - 工作队列

## 查看正在进行的任务（Flow Runs）

1. 在 WebUI 左侧导航栏，点击 **"Flow Runs"**
2. 查看所有任务运行：
   - **Running**: 正在执行的任务
   - **Completed**: 已完成的任务
   - **Failed**: 失败的任务
   - **Pending**: 等待执行的任务

3. **筛选任务**：
   - 使用状态筛选器（Running, Completed, Failed 等）
   - 使用标签筛选器（如 `crawler`, `bbc`）
   - 使用时间范围筛选器

4. **查看任务详情**：
   - 点击任意 Flow Run
   - 查看日志、任务状态、执行时间线

## 部署 Flow（如果还没有部署）

### 方式 1: 使用 CLI（推荐）

```bash
cd backend
export PREFECT_API_URL="http://localhost:4200/api"

# 查看部署配置
python scripts/deploy_prefect_flows.py

# 使用 CLI 部署（根据脚本输出的命令）
prefect deploy workers/prefect_manager.py:crawl_site_flow \
  --name crawl-bbc \
  --work-queue-name default \
  --tags crawler,bbc
```

### 方式 2: 在 WebUI 中手动创建

1. 访问 http://localhost:4200
2. 导航到 "Deployments"
3. 点击 "Create Deployment"
4. 选择 flow 并配置参数

## 启动 Worker 执行任务

部署后，需要启动 Worker 来执行任务：

```bash
export PREFECT_API_URL="http://localhost:4200/api"
prefect worker start --work-queue default
```

## 通过 API 查询

项目 API 也提供了查询接口：

- `GET /api/v1/jobs` - 获取所有部署
- `GET /api/v1/jobs/{job_id}` - 获取特定部署及其运行历史

## 详细文档

更多详细信息，请参考: [PREFECT_WEBUI_GUIDE.md](./PREFECT_WEBUI_GUIDE.md)

