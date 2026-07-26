"""
End-to-End Integration test for Industrial Multi-Agent Pipeline.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from agents.ingestion_agent import IngestionAgent
from agents.analysis_agent import AnalysisAgent
from agents.report_agent import ReportAgent
from core.tools import retrieve_documents


def test_end_to_end_industrial_pipeline_integration():
    """Validate full end-to-end execution of Agente 1 -> Agente 2 -> Agente 3."""
    csv_path = "data/sample/caged_industrial.csv"
    if not Path(csv_path).exists():
        pytest.skip("Sample dataset not present")

    # Step 1: Agente 1 (Ingestão)
    ingestion_res = IngestionAgent.run(file_path=csv_path)
    assert ingestion_res.total_records > 0

    # Step 2: Agente 2 (Análise Estatística)
    analysis_res = AnalysisAgent.run(ingestion_data=ingestion_res, z_threshold=2.0)
    assert analysis_res.total_records_analyzed == ingestion_res.total_records
    assert len(analysis_res.anomalies) > 0

    # Step 3: RAG Retrieval Context
    rag_ctx = retrieve_documents("anomalias massa salarial extrativa mineral")
    assert len(rag_ctx) > 0

    # Step 4: Agente 3 (Relatório)
    report_res = ReportAgent.run(analysis_summary=analysis_res, rag_context=rag_ctx)
    assert report_res.anomalies_addressed_count == analysis_res.anomalies_found_count
    assert len(report_res.executive_summary) > 50
    assert len(report_res.recommendations) > 0
