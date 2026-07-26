"""
Industrial Multi-Agent Ecosystem — Prometheus Metrics.

Centralized metrics definitions and helper utilities for monitoring agent performance,
pipeline latency, anomaly counts, and LLM fallback events.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from prometheus_client import Counter, Gauge, Histogram, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# ── Metrics Definitions ─────────────────────────────────────────

PIPELINE_EXECUTIONS = Counter(
    "industrial_pipeline_executions_total",
    "Total number of pipeline execution attempts",
    ["status"],
)

PIPELINE_DURATION = Histogram(
    "industrial_pipeline_duration_seconds",
    "Time taken to execute full industrial multi-agent pipeline",
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

ANOMALIES_DETECTED = Counter(
    "industrial_anomalies_detected_total",
    "Total number of statistical industrial anomalies detected",
    ["sector", "severity"],
)

AGENT_EXECUTION_DURATION = Histogram(
    "industrial_agent_execution_duration_seconds",
    "Execution duration per individual agent",
    ["agent"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)

LLM_FALLBACK_COUNT = Counter(
    "industrial_llm_fallback_total",
    "Total count of fallback activations when local LLM is unreachable",
    ["reason"],
)

AGENT_STATUS = Gauge(
    "industrial_agent_status",
    "Operational state of each agent (1 = healthy, 0 = degraded/error)",
    ["agent"],
)

# Initialize agent status gauges to 1 (healthy)
for agent_name in ("IngestionAgent", "AnalysisAgent", "ReportAgent", "RAGSpecialist"):
    AGENT_STATUS.labels(agent=agent_name).set(1.0)


def generate_prometheus_metrics() -> tuple[bytes, str]:
    """Generate Prometheus metric payload and content type header."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
