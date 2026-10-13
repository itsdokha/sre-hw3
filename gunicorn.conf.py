import os

from app.logs import GUNICORN_LOGCONFIG


bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
# Access-лог пишет само приложение (app/__init__.py) в JSON, поэтому у gunicorn он выключен.
accesslog = None
logconfig_dict = GUNICORN_LOGCONFIG
