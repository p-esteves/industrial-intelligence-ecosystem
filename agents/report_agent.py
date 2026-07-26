"""
Industrial Multi-Agent Ecosystem — Report Agent (Agente 3).

Responsible for generating natural language executive reports based on detected anomalies
and FAISS RAG context using Ollama local LLM, with graceful degradation fallback.
"""

from __future__ import annotations

import logging
import time
from typing import Any
import httpx
from pydantic import BaseModel, Field

from config import get_settings
from core.metrics import AGENT_EXECUTION_DURATION, LLM_FALLBACK_COUNT
from agents.analysis_agent import AnalysisSummary, AnomalyDetail

logger = logging.getLogger(__name__)


class ReportSummary(BaseModel):
    """Structured report payload output by the Report Agent."""

    executive_summary: str = Field(..., description="Generated natural language executive summary")
    anomalies_addressed_count: int = Field(..., description="Count of anomalies covered in report")
    llm_provider_used: str = Field(..., description="LLM provider used (ollama or fallback_rule_engine)")
    rag_context_used: bool = Field(False, description="Whether FAISS RAG context was integrated")
    recommendations: list[str] = Field(default_factory=list, description="Actionable mitigation recommendations")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")


class ReportAgent:
    """
    Report Agent: Generates natural language executive reports using LLM (Ollama)
    with graceful degradation fallback when the LLM service is unavailable.
    """

    @classmethod
    async def generate_report_async(
        cls,
        analysis_summary: AnalysisSummary | dict[str, Any],
        rag_context: str = "",
    ) -> ReportSummary:
        """Async method to generate executive report using Ollama or fallback."""
        start_time = time.perf_counter()
        settings = get_settings()

        if isinstance(analysis_summary, dict):
            anomalies = analysis_summary.get("anomalies", [])
            total_anomalies = len(anomalies)
        else:
            anomalies = analysis_summary.anomalies
            total_anomalies = analysis_summary.anomalies_found_count

        logger.info(
            "ReportAgent starting report synthesis",
            extra={
                "event_type": "agent_decision",
                "agent": "ReportAgent",
                "action": "REPORT_SYNTHESIS_START",
                "total_anomalies": total_anomalies,
                "has_rag_context": bool(rag_context),
            },
        )

        llm_provider_used = "ollama"
        report_text = ""
        recommendations: list[str] = []

        # Attempt local LLM call via Ollama
        if settings.llm_provider == "ollama":
            try:
                report_text, recommendations = await cls._query_ollama(
                    anomalies=anomalies,
                    rag_context=rag_context,
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                )
            except Exception as exc:
                logger.warning(
                    f"Ollama service unreachable ({exc}). Activating graceful degradation fallback.",
                    extra={
                        "event_type": "agent_decision",
                        "agent": "ReportAgent",
                        "action": "GRACEFUL_DEGRADATION_FALLBACK",
                        "reason": str(exc),
                    },
                )
                LLM_FALLBACK_COUNT.labels(reason="ollama_unreachable").inc()
                llm_provider_used = "fallback_rule_engine"
                report_text, recommendations = cls._generate_fallback_report(anomalies, rag_context)
        else:
            llm_provider_used = "fallback_rule_engine"
            report_text, recommendations = cls._generate_fallback_report(anomalies, rag_context)

        exec_duration_s = time.perf_counter() - start_time
        exec_duration_ms = round(exec_duration_s * 1000, 2)

        AGENT_EXECUTION_DURATION.labels(agent="ReportAgent").observe(exec_duration_s)

        logger.info(
            "ReportAgent completed report generation",
            extra={
                "event_type": "agent_decision",
                "agent": "ReportAgent",
                "action": "REPORT_SYNTHESIS_COMPLETE",
                "provider_used": llm_provider_used,
                "execution_time_ms": exec_duration_ms,
            },
        )

        return ReportSummary(
            executive_summary=report_text,
            anomalies_addressed_count=total_anomalies,
            llm_provider_used=llm_provider_used,
            rag_context_used=bool(rag_context),
            recommendations=recommendations,
            execution_time_ms=exec_duration_ms,
        )

    @classmethod
    def run(
        cls,
        analysis_summary: AnalysisSummary | dict[str, Any],
        rag_context: str = "",
    ) -> ReportSummary:
        """Synchronous wrapper for ReportAgent execution."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(
                    cls.generate_report_async(analysis_summary, rag_context)
                )
            else:
                return loop.run_until_complete(
                    cls.generate_report_async(analysis_summary, rag_context)
                )
        except Exception:
            return asyncio.run(cls.generate_report_async(analysis_summary, rag_context))

    @classmethod
    async def _query_ollama(
        cls,
        anomalies: list[Any],
        rag_context: str,
        base_url: str,
        model: str,
    ) -> tuple[str, list[str]]:
        """Call Ollama REST API to generate natural language report."""
        anomaly_lines = [
            f"- {a.description if hasattr(a, 'description') else a.get('description', '')}"
            for a in anomalies[:10]
        ]
        anomaly_str = "\n".join(anomaly_lines) if anomaly_lines else "Nenhuma anomalia crítica."

        prompt = f"""Você é um especialista em inteligência industrial e economia brasileira (CAGED/IBGE).
