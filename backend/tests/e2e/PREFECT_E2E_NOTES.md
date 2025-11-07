# Prefect E2E 测试说明

## 问题分析

### 原有测试的问题

1. **`test_complete_workflow_e2e.py` 和 `test_crawler_e2e.py`**:
   - 直接调用 `CrawlerEngine`，**绕过了 Prefect**
   - 这不是真正的 e2e 测试，因为跳过了 Prefect 调度层
   - 这些测试更像是集成测试，测试爬虫引擎本身

2. **`test_api_e2e.py::test_trigger_crawl_via_api`**:
   - 虽然调用了 API 端点（会通过 Prefect），但：
     - 期望的响应字段是 `job_id`，但实际 API 返回的是 `flow_run_id`（已修复）
     - 没有验证任务是否真的在 Prefect 中创建了 flow run
     - 没有验证 Prefect 中是否有对应的运行记录

### 真正的 E2E 测试应该是什么？

真正的 E2E 测试应该验证**完整的用户流程**：
```
用户请求 (API) 
  → Prefect 接收任务 
  → Prefect 创建 Flow Run 
  → Prefect 执行 Task 
  → 爬虫引擎执行 
  → 数据写入数据库 
  → 数据存储到 MinIO 
  → 可以通过 API 查询数据
  → 可以通过 Prefect API 查询运行状态
```

## 解决方案

### 1. 修复现有测试

- ✅ 修复了 `test_trigger_crawl_via_api` 中的字段名错误（`job_id` → `flow_run_id`）
- ✅ 更新了测试注释，明确说明这是通过 Prefect 触发的

### 2. 添加完整的 E2E 测试

新增了 `test_full_e2e_workflow_via_prefect`，这个测试：

1. **通过 API 触发爬虫** (`POST /api/v1/crawlers/sites/{site_name}/crawl`)
2. **验证 Prefect Flow Run 创建**：检查返回的 `flow_run_id` 是否有效
3. **验证 Prefect 中有运行记录**：通过 `get_flow_runs` 查询
4. **验证任务执行**：使用真实的爬虫引擎（但 mock HTTP fetcher 避免外部调用）
5. **验证数据持久化**：
   - 数据库中有内容
   - MinIO 中有存储
6. **验证 API 查询**：可以通过 API 查询到数据
7. **验证 Prefect 状态查询**：可以通过 Jobs API 查询运行状态

### 3. 测试策略

- **Mock HTTP 请求**：避免实际的外部 HTTP 调用，使用测试 fixture
- **使用真实服务**：使用真实的数据库、MinIO、Prefect 服务器
- **验证完整流程**：从 API 到数据存储的每个环节都验证

## 测试分类

### 集成测试（Integration Tests）
- `test_complete_workflow_e2e.py` - 测试爬虫引擎 → DB → MinIO
- `test_crawler_e2e.py` - 测试爬虫引擎功能

### E2E 测试（End-to-End Tests）
- `test_api_e2e.py::test_trigger_crawl_via_api` - 测试 API 端点（通过 Prefect）
- `test_prefect_e2e.py::test_full_e2e_workflow_via_prefect` - **完整的 E2E 流程**

## 运行测试

```bash
# 运行完整的 Prefect E2E 测试
pytest tests/e2e/test_prefect_e2e.py::TestPrefectAPIE2E::test_full_e2e_workflow_via_prefect -v

# 确保 Prefect 服务器运行
docker compose up -d prefect-server

# 运行所有 Prefect 相关测试
pytest tests/e2e/test_prefect_e2e.py -v
```

## 注意事项

1. **Prefect 服务器必须运行**：完整的 E2E 测试需要 Prefect 服务器
2. **测试隔离**：每个测试使用独立的数据库会话，但共享同一个数据库
3. **Mock 策略**：只 mock HTTP 请求，其他都使用真实服务
4. **异步等待**：Prefect 任务执行是异步的，测试中需要适当等待

