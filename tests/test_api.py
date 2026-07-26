"""
Unit tests for FastAPI REST Endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from api.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test /health endpoint returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_provider" in data


def test_status_endpoint():
    """Test /status endpoint returns agent status breakdown."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "healthy"
    assert len(data["agents"]) >= 3


def test_metrics_endpoint():
    """Test /metrics endpoint returns Prometheus formatted metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "industrial_pipeline_executions_total" in response.text
    assert "industrial_agent_execution_duration_seconds" in response.text


def test_pipeline_endpoint():
    """Test /pipeline endpoint triggers full agent pipeline."""
    payload = {
        "file_path": "data/sample/caged_industrial.csv",
        "z_threshold": 2.0,
        "include_rag": True,
    }
    response = client.post("/pipeline", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "ingestion" in data
    assert "analysis" in data
    assert "report" in data
    assert data["total_duration_ms"] > 0.0
