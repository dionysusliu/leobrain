# 触发爬虫任务指南

本指南说明如何触发单个或多个爬虫任务。

## 🚀 快速开始

### 方式 1: 使用脚本（推荐）

```bash
cd backend

# 触发所有站点
python scripts/trigger_crawlers.py

# 触发指定站点
python scripts/trigger_crawlers.py --sites bbc hackernews techcrunch

# 并行触发（更快）
python scripts/trigger_crawlers.py --all --parallel
```

### 方式 2: 使用 API

#### 触发单个站点

```bash
curl -X POST http://localhost:8000/api/v1/crawlers/sites/bbc/crawl
```

#### 批量触发多个站点

```bash
# 触发指定站点（串行）
curl -X POST http://localhost:8000/api/v1/crawlers/sites/batch-crawl \
  -H "Content-Type: application/json" \
  -d '{
    "sites": ["bbc", "hackernews", "techcrunch"],
    "parallel": false
  }'

# 触发所有站点（并行）
curl -X POST http://localhost:8000/api/v1/crawlers/sites/batch-crawl \
  -H "Content-Type: application/json" \
  -d '{
    "sites": null,
    "parallel": true
  }'
```

### 方式 3: 使用 API 文档（Swagger UI）

1. 访问 http://localhost:8000/docs
2. 找到 `POST /api/v1/crawlers/sites/batch-crawl` 端点
3. 点击 "Try it out"
4. 输入请求体，例如：
   ```json
   {
     "sites": ["bbc", "hackernews"],
     "parallel": true
   }
   ```
5. 点击 "Execute"

## 📋 可用站点

查看所有配置的站点：

```bash
# 使用脚本
python scripts/trigger_crawlers.py --sites  # 会显示帮助信息

# 使用 API
curl http://localhost:8000/api/v1/crawlers/sites
```

常见站点包括：
- **新闻类**: `bbc`, `theguardian`, `npr`, `cnbc`, `wsj_cn`
- **财经类**: `yahoo_finance_news`, `yahoo_finance_top`, `financial_times`, `dowjones`, `thomsonreuters`, `xueqiu`
- **科技类**: `hackernews`, `techcrunch`, `36kr`, `huxiu`

## 🔧 脚本使用说明

### 基本用法

```bash
# 触发所有站点（串行）
python scripts/trigger_crawlers.py

# 触发所有站点（并行，更快）
python scripts/trigger_crawlers.py --all --parallel

# 触发指定站点
python scripts/trigger_crawlers.py --sites bbc hackernews techcrunch

# 触发指定站点（并行）
python scripts/trigger_crawlers.py --sites bbc hackernews --parallel
```

### 参数说明

- `--sites SITE1 SITE2 ...`: 指定要触发的站点列表
- `--all`: 触发所有配置的站点
- `--parallel`: 并行触发所有任务（默认串行）
- `--api-url URL`: 指定 API 服务器地址（默认: http://localhost:8000）

### 示例

```bash
# 示例 1: 触发所有新闻类站点
python scripts/trigger_crawlers.py --sites bbc theguardian npr --parallel

# 示例 2: 触发所有财经类站点
python scripts/trigger_crawlers.py --sites yahoo_finance_news financial_times dowjones --parallel

# 示例 3: 触发所有科技类站点
python scripts/trigger_crawlers.py --sites hackernews techcrunch 36kr huxiu --parallel

# 示例 4: 触发所有站点（并行，最快）
python scripts/trigger_crawlers.py --all --parallel
```

## 📊 查看任务状态

### 在 Prefect WebUI 中查看

1. 访问 http://localhost:4200
2. 点击左侧导航栏的 **"Flow Runs"**
3. 查看任务执行状态：
   - **Running**: 正在执行
   - **Completed**: 已完成
   - **Failed**: 失败
   - **Pending**: 等待执行

### 通过 API 查看

```bash
# 查看所有站点状态
curl http://localhost:8000/api/v1/crawlers/sites

# 查看特定站点状态
curl http://localhost:8000/api/v1/crawlers/sites/bbc/status

# 查看特定站点的最近运行记录
curl http://localhost:8000/api/v1/crawlers/sites/bbc
```

