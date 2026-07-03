from __future__ import annotations

import json
import logging
from llama_index.core.llms import ChatMessage, MessageRole
from agents.factory import get_llm, llm_achat_with_retry
from events import SQLStructuredOutput, RAGStructuredOutput, ForecastStructuredOutput, AuditorVerdict

logger = logging.getLogger(__name__)


class ConsistencyAuditorAgent:
    """
    ConsistencyAuditorAgent (Quality Assurance):
    A hybrid programmatic + semantic validation engine. Performs structural and mathematical checks
    in Python, then uses the LLM to refine and compile the final report.
    """

    @staticmethod
    async def evaluate(
        query: str,
        sql_out: SQLStructuredOutput,
        rag_out: RAGStructuredOutput,
        forecast_out: ForecastStructuredOutput
    ) -> AuditorVerdict:
        """
        Validates consistency across SQL, RAG, and Forecast structured outputs.
        """
        # ============================================================
        # Phase 1: Pure Python Programmatic Validation (Deterministic)
        # ============================================================
        errors = []

        # Check 0: Specialist Execution Errors propagation
        if sql_out.error_detail:
            errors.append(f"Erro no SQLSpecialist: {sql_out.error_detail}")
        if rag_out.error_detail:
            errors.append(f"Erro no RAGSpecialist: {rag_out.error_detail}")
        if forecast_out.error_detail:
            errors.append(f"Erro no ForecastSpecialist: {forecast_out.error_detail}")

        # Check 1: Math and schema validation (Admissões - Desligamentos == Saldo)
        if not sql_out.records and not sql_out.error_detail:
            errors.append("Nenhum dado histórico retornado pela consulta SQL.")
            
        for idx, record in enumerate(sql_out.records):
            admissoes = record.get("admissoes")
            desligamentos = record.get("desligamentos")
            saldo = record.get("saldo")
            
            # Enforce that all schema columns exist
            if admissoes is None or desligamentos is None or saldo is None:
                errors.append(
                    f"Registro SQL {idx} inválido: Colunas obrigatórias ausentes no payload do banco "
                    f"(admissoes={admissoes}, desligamentos={desligamentos}, saldo={saldo})."
                )
            else:
                calculated_saldo = admissoes - desligamentos
                if calculated_saldo != saldo:
                    errors.append(
                        f"Inconsistência matemática no registro {idx} ({record.get('mes_ano')}): "
                        f"Admissões ({admissoes}) - Desligamentos ({desligamentos}) = {calculated_saldo}, "
                        f"mas o saldo registrado é {saldo}."
                    )

        # Check 2: Sector and Location matching
        if sql_out.setor.lower() != forecast_out.setor.lower():
            errors.append(
                f"Divergência de Setor: SQL consultou '{sql_out.setor}', "
                f"mas Forecast projetou '{forecast_out.setor}'."
            )

        # Check 3: Logical Trend Contradiction
        # If SQL history is dropping, RAG narrative is negative (e.g. high Selic hurting the sector),
        # but the Forecast predicts high growth without any positive factors, trigger a contradiction alert.
        if (sql_out.tendencia == "queda" and 
            rag_out.impacto_narrativa == "negativo" and 
            forecast_out.tendencia_base == "crescimento"):
            errors.append(
                "Contradição Lógica Detectada: O histórico mostra queda de emprego e a narrativa RAG indica "
                "impacto macroeconômico negativo (ex: Selic alta prejudicando), mas a projeção de base indica "
                "crescimento de massa salarial de forma inconsistente."
            )

        # If any deterministic check fails, REJECT immediately and request correction
        if errors:
            feedback_msg = " | ".join(errors)
            logger.warning(f"[Auditor] Reprovado programaticamente: {feedback_msg}")
            return AuditorVerdict(
                approved=False,
                feedback=f"Auditoria Programática detectou falhas: {feedback_msg}",
                report=""
            )

        # ============================================================
        # Phase 2: Semantic Synthesis & Polish via LLM (if programmatic passes)
        # ============================================================
        logger.info("[Auditor] Validação programática aprovada. Iniciando síntese final.")

        llm = get_llm()

        system_prompt = (
            "Você é o Chief Editor / ConsistencyAuditorAgent do Centro de Inteligência Industrial.\n"
            "Sua tarefa é redigir o relatório macroeconômico final consolidado com base nas fontes validadas.\n"
            "Você deve compilar um documento em Markdown estruturado contendo:\n"
            "- Título Profissional de Nível 1 (#)\n"
            "- Sumário Executivo explicando a conjuntura.\n"
            "- Seção de Dados Históricos: Apresente os registros SQL em uma tabela Markdown limpa.\n"
            "- Seção de Projeções: Detalhe os cenários Base, Otimista e Pessimista do Forecast.\n"
            "- Análise Conjuntural: Use as informações qualitativas do RAG (taxa Selic, custos de insumos) para fundamentar as tendências.\n"
            "- Conclusão e Recomendações Estratégicas para o Centro de Inteligência.\n"
            "\n"
            "Certifique-se de que os números coincidem EXATAMENTE com as fontes fornecidas. Não adicione alucinações."
        )

        user_content = (
            f"Consulta do Usuário: {query}\n\n"
            f"Dados Históricos (SQL): Setor {sql_out.setor}, UF {sql_out.uf}, Saldo Acumulado: {sql_out.saldo_total}.\n"
            f"Registros:\n{json.dumps(sql_out.records, ensure_ascii=False, indent=2)}\n\n"
            f"Contexto Qualitativo (RAG): Setor {rag_out.setor_mencionado}, Fator: {rag_out.fator_macroeconomico}, Impacto: {rag_out.impacto_narrativa}.\n"
            f"Relatório RAG:\n{rag_out.retrieved_passages[0] if rag_out.retrieved_passages else ''}\n\n"
            f"Projeções (Forecast): Setor {forecast_out.setor}, Horizonte {forecast_out.horizonte_meses} meses.\n"
            f"Cenários:\n{json.dumps(forecast_out.cenarios, ensure_ascii=False, indent=2)}\n"
            f"Modelo e Justificativa:\n{forecast_out.modelo_utilizado}\n"
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_content)
        ]

        try:
            response = await llm_achat_with_retry(llm, messages)
            final_report = response.message.content.strip()
            
            # Programmatic verification of the synthesized Markdown structure
            if not final_report.startswith("#"):
                logger.warning("[Auditor] LLM output did not start with heading level 1 (#). Appending title.")
                final_report = f"# Relatório de Inteligência Industrial - {sql_out.setor} ({sql_out.uf})\n\n{final_report}"
            
            if "|" not in final_report:
                logger.warning("[Auditor] Markdown tables missing in generated report.")
                # We do not crash but we warning or fallback
                
        except Exception as exc:
            logger.exception("[Auditor] Synthesizing report failed")
            return AuditorVerdict(
                approved=False,
                feedback=f"Falha técnica na síntese final do relatório: {str(exc)}",
                report=""
            )

        return AuditorVerdict(
            approved=True,
            feedback="",
            report=final_report
        )
