from flask import Flask, jsonify, request
import psutil
import os
import json
from datetime import datetime
import threading
import uuid
from typing import Dict, List, Any

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SERVICES = [
    {"name": "nginx", "port": 80},
    {"name": "mysql", "port": 3306},
    {"name": "redis", "port": 6379},
    {"name": "mongodb", "port": 27017},
]

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
ALERTS_FILE = os.path.join(DATA_DIR, 'alerts.json')
DEPLOYMENTS_FILE = os.path.join(DATA_DIR, 'deployments.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')

# ========== 初始化 ==========
def init_data():
    default_config = {"environment": "production", "log_level": "info", "max_connections": 100, "timeout": 30}
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(DEPLOYMENTS_FILE):
        with open(DEPLOYMENTS_FILE, 'w') as f:
            json.dump([], f)
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
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return default

def save_json_file(filepath: str, data: Any) -> bool:
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

def check_port(port: int) -> bool:
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return True
        return False
    except Exception as e:
        print(f"Error checking port {port}: {e}")
        return False

def get_service_status(service: dict) -> dict:
    status = {
        "name": service["name"],
        "port": service["port"],
        "status": "unknown",
        "message": "",
        "checked_at": datetime.now().isoformat()
    }
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
    services_status = [get_service_status(svc) for svc in SERVICES]
    running = sum(1 for s in services_status if s["status"] == "running")
    return jsonify({
        "services": services_status,
        "total": len(services_status),
        "running": running,
        "stopped": len(services_status) - running,
        "checked_at": datetime.now().isoformat()
    })

@app.route("/api/ops/services/<service_name>", methods=["GET"])
def get_service_status_by_name(service_name: str):
    service = next((s for s in SERVICES if s["name"] == service_name), None)
    if not service:
        return jsonify({"error": "Service not found"}), 404
    return jsonify({"service": get_service_status(service)})

@app.route("/api/ops/services/check", methods=["POST"])
def check_service():
    data = request.get_json() or {}
    if "service_name" in data:
        service = next((s for s in SERVICES if s["name"] == data["service_name"]), None)
        if not service:
            return jsonify({"error": "Service not found"}), 404
        return jsonify({"service": get_service_status(service)})
    else:
        services_status = [get_service_status(svc) for svc in SERVICES]
        return jsonify({"services": services_status, "checked_at": datetime.now().isoformat()})

# ========== 2. 配置文件管理 ==========
@app.route("/api/ops/config", methods=["GET"])
def get_config():
    config = load_json_file(CONFIG_FILE)
    return jsonify({
        "config": config,
        "updated_at": datetime.fromtimestamp(os.path.getmtime(CONFIG_FILE)).isoformat() if os.path.exists(CONFIG_FILE) else None
    })

@app.route("/api/ops/config", methods=["PUT"])
def update_config():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    current_config = load_json_file(CONFIG_FILE, {})
    updated_config = {**current_config, **data}
    if save_json_file(CONFIG_FILE, updated_config):
        return jsonify({"config": updated_config, "message": "Config updated successfully"})
    else:
        return jsonify({"error": "Failed to save config"}), 500

@app.route("/api/ops/config/<key>", methods=["GET"])
def get_config_key(key: str):
    config = load_json_file(CONFIG_FILE, {})
    if key in config:
        return jsonify({key: config[key]})
    return jsonify({"error": "Config key not found"}), 404

# ========== 3. 日志查询接口 ==========
@app.route("/api/ops/logs", methods=["GET"])
def get_logs():
    logs = load_json_file(LOGS_FILE, [])
    level = request.args.get("level")
    service = request.args.get("service")
    limit = request.args.get("limit", 100, type=int)
    
    filtered_logs = logs
    if service:
        filtered_logs = [log for log in filtered_logs if log.get("service") == service]
    if level:
        filtered_logs = [log for log in filtered_logs if log.get("level") == level]
    
    filtered_logs = sorted(filtered_logs, key=lambda x: x["timestamp"], reverse=True)
    
    return jsonify({
        "logs": filtered_logs[:limit],
        "total": len(filtered_logs),
        "filters": {"level": level, "service": service, "limit": limit}
    })

@app.route("/api/ops/logs", methods=["POST"])
def add_log():
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
    alerts = load_json_file(ALERTS_FILE, [])
    status = request.args.get("status")
    if status:
        alerts = [a for a in alerts if a.get("status") == status]
    return jsonify({"alerts": alerts, "total": len(alerts)})

@app.route("/api/ops/alerts/<alert_id>", methods=["GET"])
def get_alert(alert_id: str):
    alerts = load_json_file(ALERTS_FILE, [])
    alert = next((a for a in alerts if a["id"] == alert_id), None)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"alert": alert})

@app.route("/api/ops/alerts", methods=["POST"])
def create_alert():
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
        return jsonify({"alert": alert, "message": "Alert created successfully"}, 201)
    return jsonify({"error": "Failed to save alert"}), 500

@app.route("/api/ops/alerts/<alert_id>", methods=["PUT"])
def update_alert(alert_id: str):
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
    alerts = load_json_file(ALERTS_FILE, [])
    alerts = [a for a in alerts if a["id"] != alert_id]
    if save_json_file(ALERTS_FILE, alerts):
        return jsonify({"message": "Alert deleted successfully"})
    return jsonify({"error": "Failed to delete alert"}), 500

