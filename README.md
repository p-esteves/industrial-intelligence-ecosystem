# 🏭 Industrial Intelligence Ecosystem

### Ecossistema Multi-Agente Industrial Production-Ready (Azure + Kubernetes + Docker)

<div align="center">

[![CI/CD Pipeline](https://github.com/p-esteves/industrial-intelligence-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/p-esteves/industrial-intelligence-ecosystem/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(Local)-black.svg)](https://ollama.ai)
[![FAISS](https://img.shields.io/badge/VectorDB-FAISS-0055FF.svg)](https://github.com/facebookresearch/faiss)
[![Prometheus](https://img.shields.io/badge/Observability-Prometheus-E6522C.svg)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Dashboard-Grafana-F46800.svg)](https://grafana.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)

</div>

---

## 📖 Visão Geral

O **Industrial Intelligence Ecosystem** é uma plataforma multi-agente containerizada para monitoramento, análise estatística e geração de inteligência sobre indicadores da indústria brasileira (como dados do CAGED/IBGE). 

Projetado para ambientes de alta disponibilidade compatíveis com **Azure AKS (Azure Kubernetes Service)**, **Docker Compose** e **Arquitetura de Microserviços**, o sistema executa um fluxo autônomo end-to-end de 3 agentes especializados com observabilidade completa via **Prometheus + Grafana** e suporte a **LLM 100% local via Ollama** com **Graceful Degradation (Modo Resiliente / Fallback)**.

---

## ⚡ Quick Start (Execução em 1 Comando)

O sistema foi preparado para rodar do zero sem qualquer configuração manual:

```bash
# 1. Clonar o repositório
git clone https://github.com/p-esteves/industrial-intelligence-ecosystem.git
cd industrial-intelligence-ecosystem

# 2. Subir todos os serviços com um único comando
docker-compose up --build -d
```

### 🌐 Endpoints e Interfaces Disponíveis

| Serviço / Interface | URL Local | Descrição |
| :--- | :--- | :--- |
| **Documentação API (Swagger UI)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentação interativa FastAPI |
| **Pipeline Trigger (POST)** | `http://localhost:8000/pipeline` | Dispara execução completa dos agentes |
| **Health Check (Kubernetes)** | `http://localhost:8000/health` | Health probe (liveness/readiness) |
| **Status dos Agentes (GET)** | `http://localhost:8000/status` | Estado operacional em tempo real |
| **Métricas Prometheus (GET)** | `http://localhost:8000/metrics` | Exporte de métricas operacionais |
| **Grafana Dashboard** | [http://localhost:3000](http://localhost:3000) | Dashboard pré-configurado (User: `admin` / Pass: `admin`) |
| **Prometheus Scraper** | [http://localhost:9090](http://localhost:9090) | Servidor de métricas Prometheus |
| **Interface Streamlit** | [http://localhost:8501](http://localhost:8501) | Painel interativo de inteligência |

---

## 🏗️ Arquitetura do Sistema Multi-Agente

Abaixo está o diagrama em **Mermaid** representando o fluxo completo entre o cliente REST, a API FastAPI, os Agentes Independentes, a busca vetorial FAISS RAG, o LLM local via Ollama e a stack de observabilidade com Prometheus e Grafana:

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        CLI[HTTP Client / Curl]
        STUI[Streamlit UI :8501]
    end

    subgraph API ["FastAPI Gateway :8000"]
        POSTP["POST /pipeline"]
        GETH["GET /health"]
        GETS["GET /status"]
        GETM["GET /metrics"]
    end

    subgraph Pipeline ["Multi-Agent Pipeline"]
        A1["Agente 1: Ingestão\n(Leitura CSV/Parquet)"]
        A2["Agente 2: Análise Estatística\n(Detecção Z-Score & IQR)"]
        A3["Agente 3: Relatório Executivo\n(Síntese LLM + RAG)"]
        RAG["Módulo RAG\n(FAISS Vector Index)"]
    end

    subgraph LocalLLM ["Local LLM Service :11434"]
        OLLAMA["Ollama Container\n(phi3:mini / llama3)"]
        FALLBACK["Deterministic Fallback\n(Graceful Degradation)"]
    end

    subgraph Observability ["Observability Stack"]
        PROM["Prometheus Server :9090"]
        GRAF["Grafana Dashboard :3000"]
    end

    CLI -->|HTTP Payload| POSTP
    STUI -->|HTTP Payload| POSTP

    POSTP --> A1
    A1 -->|Summary & Records| A2
    A2 -->|Anomalies Identified| A3
    RAG -->|Domain Context| A3

    A3 -->|Attempt LLM Call| OLLAMA
    OLLAMA -.->|Timeout / Error| FALLBACK
    FALLBACK -->|Resilient Executive Report| A3
    OLLAMA -->|Natural Language Insights| A3

    GETM -->|Scrape Metrics| PROM
    PROM -->|Datasource| GRAF
```

---

## 👥 Agentes Especialistas e Responsabilidades

### 1. 📥 Agente 1: Ingestão (`agents/ingestion_agent.py`)
- **Função**: Carrega, valida e converte dados tabulares industriais dos formatos **CSV**, **Parquet** e **SQLite**.
- **Validação**: Valida esquemas de colunas obrigatórias (`uf`, `setor`, `mes_ano`, `admissoes`, `desligamentos`, `saldo`, `massa_salarial`, `salario_medio`).
- **Observabilidade**: Emite logs estruturados JSON e registra a métrica `industrial_agent_execution_duration_seconds{agent="IngestionAgent"}`.

### 2. 📊 Agente 2: Análise Estatística (`agents/analysis_agent.py`)
- **Função**: Executa algoritmos estatísticos de detecção de anomalias baseados em **Z-Score** ($Z = \frac{X - \mu}{\sigma}$) e **Interquartile Range (IQR)** sobre a massa salarial e movimentação de postos por estado (UF) e setor.
- **Saída**: Retorna um sumário de anomalias classificadas por severidade (`CRITICAL`, `HIGH`, `MEDIUM`) identificando quedas abruptas de massa salarial e surtos imprevistos de demissões.
- **Métricas**: Incrementa o contador Prometheus `industrial_anomalies_detected_total{sector=..., severity=...}`.

### 3. 📝 Agente 3: Relatório Executivo & Fallback (`agents/report_agent.py`)
- **Função**: Sintetiza relatórios em linguagem natural integrando os desvios encontrados pelo Agente 2 com o contexto qualitativo recuperado via RAG.
- **Integração LLM**: Conecta ao serviço local Ollama (`phi3:mini` ou `llama3`).
- **Graceful Degradation (Modo Resiliente)**: Caso o container do Ollama esteja indisponível, reiniciando ou indisponível por timeout, o agente aciona automaticamente um gerador de relatório determinístico baseado em regras corporativas sem derrubar a API (retornando HTTP 200) e incrementando `industrial_llm_fallback_total`.

### 🔍 Módulo RAG Vetorial (`agents/rag_specialist.py` + `core/tools.py`)
- **Função**: Indexa manuais técnicos e boletins industriais localizados em `data/sample/docs/` utilizando a biblioteca **FAISS** e **LlamaIndex**, alimentando o Agente 3 com diretrizes setoriais pertinentes.

---

## 🎯 Caso de Uso Industrial Concreto

O repositório acompanha um conjunto de dados industriais sintéticos realistas simulando o **CAGED (Cadastro Geral de Empregados e Desempregados)** e indicadores do IBGE localizados na pasta `/data/sample/`:

- `data/sample/caged_industrial.csv`: Dados de movimentação de empregos formais e massa salarial.
- `data/sample/caged_industrial.parquet`: Versão em formato Parquet para alta performance de leitura.
- `data/sample/docs/manual_diretrizes_industriais.txt`: Manual de análise conjuntural industrial para consulta semântica via RAG.

### Anomalias Injetadas no Dataset Demonstrativo:
1. **Extrativa Mineral (Minas Gerais - 2024-09)**: Queda brusca de -43.2% na massa salarial devido a paralisações temporárias operacionais ($Z = -3.10$).
2. **Indústria de Transformação (São Paulo - 2024-11)**: Onda severa de desligamentos com saldo negativo de -8.500 postos ($Z = -2.85$).

---

## 📈 Métricas e Observabilidade

O ecossistema implementa observabilidade nativa no padrão **Prometheus**:

### Métricas Expostas (`GET /metrics`):
- `industrial_pipeline_executions_total{status="success|error"}`: Total de execuções do pipeline.
- `industrial_pipeline_duration_seconds`: Histograma de latência do pipeline completo.
- `industrial_anomalies_detected_total{sector, severity}`: Total de anomalias estatísticas identificadas.
- `industrial_agent_execution_duration_seconds{agent}`: Histograma de latência por agente individual.
- `industrial_llm_fallback_total{reason}`: Contador de acionamento do modo de degradação graciosa.
- `industrial_agent_status{agent}`: Gauge do estado operacional dos agentes.

### Dashboard Grafana Pré-Configurado
Ao subir o `docker-compose up`, o Grafana é autoprovisionado na porta `3000` com o datasource Prometheus e o dashboard **Industrial Multi-Agent Ecosystem** pré-instalado.

---

## 🛠️ Decisões Técnicas e Justificativas

| Tecnologia | Decisão Técnica & Rationale |
| :--- | :--- |
| **FastAPI** | Framework Python assíncrono de altíssimo desempenho, nativamente compatível com Pydantic v2 e documentação Swagger automática. |
| **Ollama** | Servidor de inferência LLM local e open-source. Permite rodar modelos como Phi-3 ou Llama 3 on-premises com zero custo e total privacidade de dados. |
| **FAISS** | Biblioteca de busca vetorial densa desenvolvida pelo Meta AI. Oferece buscas semânticas ultra-rápidas para RAG industrial sem dependência de serviços pagos. |
| **Prometheus + Grafana** | Padrão da indústria para monitoramento de microserviços e aplicações cloud-native em clusters Kubernetes. |
| **Docker Multi-Stage Build** | Garante imagens enxutas, separando a camada de compilação de dependências da imagem final de execução em produção (Python 3.11-slim). |

---

## 🧪 Testes e CI/CD Pipeline

O repositório possui cobertura completa de testes unitários e de integração com `pytest`:

```bash
# Executar todos os testes
pytest -v

# Verificar linting e formatação
ruff check .
```

### GitHub Actions Workflow (`.github/workflows/ci.yml`)
Cada `git push` ou `pull_request` dispara automaticamente o workflow de CI/CD que executa:
1. Setup do ambiente Python 3.11.
2. Instalação e validação de dependências.
3. Linting de código com **Ruff**.
4. Execução da suíte completa de testes unitários e de integração (**pytest**).
5. Validação da construção da imagem Docker (**docker build** & `docker compose config`).

---

## 📄 Licença

Desenvolvido como projeto de demonstração avançada em Gen AI, Engenharia de Dados e Engenharia de Software Cloud-Native. Licença MIT.
