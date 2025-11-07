# LeoBrain 运维工具使用指南

## 🚀 统一入口

**Heimdall Dashboard**: http://localhost:8080

这是所有服务的统一入口，可以快速访问各个子系统。

## 📋 服务列表

### 开发工具

| 服务 | URL | 说明 | 账号 |
|------|-----|------|------|
| **API 文档** | http://localhost:8000/docs | FastAPI Swagger UI，可测试所有 API | - |
| **API 健康检查** | http://localhost:8000/health | API 服务健康状态 | - |

### 数据库管理

| 服务 | URL | 说明 | 账号 |
|------|-----|------|------|
| **pgAdmin** | http://localhost:8081 | PostgreSQL 管理界面 | Email: `admin@leobrain.com`<br>Password: `admin` |

**首次使用 pgAdmin：**
1. 访问 http://localhost:8081
2. 使用上述账号登录
3. 右键 "Servers" → "Register" → "Server"
4. 配置连接：
   - **Name**: `LeoBrain PostgreSQL`
   - **Host**: `postgres` (容器内) 或 `localhost` (宿主机)
   - **Port**: `5432`
   - **Database**: `leobrain`
   - **Username**: `leobrain`
   - **Password**: `leobrain_dev`
   - 勾选 "Save password"

### 存储管理

| 服务 | URL | 说明 | 账号 |
|------|-----|------|------|
| **MinIO Console** | http://localhost:9001 | 对象存储管理控制台 | `minioadmin` / `minioadmin` |

### 监控和日志

| 服务 | URL | 说明 | 账号 |
|------|-----|------|------|
| **Grafana** | http://localhost:3001 | 监控面板和日志查看 | `admin` / `admin` |
| **Prometheus** | http://localhost:9090 | 指标查询 | - |
| **Loki** | http://localhost:3100 | 日志聚合服务 | - |

**在 Grafana 中查看日志：**
1. 访问 http://localhost:3001
2. 登录后进入 **Explore** (左侧菜单)
3. 选择 **Loki** 数据源
4. 使用 LogQL 查询，例如：
   - `{container="leobrain-postgres"}` - PostgreSQL 日志
   - `{container="leobrain-minio"}` - MinIO 日志
   - `{service="api"}` - API 服务日志
   - `{container=~"leobrain-.*"}` - 所有 leobrain 容器日志

## 🔧 配置 Heimdall

### 添加应用

1. 访问 http://localhost:8080
2. 点击右上角 "+" 或 "Add Application"
3. 填写信息：
   - **Application Title**: 应用名称
   - **URL**: 应用地址
   - **Icon**: 选择或上传图标
   - **Category**: 选择分类（开发工具、数据库、存储、监控等）
   - **Health Check URL**: (可选) 健康检查地址

### 推荐的应用配置

#### 开发工具分类
- **API 文档**: http://localhost:8000/docs
- **API 健康**: http://localhost:8000/health

#### 数据库分类
- **pgAdmin**: http://localhost:8081

#### 存储分类
- **MinIO Console**: http://localhost:9001

#### 监控分类
- **Grafana**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **日志查看**: http://localhost:3001/explore

## 📊 Grafana Dashboard

### 数据源

已自动配置的数据源：
- **Prometheus**: http://prometheus:9090 (默认数据源)
- **Loki**: http://loki:3100

### 创建 Dashboard

1. 登录 Grafana
2. 进入 **Dashboards** → **New Dashboard**
3. 添加 Panel，选择数据源：
   - **Prometheus**: 用于指标监控
   - **Loki**: 用于日志查看

### 推荐的 Dashboard 面板

1. **系统健康**
   - API 请求速率 (QPS)
   - API 响应时间 (P50/P95/P99)
   - 数据库连接数

2. **爬虫监控**
   - 爬虫任务执行状态
   - 任务成功率
   - 各站点爬取数量

3. **存储监控**
   - MinIO 存储使用量
   - 各源数据量分布

4. **日志面板**
   - 实时日志流
   - 错误日志过滤
   - 日志级别分布

## 🐛 故障排查

### 服务无法启动

```bash
# 查看服务状态
docker compose ps

# 查看服务日志
docker logs leobrain-<service-name>

# 重启服务
docker compose restart <service-name>
```

### Loki 日志收集问题

```bash
# 检查 Promtail 是否正常运行
docker logs leobrain-promtail

# 检查 Loki 是否正常运行
docker logs leobrain-loki

# 验证 Loki 健康状态
curl http://localhost:3100/ready
```

### Grafana 数据源问题

1. 登录 Grafana
2. 进入 **Configuration** → **Data Sources**
3. 检查 Prometheus 和 Loki 数据源状态
4. 点击 "Test" 按钮验证连接

### pgAdmin 连接问题

1. 确认 PostgreSQL 服务运行正常：`docker compose ps postgres`
2. 在 pgAdmin 中使用正确的连接信息：
   - 从容器内连接：Host 使用 `postgres`
   - 从宿主机连接：Host 使用 `localhost`

## 📝 常用命令

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f <service-name>

# 重启服务
docker compose restart <service-name>

# 更新配置后重启
docker compose up -d --force-recreate <service-name>
```

## 🔐 默认账号汇总

| 服务 | 账号 | 密码 |
|------|------|------|
| Grafana | admin | admin |
| pgAdmin | admin@leobrain.com | admin |
| MinIO | minioadmin | minioadmin |

## 📚 更多资源

- [Grafana 文档](https://grafana.com/docs/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Loki 文档](https://grafana.com/docs/loki/)
- [pgAdmin 文档](https://www.pgadmin.org/docs/)
- [MinIO 文档](https://min.io/docs/)