## 🔍 监控任务执行

### 查看任务日志

任务执行日志会输出到：
- 后端服务控制台（如果使用 `uvicorn` 启动）
- Prefect WebUI 的 Flow Run 详情页面
- 日志文件（如果配置了文件日志）

### 在 Prefect WebUI 中查看日志

1. 访问 http://localhost:4200
2. 进入 **"Flow Runs"** 页面
3. 点击要查看的任务
4. 在详情页面查看实时日志

## ⚙️ 串行 vs 并行

### 串行执行（默认）

- 任务按顺序逐个触发
- 适合：需要控制资源使用、避免过载
- 使用：不添加 `--parallel` 参数

```bash
python scripts/trigger_crawlers.py --sites bbc hackernews techcrunch
```

### 并行执行

- 所有任务同时触发
- 适合：需要快速启动所有任务
- 使用：添加 `--parallel` 参数

```bash
python scripts/trigger_crawlers.py --sites bbc hackernews techcrunch --parallel
```

**注意**: 并行执行会同时启动多个任务，确保：
- Prefect Worker 有足够的并发能力
- 系统资源（CPU、内存、网络）充足
- 目标网站可以承受并发请求

## 🐛 故障排除

### 问题 1: 任务未启动

**检查**:
1. 后端服务是否运行: `curl http://localhost:8000/health`
2. Prefect 服务器是否运行: `docker compose ps prefect-server`
3. Prefect Worker 是否运行（需要 worker 来执行任务）

**解决方案**:
```bash
# 启动 Prefect Worker
export PREFECT_API_URL="http://localhost:4200/api"
prefect worker start --work-queue default
```

### 问题 2: 站点不存在

**错误**: `Site xxx not found`

**解决方案**:
```bash
# 查看所有可用站点
curl http://localhost:8000/api/v1/crawlers/sites
```

### 问题 3: API 连接失败

**错误**: `Connection refused` 或 `Connection timeout`

**解决方案**:
1. 确保后端服务正在运行
2. 检查 API URL 是否正确
3. 使用 `--api-url` 参数指定正确的地址

### 问题 4: 任务执行失败

**检查**:
1. 在 Prefect WebUI 中查看任务日志
2. 检查网络连接（是否能访问目标网站）
3. 检查站点配置是否正确

## 📝 API 参考

### POST /api/v1/crawlers/sites/{site_name}/crawl

触发单个站点的爬虫任务。

**响应示例**:
```json
{
  "message": "Crawl task started for bbc",
  "site": "bbc",
  "flow_run_id": "abc123-def456-ghi789"
}
```

### POST /api/v1/crawlers/sites/batch-crawl

批量触发多个站点的爬虫任务。

**请求体**:
```json
{
  "sites": ["bbc", "hackernews"],  // null 表示所有站点
  "parallel": true  // 是否并行执行
}
```

**响应示例**:
```json
{
  "message": "Triggered 2 crawl tasks",
  "total": 2,
  "success": 2,
  "failed": 0,
  "results": {
    "bbc": {
      "success": true,
      "site": "bbc",
      "flow_run_id": "abc123",
      "message": "Crawl task started for bbc"
    },
    "hackernews": {
      "success": true,
      "site": "hackernews",
      "flow_run_id": "def456",
      "message": "Crawl task started for hackernews"
    }
  }
}
```

## 🎯 最佳实践

1. **首次运行**: 先触发单个站点测试，确保配置正确
2. **批量运行**: 使用并行模式快速启动所有任务
3. **监控执行**: 在 Prefect WebUI 中监控任务状态
4. **错误处理**: 检查失败的任务日志，修复问题后重新触发
5. **资源管理**: 根据系统资源调整并发数量

## 📚 相关文档

- [启动指南](./STARTUP_GUIDE.md) - 如何启动后端服务
- [Prefect WebUI 指南](./PREFECT_WEBUI_GUIDE.md) - 如何查看和管理任务

