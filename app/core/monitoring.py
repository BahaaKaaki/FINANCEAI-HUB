import psutil
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """A single metric measurement."""

    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """System alert information."""

    id: str
    severity: AlertSeverity
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class HealthCheck:
    """Health check result."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: float
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Performance monitoring system for tracking metrics and generating alerts.
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize performance monitor.

        Args:
            max_history: Maximum number of metric values to keep in memory
        """
        self.max_history = max_history
        self._metrics: Dict[str, Deque[MetricValue]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._alerts: Dict[str, Alert] = {}
        self._alert_rules: Dict[str, Dict[str, Any]] = {}
        self._health_checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._lock = threading.Lock()

        # System metrics collection
        self._system_metrics_enabled = True
        self._system_metrics_thread = None
        self._start_system_monitoring()

        logger.info("Performance monitor initialized with max_history=%d", max_history)

    def record_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a counter metric (monotonically increasing).

        Args:
            name: Metric name
            value: Value to add to counter
            labels: Optional labels for the metric
        """
        with self._lock:
            self._counters[name] += value
            self._record_metric(name, self._counters[name], MetricType.COUNTER, labels)

    def record_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a gauge metric (can go up or down).

        Args:
            name: Metric name
            value: Current value
            labels: Optional labels for the metric
        """
        with self._lock:
            self._gauges[name] = value
            self._record_metric(name, value, MetricType.GAUGE, labels)

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a histogram metric (for measuring distributions).

        Args:
            name: Metric name
            value: Measured value
            labels: Optional labels for the metric
        """
        with self._lock:
            self._record_metric(name, value, MetricType.HISTOGRAM, labels)

    @contextmanager
    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        Context manager for timing operations.

        Args:
            name: Metric name
            labels: Optional labels for the metric
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                self._record_metric(name, duration, MetricType.TIMER, labels)

    def _record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]],
    ) -> None:
        """Internal method to record a metric value."""
        metric_value = MetricValue(
            timestamp=time.time(), value=value, labels=labels or {}
        )

        self._metrics[name].append(metric_value)

        # Check alert rules
        self._check_alert_rules(name, value)

        logger.debug(
            "Recorded %s metric '%s': %.3f %s",
            metric_type.value,
            name,
            value,
            labels or "",
        )

    def get_metric_values(
        self, name: str, limit: Optional[int] = None
    ) -> List[MetricValue]:
        """
        Get recent values for a metric.

        Args:
            name: Metric name
            limit: Maximum number of values to return

        Returns:
            List of metric values
        """
        with self._lock:
            values = list(self._metrics[name])
            if limit:
                values = values[-limit:]
            return values

    def get_metric_summary(self, name: str) -> Dict[str, Any]:
        """
        Get summary statistics for a metric.

        Args:
            name: Metric name

        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            values = [mv.value for mv in self._metrics[name]]

            if not values:
                return {"count": 0}

            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1] if values else None,
                "latest_timestamp": (
                    self._metrics[name][-1].timestamp if self._metrics[name] else None
                ),
            }

    def add_alert_rule(
        self,
        metric_name: str,
        threshold: float,
        condition: str = "greater_than",
        severity: AlertSeverity = AlertSeverity.WARNING,
        message_template: Optional[str] = None,
    ) -> None:
        """
        Add an alert rule for a metric.

        Args:
            metric_name: Name of metric to monitor
            threshold: Threshold value for alert
            condition: Condition type ("greater_than", "less_than", "equals")
            severity: Alert severity level
            message_template: Optional custom message template
        """
        rule_id = f"{metric_name}_{condition}_{threshold}"

        self._alert_rules[rule_id] = {
            "metric_name": metric_name,
            "threshold": threshold,
            "condition": condition,
            "severity": severity,
            "message_template": message_template
            or f"{metric_name} {condition} {threshold}",
        }

        logger.info(
            "Added alert rule: %s %s %.3f (severity: %s)",
            metric_name,
            condition,
            threshold,
            severity.value,
        )

    def _check_alert_rules(self, metric_name: str, value: float) -> None:
        """Check if any alert rules are triggered by the metric value."""
        for rule_id, rule in self._alert_rules.items():
            if rule["metric_name"] != metric_name:
                continue

            triggered = False
            condition = rule["condition"]
            threshold = rule["threshold"]

            if condition == "greater_than" and value > threshold:
                triggered = True
            elif condition == "less_than" and value < threshold:
                triggered = True
            elif condition == "equals" and abs(value - threshold) < 0.001:
                triggered = True

            if triggered:
                self._trigger_alert(rule_id, rule, value)
            else:
                self._resolve_alert(rule_id)

    def _trigger_alert(
        self, rule_id: str, rule: Dict[str, Any], current_value: float
    ) -> None:
        """Trigger an alert based on a rule."""
        # Check if alert is already active
        if rule_id in self._alerts and not self._alerts[rule_id].resolved:
            return

        alert = Alert(
            id=rule_id,
            severity=rule["severity"],
            message=rule["message_template"].format(
                metric_name=rule["metric_name"],
                current_value=current_value,
                threshold=rule["threshold"],
            ),
            metric_name=rule["metric_name"],
            current_value=current_value,
            threshold=rule["threshold"],
            timestamp=time.time(),
        )

        self._alerts[rule_id] = alert

        logger.log(
            self._severity_to_log_level(alert.severity),
            "ALERT TRIGGERED [%s]: %s (current: %.3f, threshold: %.3f)",
            alert.severity.value.upper(),
            alert.message,
            current_value,
            rule["threshold"],
        )

    def _resolve_alert(self, rule_id: str) -> None:
        """Resolve an active alert."""
        if rule_id in self._alerts and not self._alerts[rule_id].resolved:
            alert = self._alerts[rule_id]
            alert.resolved = True
            alert.resolved_at = time.time()

            logger.info(
                "ALERT RESOLVED [%s]: %s", alert.severity.value.upper(), alert.message
            )

    def _severity_to_log_level(self, severity: AlertSeverity) -> int:
        """Convert alert severity to logging level."""
        mapping = {
            AlertSeverity.INFO: 20,  # INFO
            AlertSeverity.WARNING: 30,  # WARNING
            AlertSeverity.ERROR: 40,  # ERROR
            AlertSeverity.CRITICAL: 50,  # CRITICAL
        }
        return mapping.get(severity, 30)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts."""
        with self._lock:
            return [alert for alert in self._alerts.values() if not alert.resolved]

    def get_all_alerts(self, limit: Optional[int] = None) -> List[Alert]:
        """Get all alerts (active and resolved)."""
        with self._lock:
            alerts = list(self._alerts.values())
            alerts.sort(key=lambda a: a.timestamp, reverse=True)
            if limit:
                alerts = alerts[:limit]
            return alerts

    def register_health_check(
        self, name: str, check_func: Callable[[], HealthCheck]
    ) -> None:
        """
        Register a health check function.

        Args:
            name: Health check name
            check_func: Function that returns HealthCheck result
        """
        self._health_checks[name] = check_func
        logger.info("Registered health check: %s", name)

    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """
        Run all registered health checks.

        Returns:
            Dictionary of health check results
        """
        results = {}

        for name, check_func in self._health_checks.items():
            start_time = time.time()
            try:
                result = check_func()
                result.duration_ms = (time.time() - start_time) * 1000
                results[name] = result

                logger.debug(
                    "Health check '%s': %s (%.1fms)",
                    name,
                    result.status,
                    result.duration_ms,
                )

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                results[name] = HealthCheck(
                    name=name,
                    status="unhealthy",
                    message=f"Health check failed: {str(e)}",
                    timestamp=time.time(),
                    duration_ms=duration_ms,
                )

                logger.error(
                    "Health check '%s' failed (%.1fms): %s", name, duration_ms, str(e)
                )

        return results

    def _start_system_monitoring(self) -> None:
        """Start background thread for system metrics collection."""
        if not self._system_metrics_enabled:
            return

        def collect_system_metrics():
            # Initialize CPU monitoring (non-blocking first call)
            psutil.cpu_percent()  # First call to establish baseline
            
            while self._system_metrics_enabled:
                try:
                    # CPU usage (non-blocking after first call)
                    cpu_percent = psutil.cpu_percent(interval=None)
                    self.record_gauge("system.cpu.usage_percent", cpu_percent)

                    # Memory usage
                    memory = psutil.virtual_memory()
                    self.record_gauge("system.memory.usage_percent", memory.percent)
                    self.record_gauge(
                        "system.memory.available_mb", memory.available / 1024 / 1024
                    )

                    # Disk usage - temporarily disabled due to performance issues
                    # disk = psutil.disk_usage("/")
                    # self.record_gauge("system.disk.usage_percent", disk.percent)
                    # self.record_gauge(
                    #     "system.disk.free_gb", disk.free / 1024 / 1024 / 1024
                    # )

                    # Process info
                    process = psutil.Process()
                    self.record_gauge(
                        "process.memory.rss_mb", process.memory_info().rss / 1024 / 1024
                    )
                    self.record_gauge("process.cpu.percent", process.cpu_percent())

                except Exception as e:
                    logger.warning("Failed to collect system metrics: %s", str(e))

                time.sleep(30)  # Collect every 30 seconds

        self._system_metrics_thread = threading.Thread(
            target=collect_system_metrics, daemon=True, name="SystemMetricsCollector"
        )
        self._system_metrics_thread.start()
        logger.info("Started system metrics collection thread")

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status and metrics summary.

        Returns:
            Dictionary with system status information
        """
        with self._lock:
            active_alerts = self.get_active_alerts()

            # Determine overall health
            if any(alert.severity == AlertSeverity.CRITICAL for alert in active_alerts):
                overall_status = "critical"
            elif any(alert.severity == AlertSeverity.ERROR for alert in active_alerts):
                overall_status = "error"
            elif any(
                alert.severity == AlertSeverity.WARNING for alert in active_alerts
            ):
                overall_status = "warning"
            else:
                overall_status = "healthy"

            return {
                "status": overall_status,
                "timestamp": time.time(),
                "metrics_count": len(self._metrics),
                "active_alerts": len(active_alerts),
                "total_alerts": len(self._alerts),
                "health_checks_registered": len(self._health_checks),
                "alert_rules": len(self._alert_rules),
                "uptime_seconds": (
                    time.time() - self._start_time
                    if hasattr(self, "_start_time")
                    else 0
                ),
            }

    def get_metrics_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all metrics."""
        with self._lock:
            summary = {}
            for metric_name in self._metrics.keys():
                summary[metric_name] = self.get_metric_summary(metric_name)
            return summary

    def shutdown(self) -> None:
        """Shutdown the performance monitor."""
        self._system_metrics_enabled = False
        if self._system_metrics_thread and self._system_metrics_thread.is_alive():
            self._system_metrics_thread.join(timeout=5)

        logger.info("Performance monitor shutdown complete")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _performance_monitor

    with _monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
            _performance_monitor._start_time = time.time()

            # Add default alert rules
            _performance_monitor.add_alert_rule(
                "system.cpu.usage_percent",
                80.0,
                "greater_than",
                AlertSeverity.WARNING,
                "High CPU usage: {current_value:.1f}%",
            )
            _performance_monitor.add_alert_rule(
                "system.memory.usage_percent",
                85.0,
                "greater_than",
                AlertSeverity.WARNING,
                "High memory usage: {current_value:.1f}%",
            )
            # Temporarily disabled - cz disk usage alert was causing API timeouts
            # _performance_monitor.add_alert_rule(
            #     "system.disk.usage_percent",
            #     90.0,
            #     "greater_than",
            #     AlertSeverity.ERROR,
            #     "High disk usage: {current_value:.1f}%",
            # )

        return _performance_monitor


# Convenience functions for common monitoring operations


def record_request_duration(endpoint: str, duration: float, status_code: int) -> None:
    """Record API request duration and count."""
    monitor = get_performance_monitor()
    labels = {"endpoint": endpoint, "status_code": str(status_code)}

    monitor.record_histogram("api.request.duration_seconds", duration, labels)
    monitor.record_counter("api.request.count", 1.0, labels)


def record_database_operation(operation: str, duration: float, success: bool) -> None:
    """Record database operation metrics."""
    monitor = get_performance_monitor()
    labels = {"operation": operation, "success": str(success)}

    monitor.record_histogram("database.operation.duration_seconds", duration, labels)
    monitor.record_counter("database.operation.count", 1.0, labels)


def record_llm_api_call(
    provider: str,
    model: str,
    duration: float,
    success: bool,
    tokens_used: Optional[int] = None,
) -> None:
    """Record LLM API call metrics."""
    monitor = get_performance_monitor()
    labels = {"provider": provider, "model": model, "success": str(success)}

    monitor.record_histogram("llm.api.duration_seconds", duration, labels)
    monitor.record_counter("llm.api.calls", 1.0, labels)

    if tokens_used is not None:
        monitor.record_histogram("llm.api.tokens_used", float(tokens_used), labels)


@contextmanager
def monitor_operation(operation_name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager for monitoring operation duration and success."""
    monitor = get_performance_monitor()
    start_time = time.time()
    success = False

    try:
        yield
        success = True
    finally:
        duration = time.time() - start_time
        final_labels = (labels or {}).copy()
        final_labels["success"] = str(success)

        monitor.record_histogram(
            f"{operation_name}.duration_seconds", duration, final_labels
        )
        monitor.record_counter(f"{operation_name}.count", 1.0, final_labels)
