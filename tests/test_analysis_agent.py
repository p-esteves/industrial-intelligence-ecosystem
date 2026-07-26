"""
Unit tests for Agente 2 (AnalysisAgent).
"""

from __future__ import annotations

import pytest
from agents.analysis_agent import AnalysisAgent, AnalysisSummary, AnomalyDetail


def test_analysis_agent_anomaly_detection():
    """Test analysis agent detects injected anomalies correctly."""
    mock_records = [
        # Normal records for SP Indústria de Transformação
        {"uf": "SP", "setor": "Indústria de Transformação", "mes_ano": "2024-01", "massa_salarial": 100000.0, "saldo": 500},
        {"uf": "SP", "setor": "Indústria de Transformação", "mes_ano": "2024-02", "massa_salarial": 102000.0, "saldo": 510},
        {"uf": "SP", "setor": "Indústria de Transformação", "mes_ano": "2024-03", "massa_salarial": 101000.0, "saldo": 490},
        {"uf": "SP", "setor": "Indústria de Transformação", "mes_ano": "2024-04", "massa_salarial": 99000.0, "saldo": 505},
        # Sharp injected drop anomaly
        {"uf": "SP", "setor": "Indústria de Transformação", "mes_ano": "2024-05", "massa_salarial": 20000.0, "saldo": -2000},
    ]

    summary = AnalysisAgent.run(ingestion_data=mock_records, z_threshold=2.0)

    assert isinstance(summary, AnalysisSummary)
    assert summary.total_records_analyzed == 5
    assert summary.anomalies_found_count > 0
    assert summary.critical_count > 0

    anomaly = summary.anomalies[0]
    assert isinstance(anomaly, AnomalyDetail)
    assert anomaly.uf == "SP"
    assert anomaly.setor == "Indústria de Transformação"
    assert anomaly.mes_ano == "2024-05"
    assert anomaly.z_score <= -2.0


def test_analysis_agent_empty_records():
    """Test analysis agent gracefully handles empty records list."""
    summary = AnalysisAgent.run(ingestion_data=[], z_threshold=2.0)
    assert summary.total_records_analyzed == 0
    assert summary.anomalies_found_count == 0
    assert len(summary.anomalies) == 0
