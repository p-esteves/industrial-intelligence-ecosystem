"""
Unit tests for Agente 1 (IngestionAgent).
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from agents.ingestion_agent import IngestionAgent, IngestionSummary


def test_ingestion_agent_sample_csv():
    """Test ingestion agent reading CSV sample dataset."""
    sample_path = "data/sample/caged_industrial.csv"
    if not Path(sample_path).exists():
        pytest.skip("Sample CSV dataset not generated")

    summary = IngestionAgent.run(file_path=sample_path)

    assert isinstance(summary, IngestionSummary)
    assert summary.total_records > 0
    assert summary.format_type == "csv"
    assert "SP" in summary.ufs_covered
    assert "Indústria de Transformação" in summary.sectors_covered
    assert summary.execution_time_ms > 0.0


def test_ingestion_agent_sample_parquet():
    """Test ingestion agent reading Parquet sample dataset."""
    sample_path = "data/sample/caged_industrial.parquet"
    if not Path(sample_path).exists():
        pytest.skip("Sample Parquet dataset not generated")

    summary = IngestionAgent.run(file_path=sample_path)

    assert isinstance(summary, IngestionSummary)
    assert summary.total_records > 0
    assert summary.format_type == "parquet"
    assert len(summary.records) == summary.total_records


def test_ingestion_agent_nonexistent_file():
    """Test ingestion agent raising FileNotFoundError on invalid path."""
    with pytest.raises(FileNotFoundError):
        IngestionAgent.run(file_path="nonexistent_directory/file.csv")
