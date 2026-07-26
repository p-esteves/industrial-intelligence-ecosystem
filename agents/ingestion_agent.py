"""
Industrial Multi-Agent Ecosystem — Ingestion Agent (Agente 1).

Responsible for loading, validating, and structuring tabular industrial datasets
(CSV, Parquet, or SQLite) simulating CAGED/IBGE economic indicators.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field

from config import get_settings
from core.metrics import AGENT_EXECUTION_DURATION

logger = logging.getLogger(__name__)


class IngestionSummary(BaseModel):
    """Structured data payload output by the Ingestion Agent."""

    total_records: int = Field(..., description="Total rows ingested and validated")
    file_path: str = Field(..., description="Path to the ingested data source")
    format_type: str = Field(..., description="File format (csv, parquet, or sqlite)")
    ufs_covered: list[str] = Field(..., description="List of unique Brazilian states in data")
    sectors_covered: list[str] = Field(..., description="List of unique industrial sectors in data")
    periods_covered: list[str] = Field(..., description="List of time periods covered (YYYY-MM)")
    records: list[dict[str, Any]] = Field(..., description="Parsed tabular records sample")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")


class IngestionAgent:
    """
    Ingestion Agent: Loads, validates, and structures industrial tabular datasets.
    """

    @classmethod
    def run(cls, file_path: str | None = None) -> IngestionSummary:
        """
        Execute data ingestion pipeline on specified file or default sample dataset.
        """
        start_time = time.perf_counter()
        settings = get_settings()

        if not file_path:
            file_path = f"{settings.sample_dir}/caged_industrial.csv"
            path = Path(file_path)
            if not path.exists():
                fallback_sqlite = f"{settings.data_dir}/mock_caged.db"
                if Path(fallback_sqlite).exists():
                    file_path = fallback_sqlite
                    path = Path(file_path)
        else:
            path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")

        format_type = path.suffix.lstrip(".").lower()

        logger.info(
            "IngestionAgent starting data load",
            extra={
                "event_type": "agent_decision",
                "agent": "IngestionAgent",
                "action": "DATA_INGESTION_START",
                "file_path": str(path),
                "format_type": format_type,
            },
        )

        try:
            if format_type == "csv":
                df = pd.read_csv(path)
            elif format_type == "parquet":
                df = pd.read_parquet(path)
            elif format_type in ("db", "sqlite", "sqlite3"):
                import sqlite3
                conn = sqlite3.connect(path)
                df = pd.read_sql_query("SELECT * FROM emprego_formal", conn)
                conn.close()
                if "massa_salarial" not in df.columns:
                    df["massa_salarial"] = df["saldo"] * df["salario_medio"]
            else:
                raise ValueError(f"Unsupported dataset format: {format_type}")

            # Standardize columns
            required_cols = {"uf", "setor", "mes_ano", "admissoes", "desligamentos", "saldo"}
            if not required_cols.issubset(set(df.columns)):
                missing = required_cols - set(df.columns)
                raise ValueError(f"Dataset missing required columns: {missing}")

            if "massa_salarial" not in df.columns:
                df["massa_salarial"] = df["admissoes"] * df["salario_medio"]

            ufs = sorted(df["uf"].unique().tolist())
            sectors = sorted(df["setor"].unique().tolist())
            periods = sorted(df["mes_ano"].unique().tolist())
            records = df.to_dict(orient="records")

            exec_duration_s = time.perf_counter() - start_time
            exec_duration_ms = round(exec_duration_s * 1000, 2)

            AGENT_EXECUTION_DURATION.labels(agent="IngestionAgent").observe(exec_duration_s)

            logger.info(
                "IngestionAgent completed successfully",
                extra={
                    "event_type": "agent_decision",
                    "agent": "IngestionAgent",
                    "action": "DATA_INGESTION_COMPLETE",
                    "total_records": len(df),
                    "execution_time_ms": exec_duration_ms,
                },
            )

            return IngestionSummary(
                total_records=len(df),
                file_path=str(path),
                format_type=format_type,
                ufs_covered=ufs,
                sectors_covered=sectors,
                periods_covered=periods,
                records=records,
                execution_time_ms=exec_duration_ms,
            )

        except Exception as exc:
            exec_duration_s = time.perf_counter() - start_time
            logger.exception(
                "IngestionAgent failed to load dataset",
                extra={
                    "event_type": "agent_decision",
                    "agent": "IngestionAgent",
                    "action": "DATA_INGESTION_ERROR",
                    "error": str(exc),
                },
            )
            raise
