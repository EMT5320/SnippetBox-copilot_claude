"""Middleware for logging, tracing, and rate limiting."""
import time
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils import generate_trace_id, set_trace_id, get_trace_id
from src.config import settings


# Configure structured logging
class StructuredLogger:
    """Structured JSON logger."""
    
    def __init__(self):
        self.logger = logging.getLogger("snippetbox")
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        handler = logging.StreamHandler()
        if settings.LOG_FORMAT.lower() == "json":
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        self.logger.addHandler(handler)
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message."""
        extra = {
            "trace_id": get_trace_id(),
            **kwargs
        }
        getattr(self.logger, level.lower())(message, extra=extra)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "trace_id": getattr(record, 'trace_id', ''),
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'trace_id']:
                log_data[key] = value
        
        return json.dumps(log_data)


logger = StructuredLogger()


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace_id to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = generate_trace_id()
        set_trace_id(trace_id)
        
        # Log request
        start_time = time.time()
        logger.log("info", "Request started", 
                  method=request.method, 
                  path=request.url.path,
                  client_ip=request.client.host if request.client else None)
        
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.log("info", "Request completed",
                  method=request.method,
                  path=request.url.path,
                  status_code=response.status_code,
                  duration_ms=round(duration * 1000, 2))
        
        response.headers["X-Trace-ID"] = trace_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for write operations."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.write_methods = {"POST", "PATCH", "PUT", "DELETE"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Only rate limit write operations
        if request.method not in self.write_methods:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = datetime.utcnow()
        
        # Clean old requests (older than 1 minute)
        cutoff_time = current_time - timedelta(minutes=1)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff_time
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.log("warning", "Rate limit exceeded",
                      client_ip=client_ip,
                      method=request.method,
                      path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} write operations per minute.",
                    "trace_id": get_trace_id()
                }
            )
        
        # Record this request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)
