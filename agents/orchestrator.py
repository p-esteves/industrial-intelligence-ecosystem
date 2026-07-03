from __future__ import annotations

import json
import logging
from llama_index.core.llms import ChatMessage, MessageRole
from agents.factory import get_llm, llm_achat_with_retry

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    OrchestratorAgent (Manager/Steward):
    The main coordinator agent. Analyzes natural language queries,
    creates execution plans (subtasks), and extracts parameters.
    """

    @staticmethod
    async def plan(query: str) -> dict:
        """
        Analyzes the user's query and returns extracted parameters and a plan.
        """
        llm = get_llm()

        system_prompt = (
            "Você é o OrchestratorAgent, o Gerente e Data Steward de um Centro de Inteligência Industrial.\n"
            "Sua tarefa é analisar a pergunta do usuário e estruturar uma estratégia de execução dividida em subtarefas.\n"
            "Você deve detectar as seguintes variáveis:\n"
            "- UF (ex: 'SP', 'CE', 'MG' - padrão 'SP')\n"
            "- Setor industrial (Deve ser exatamente um dos seguintes: 'Indústria de Transformação', "
            "'Construção Civil', 'Extrativa Mineral', 'Serviços Industriais de Utilidade Pública', 'Comércio', 'Agropecuária' - padrão 'Indústria de Transformação')\n"
            "- Horizonte de meses para o forecast (número inteiro - padrão 6)\n"
            "\n"
            "Retorne estritamente um JSON com a seguinte estrutura (sem markdown ou outros textos):\n"
            "{\n"
            '  "uf": "UF_DETECTADA",\n'
            '  "setor": "SETOR_DETECTADO",\n'
            '  "horizonte_meses": 6,\n'
            '  "subtasks": [\n'
            '     "Subtarefa 1: ...",\n'
            '     "Subtarefa 2: ..."\n'
            '  ],\n'
            '  "explanation": "Breve explicação sobre os objetivos do relatório"\n'
            "}"
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=f"Analise esta consulta do usuário: {query}")
        ]

        try:
            response = await llm_achat_with_retry(llm, messages)
            content = response.message.content.strip()

            # Clean JSON from markdown if necessary
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            content = content.strip()

            plan_data = json.loads(content)
        except Exception as exc:
            logger.warning(f"Failed to parse or fetch Orchestrator JSON: {exc}. Using fallback values.")
            plan_data = {
                "uf": "SP",
                "setor": "Indústria de Transformação",
                "horizonte_meses": 6,
                "subtasks": [
                    "Subtarefa 1: Executar consulta SQL histórica para o setor na UF correspondente.",
                    "Subtarefa 2: Projetar cenários de massa salarial para o horizonte solicitado.",
                    "Subtarefa 3: Integrar insights qualitativos com RAG sobre relatórios industriais."
                ],
                "explanation": "Relatório analítico sobre dinâmica de emprego e massa salarial."
            }

        return plan_data

    @staticmethod
    async def synthesize(query: str, sql_data: str, rag_data: str, forecast_data: str) -> str:
        """
        Consolidates the final approved report if all validations pass.
        Called by the consistency auditor or orchestrator for final rendering.
        """
        llm = get_llm()

        system_prompt = (
            "Você é o OrchestratorAgent do Centro de Inteligência Industrial.\n"
            "Consolide o rascunho de relatório final integrando os dados brutos e análises coletadas.\n"
            "Garanta um tom altamente executivo, profissional, estruturado em Markdown com tabelas limpas."
        )

        context = (
            f"Consulta original: {query}\n\n"
            f"Dados Históricos SQL: {sql_data}\n\n"
            f"Contexto do RAG: {rag_data}\n\n"
            f"Previsões e Cenários: {forecast_data}\n"
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=context)
        ]

        try:
            response = await llm_achat_with_retry(llm, messages)
            return response.message.content.strip()
        except Exception as exc:
            logger.exception("Synthesize failed")
            return f"Erro ao sintetizar relatório final: {str(exc)}"
