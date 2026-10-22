"""Content-free JSON formatting for application and server diagnostics.

Call sites must supply only fixed event descriptions, opaque record IDs, enum
codes, and exception class names. Exception messages and tracebacks can contain
provider responses or credentials and are deliberately excluded from stdout.
"""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["error_type"] = record.exc_info[0].__name__
        return json.dumps(entry)
