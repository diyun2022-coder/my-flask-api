from flask import Flask, jsonify, request
import psutil
import os
import json
from datetime import datetime
from functools import wraps
import threading
import uuid
from typing import Dict, List, Any, Optional

app = Flask(__name__)

# ========== 数据存储 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# 监控的服务列表
SERVICES = [
    {"name": "nginx", "port": 80, "check_url": "http://localhost/status"},
    {"name": "mysql", "port": 3306, "check_method": "port"},
    {"name": "redis", "port": 6379, "check_method": "port"},
    {"name": "mongodb", "port": 27017, "check_method": "port"},
]

# 配置文件路径
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
ALERTS_FILE = os.path.join(DATA_DIR, 'alerts.json')
DEPLOYMENTS_FILE = os.path.join(DATA_DIR, 'deployments.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')

# ========== 初始化数据 ==========
def init_data():
    """初始化数据文件"""
    # 默认配置
    default_config = {
        "environment": "production",
        "log_level": "info",
        "max_connections": 100,
        "timeout": 30,
        "notification": {
            "email": "admin@example.com",
            "slack_webhook": ""
        }
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)

    # 告警规则
    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'w') as f:
            json.dump([], f)

    # 部署任务
    if not os.path.exists(DEPLOYMENTS_FILE):
        with open(DEPLOYMENTS_FILE, 'w') as f:
            json.dump([], f)

    # 模拟日志数据
    if not os.path.exists(LOGS_FILE):
        sample_logs = [
            {"timestamp": "2026-03-24T10:00:00", "level": "INFO", "service": "nginx", "message": "Server started"},
            {"timestamp": "2026-03-24T10:01:00", "level": "WARN", "service": "mysql", "message": "High connection count"},
            {"timestamp": "2026-03-24T10:02:00", "level": "ERROR", "service": "api", "message": "Connection timeout"},
        ]
        with open(LOGS_FILE, 'w') as f:
            json.dump(sample_logs, f)

init_data()

# ========== 工具函数 ==========
def load_json_file(filepath: str, default: Any = None) -> Any:
    """安全加载 JSON 文件"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return default

def save_json_file(filepath: str, data: Any) -> bool:
    """安全保存 JSON 文件"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

def check_port(port: int) -> bool:
    """检查端口是否开放"""
    try:
        with psutil.net_connections() as connections:
            for conn in connections:
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    return True
        return False
    except Exception:
        return False

def get_service_status(service: dict) -> dict:
    """获取服务状态"""
    status = {
        "name": service["name"],
        "port": service["port"],
        "status": "unknown",
        "message": "",
        "checked_at": datetime.now().isoformat()
    }

    # 检查端口
    if check_port(service["port"]):
        status["status"] = "running"
        status["message"] = f"Service is running on port {service['port']}"
    else:
        status["status"] = "stopped"
        status["message"] = f"Port {service['port']} is not listening"

    return status

# ========== 1. 服务状态管理 ==========
@app.route("/api/ops/services", methods=["GET"])
def get_services_status():
    """获取所有服务状态"""
    services_status = [get_service_status(svc) for svc in SERVICES]
    return jsonify({
        "services": services_status,
        "total": len(services_status),
        "running": sum(1 for s in services_status if s["status"] == "running"),
        "checked_at": datetime.now().isoformat()
    })

@app.route("/api/ops/services/<service_name>", methods=["GET"])
def get_service_status_by_name(service_name: str):
    """获取单个服务状态"""
    service = next((s for s in SERVICES if s["name"] == service_name), None)
    if not service:
        return jsonify({"error": "Service not found"}), 404

    return jsonify({"service": get_service_status(service)})

@app.route("/api/ops/services/check", methods=["POST"])
def check_service():
    """手动触发服务检查"""
    service_name = request.json.get("service_name")
    if service_name:
        service = next((s for s in SERVICES if s["name"] == service_name), None)
        if not service:
            return jsonify({"error": "Service not found"}), 404
        status = get_service_status(service)
        return jsonify({"service": status})
    else:
        services_status = [get_service_status(svc) for svc in SERVICES]
        return jsonify({"services": services_status})

# ========== 2. 配置文件管理 ==========
@app.route("/api/ops/config", methods=["GET"])
def get_config():
    """获取配置"""
    config = load_json_file(CONFIG_FILE)
    return jsonify({
        "config": config,
        "updated_at": datetime.fromtimestamp(os.path.getmtime(CONFIG_FILE)).isoformat()
    })

