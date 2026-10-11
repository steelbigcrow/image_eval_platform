"""图片比对平台 —— Flask 应用入口。

后端只提供两个 JSON 接口，页面本身由 Jinja2 模板渲染，
前端为原生 HTML/CSS/JS，不需要任何构建步骤。

启动：
    python app.py
然后访问 http://127.0.0.1:5000
"""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

import comparators  # noqa: F401  导入即完成内置算法注册
import config
from comparators.base import ComparisonResult
from comparators.registry import AlgorithmNotFoundError, get, list_all
from imaging.processor import InvalidImageError, load_image


def _score_level(score: float) -> str:
    """把分数映射成粗粒度结论，仅用于界面提示。"""
    if score >= 90:
        return "高度相似"
    if score >= 75:
        return "较为相似"
    if score >= 50:
        return "差异明显"
    return "差异很大"


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(config.TEMPLATES_DIR),
        static_folder=str(config.STATIC_DIR),
    )
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH_MB * 1024 * 1024
    app.json.ensure_ascii = False

    @app.after_request
    def ensure_json_charset(response):
        """显式声明 JSON 响应使用 UTF-8，避免个别客户端按本地编码误解码。"""
        content_type = response.headers.get("Content-Type", "")
        if response.mimetype == "application/json" and "charset" not in content_type:
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response

    @app.get("/")
    def index():
        """渲染单页前端。"""
        algorithms = list_all()
        default = (
            config.DEFAULT_ALGORITHM
            if any(item["key"] == config.DEFAULT_ALGORITHM for item in algorithms)
            else (algorithms[0]["key"] if algorithms else "")
        )
        return render_template(
            "index.html",
            algorithms=algorithms,
            default_algorithm=default,
            max_upload_mb=config.MAX_CONTENT_LENGTH_MB,
        )

    @app.get("/api/algorithms")
    def api_algorithms():
        """返回已注册的算法列表，供前端下拉框使用。"""
        return jsonify({"ok": True, "data": {"algorithms": list_all()}})

    @app.post("/api/compare")
    def api_compare():
        """比对原图与目标图，返回相似度结果。"""
        source_file = request.files.get("source")
        target_file = request.files.get("target")
        requested_algorithm = request.form.get("algorithm") or config.DEFAULT_ALGORITHM
        algorithm_key = requested_algorithm.strip()

        if source_file is None or not source_file.filename:
            return jsonify({"ok": False, "message": "请上传原图片"}), 400
        if target_file is None or not target_file.filename:
            return jsonify({"ok": False, "message": "请上传目标图片"}), 400

        try:
            comparator = get(algorithm_key)
        except AlgorithmNotFoundError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        try:
            source = load_image(source_file.stream, source_file.filename)
            target = load_image(target_file.stream, target_file.filename)
        except InvalidImageError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

        result: ComparisonResult = comparator.compare(source.image, target.image)

        return jsonify(
            {
                "ok": True,
                "data": {
                    "algorithm": {
                        "key": comparator.key,
                        "label": comparator.label,
                        "description": comparator.description,
                    },
                    "score": round(result.score, 2),
                    "level": _score_level(result.score),
                    "metrics": result.metrics,
                    "message": result.message,
                    "source": source.to_dict(),
                    "target": target.to_dict(),
                    "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
                },
            }
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        limit = config.MAX_CONTENT_LENGTH_MB
        return jsonify({"ok": False, "message": f"上传内容超过 {limit} MB 限制"}), 413

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "message": "接口不存在"}), 404
        return error

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        app.logger.exception("未处理的异常")
        return jsonify({"ok": False, "message": f"服务内部错误: {error}"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=config.USE_RELOADER,
    )
