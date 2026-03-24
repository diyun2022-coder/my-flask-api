# DevOps Tools API 🚀

一套完整的运维工具集合 API，用于服务监控、配置管理、日志查询、告警管理和部署任务调度。

## 📋 功能特性

### 1. 服务状态管理 🖥️
- 监控多个服务的运行状态（Nginx、MySQL、Redis、MongoDB 等）
- 端口检查和健康聚合
- 单服务和全批量状态查询

### 2. 配置文件管理 ⚙️
- 统一的配置管理接口
- 支持部分更新和完整覆盖
- 配置变更时间追踪

### 3. 日志查询接口 📝
- 多维度日志筛选（时间、级别、服务）
- 关键词搜索
- 日志级别：INFO、WARN、ERROR

### 4. 告警规则管理 🔔
- 灵活的告警规则配置
- 告警触发和通知
- 告警历史记录

### 5. 部署任务调度 🚀
- 异步部署任务执行
- 任务状态追踪（pending、running、completed、cancelled）
- 部署日志实时记录
- 支持任务取消

### 6. 系统信息监控 📊
- CPU 使用率
- 内存使用情况
- 磁盘空间
- 系统运行时间

## 🛠️ 技术栈

- **Flask** - Web 框架
- **psutil** - 系统监控
- **threading** - 异步任务执行
- **JSON** - 本地数据存储

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/diyun2022-coder/my-flask-api.git
cd my-flask-api

# 安装依赖
pip install -r requirements.txt

# 运行服务
flask run --host=0.0.0.0 --port=5000
```

## 📁 项目结构

```
my-flask-api/
├── app.py              # 主应用文件
├── requirements.txt    # Python 依赖
├── README.md          # 项目文档
├── ROADMAP.md         # 功能规划
└── data/              # 数据存储目录
    ├── config.json    # 配置文件
    ├── alerts.json    # 告警规则
    ├── deployments.json # 部署任务
    └── logs.json      # 日志数据
```

## 🔌 API 端点

### 服务状态管理
```
GET  /api/ops/services              # 获取所有服务状态
GET  /api/ops/services/<name>       # 获取单个服务状态
POST /api/ops/services/check        # 手动触发检查
```

### 配置管理
```
GET  /api/ops/config                # 获取配置
PUT  /api/ops/config                # 更新配置
GET  /api/ops/config/<key>          # 获取单个配置项
```

### 日志查询
```
GET  /api/ops/logs?level=ERROR&service=nginx&limit=50
POST /api/ops/logs                  # 添加日志（测试）
```

### 告警管理
```
GET    /api/ops/alerts              # 获取告警列表
GET    /api/ops/alerts/<id>         # 获取单个告警
POST   /api/ops/alerts              # 创建告警规则
PUT    /api/ops/alerts/<id>         # 更新告警规则
DELETE /api/ops/alerts/<id>         # 删除告警规则
```

### 部署任务
```
GET  /api/ops/deployments           # 获取部署任务列表
GET  /api/ops/deployments/<id>      # 获取单个任务
POST /api/ops/deployments           # 创建部署任务
POST /api/ops/deployments/<id>/cancel  # 取消部署任务
```

### 系统信息
```
GET /api/ops/system                 # 获取系统监控信息
```

### 健康检查
```
GET /api/health                     # API 健康检查
GET /api                             # API 文档
```

## 📊 使用示例

### 检查所有服务状态
```bash
curl http://localhost:5000/api/ops/services
```

响应：
```json
{
  "services": [
    {
      "name": "nginx",
      "port": 80,
      "status": "running",
      "message": "Service is running on port 80",
      "checked_at": "2026-03-24T10:00:00"
    }
  ],
  "total": 4,
  "running": 2
}
```

### 创建部署任务
```bash
curl -X POST http://localhost:5000/api/ops/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "project": "my-api",
    "environment": "production",
    "version": "v1.2.3",
    "triggered_by": "api"
  }'
```

响应：
```json
{
  "message": "Deployment created successfully",
  "deployment": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "project": "my-api",
    "environment": "production",
    "version": "v1.2.3",
    "status": "pending"
  }
}
```

### 创建告警规则
```bash
curl -X POST http://localhost:5000/api/ops/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "High CPU Usage",
    "condition": "cpu_percent > 80",
    "threshold": 80,
    "notification": {
      "email": "admin@example.com",
      "slack_webhook": "https://hooks.slack.com/..."
    },
    "status": "active"
  }'
```

### 查询错误日志
```bash
curl "http://localhost:5000/api/ops/logs?level=ERROR&limit=10"
```

## 🔧 配置

默认配置存储在 `data/config.json`：

```json
{
  "environment": "production",
  "log_level": "info",
  "max_connections": 100,
  "timeout": 30,
  "notification": {
    "email": "admin@example.com",
    "slack_webhook": ""
  }
}
```

## 🚀 生产部署建议

1. **使用 Gunicorn**：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **添加 Nginx 反向代理**
3. **启用 HTTPS 和身份验证**
4. **使用数据库替代 JSON 文件存储**（PostgreSQL、MongoDB）
5. **添加日志轮转**（logrotate）
6. **配置监控告警**

## 📝 待办事项

- [ ] 添加用户认证（JWT）
- [ ] 支持 WebSocket 实时推送
- [ ] 添加速率限制
- [ ] 完善单元测试
- [ ] Docker 容器化
- [ ] CI/CD 流水线

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

---

**作者**: diyun2022-coder
**项目**: DevOps Tools API
**版本**: 2.0.0
