import logging
from pathlib import Path

from . import connection


logger = logging.getLogger(__name__)


def main():
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with connection() as db:
        db.execute(schema)
    logger.info("Database schema is ready")


if __name__ == "__main__":
    main()
