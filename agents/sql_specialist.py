from __future__ import annotations

import json
import logging
from llama_index.core.llms import ChatMessage, MessageRole
from agents.factory import get_llm, llm_achat_with_retry
from events import SQLStructuredOutput
from core.tools import query_industrial_sql

logger = logging.getLogger(__name__)

# DDL Schema Mock for the Centro de Inteligência database
DB_SCHEMA_DDL = """
-- DDL para a Base de Emprego Formal do Centro de Inteligência
CREATE TABLE emprego_formal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uf VARCHAR(2) NOT NULL, -- Unidade Federativa: 'SP', 'MG', 'RJ', 'RS', 'PR', 'BA', 'SC', 'GO', 'PE', 'CE'
    setor VARCHAR(60) NOT NULL, -- Setor Industrial: 'Indústria de Transformação', 'Construção Civil', 'Extrativa Mineral', 'Serviços Industriais de Utilidade Pública', 'Comércio', 'Agropecuária'
    mes_ano VARCHAR(7) NOT NULL, -- Período no formato YYYY-MM (de 2023-01 a 2024-12)
    admissoes INTEGER NOT NULL, -- Número de contratações
    desligamentos INTEGER NOT NULL, -- Número de demissões
    saldo INTEGER NOT NULL, -- Saldo líquido de empregos (admissões - desligamentos)
    salario_medio DOUBLE NOT NULL -- Média salarial em Reais (R$)
);
"""


class SQLSpecialistAgent:
    """
    SQLSpecialistAgent:
    Translates user query requirements into database queries,
    runs the SQL queries against SQLite, and returns a structured output.
    """

    @staticmethod
    async def run(query: str, uf: str, setor: str, revisor_feedback: str = "") -> SQLStructuredOutput:
        llm = get_llm()

        feedback_str = ""
        if revisor_feedback:
            feedback_str = f"\n\nATENÇÃO: O ConsistencyAuditorAgent rejeitou o resultado anterior com o feedback: '{revisor_feedback}'. Corrija a query SQL para sanar o problema."

        system_prompt = (
            "Você é o SQLSpecialistAgent do Centro de Inteligência Industrial.\n"
            "Seu objetivo é gerar e executar uma consulta SQL válida para recuperar dados de emprego.\n"
            f"Aqui está a DDL da tabela do banco de dados:\n{DB_SCHEMA_DDL}\n"
            "Lembre-se:\n"
            f"- Sempre filtre no WHERE por uf='{uf}' E setor='{setor}' para evitar misturar dados.\n"
            "- Ordene a consulta por 'mes_ano' de forma ascendente.\n"
            "- Limite a consulta a no máximo 15 registros para economizar tokens.\n"
            "Retorne APENAS um bloco de código SQL (dentro de ```sql ... ```) que extrai os dados necessários para responder à pergunta do usuário.\n"
            "Não adicione nenhuma explicação ao redor, apenas o bloco de código SQL."
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=f"Consulta do usuário: {query}{feedback_str}")
        ]

        sql_query = ""
        try:
            response = await llm_achat_with_retry(llm, messages)
            content = response.message.content.strip()

            # Extract SQL query
            if "```sql" in content:
                sql_query = content.split("```sql")[1].split("```")[0]
            elif "```" in content:
                sql_query = content.split("```")[1].split("```")[0]
            else:
                sql_query = content
            sql_query = sql_query.strip()

            # Execute query using tool
            sql_result_str = query_industrial_sql(sql_query)
            sql_payload = json.loads(sql_result_str)
            
            if sql_payload.get("status") == "error":
                logger.error(f"[SQLSpecialist] Database execution error: {sql_payload.get('error_detail')}")
                return SQLStructuredOutput(
                    query=sql_query,
                    records=[],
                    uf=uf,
                    setor=setor,
                    saldo_total=0,
                    tendencia="estavel",
                    error_detail=sql_payload.get("error_detail", "Erro desconhecido na execução do SQL.")
                )
                
            records = sql_payload.get("records", [])
        except Exception as exc:
            logger.exception("[SQLSpecialist] Execution crashed")
            return SQLStructuredOutput(
                query=sql_query,
                records=[],
                uf=uf,
                setor=setor,
                saldo_total=0,
                tendencia="estavel",
                error_detail=f"Exceção interna no SQLSpecialistAgent: {str(exc)}"
            )

        # Analyze trend and compute total balance
        saldo_total = sum(r.get("saldo", 0) for r in records)
        
        # Simple programmatic trend calculation
        if len(records) >= 2:
            first_half = records[:len(records)//2]
            second_half = records[len(records)//2:]
            avg_first = sum(r.get("saldo", 0) for r in first_half) / len(first_half)
            avg_second = sum(r.get("saldo", 0) for r in second_half) / len(second_half)
            if avg_second > avg_first + 50:
                tendencia = "crescimento"
            elif avg_second < avg_first - 50:
                tendencia = "queda"
            else:
                tendencia = "estavel"
        else:
            tendencia = "estavel"

        # Build SQLStructuredOutput
        return SQLStructuredOutput(
            query=sql_query,
            records=records,
            uf=uf,
            setor=setor,
            saldo_total=saldo_total,
            tendencia=tendencia,
            error_detail=""
        )
