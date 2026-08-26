import logging
import sys
from contextvars import ContextVar
from app.core.config import settings

# Global ContextVar to track correlation/request IDs across threads and async tasks
correlation_id_var = ContextVar("correlation_id", default="req_system")


class CorrelationIdFilter(logging.Filter):
    """Logging filter to inject correlation ID into every log record."""
    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging():
    """Sets up standard application logging with correlation ID tracing."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Clear default handlers to avoid duplication
    root_logger.handlers = [handler]
    
    # Minimize noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)


logger = logging.getLogger("recoverai")
