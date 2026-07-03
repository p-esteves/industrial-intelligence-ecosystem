"""
Industrial Multi-Agent Ecosystem — Mock Data Generator.

Creates a realistic SQLite database with CAGED/IBGE employment data
and provides forecast scenario generators that simulate XGBoost/Prophet
model outputs for industrial payroll mass projections.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────

SETORES: list[str] = [
    "Indústria de Transformação",
    "Construção Civil",
    "Extrativa Mineral",
    "Serviços Industriais de Utilidade Pública",
    "Comércio",
    "Agropecuária",
]

UFS: list[str] = ["SP", "MG", "RJ", "RS", "PR", "BA", "SC", "GO", "PE", "CE"]

PERIODOS: list[str] = [
    f"{ano}-{mes:02d}"
    for ano in (2023, 2024)
    for mes in range(1, 13)
]


def init_mock_database() -> Engine:
    """
    Create a file-based SQLite database with realistic CAGED/IBGE data.
    """
    import os
    os.makedirs("data", exist_ok=True)
    engine: Engine = create_engine("sqlite:///data/mock_caged.db", echo=False)
    metadata_obj = MetaData()

    emprego_formal = Table(
        "emprego_formal",
        metadata_obj,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("uf", String(2), nullable=False),
        Column("setor", String(60), nullable=False),
        Column("mes_ano", String(7), nullable=False),
        Column("admissoes", Integer, nullable=False),
        Column("desligamentos", Integer, nullable=False),
        Column("saldo", Integer, nullable=False),
        Column("salario_medio", Float, nullable=False),
    )

    metadata_obj.create_all(engine)

    # Seed for reproducibility
    rng = random.Random(42)

    rows: list[dict[str, Any]] = []
    for uf in UFS:
        # Base values vary by state economic strength
        base_multiplier: float = {
            "SP": 3.0, "MG": 1.5, "RJ": 1.8, "RS": 1.2, "PR": 1.3,
            "BA": 0.9, "SC": 1.1, "GO": 0.8, "PE": 0.7, "CE": 0.6,
        }.get(uf, 1.0)

        for setor in SETORES:
            sector_base: int = {
                "Indústria de Transformação": 5000,
                "Construção Civil": 3000,
                "Extrativa Mineral": 800,
                "Serviços Industriais de Utilidade Pública": 600,
                "Comércio": 7000,
                "Agropecuária": 2000,
            }.get(setor, 1000)

            salary_base: float = {
                "Indústria de Transformação": 3200.0,
                "Construção Civil": 2400.0,
                "Extrativa Mineral": 5800.0,
                "Serviços Industriais de Utilidade Pública": 4500.0,
                "Comércio": 2100.0,
                "Agropecuária": 1800.0,
            }.get(setor, 2500.0)

            for periodo in PERIODOS:
                admissoes = int(
                    sector_base * base_multiplier * rng.uniform(0.7, 1.3)
                )
                desligamentos = int(
                    admissoes * rng.uniform(0.75, 1.15)
                )
                saldo = admissoes - desligamentos
                salario = round(salary_base * rng.uniform(0.9, 1.15), 2)

                rows.append({
                    "uf": uf,
                    "setor": setor,
                    "mes_ano": periodo,
                    "admissoes": admissoes,
                    "desligamentos": desligamentos,
                    "saldo": saldo,
                    "salario_medio": salario,
                })

    with engine.connect() as conn:
        conn.execute(emprego_formal.insert(), rows)
        conn.commit()

        count_result = conn.execute(text("SELECT COUNT(*) FROM emprego_formal"))
        total_rows: int = count_result.scalar() or 0

    logger.info(
        "Mock CAGED/IBGE database initialized",
        extra={"total_rows": total_rows, "states": len(UFS), "sectors": len(SETORES)},
    )

    return engine


def generate_forecast_data(setor: str, horizonte_meses: int = 6) -> dict[str, Any]:
    """
    Generate simulated forecast scenarios for industrial payroll mass.
    """
    rng = random.Random(hash(setor) + horizonte_meses)

    # Base projections per sector
    base_massa_salarial: float = {
        "Indústria de Transformação": 45_000_000.0,
        "Construção Civil": 28_000_000.0,
        "Extrativa Mineral": 12_000_000.0,
        "Serviços Industriais de Utilidade Pública": 8_500_000.0,
        "Comércio": 52_000_000.0,
        "Agropecuária": 15_000_000.0,
    }.get(setor, 20_000_000.0)

    base_empregados: int = {
        "Indústria de Transformação": 12_500,
        "Construção Civil": 9_800,
        "Extrativa Mineral": 2_100,
        "Serviços Industriais de Utilidade Pública": 1_900,
        "Comércio": 22_000,
        "Agropecuária": 7_500,
    }.get(setor, 5_000)

    def _build_scenario(
        growth_rate: float,
        label: str,
    ) -> dict[str, Any]:
        months: list[dict[str, Any]] = []
        current_massa = base_massa_salarial
        current_emp = base_empregados

        for m in range(1, horizonte_meses + 1):
            monthly_variation = growth_rate + rng.uniform(-0.005, 0.005)
            current_massa *= 1 + monthly_variation
            current_emp = int(current_emp * (1 + monthly_variation * 0.6))

            now = datetime.now()
            month_idx = (now.month + m - 1) % 12 + 1
            year = now.year + (now.month + m - 1) // 12

            months.append({
                "periodo": f"{year}-{month_idx:02d}",
                "massa_salarial_estimada": round(current_massa, 2),
                "empregados_estimados": current_emp,
                "salario_medio_estimado": round(current_massa / max(current_emp, 1), 2),
            })

        return {
            "cenario": label,
            "taxa_crescimento_mensal": f"{growth_rate * 100:.2f}%",
            "projecoes": months,
        }

    forecast: dict[str, Any] = {
        "setor": setor,
        "horizonte_meses": horizonte_meses,
        "data_geracao": datetime.now().isoformat(),
        "modelo": "XGBoost + Prophet (Ensemble Simulado)",
        "confianca_modelo": f"{rng.uniform(82, 96):.1f}%",
        "cenarios": {
            "pessimista": _build_scenario(-0.012, "Pessimista"),
            "base": _build_scenario(0.005, "Base"),
            "otimista": _build_scenario(0.018, "Otimista"),
        },
        "variaveis_macroeconomicas": {
            "selic_atual": "10.50%",
            "ipca_acumulado_12m": "4.23%",
            "pib_projecao_anual": "2.1%",
            "taxa_desemprego": "7.8%",
            "confianca_industria_fgv": 98.5,
            "cambio_usd_brl": 5.15,
        },
        "alertas": [
            "Setor sensível a variações cambiais acima de R$5.30/USD",
            "Sazonalidade histórica indica pico de admissões em Março e Setembro",
            f"Projeção assume manutenção da Selic em 10.50% para os próximos {horizonte_meses} meses",
        ],
    }

    logger.info(
        "Forecast data generated",
        extra={"setor": setor, "horizonte_meses": horizonte_meses},
    )

    return forecast
