# My Flask API

一个简单的 Flask REST API 服务。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

服务将运行在 `http://localhost:5000`

## API 端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | /api/items | 获取所有项目 |
| GET | /api/items/:id | 获取单个项目 |
| POST | /api/items | 创建新项目 |
| PUT | /api/items/:id | 更新项目 |
| DELETE | /api/items/:id | 删除项目 |
| GET | /api/health | 健康检查 |

## 示例

```bash
# 获取所有项目
curl http://localhost:5000/api/items

# 创建项目
curl -X POST http://localhost:5000/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "New Item", "description": "A new item"}'

# 更新项目
curl -X PUT http://localhost:5000/api/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Item"}'

# 删除项目
curl -X DELETE http://localhost:5000/api/items/1
```