Sua tarefa é analisar as seguintes anomalias estatísticas detectadas na indústria e gerar um relatório executivo estruturado em linguagem natural (Português).

ANOMALIAS DETECTADAS:
{anomaly_str}

CONTEXTO DE DIRETRIZES INDUSTRIAIS (RAG):
{rag_context if rag_context else "Nenhum contexto RAG adicional disponível."}

FORMATO DO RELATÓRIO REQUERIDO:
1. Resumo Executivo das Anomalias
2. Análise de Causa Raiz e Impacto Setorial
3. Recomendações Estratégicas e Mitigação
"""

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            if response.status_code == 200:
                res_data = response.json()
                text_out = res_data.get("response", "")
                recs = [
                    "Acompanhamento contínuo dos setores afetados via CAGED mensal",
                    "Implementação de comitê de crise para retenção de postos de trabalho",
                    "Revisão de incentivos fiscais estaduais para polos em desaceleração",
                ]
                return text_out if text_out else "Relatório gerado sem conteúdo.", recs
            else:
                raise RuntimeError(f"Ollama returned HTTP {response.status_code}")

    @classmethod
    def _generate_fallback_report(
        cls,
        anomalies: list[Any],
        rag_context: str,
    ) -> tuple[str, list[str]]:
        """
        Deterministic rule-based report synthesizer used during Ollama downtime.
        """
        if not anomalies:
            report = (
                "### 📊 Relatório Executivo de Desempenho Industrial\n\n"
                "**Status:** Normalidade Operacional.\n"
                "Nenhuma anomalia estatística significativa foi detectada nos setores analisados. "
                "A massa salarial e a movimentação de trabalhadores mantêm-se dentro dos limites históricos normais."
            )
            recs = ["Manter monitoramento de rotina das bases do CAGED e IBGE."]
            return report, recs

        critical_list = []
        for a in anomalies:
            desc = a.description if hasattr(a, "description") else a.get("description", str(a))
            critical_list.append(f"- ⚠️ {desc}")

        report = (
            "### 📊 Relatório Executivo de Diagnóstico Industrial (Modo Resiliente / Fallback)\n\n"
            f"**Resumo de Anomalias:** Foram identificadas {len(anomalies)} anomalias estatísticas relevantes "
            "na massa salarial e no saldo de empregos industriais.\n\n"
            "**Principais Desvios Detectados:**\n" + "\n".join(critical_list) + "\n\n"
            "**Análise de Impacto:**\n"
            "Os desvios observados indicam retrações acentuadas em polos específicos, potencialmente "
            "decorrentes de oscilações na demanda externa, manutenção operacional em plantas de grande porte "
            "ou ajustamentos em cadeias de suprimentos estaduais.\n\n"
        )

        if rag_context:
            report += f"**Diretrizes Industriais Aplicáveis (RAG Context):**\n{rag_context[:500]}...\n\n"

        recs = [
            "Incentivar programas estaduais de qualificação profissional nos polos industriais afetados.",
            "Solicitar relatórios complementares da ANM/MME para setores mineradores com retração de massa salarial.",
            "Estabelecer linha de crédito emergencial para sustentação do emprego em municípios com saldo negativo agudo.",
        ]

        report += "**Recomendações de Mitigação:**\n" + "\n".join([f"1. {r}" for r in recs])

        return report, recs
