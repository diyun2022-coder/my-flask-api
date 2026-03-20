from flask import Flask, jsonify, request

app = Flask(__name__)

# 模拟数据存储
items = [
    {"id": 1, "name": "Item 1", "description": "First item"},
    {"id": 2, "name": "Item 2", "description": "Second item"},
]


@app.route("/api/items", methods=["GET"])
def get_items():
    """获取所有项目"""
    return jsonify({"items": items})


@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    """获取单个项目"""
    item = next((i for i in items if i["id"] == item_id), None)
    if item:
        return jsonify({"item": item})
    return jsonify({"error": "Item not found"}), 404


@app.route("/api/items", methods=["POST"])
def create_item():
    """创建新项目"""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Name is required"}), 400

    new_id = max(i["id"] for i in items) + 1 if items else 1
    new_item = {
        "id": new_id,
        "name": data["name"],
        "description": data.get("description", ""),
    }
    items.append(new_item)
    return jsonify({"item": new_item}), 201


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    """更新项目"""
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    item["name"] = data.get("name", item["name"])
    item["description"] = data.get("description", item["description"])
    return jsonify({"item": item})


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    """删除项目"""
    global items
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    items = [i for i in items if i["id"] != item_id]
    return jsonify({"message": "Item deleted"})


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
