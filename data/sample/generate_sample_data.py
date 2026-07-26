"""
Industrial Multi-Agent Ecosystem — Sample Industrial Dataset Generator.

Generates realistic CAGED/IBGE industrial dataset files (CSV and Parquet)
with injected statistical anomalies for testing Agente 1 (Ingestão) and
Agente 2 (Análise).
"""

import os
import random
import pandas as pd

def generate_sample_data():
    os.makedirs("data/sample/docs", exist_ok=True)
    
    rng = random.Random(2026)
    
    ufs = ["SP", "MG", "RJ", "RS", "PR", "BA", "SC"]
    setores = [
        "Indústria de Transformação",
        "Extrativa Mineral",
        "Construção Civil",
        "Serviços Industriais de Utilidade Pública"
    ]
    periodos = [f"{ano}-{mes:02d}" for ano in [2023, 2024] for mes in range(1, 13)]
    
    records = []
    
    for uf in ufs:
        uf_mult = {"SP": 3.0, "MG": 1.6, "RJ": 1.8, "RS": 1.2, "PR": 1.3, "BA": 0.9, "SC": 1.1}.get(uf, 1.0)
        
        for setor in setores:
            sector_base = {
                "Indústria de Transformação": 6000,
                "Extrativa Mineral": 1200,
                "Construção Civil": 3500,
                "Serviços Industriais de Utilidade Pública": 800
            }.get(setor, 2000)
            
            salary_base = {
                "Indústria de Transformação": 3400.0,
                "Extrativa Mineral": 6200.0,
                "Construção Civil": 2600.0,
                "Serviços Industriais de Utilidade Pública": 4800.0
            }.get(setor, 3000.0)
            
            for periodo in periodos:
                admissoes = int(sector_base * uf_mult * rng.uniform(0.85, 1.15))
                desligamentos = int(admissoes * rng.uniform(0.80, 1.10))
                
                # Default normal calculations
                saldo = admissoes - desligamentos
                salario_medio = round(salary_base * rng.uniform(0.95, 1.08), 2)
                massa_salarial = round((admissoes + desligamentos) * 0.5 * salario_medio, 2)
                
                # Inject explicit statistical anomalies
                if uf == "MG" and setor == "Extrativa Mineral" and periodo == "2024-09":
                    massa_salarial = round(massa_salarial * 0.45, 2)  # -55% drop
                    salario_medio = round(salario_medio * 0.60, 2)
                elif uf == "SP" and setor == "Indústria de Transformação" and periodo == "2024-11":
                    desligamentos = int(admissoes * 2.8)  # Sudden severe layoff wave
                    saldo = admissoes - desligamentos
                    massa_salarial = round(massa_salarial * 0.52, 2)
                elif uf == "RJ" and setor == "Construção Civil" and periodo == "2024-08":
                    desligamentos = int(admissoes * 2.2)
                    saldo = admissoes - desligamentos
                
                records.append({
                    "uf": uf,
                    "setor": setor,
                    "mes_ano": periodo,
                    "admissoes": admissoes,
                    "desligamentos": desligamentos,
                    "saldo": saldo,
                    "salario_medio": salario_medio,
                    "massa_salarial": massa_salarial
                })
                
    df = pd.DataFrame(records)
    
    csv_path = "data/sample/caged_industrial.csv"
    parquet_path = "data/sample/caged_industrial.parquet"
    
    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_parquet(parquet_path, index=False)
    
    print(f"Generated {len(df)} records.")
    print(f"Saved CSV to: {csv_path}")
    print(f"Saved Parquet to: {parquet_path}")

if __name__ == "__main__":
    generate_sample_data()
