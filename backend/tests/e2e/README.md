# End-to-End (E2E) Tests

端到端测试使用真实的服务（PostgreSQL、MinIO）来验证整个系统的功能。

## 前置要求

1. **启动 Docker 服务**
   ```bash
   # 在项目根目录
   docker compose up -d
   ```

2. **等待服务就绪**
   测试会自动等待服务就绪，但首次启动可能需要一些时间。

3. **环境变量（可选）**
   如果需要使用不同的测试数据库或MinIO配置：
   ```bash
   export TEST_DATABASE_URL="postgresql://leobrain:leobrain_dev@localhost:5432/leobrain_test"
   export TEST_MINIO_ENDPOINT="localhost:9000"
   export TEST_MINIO_ACCESS_KEY="minioadmin"
   export TEST_MINIO_SECRET_KEY="minioadmin"
   export TEST_MINIO_BUCKET="leobrain-content-test"
   export PREFECT_API_URL="http://localhost:4200/api"  # Prefect API URL
   ```

### 服务要求

- **必需服务**: PostgreSQL, MinIO
- **可选服务**: Prefect Server（用于 Prefect 相关测试）
  - 如果 Prefect 服务器未运行，相关测试会被跳过
  - 启动 Prefect 服务器：`docker compose up -d prefect-server`

## 运行 E2E 测试

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v -m e2e

# 运行特定测试文件
pytest tests/e2e/test_api_e2e.py -v
pytest tests/e2e/test_prefect_e2e.py -v  # Prefect 相关测试

# 带覆盖率
pytest tests/e2e/ -v --cov=app --cov=crawlers --cov=common --cov=workers
```

## 测试框架说明

### 使用的框架和工具

1. **FastAPI TestClient / httpx.AsyncClient**
   - 用于测试 API 端点
   - 不需要启动实际的 HTTP 服务器
   - 直接测试 FastAPI 应用实例

2. **pytest + pytest-asyncio**
   - 异步测试支持
   - Fixture 管理

3. **Docker Compose**
   - 管理真实的服务（PostgreSQL、MinIO、Redis、Prefect Server）
   - 测试使用真实的数据存储和服务

### 测试流程

1. **服务检查**: 检查 Docker 服务是否运行
2. **数据库准备**: 创建测试数据库会话
3. **存储准备**: 连接到真实的 MinIO
4. **API 测试**: 使用 httpx 客户端测试 API
5. **数据验证**: 验证数据库和 MinIO 中的数据

### Fixtures

- `docker_services_required`: 检查 Docker 服务是否运行
- `e2e_db_session`: 真实的 PostgreSQL 数据库会话
- `e2e_storage_service`: 真实的 MinIO 存储服务
- `async_client`: 异步 HTTP 客户端（用于测试 API）
- `sync_client`: 同步 HTTP 客户端（用于测试 API）
- `mock_fetcher_for_e2e`: Mock 的 HTTP fetcher（返回测试数据）

## 测试覆盖

### API 端点测试
- ✅ Health check
- ✅ Root endpoint
- ✅ 获取所有站点
- ✅ 获取内容列表
- ✅ 创建内容
- ✅ 获取单个内容
- ✅ 触发爬虫任务

### Prefect 集成测试
- ✅ Prefect 服务器健康检查
- ✅ Prefect WebUI 可访问性
- ✅ 获取部署列表（从服务器和本地配置）
- ✅ 创建部署配置
- ✅ 获取流程运行记录
- ✅ 手动触发爬虫任务
- ✅ Jobs API 端点 (`/api/v1/jobs/`)
- ✅ 特定 Job API 端点 (`/api/v1/jobs/{job_id}`)
- ✅ 服务器连接失败回退机制
- ✅ Crawlers API 中的 Prefect 状态集成
- ✅ **完整 E2E 流程**: API -> Prefect -> Crawler -> DB -> MinIO（验证整个流程通过 Prefect）

### 完整流程测试
- ✅ 爬虫 → 数据库 → MinIO 完整流程
- ✅ 重复检测
- ✅ 数据一致性验证

## 注意事项

1. **数据清理**: 测试后可能需要手动清理测试数据
2. **服务依赖**: 确保 Docker 服务在运行
3. **端口冲突**: 确保 5432、9000 等端口未被占用
4. **测试隔离**: 每个测试使用独立的数据库会话，但共享同一个数据库

## 故障排查

### Docker 服务未运行
```bash
docker compose ps
docker compose up -d
```

### 数据库连接失败
检查环境变量和数据库配置：
```bash
echo $DATABASE_URL
```

### MinIO 连接失败
检查 MinIO 是否可访问：
```bash
curl http://localhost:9000/minio/health/live
```

### Prefect 服务器连接失败
检查 Prefect 服务器是否可访问：
```bash
curl http://localhost:4200/api/health
docker compose ps prefect-server
```

如果 Prefect 服务器未运行，Prefect 相关的 e2e 测试会被自动跳过，不会导致测试失败。

