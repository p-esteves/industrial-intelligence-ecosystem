from __future__ import annotations

import pytest
import unittest.mock as mock
from events import SQLStructuredOutput, RAGStructuredOutput, ForecastStructuredOutput
from agents.consistency_auditor import ConsistencyAuditorAgent
from agents.forecast_specialist import ForecastSpecialistAgent


@pytest.mark.anyio
async def test_auditor_math_success():
    """Test that ConsistencyAuditorAgent approves mathematical consistency when values match."""
    sql_out = SQLStructuredOutput(
        query="SELECT * FROM emprego_formal",
        records=[
            {"mes_ano": "2024-01", "admissoes": 100, "desligamentos": 80, "saldo": 20, "salario_medio": 3000.0}
        ],
        uf="SP",
        setor="Construção Civil",
        saldo_total=20,
        tendencia="crescimento"
    )
    rag_out = RAGStructuredOutput(
        retrieved_passages=["Construção civil está em alta."],
        setor_mencionado="Construção Civil",
        fator_macroeconomico="Juros estáveis",
        impacto_narrativa="positivo"
    )
    forecast_out = ForecastStructuredOutput(
        setor="Construção Civil",
        horizonte_meses=6,
        cenarios={
            "base": {
                "projecoes": [
                    {"periodo": "2024-02", "massa_salarial_estimada": 31000.0, "empregados_estimados": 100}
                ]
            }
        },
        tendencia_base="crescimento",
        modelo_utilizado="Prophet"
    )
    
    with mock.patch("agents.consistency_auditor.get_llm") as mock_get_llm:
        mock_llm = mock.MagicMock()
        mock_llm.achat = mock.AsyncMock()
        mock_llm.achat.return_value.message.content = "Relatório Mock Aprovado"
        mock_get_llm.return_value = mock_llm
        
        verdict = await ConsistencyAuditorAgent.evaluate("query", sql_out, rag_out, forecast_out)
        assert verdict.approved is True
        assert "Relatório Mock Aprovado" in verdict.report
        assert verdict.report.startswith("#")


@pytest.mark.anyio
async def test_auditor_math_failure():
    """Test that ConsistencyAuditorAgent rejects mathematical inconsistency when values do not match."""
    sql_out = SQLStructuredOutput(
        query="SELECT * FROM emprego_formal",
        records=[
            {"mes_ano": "2024-01", "admissoes": 100, "desligamentos": 80, "saldo": 15, "salario_medio": 3000.0}  # 100 - 80 != 15!
        ],
        uf="SP",
        setor="Construção Civil",
        saldo_total=15,
        tendencia="crescimento"
    )
    rag_out = RAGStructuredOutput(
        retrieved_passages=["Construção civil."],
        setor_mencionado="Construção Civil",
        fator_macroeconomico="Juros",
        impacto_narrativa="positivo"
    )
    forecast_out = ForecastStructuredOutput(
        setor="Construção Civil",
        horizonte_meses=6,
        cenarios={
            "base": {
                "projecoes": [
                    {"periodo": "2024-02", "massa_salarial_estimada": 31000.0, "empregados_estimados": 100}
                ]
            }
        },
        tendencia_base="crescimento",
        modelo_utilizado="Prophet"
    )

    verdict = await ConsistencyAuditorAgent.evaluate("query", sql_out, rag_out, forecast_out)
    assert verdict.approved is False
    assert "Inconsistência matemática" in verdict.feedback


@pytest.mark.anyio
async def test_auditor_sector_mismatch():
    """Test that ConsistencyAuditorAgent rejects when SQL sector does not match Forecast sector."""
    sql_out = SQLStructuredOutput(
        query="SELECT * FROM emprego_formal",
        records=[
            {"mes_ano": "2024-01", "admissoes": 100, "desligamentos": 80, "saldo": 20, "salario_medio": 3000.0}
        ],
        uf="SP",
        setor="Construção Civil",
        saldo_total=20,
        tendencia="crescimento"
    )
    rag_out = RAGStructuredOutput(
        retrieved_passages=["Construção civil."],
        setor_mencionado="Construção Civil",
        fator_macroeconomico="Juros",
        impacto_narrativa="positivo"
    )
    forecast_out = ForecastStructuredOutput(
        setor="Indústria de Transformação",  # Mismatched sector!
        horizonte_meses=6,
        cenarios={
            "base": {
                "projecoes": [
                    {"periodo": "2024-02", "massa_salarial_estimada": 31000.0, "empregados_estimados": 100}
                ]
            }
        },
        tendencia_base="crescimento",
        modelo_utilizado="Prophet"
    )

    verdict = await ConsistencyAuditorAgent.evaluate("query", sql_out, rag_out, forecast_out)
    assert verdict.approved is False
    assert "Divergência de Setor" in verdict.feedback


@pytest.mark.anyio
async def test_auditor_trend_contradiction():
    """Test that ConsistencyAuditorAgent rejects on a logical trend contradiction (historic drop + negative RAG vs growth forecast)."""
    sql_out = SQLStructuredOutput(
        query="SELECT * FROM emprego_formal",
        records=[
            {"mes_ano": "2024-01", "admissoes": 80, "desligamentos": 100, "saldo": -20, "salario_medio": 3000.0}
        ],
        uf="SP",
        setor="Construção Civil",
        saldo_total=-20,
        tendencia="queda"  # Downward historic trend
    )
    rag_out = RAGStructuredOutput(
        retrieved_passages=["Setor em crise."],
        setor_mencionado="Construção Civil",
        fator_macroeconomico="Selic alta",
        impacto_narrativa="negativo"  # Negative RAG narrative
    )
    forecast_out = ForecastStructuredOutput(
        setor="Construção Civil",
        horizonte_meses=6,
        cenarios={
            "base": {
                "projecoes": [
                    {"periodo": "2024-02", "massa_salarial_estimada": 31000.0, "empregados_estimados": 100}
                ]
            }
        },
        tendencia_base="crescimento",  # Contradictory growth forecast!
        modelo_utilizado="Prophet"
    )

    verdict = await ConsistencyAuditorAgent.evaluate("query", sql_out, rag_out, forecast_out)
    assert verdict.approved is False
    assert "Contradição Lógica Detectada" in verdict.feedback


@pytest.mark.anyio
async def test_forecast_revisor_feedback_adjustment():
    """Test that ForecastSpecialistAgent adjusts projections downwards if revisor flags a contradiction."""
    with mock.patch("agents.forecast_specialist.get_llm") as mock_get_llm:
        mock_llm = mock.MagicMock()
        mock_llm.achat = mock.AsyncMock()
        mock_llm.achat.return_value.message.content = "Justificativa estatística mock"
        mock_get_llm.return_value = mock_llm
        
        # Test run with revisor feedback flagging a contradiction
        feedback = "Contradição Lógica Detectada: Forecast mostra crescimento mas RAG/SQL mostram queda."
        output = await ForecastSpecialistAgent.run(setor="Construção Civil", horizonte_meses=6, revisor_feedback=feedback)
        
        # Check that tendency is now 'queda' or 'estavel' instead of 'crescimento'
        assert output.tendencia_base in ["queda", "estavel"]
        
        # Check that projections show decay
        proj = output.cenarios["base"]["projecoes"]
        assert proj[-1]["massa_salarial_estimada"] < proj[0]["massa_salarial_estimada"]
