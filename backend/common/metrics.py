"""Prometheus metrics for LeoBrain"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import CollectorRegistry, generate_latest

# Create a custom registry
registry = CollectorRegistry()

# Crawler metrics
crawler_requests_total = Counter(
    'crawler_requests_total',
    'Total number of crawler requests',
    ['site_name', 'status'],
    registry=registry
)

crawler_request_duration = Histogram(
    'crawler_request_duration_seconds',
    'Crawler request duration in seconds',
    ['site_name'],
    registry=registry
)

crawler_items_collected = Counter(
    'crawler_items_collected_total',
    'Total number of items collected',
    ['site_name'],
    registry=registry
)

crawler_errors_total = Counter(
    'crawler_errors_total',
    'Total number of crawler errors',
    ['site_name', 'error_type'],
    registry=registry
)

# Task/Job metrics
task_runs_total = Counter(
    'task_runs_total',
    'Total number of task runs',
    ['task_name', 'status'],
    registry=registry
)

task_duration = Histogram(
    'task_duration_seconds',
    'Task execution duration in seconds',
    ['task_name'],
    registry=registry
)

active_tasks = Gauge(
    'active_tasks',
    'Number of currently active tasks',
    ['task_name'],
    registry=registry
)

# System info
system_info = Info(
    'system',
    'System information',
    registry=registry
)

system_info.info({'version': '1.0.0', 'component': 'leobrain-backend'})


def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest(registry)

