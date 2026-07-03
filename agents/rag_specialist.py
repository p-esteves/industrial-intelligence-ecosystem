from __future__ import annotations

import json
import logging
from llama_index.core.llms import ChatMessage, MessageRole
from agents.factory import get_llm, llm_achat_with_retry
from events import RAGStructuredOutput
from core.tools import retrieve_documents

logger = logging.getLogger(__name__)


class RAGSpecialistAgent:
    """
    RAGSpecialistAgent:
    Queries semantic document indexes (FAISS/LlamaIndex) and parses
    qualitative reports into a structured narrative format.
    """

    @staticmethod
    async def run(query: str, setor: str) -> RAGStructuredOutput:
        llm = get_llm()

        try:
            # 1. Fetch raw documents text from tool
            raw_retrieved_text = retrieve_documents(query)
        except Exception as exc:
            logger.exception("[RAGSpecialist] Document retrieval tool failed")
            return RAGStructuredOutput(
                retrieved_passages=[],
                setor_mencionado=setor,
                fator_macroeconomico="Desconhecido",
                impacto_narrativa="neutro",
                error_detail=f"Falha ao recuperar documentos: {str(exc)}"
            )

        # 2. Extract qualitative entities and narrative factors using LLM
        system_prompt = (
            "Você é o RAGSpecialistAgent do Centro de Inteligência Industrial.\n"
            "Sua tarefa é analisar o trecho do relatório industrial recuperado e extrair entidades estruturadas.\n"
            "\n"
            "Você deve retornar estritamente um JSON no seguinte formato (sem markdown ou explicações):\n"
            "{\n"
            f'  "setor_mencionado": "Nome do setor industrial (ex: {setor})",\n'
            '  "fator_macroeconomico": "Fator econômico dominante (ex: Selic alta, Câmbio, Custo de insumos)",\n'
            '  "impacto_narrativa": "positivo ou negativo ou neutro"\n'
            "}"
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=f"Analise o seguinte trecho recuperado:\n{raw_retrieved_text}")
        ]

        try:
            response = await llm_achat_with_retry(llm, messages)
            content = response.message.content.strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            content = content.strip()

            entities = json.loads(content)
            setor_mencionado = entities.get("setor_mencionado", setor)
            fator_macroeconomico = entities.get("fator_macroeconomico", "Selic alta")
            impacto_narrativa = entities.get("impacto_narrativa", "neutro")
            if impacto_narrativa not in ["positivo", "negativo", "neutro"]:
                impacto_narrativa = "neutro"
            error_detail = ""
        except Exception as exc:
            logger.warning(f"[RAGSpecialist] Failed to execute or parse LLM extraction: {exc}. Using fallback values.")
            setor_mencionado = setor
            fator_macroeconomico = "Condições gerais de mercado"
            impacto_narrativa = "neutro"
            error_detail = f"Falha na extração de entidades via LLM: {str(exc)}"

        return RAGStructuredOutput(
            retrieved_passages=[raw_retrieved_text] if raw_retrieved_text else [],
            setor_mencionado=setor_mencionado,
            fator_macroeconomico=fator_macroeconomico,
            impacto_narrativa=impacto_narrativa,
            error_detail=error_detail
        )
