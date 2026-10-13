import logging
import os
import time
import uuid

import psycopg
from flask import Flask, g, jsonify, request
from psycopg.rows import dict_row

from .logs import setup_logging


setup_logging()
app = Flask(__name__, static_folder="static", static_url_path="")
logger = logging.getLogger(__name__)
access_logger = logging.getLogger("tasks.access")


def connection():
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )


def task_json(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": row["completed"],
        "created_at": row["created_at"].isoformat(),
    }


def input_data(require_completed=False):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, "Ожидается объект JSON"
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
        return None, "Название должно содержать от 1 до 200 символов"
    title = title.strip()
    completed = data.get("completed", False)
    if require_completed and "completed" not in data:
        return None, "Укажите completed"
    if not isinstance(completed, bool):
        return None, "completed должен быть логическим значением"
    return {"title": title, "completed": completed}, None


@app.before_request
def start_timer():
    g.started = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex


@app.after_request
def log_request(response):
    duration_ms = round((time.perf_counter() - g.started) * 1000, 2)
    status = response.status_code
    level = logging.ERROR if status >= 500 else logging.WARNING if status >= 400 else logging.INFO
    access_logger.log(
        level,
        "%s %s %s",
        request.method,
        request.path,
        status,
        extra={
            "request_id": g.request_id,
            "http.method": request.method,
            "http.route": request.url_rule.rule if request.url_rule else "unmatched",
            "url.path": request.path,
            "http.status_code": status,
            "duration_ms": duration_ms,
            "client.address": request.headers.get("X-Forwarded-For", request.remote_addr),
            "user_agent": request.user_agent.string,
        },
    )
    response.headers["X-Request-ID"] = g.request_id
    return response


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/tasks")
def list_tasks():
    with connection() as db:
        rows = db.execute(
            "SELECT id, title, completed, created_at FROM tasks ORDER BY id DESC"
        ).fetchall()
    return jsonify([task_json(row) for row in rows])


@app.post("/api/tasks")
def create_task():
    data, error = input_data()
    if error:
        logger.warning("Task validation failed", extra={"reason": error, "request_id": g.request_id})
        return jsonify(error=error), 400
    with connection() as db:
        row = db.execute(
            "INSERT INTO tasks (title, completed) VALUES (%s, %s) "
            "RETURNING id, title, completed, created_at",
            (data["title"], data["completed"]),
        ).fetchone()
    logger.info("Task created", extra={"task.id": row["id"], "request_id": g.request_id})
    return jsonify(task_json(row)), 201


@app.get("/api/tasks/<int:task_id>")
def get_task(task_id):
    with connection() as db:
        row = db.execute(
            "SELECT id, title, completed, created_at FROM tasks WHERE id = %s",
            (task_id,),
        ).fetchone()
    if row is None:
        return jsonify(error="Задача не найдена"), 404
    return jsonify(task_json(row))


@app.put("/api/tasks/<int:task_id>")
def update_task(task_id):
    data, error = input_data(require_completed=True)
    if error:
        logger.warning("Task validation failed", extra={"reason": error, "request_id": g.request_id})
        return jsonify(error=error), 400
    with connection() as db:
        row = db.execute(
            "UPDATE tasks SET title = %s, completed = %s WHERE id = %s "
            "RETURNING id, title, completed, created_at",
            (data["title"], data["completed"], task_id),
        ).fetchone()
    if row is None:
        return jsonify(error="Задача не найдена"), 404
    logger.info(
        "Task updated",
        extra={"task.id": task_id, "task.completed": data["completed"], "request_id": g.request_id},
    )
    return jsonify(task_json(row))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    with connection() as db:
        row = db.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,)).fetchone()
    if row is None:
        return jsonify(error="Задача не найдена"), 404
    logger.info("Task deleted", extra={"task.id": task_id, "request_id": g.request_id})
    return "", 204


@app.errorhandler(psycopg.OperationalError)
def database_unavailable(error):
    logger.exception("Database unavailable", extra={"request_id": g.get("request_id")})
    return jsonify(error="База данных недоступна"), 503
