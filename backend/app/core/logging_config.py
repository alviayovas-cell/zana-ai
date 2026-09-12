import logging
import sys
from app.core.config import settings


def setup_logging():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet down third party loggers if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("zana")
