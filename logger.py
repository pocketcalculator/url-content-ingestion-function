"""
Structured logging for the scraper function.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """Structured logging handler for Azure Functions."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
    
    def _log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None):
        """Log with structured context."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
        }
        if context:
            log_data.update(context)
        
        if level == "ERROR":
            self.logger.error(json.dumps(log_data))
        elif level == "WARNING":
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log("INFO", message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log("WARNING", message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log("ERROR", message, context)