# ========== 5. 部署任务调度 ==========
@app.route("/api/ops/deployments", methods=["GET"])
def get_deployments():
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    status = request.args.get("status")
    if status:
        deployments = [d for d in deployments if d.get("status") == status]
    return jsonify({"deployments": deployments, "total": len(deployments)})

@app.route("/api/ops/deployments/<deployment_id>", methods=["GET"])
def get_deployment(deployment_id: str):
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployment = next((d for d in deployments if d["id"] == deployment_id), None)
    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404
    return jsonify({"deployment": deployment})

@app.route("/api/ops/deployments", methods=["POST"])
def create_deployment():
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
    
    # 异步执行部署
    def execute_deployment():
        import time
        deployments = load_json_file(DEPLOYMENTS_FILE, [])
        idx = next((i for i, d in enumerate(deployments) if d["id"] == deployment["id"]), None)
        if idx is not None:
            deployments[idx]["status"] = "running"
            deployments[idx]["started_at"] = datetime.now().isoformat()
            deployments[idx]["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment started"})
            save_json_file(DEPLOYMENTS_FILE, deployments)
            
            time.sleep(1)
            deployments[idx]["logs"].append({"time": datetime.now().isoformat(), "message": "Pulling code..."})
            save_json_file(DEPLOYMENTS_FILE, deployments)
            time.sleep(1)
            deployments[idx]["logs"].append({"time": datetime.now().isoformat(), "message": "Running tests..."})
            save_json_file(DEPLOYMENTS_FILE, deployments)
            time.sleep(1)
            deployments[idx]["logs"].append({"time": datetime.now().isoformat(), "message": "Deploying to production..."})
            save_json_file(DEPLOYMENTS_FILE, deployments)
            time.sleep(1)
            
            deployments[idx]["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment completed successfully"})
            deployments[idx]["status"] = "completed"
            deployments[idx]["completed_at"] = datetime.now().isoformat()
            save_json_file(DEPLOYMENTS_FILE, deployments)
    
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployments.append(deployment)
    save_json_file(DEPLOYMENTS_FILE, deployments)
    
    thread = threading.Thread(target=execute_deployment)
    thread.start()
    
    return jsonify({"deployment": deployment, "message": "Deployment created successfully"}, 201)

@app.route("/api/ops/deployments/<deployment_id>/cancel", methods=["POST"])
def cancel_deployment(deployment_id: str):
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    deployment = next((d for d in deployments if d["id"] == deployment_id), None)
    
    if not deployment:
        return jsonify({"error": "Deployment not found"}), 404
    
    if deployment["status"] not in ["pending", "running"]:
        return jsonify({"error": "Cannot cancel deployment in current state"}), 400
    
    deployment["status"] = "cancelled"
    deployment["completed_at"] = datetime.now().isoformat()
    deployment["logs"].append({"time": datetime.now().isoformat(), "message": "Deployment cancelled by user"})
    
    deployments = load_json_file(DEPLOYMENTS_FILE, [])
    idx = next((i for i, d in enumerate(deployments) if d["id"] == deployment_id), None)
    if idx is not None:
        deployments[idx] = deployment
        save_json_file(DEPLOYMENTS_FILE, deployments)
    
    return jsonify({"deployment": deployment, "message": "Deployment cancelled"})

# ========== 6. 系统信息监控 ==========
@app.route("/api/ops/system", methods=["GET"])
def get_system_info():
    return jsonify({
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "uptime": datetime.now().isoformat()
        },
        "timestamp": datetime.now().isoformat()
    })

# ========== 兼容和文档API ==========
@app.route("/api/items", methods=["GET"])
def get_items():
    return jsonify({"items": [], "message": "Deprecated. Use /api/ops/* endpoints instead."})

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": len(SERVICES)
    })

@app.route("/api", methods=["GET"])
def api_docs():
    return jsonify({
        "name": "DevOps Tools API",
        "version": "2.0.0",
        "description": "运维工具集合 API - 服务监控、配置管理、日志查询、告警管理、部署调度",
        "endpoints": {
            "services": {
                "GET /api/ops/services": "获取所有服务状态",
                "GET /api/ops/services/<name>": "获取单个服务状态",
                "POST /api/ops/services/check": "手动触发检查"
            },
            "config": {
                "GET /api/ops/config": "获取配置",
                "PUT /api/ops/config": "更新配置",
                "GET /api/ops/config/<key>": "获取单个配置项"
            },
            "logs": {
                "GET /api/ops/logs": "查询日志 (params: level, service, limit)",
                "POST /api/ops/logs": "添加日志"
            },
            "alerts": {
                "GET /api/ops/alerts": "获取告警规则列表",
                "GET /api/ops/alerts/<id>": "获取单个告警",
                "POST /api/ops/alerts": "创建告警规则",
                "PUT /api/ops/alerts/<id>": "更新告警规则",
                "DELETE /api/ops/alerts/<id>": "删除告警规则"
            },
            "deployments": {
                "GET /api/ops/deployments": "获取部署任务列表",
                "GET /api/ops/deployments/<id>": "获取单个任务",
                "POST /api/ops/deployments": "创建部署任务",
                "POST /api

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

