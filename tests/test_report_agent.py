"""
Unit tests for Agente 3 (ReportAgent).
"""

from __future__ import annotations

import pytest
from agents.analysis_agent import AnalysisSummary, AnomalyDetail
from agents.report_agent import ReportAgent, ReportSummary


def test_report_agent_fallback_generation():
    """Test ReportAgent fallback report synthesis when Ollama is unreachable."""
    mock_anomaly = AnomalyDetail(
        uf="MG",
        setor="Extrativa Mineral",
        mes_ano="2024-09",
        metric_name="massa_salarial",
        observed_value=7100000.0,
        baseline_mean=12500000.0,
        z_score=-3.1,
        percentage_change=-43.2,
        severity="CRITICAL",
        description="Anomalia estatística em Extrativa Mineral (MG): queda de 43.2%",
    )

    mock_analysis = AnalysisSummary(
        total_records_analyzed=100,
        anomalies_found_count=1,
        anomalies=[mock_anomaly],
        critical_count=1,
        execution_time_ms=15.0,
    )

    # Force run ReportAgent (will use fallback if Ollama container isn't running)
    summary = ReportAgent.run(analysis_summary=mock_analysis, rag_context="Diretriz de mineração em MG.")

    assert isinstance(summary, ReportSummary)
    assert summary.anomalies_addressed_count == 1
    assert summary.llm_provider_used in ("ollama", "fallback_rule_engine")
    assert len(summary.recommendations) > 0
    assert "Extrativa Mineral" in summary.executive_summary
    assert summary.execution_time_ms >= 0.0
