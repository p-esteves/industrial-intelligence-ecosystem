from __future__ import annotations

import logging
import json
import uuid
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from config import get_settings
from core.tools import rebuild_vector_index
from workflow import IndustrialMultiAgentWorkflow, AgentThoughtEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Industrial Multi-Agent Ecosystem"])


# ── Request / Response Schemas ─────────────────────────────────


class ChatRequest(BaseModel):
    """Schema for incoming chat messages."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier. Auto-generated if not provided.",
        examples=["sess-001"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The user's natural language message.",
        examples=["Qual o saldo de emprego em São Paulo no setor de Construção Civil?"],
    )


class ToolCallMetadata(BaseModel):
    """Schema for tool execution metadata details within chat responses."""
    tool: str = Field(..., description="Nome do agente/ferramenta que foi acionado")
    arguments: dict[str, Any] = Field(..., description="Ação ou argumentos do agente")
    result: Any = Field(..., description="Resultado ou output gerado pelo agente")


class ChatResponse(BaseModel):
    """Schema for chat responses."""

    session_id: str
    response: str
    duration_ms: int
    tool_calls: list[ToolCallMetadata] = Field(
        default_factory=list,
        description="Lista de agentes/ferramentas executadas com seus logs de raciocínio.",
    )


class IngestResponse(BaseModel):
    """Schema for document ingestion responses."""

    filename: str
    num_chunks: int
    status: str


class HealthResponse(BaseModel):
    """Schema for health check responses."""

    status: str
    llm_provider: str
    ollama_reachable: bool | None = None


class SQLRequest(BaseModel):
    """Schema for incoming SQL queries to execute."""
    sql_query: str = Field(..., description="The SQL query to execute on the CAGED database.")


class SQLResponsePayload(BaseModel):
    """Schema for corporate SQL query response payload."""
    status: str = Field(..., description="Status da consulta SQL (success ou error)")
    query: str = Field(..., description="Query SQL que foi executada")
    columns: list[str] = Field(..., description="Lista de colunas retornadas")
    records: list[dict[str, Any]] = Field(..., description="Lista de registros retornados da base de dados")
    row_count: int = Field(..., description="Quantidade total de registros retornados")
    execution_time_ms: float = Field(..., description="Tempo de execução da query em milissegundos")
    error_detail: str | None = Field(None, description="Detalhamento de erro se status for error")


class ForecastRequest(BaseModel):
    """Schema for incoming forecasting requests."""
    setor: str = Field(..., description="The industrial sector.")
    horizonte_meses: int = Field(default=6, description="Prediction horizon in months.")


class ForecastPeriodProjections(BaseModel):
    """Schema for monthly forecast values."""
    periodo: str = Field(..., description="Período da projeção no formato YYYY-MM")
    massa_salarial_estimada: float = Field(..., description="Massa salarial estimada")
    empregados_estimados: int = Field(..., description="Número de empregados estimados")
    salario_medio_estimado: float = Field(..., description="Salário médio estimado")


class ForecastScenarioDetails(BaseModel):
    """Schema for scenario detailed projections."""
    cenario: str = Field(..., description="Nome do cenário")
    taxa_crescimento_mensal: str = Field(..., description="Taxa de crescimento mensal")
    projecoes: list[ForecastPeriodProjections] = Field(..., description="Projeções mensais para o cenário")


class ForecastScenarios(BaseModel):
    """Schema representing forecasted scenarios."""
    pessimista: ForecastScenarioDetails = Field(..., description="Cenário pessimista")
    base: ForecastScenarioDetails = Field(..., description="Cenário de linha de base")
    otimista: ForecastScenarioDetails = Field(..., description="Cenário otimista")


class MacroeconomicVariables(BaseModel):
    """Schema for baseline macroeconomic indicators."""
    selic_atual: str = Field(..., description="Taxa Selic atual")
    ipca_acumulado_12m: str = Field(..., description="IPCA acumulado em 12 meses")
    pib_projecao_anual: str = Field(..., description="Projeção anual de PIB")
    taxa_desemprego: str = Field(..., description="Taxa de desemprego atual")
    confianca_industria_fgv: float = Field(..., description="Índice de confiança da indústria da FGV")
    cambio_usd_brl: float = Field(..., description="Taxa de câmbio USD para BRL")


class ForecastResponsePayload(BaseModel):
    """Schema for macroeconomic and workforce forecasting payload."""
    status: str = Field(..., description="Status da previsão (success ou error)")
    setor: str = Field(..., description="Setor industrial analisado")
    horizonte_meses: int = Field(..., description="Horizonte de tempo da projeção em meses")
    data_geracao: str | None = Field(None, description="Timestamp de geração")
    modelo: str | None = Field(None, description="Modelo de séries temporais utilizado")
    confianca_modelo: str | None = Field(None, description="Confiança do modelo estatístico")
    cenarios: ForecastScenarios | None = Field(None, description="Cenários simulados")
    variaveis_macroeconomicas: MacroeconomicVariables | None = Field(None, description="Variáveis macroeconômicas de contorno")
    alertas: list[str] = Field(default_factory=list, description="Lista de alertas gerados")
    execution_time_ms: float = Field(..., description="Tempo de processamento da previsão em milissegundos")
    error_detail: str | None = Field(None, description="Detalhamento de erro se status for error")


# ── Endpoints ──────────────────────────────────────────────────


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Conversar com o ecossistema multi-agente",
    description=(
        "Envia uma mensagem ao sistema multi-agente (LlamaIndex Workflow) "
        "que executa de forma cíclica e autônoma a geração de dados analíticos."
    ),
)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    start_time: float = time.perf_counter()
    logger.info(
        "Workflow chat request received",
        extra={
            "event_type": "audit_chat_endpoint_start",
            "session_id": request.session_id,
            "message_length": len(request.message),
        },
    )

    try:
        # Instantiate and run LlamaIndex Workflow
        wf = IndustrialMultiAgentWorkflow(timeout=120.0, verbose=True)
        handler = wf.run(query=request.message)

        tool_calls: list[ToolCallMetadata] = []

        # Listen to stream thought events
        async for event in handler.stream_events():
            if isinstance(event, AgentThoughtEvent):
                # Try parsing string records for clean JSON output exposure
                parsed_res: Any
                try:
                    parsed_res = json.loads(event.output)
                except Exception:
                    parsed_res = event.output

                tool_calls.append(ToolCallMetadata(
                    tool=event.agent,
                    arguments={"action": event.action, "thought": event.thought},
                    result=parsed_res
                ))

        # Wait for the workflow final result
        workflow_result = await handler
        final_report: str = workflow_result.get("report", "Erro ao gerar o relatório.")

        duration_ms: int = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "Workflow chat request completed successfully",
            extra={
                "event_type": "audit_chat_endpoint_success",
                "session_id": request.session_id,
                "duration_ms": duration_ms,
                "iterations": workflow_result.get("iteration", 0)
            }
        )

        return ChatResponse(
            session_id=request.session_id,
            response=final_report,
            duration_ms=duration_ms,
            tool_calls=tool_calls,
        )

    except Exception as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception(
            "Workflow chat endpoint error",
            extra={
                "event_type": "audit_chat_endpoint_failure",
                "session_id": request.session_id,
                "duration_ms": duration_ms,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no workflow: {exc}",
        ) from exc


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingerir documento PDF",
    description="Recebe um PDF e executa o pipeline de indexação semântica.",
)
async def ingest_endpoint(
    file: UploadFile = File(..., description="Ficheiro PDF para RAG."),
) -> IngestResponse:
    start_time: float = time.perf_counter()
    
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas ficheiros PDF são aceites.",
        )

    settings = get_settings()
    docs_dir = Path(settings.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    safe_filename: str = file.filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    target_path: Path = docs_dir / safe_filename

    try:
        with open(target_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        num_chunks: int = rebuild_vector_index(settings)
        return IngestResponse(
            filename=safe_filename,
            num_chunks=num_chunks,
            status="indexed",
        )
    except Exception as exc:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar o documento: {exc}",
        ) from exc


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar saúde do serviço",
)
async def health_endpoint() -> HealthResponse:
    settings = get_settings()
    ollama_reachable: bool | None = None

    if settings.llm_provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                ollama_reachable = resp.status_code == 200
        except Exception:
            ollama_reachable = False

    return HealthResponse(
        status="healthy",
        llm_provider=settings.llm_provider,
        ollama_reachable=ollama_reachable,
    )


@router.post(
    "/sql",
    response_model=SQLResponsePayload,
    summary="Executar consulta SQL na base do CAGED/IBGE",
)
async def sql_endpoint(request: SQLRequest) -> SQLResponsePayload:
    from core.tools import query_industrial_sql
    import json

    try:
        result_str = query_industrial_sql(request.sql_query)
        payload_dict = json.loads(result_str)
        return SQLResponsePayload(**payload_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar SQL: {exc}"
        ) from exc


@router.post(
    "/forecast",
    response_model=ForecastResponsePayload,
    summary="Gerar previsões de séries temporais de massa salarial",
)
async def forecast_endpoint(request: ForecastRequest) -> ForecastResponsePayload:
    from core.tools import forecast_insight
    import json

    try:
        result_str = forecast_insight(request.setor, request.horizonte_meses)
        payload_dict = json.loads(result_str)
        return ForecastResponsePayload(**payload_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar forecast: {exc}"
        ) from exc


# ── Production Industrial Pipeline Endpoints ───────────────────


class PipelineRequest(BaseModel):
    file_path: str | None = Field(None, description="Path to CSV/Parquet data file. Defaults to sample CAGED dataset.")
    z_threshold: float = Field(2.0, description="Z-score threshold for statistical anomaly detection.")
    include_rag: bool = Field(True, description="Whether to include FAISS/document RAG context in report.")


class PipelineResponsePayload(BaseModel):
    pipeline_id: str = Field(..., description="Unique pipeline execution ID")
    status: str = Field(..., description="Execution status (success or error)")
    ingestion: dict[str, Any] = Field(..., description="Agente 1 (Ingestão) output summary")
    analysis: dict[str, Any] = Field(..., description="Agente 2 (Análise) statistical anomaly output summary")
    report: dict[str, Any] = Field(..., description="Agente 3 (Relatório) LLM executive summary")
    total_duration_ms: float = Field(..., description="Total pipeline execution duration in ms")


class AgentStatusDetail(BaseModel):
    name: str
    status: str
    description: str


class SystemStatusResponsePayload(BaseModel):
    overall_status: str
    agents: list[AgentStatusDetail]
    ollama_reachable: bool
    llm_provider: str


@router.post(
    "/pipeline",
    response_model=PipelineResponsePayload,
    summary="Disparar pipeline completo dos agentes industriais",
    description="Executa o fluxo completo: Agente 1 (Ingestão) -> Agente 2 (Análise Estatística) -> Agente 3 (Relatório LLM + RAG)",
)
async def pipeline_endpoint(request: PipelineRequest) -> PipelineResponsePayload:
    from agents.ingestion_agent import IngestionAgent
    from agents.analysis_agent import AnalysisAgent
    from agents.report_agent import ReportAgent
    from core.tools import retrieve_documents
    from core.metrics import PIPELINE_EXECUTIONS, PIPELINE_DURATION

    start_time = time.perf_counter()
    pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"

    logger.info("Pipeline execution started", extra={"pipeline_id": pipeline_id, "file_path": request.file_path})

    try:
        # Step 1: Ingestion Agent
        ing_summary = IngestionAgent.run(file_path=request.file_path)

        # Step 2: Analysis Agent
        ana_summary = AnalysisAgent.run(ingestion_data=ing_summary, z_threshold=request.z_threshold)

        # Step 3: RAG Retrieval Context
        rag_context = ""
        if request.include_rag:
            rag_context = retrieve_documents("anomalias massa salarial industria extrativa e transformacao")

        # Step 4: Report Agent
        rep_summary = await ReportAgent.generate_report_async(
            analysis_summary=ana_summary,
            rag_context=rag_context,
        )

        duration_s = time.perf_counter() - start_time
        total_duration_ms = round(duration_s * 1000, 2)

        PIPELINE_EXECUTIONS.labels(status="success").inc()
        PIPELINE_DURATION.observe(duration_s)

        return PipelineResponsePayload(
            pipeline_id=pipeline_id,
            status="success",
            ingestion=ing_summary.model_dump(),
            analysis=ana_summary.model_dump(),
            report=rep_summary.model_dump(),
            total_duration_ms=total_duration_ms,
        )

    except Exception as exc:
        duration_s = time.perf_counter() - start_time
        PIPELINE_EXECUTIONS.labels(status="error").inc()
        logger.exception("Pipeline execution failed", extra={"pipeline_id": pipeline_id, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar o pipeline de agentes: {exc}",
        ) from exc


@router.get(
    "/status",
    response_model=SystemStatusResponsePayload,
    summary="Verificar estado de todos os agentes do ecossistema",
)
async def status_endpoint() -> SystemStatusResponsePayload:
    settings = get_settings()
    ollama_reachable = False

    if settings.llm_provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                ollama_reachable = resp.status_code == 200
        except Exception:
            ollama_reachable = False

    agents_status = [
        AgentStatusDetail(
            name="Agente 1 (Ingestão)",
            status="operational",
            description="Leitura e validação de dados tabulares (CSV, Parquet, SQLite).",
        ),
        AgentStatusDetail(
            name="Agente 2 (Análise de Anomalias)",
            status="operational",
            description="Detecção estatística de desvios (Z-Score & IQR).",
        ),
        AgentStatusDetail(
            name="Agente 3 (Relatório Executivo)",
            status="operational" if (ollama_reachable or settings.llm_provider != "ollama") else "degraded_fallback",
            description="Síntese em linguagem natural via Ollama LLM ou Modo Resiliente.",
        ),
        AgentStatusDetail(
            name="Módulo RAG (FAISS)",
            status="operational",
            description="Busca semântica em diretrizes e relatórios industriais.",
        ),
    ]

    return SystemStatusResponsePayload(
        overall_status="healthy",
        agents=agents_status,
        ollama_reachable=ollama_reachable,
        llm_provider=settings.llm_provider,
    )


@router.get(
    "/metrics",
    summary="Expor métricas no formato Prometheus",
    description="Endpoint compatível com Prometheus scraper.",
)
async def metrics_endpoint() -> Response:
    from fastapi.responses import Response
    from core.metrics import generate_prometheus_metrics

    body, content_type = generate_prometheus_metrics()
    return Response(content=body, media_type=content_type)

