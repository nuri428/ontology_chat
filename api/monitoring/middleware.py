"""Monitoring middleware for FastAPI."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import metrics_collector


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()

        # Get request info
        method = request.method
        path_template = request.url.path

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        metrics_collector.record_http_request(
            method=method,
            endpoint=path_template,
            status_code=response.status_code,
            duration=duration
        )

        return response


class HealthMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor service health and degradation."""

    def __init__(self, app, health_checker=None):
        super().__init__(app)
        self.health_checker = health_checker
        self.request_count = 0
        self.error_count = 0
        self.last_check = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request health and update degradation level."""
        self.request_count += 1

        try:
            response = await call_next(request)

            # Track errors
            if response.status_code >= 500:
                self.error_count += 1

            # Periodic health check
            current_time = time.time()
            if current_time - self.last_check > 60:  # Check every minute
                await self._update_health_metrics()
                self.last_check = current_time

            return response

        except Exception as e:
            self.error_count += 1
            await self._update_health_metrics()
            raise

    async def _update_health_metrics(self):
        """Update health and degradation metrics."""
        if self.request_count == 0:
            error_rate = 0
        else:
            error_rate = self.error_count / self.request_count

        # Determine health status
        is_healthy = error_rate < 0.1  # Less than 10% error rate

        # Determine degradation level
        degradation_level = 0  # Full service
        if error_rate > 0.05:
            degradation_level = 1  # Degraded
        if error_rate > 0.1:
            degradation_level = 2  # Minimal
        if error_rate > 0.2:
            degradation_level = 3  # Emergency

        # Update metrics
        metrics_collector.update_health_status(is_healthy, degradation_level)

        # Reset counters periodically
        if self.request_count > 1000:
            self.request_count = 0
            self.error_count = 0