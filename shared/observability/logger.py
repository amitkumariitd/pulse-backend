import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def _log(
        self,
        level: str,
        message: str,
        trace_id: Optional[str] = None,
        trace_source: Optional[str] = None,
        request_id: Optional[str] = None,
        request_source: Optional[str] = None,
        order_id: Optional[str] = None,
        data: Optional[dict] = None
    ):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": level,
            "service": self.service_name,
            "message": message
        }
        
        if trace_id:
            log_entry["trace_id"] = trace_id
        if trace_source:
            log_entry["trace_source"] = trace_source
        if request_id:
            log_entry["request_id"] = request_id
        if request_source:
            log_entry["request_source"] = request_source
        if order_id:
            log_entry["order_id"] = order_id
        if data:
            log_entry["data"] = data
        
        log_line = json.dumps(log_entry)
        
        log_method = getattr(self.logger, level.lower())
        log_method(log_line)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)


def get_logger(service_name: str) -> StructuredLogger:
    return StructuredLogger(service_name)