@app.route("/api/ops/config", methods=["PUT"])
def update_config():
    """更新配置"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    current_config = load_json_file(CONFIG_FILE, {})

    # 合并配置
    updated_config = {**current_config, **data}

    if save_json_file(CONFIG_FILE, updated_config):
        return jsonify({
            "config": updated_config,
            "message": "Config updated successfully"
        })
    else:
        return jsonify({"error": "Failed to save config"}), 500

@app.route("/api/ops/config/<key>", methods=["GET"])
def get_config_key(key: str):
    """获取单个配置项"""
    config = load_json_file(CONFIG_FILE, {})
    if key in config:
        return jsonify({key: config[key]})
    return jsonify({"error": "Config key not found"}), 404

# ========== 3. 日志查询接口 ==========
@app.route("/api/ops/logs", methods=["GET"])
def get_logs():
    """查询日志"""
    logs = load_json_file(LOGS_FILE, [])

    # 筛选参数
    level = request.args.get("level")
    service = request.args.get("service")
    limit = request.args.get("limit", 100, type=int)

    filtered_logs = logs

    if service:
        filtered_logs = [log for log in filtered_logs if log["service"] == service]

    if level:
        filtered_logs = [log for log in filtered_logs if log["level"] == level]

    # 按时间倒序
    filtered_logs = sorted(filtered_logs, key=lambda x: x["timestamp"], reverse=True)

    return jsonify({
        "logs": filtered_logs[:limit],
        "total": len(filtered_logs),
        "filters": {"level": level, "service": service}
    })

@app.route("/api/ops/logs", methods=["POST"])
def add_log():
    """添加日志（用于测试）"""
    data = request.get_json()
    if not data or "level" not in data or "message" not in data:
        return jsonify({"error": "level and message are required"}), 400

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": data["level"],
        "service": data.get("service", "unknown"),
        "message": data["message"]
    }

    logs = load_json_file(LOGS_FILE, [])
    logs.append(log_entry)

    if save_json_file(LOGS_FILE, logs):
        return jsonify({"log": log_entry, "message": "Log added successfully"})
    return jsonify({"error": "Failed to save log"}), 500

# ========== 4. 告警规则管理 ==========
@app.route("/api/ops/alerts", methods=["GET"])
def get_alerts():
    """获取告警规则列表"""
    alerts = load_json_file(ALERTS_FILE, [])
    status = request.args.get("status")

    if status:
        alerts = [a for a in alerts if a.get("status") == status]

    return jsonify({
        "alerts": alerts,
        "total": len(alerts)
    })

@app.route("/api/ops/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: str):
    """获取单个告警规则"""
    alerts = load_json_file(ALERTS_FILE, [])
    alert = next((a for a in alerts if a["id"] == alert_id), None)

    if not alert:
        return jsonify({"error": "Alert not found"}), 404

    return jsonify({"alert": alert})

@app.route("/api/ops/alerts", methods=["POST"])
def create_alert():
    """创建告警规则"""
    data = request.get_json()

    if not data or "rule_name" not in data or "condition" not in data:
        return jsonify({"error": "rule_name and condition are required"}), 400

    alert = {
        "id": str(uuid.uuid4()),
        "rule_name": data["rule_name"],
        "condition": data["condition"],
        "threshold": data.get("threshold"),
        "notification": data.get("notification", {}),
        "status": data.get("status", "active"),
        "created_at": datetime.now().isoformat(),
        "triggered_count": 0
    }

    alerts = load_json_file(ALERTS_FILE, [])
    alerts.append(alert)

    if save_json_file(ALERTS_FILE, alerts):
        return jsonify({"alert": alert, "message": "Alert created successfully"}), 201
    return jsonify({"error": "Failed to save alert"}), 500

@app.route("/api/ops/alerts/<alert_id>", methods=["PUT"])
def update_alert(alert_id: str):
    """更新告警规则"""
    alerts = load_json_file(ALERTS_FILE, [])
    alert_index = next((i for i, a in enumerate(alerts) if a["id"] == alert_id), None)

    if alert_index is None:
        return jsonify({"error": "Alert not found"}), 404

    data = request.get_json()
    alerts[alert_index].update(data)
    alerts[alert_index]["updated_at"] = datetime.now().isoformat()

    if save_json_file(ALERTS_FILE, alerts):
        return jsonify({"alert": alerts[alert_index], "message": "Alert updated successfully"})
    return jsonify({"error": "Failed to save alert"}), 500

@app.route("/api/ops/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id: str):
    """删除告警规则"""
    alerts = load_json_file(ALERTS_FILE, [])
    alerts = [a for a in alerts if a["id"] != alert_id]

    if save_json_file(ALERTS_FILE, alerts):
        return jsonify({"message": "Alert deleted successfully"})
    return jsonify({"error": "Failed to delete alert"}), 500

# ========== 5. 部署任务调度 ==========
@app.route("/api/ops/deployments", methods=["GET"])
def get_deployments():
    """获取部署任务列表"""
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    status = request.args.get("status")

    if status:
        deployments = [d for d in deployments if d.get("status") == status]

    return jsonify({
        "deployments": deployments,
        "total": len(deployments)
    })

@app.route("/api/ops/deployments/<deployment_id>", methods=["GET"])
def get_deployment(deployment_id: str):
    """获取单个部署任务"""
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployment = next((d for d in deployments if d["id"] == deployment_id), None)

    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404

    return jsonify({"deployment": deployment})

@app.route("/api/ops/deployments", methods=["POST"])
def create_deployment():
    """创建部署任务"""
    data = request.get_json()

    if not data or "project" not in data or "environment" not in data:
        return jsonify({"error": "project and environment are required"}), 400

    deployment = {
        "id": str(uuid.uuid4()),
        "project": data["project"],
        "environment": data["environment"],
        "version": data.get("version", "latest"),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "logs": [],
        "triggered_by": data.get("triggered_by", "api")
    }

    # 异步执行部署（模拟）
    def execute_deployment():
        deployment["status"] = "running"
        deployment["started_at"] = datetime.now().isoformat()
        deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment started"})
        save_json_file(DEPLOYMENTS_FILE, load_json_file(DEPLOYMENTS_FILE, []) + [deployment])

        # 模拟部署步骤
        import time
        time.sleep(2)
        deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Pulling code..."})
        time.sleep(1)
        deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Running tests..."})
        time.sleep(1)
        deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Deploying to production..."})
        time.sleep(1)

        deployment["status"] = "completed"
        deployment["completed_at"] = datetime.now().isoformat()
        deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment completed successfully"})

        deployments = load_json_file(DEPLOYMENTS_FILE, [])
        idx = next((i for i, d in enumerate(deployments) if d["id"] == deployment["id"]), None)
        if idx is not None:
            deployments[idx] = deployment
            save_json_file(DEPLOYMENTS_FILE, deployments)

    # 启动后台任务
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployments.append(deployment)
    save_json_file(DEPLOYMENTS_FILE, deployments)

    thread = threading.Thread(target=execute_deployment)
    thread.start()

    return jsonify({"deployment": deployment, "message": "Deployment created successfully"}), 201

@app.route("/api/ops/deployments/<deployment_id>/cancel", methods=["POST"])
def cancel_deployment(deployment_id: str):
    """取消部署任务"""
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployment = next((d for d in deployments if d["id"] == deployment_id), None)

    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404

    if deployment["status"] not in ["pending", "running"]:
        return jsonify({"error": "Cannot cancel deployment in current state"}), 400

    deployment["status"] = "cancelled"
    deployment["completed_at"] = datetime.now().isoformat()
    deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment cancelled by user"})

    if save_json_file(DEPLOYMENTS_FILE, deployments):
        return jsonify({"deployment": deployment, "message": "Deployment cancelled"})
    return jsonify({"error": "Failed to cancel deployment"}), 500

# ========== 系统信息 ==========
@app.route("/api/ops/system", methods=["GET"])
def get_system_info():
    """获取系统信息"""
    return jsonify({
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "uptime": datetime.now().isoformat()
        }
    })

# ========== 健康检查 ==========
@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    })

# ========== API 文档 ==========
@app.route("/api", methods=["GET"])
def api_docs():
    """API 文档"""
    return jsonify({
        "name": "DevOps Tools API",
        "version": "2.0.0",
        "endpoints": {
            "services": {
                "GET /api/ops/services": "获取所有服务状态",
                "GET /api/ops/services/<name>": "获取单个服务状态",
                "POST /api/ops/services/check": "手动触发服务检查"
            },
            "config": {
                "GET /api/ops/config": "获取配置",
                "PUT /api/ops/config": "更新配置",
                "GET /api/ops/config/<key>": "获取单个配置项"
            },
            "logs": {
                "GET /api/ops/logs": "查询日志",
                "POST /api/ops/logs": "添加日志（测试用）"
            },
            "alerts": {
                "GET /api/ops/alerts": "获取告警规则列表",
                "GET /api/ops/alerts/<id