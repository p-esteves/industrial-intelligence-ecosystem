from __future__ import annotations

import logging
from typing import Union

from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Context,
)
from events import (
    SQLQueryEvent,
    RAGRetrievalEvent,
    ForecastEvent,
    SQLResultEvent,
    RAGResultEvent,
    ForecastResultEvent,
    ConclusionEvent,
    AgentThoughtEvent,
    OrchestratorThoughtEvent,
)
from agents import (
    OrchestratorAgent,
    SQLSpecialistAgent,
    RAGSpecialistAgent,
    ForecastSpecialistAgent,
    ConsistencyAuditorAgent,
)

logger = logging.getLogger(__name__)


class IndustrialMultiAgentWorkflow(Workflow):
    """
    State-of-the-art event-driven LlamaIndex Workflow coordinating the multi-agent system.
    Runs asynchronously and cycles back for auto-correction if the ConsistencyAuditor
    fails the quality verification.
    """

    @step
    async def planning_step(
        self,
        ctx: Context,
        ev: StartEvent
    ) -> Union[SQLQueryEvent, RAGRetrievalEvent, ForecastEvent, None]:
        """
        Orchestrator plan phase: receives the query, extracts parameters,
        and fires parallel events for specialized agents.
        """
        query = ev.get("query")
        await ctx.store.set("query", query)
        await ctx.store.set("iteration", 0)

        logger.info(f"[Workflow] Initializing Orchestrator plan for: {query}")

        # Run Orchestrator planning
        plan_data = await OrchestratorAgent.plan(query)
        uf = plan_data.get("uf", "SP")
        setor = plan_data.get("setor", "Indústria de Transformação")
        horizonte_meses = plan_data.get("horizonte_meses", 6)

        await ctx.store.set("uf", uf)
        await ctx.store.set("setor", setor)
        await ctx.store.set("horizonte_meses", horizonte_meses)

        # Send orchestrator status event for UI display
        ctx.send_event(OrchestratorThoughtEvent(
            message=f"Plano de Execução Criado! Foco no setor: {setor} ({uf}).",
            subtasks=plan_data.get("subtasks", [])
        ))

        # Fire parallel execution events
        ctx.send_event(SQLQueryEvent(
            query=query,
            revisor_feedback=""
        ))
        ctx.send_event(RAGRetrievalEvent(
            query=query
        ))
        ctx.send_event(ForecastEvent(
            setor=setor,
            horizonte_meses=horizonte_meses
        ))
        return None

    @step
    async def sql_specialist_step(self, ctx: Context, ev: SQLQueryEvent) -> SQLResultEvent:
        """Runs the SQLSpecialistAgent to query historical CAGED statistics."""
        query = await ctx.store.get("query")
        uf = await ctx.store.get("uf")
        setor = await ctx.store.get("setor")
        iteration = await ctx.store.get("iteration")

        logger.info(f"[Workflow] Node: SQLSpecialistAgent | Iteration: {iteration}")

        sql_output = await SQLSpecialistAgent.run(
            query=query,
            uf=uf,
            setor=setor,
            revisor_feedback=ev.revisor_feedback
        )

        # Send thought log event
        ctx.send_event(AgentThoughtEvent(
            agent="SQLSpecialistAgent",
            thought=f"Consulta SQL gerada e executada com sucesso para {setor} ({uf}). Saldo acumulado: {sql_output.saldo_total}.",
            action="SQL_QUERY_GENERATION_AND_EXECUTION",
            output=sql_output.model_dump_json()
        ))

        return SQLResultEvent(data=sql_output)

    @step
    async def rag_specialist_step(self, ctx: Context, ev: RAGRetrievalEvent) -> RAGResultEvent:
        """Runs the RAGSpecialistAgent to query PDF and documents database."""
        query = await ctx.store.get("query")
        setor = await ctx.store.get("setor")
        iteration = await ctx.store.get("iteration")

        logger.info(f"[Workflow] Node: RAGSpecialistAgent | Iteration: {iteration}")

        rag_output = await RAGSpecialistAgent.run(
            query=query,
            setor=setor
        )

        # Send thought log event
        ctx.send_event(AgentThoughtEvent(
            agent="RAGSpecialistAgent",
            thought=(
                f"Busca semântica realizada no banco vetorial. "
                f"Fator macroeconomico dominante: '{rag_output.fator_macroeconomico}' com impacto '{rag_output.impacto_narrativa}'."
            ),
            action="RAG_SECTOR_CONTEXT_RETRIEVAL",
            output=rag_output.model_dump_json()
        ))

        return RAGResultEvent(data=rag_output)

    @step
    async def forecast_specialist_step(self, ctx: Context, ev: ForecastEvent) -> ForecastResultEvent:
        """Runs the ForecastSpecialistAgent to simulate macroeconomic scenarios."""
        setor = ev.setor
        horizonte_meses = ev.horizonte_meses
        iteration = await ctx.store.get("iteration")

        logger.info(f"[Workflow] Node: ForecastSpecialistAgent | Iteration: {iteration}")

        forecast_output = await ForecastSpecialistAgent.run(
            setor=setor,
            horizonte_meses=horizonte_meses,
            revisor_feedback=ev.revisor_feedback
        )

        # Send thought log event
        ctx.send_event(AgentThoughtEvent(
            agent="ForecastSpecialistAgent",
            thought=(
                f"Previsões estatísticas geradas para {horizonte_meses} meses no setor {setor}. "
                f"Tendência projetada do cenário base: '{forecast_output.tendencia_base}'."
            ),
            action="ECONOMETRIC_SCENARIO_FORECASTING",
            output=forecast_output.model_dump_json()
        ))

        return ForecastResultEvent(data=forecast_output)

    @step
    async def consistency_auditor_step(
        self,
        ctx: Context,
        ev: SQLResultEvent | RAGResultEvent | ForecastResultEvent
    ) -> Union[ConclusionEvent, SQLQueryEvent, RAGRetrievalEvent, ForecastEvent, None]:
        """
        Gathers events from SQL, RAG, and Forecast specialists.
        Runs the hybrid Consistency Auditor to validate quality before stop.
        """
        # Wait for all three specialist events
        results = ctx.collect_events(ev, [SQLResultEvent, RAGResultEvent, ForecastResultEvent])
        if results is None:
            return None  # Wait for remaining events

        sql_ev, rag_ev, forecast_ev = results
        query = await ctx.store.get("query")
        iteration = await ctx.store.get("iteration")
        setor = await ctx.store.get("setor")
        horizonte_meses = await ctx.store.get("horizonte_meses")

        logger.info(f"[Workflow] Node: ConsistencyAuditorAgent | Evaluation phase | Iteration: {iteration}")

        # Execute Quality Auditor evaluation
        verdict = await ConsistencyAuditorAgent.evaluate(
            query=query,
            sql_out=sql_ev.data,
            rag_out=rag_ev.data,
            forecast_out=forecast_ev.data
        )

        # Send thought event
        ctx.send_event(AgentThoughtEvent(
            agent="ConsistencyAuditorAgent",
            thought=f"Revisão e controle de consistência finalizado. Veredito: {'APROVADO' if verdict.approved else 'REJEITADO'}.",
            action="CONSISTENCY_AUDIT_AND_COMPLIANCE",
            output=verdict.model_dump_json()
        ))

        next_iteration = iteration + 1
        await ctx.store.set("iteration", next_iteration)

        if verdict.approved:
            logger.info(f"[Workflow] Report approved on iteration {next_iteration}.")
            return ConclusionEvent(
                report=verdict.report,
                sql_data=sql_ev.data,
                rag_data=rag_ev.data,
                forecast_data=forecast_ev.data,
                verdict=verdict
            )

        if next_iteration >= 5:
            logger.warning(f"[Workflow] Reaching maximum loop iterations ({next_iteration}). Terminating safety block.")
            # Synthesize last draft as fallback
            fallback_report = await OrchestratorAgent.synthesize(
                query=query,
                sql_data=sql_ev.data.model_dump_json(),
                rag_data=rag_ev.data.model_dump_json(),
                forecast_data=forecast_ev.data.model_dump_json()
            )
            verdict.report = f"⚠️ **[RELATÓRIO FORÇADO POR LIMITE DE ITERAÇÕES]**\n\n{fallback_report}"
            return ConclusionEvent(
                report=verdict.report,
                sql_data=sql_ev.data,
                rag_data=rag_ev.data,
                forecast_data=forecast_ev.data,
                verdict=verdict
            )

        # If rejected, cycle back by re-firing events (with feedback for SQL Specialist)
        logger.info(f"[Workflow] Report rejected. Cycling back to specialists with feedback: {verdict.feedback}")
        ctx.send_event(SQLQueryEvent(
            query=query,
            revisor_feedback=verdict.feedback
        ))
        ctx.send_event(RAGRetrievalEvent(
            query=query
        ))
        ctx.send_event(ForecastEvent(
            setor=setor,
            horizonte_meses=horizonte_meses,
            revisor_feedback=verdict.feedback
        ))
        return None

    @step
    async def conclusion_step(self, ctx: Context, ev: ConclusionEvent) -> StopEvent:
        """Concludes the workflow run and returns the final payloads."""
        logger.info("[Workflow] Workflow completed successfully.")
        iteration = await ctx.store.get("iteration")
        return StopEvent(result={
            "report": ev.report,
            "sql_data": ev.sql_data.model_dump_json(),
            "rag_data": ev.rag_data.model_dump_json(),
            "forecast_data": ev.forecast_data.model_dump_json(),
            "verdict": ev.verdict.model_dump(),
            "iteration": iteration
        })
