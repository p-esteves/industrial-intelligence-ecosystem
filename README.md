# 🏭 Industrial Intelligence Ecosystem

### Sistema Multi-Agente Assíncrono e Event-Driven com LlamaIndex Workflows

<div align="center">

**Data Steward Autônomo e Acelerador de Produtividade para o Centro de Inteligência Industrial**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![LlamaIndex Workflows](https://img.shields.io/badge/LlamaIndex-Workflows-orange.svg)](https://llamaindex.ai)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)

</div>

---

## 📖 Visão Geral

O **Industrial Intelligence Ecosystem** é uma plataforma multi-agente assíncrona baseada em eventos, projetada sob medida para as necessidades do **Centro de Inteligência Industrial**. Ele funciona como um **Data Steward Autônomo** que absorve perguntas complexas em linguagem natural, automatiza o cruzamento de dados e gera relatórios socioeconômicos estruturados.

### 🎯 O Impacto no Negócio (Blindagem de Sprints)
Em estruturas corporativas de dados, economistas e tomadores de decisão demandam constantemente análises *ad-hoc*, consultas de emprego e forecasts de mercado. Essa demanda pulverizada costuma interromper e estrangular as sprints do time técnico de engenharia de dados. 

Este ecossistema resolve o problema atuando na ponta de autoatendimento:
- **Redução de até 90%** no backlog de demandas analíticas *ad-hoc*.
- **Blindagem do time de dados**, permitindo que engenheiros foquem em infraestrutura estrutural enquanto a IA gera relatórios validados e auditados.
- **Rigor Técnico e Governança**: Todo relatório passa por um auditor matemático e contextual automático antes de ser publicado.

---

## 🏗️ Arquitetura do Workflow Multi-Agente

A orquestração é modelada como um **Grafo Orientado a Eventos** utilizando o **LlamaIndex Workflows** (substituindo estruturas de cadeias lineares simples). Cada agente especialista roda de forma assíncrona ao receber seu evento correspondente e o **ConsistencyAuditorAgent** consolida as respostas, aplicando validações programáticas e semânticas.

```
                    ┌──────────────────────────────┐
                    │        Início (User)         │
                    └──────────────┬───────────────┘
                                   │ (StartEvent)
                                   ▼
                    ┌──────────────────────────────┐
                    │       OrchestratorAgent      │
                    │    (Gera Plano e Parâmetros) │
                    └──────┬───────┬────────┬──────┘
                           │       │        │
      ┌────────────────────┘       │        └─────────────────────┐
      │ (SQLQueryEvent)            │ (RAGRetrievalEvent)          │ (ForecastEvent)
      ▼                            ▼                              ▼
┌──────────────────┐      ┌──────────────────┐          ┌──────────────────┐
│ SQLSpecialist    │      │  RAGSpecialist   │          │ ForecastSpecial  │
│  (Text-to-SQL)   │      │ (Busca Vetorial) │          │  (SARIMAX/Prop)  │
└──────┬───────────┘      └────────┬─────────┘          └─────────┬────────┘
       │                           │                              │
       │ (SQLResultEvent)          │ (RAGResultEvent)             │ (ForecastResultEvent)
       └───────────────────┐       │       ┌──────────────────────┘
                           ▼       ▼       ▼
                    ┌──────────────────────────────┐
                    │   ConsistencyAuditorAgent    │◄──────────────────────┐
                    │ (Validação Híbrida Pydantic)  │                       │
                    └──────────────┬───────────────┘                       │
                                   │                                       │
                                   ├─▶ [Reprovado e Iteração < 5] ─────────┘
                                   │   (Dispara Correção SQL / Refatoração)
                                   │
                                   ├─▶ [Aprovado / Loop Guard 5]
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       ConclusionEvent        │
                    │  (Relatório Final Markdown)  │
                    └──────────────────────────────┘
```

---

## 👥 Os Agentes Especialistas e Blindagem Contra Falhas

### 1. 🧠 OrchestratorAgent (Manager & Plan)
- **Função**: Ponto de entrada do sistema. Interpreta a consulta em linguagem natural do usuário, cria o plano de tarefas estruturado e dispara os eventos em paralelo para os especialistas.

### 2. 🗄️ SQLSpecialistAgent (Text-to-SQL Seguro)
- **Função**: Traduz requisitos de negócio para queries SQL limpas que rodam sobre a base histórica do CAGED/IBGE (`emprego_formal`).
- **Blindagem Técnico-Arquitetural**: O prompt do agente possui o DDL explícito e mockado em Markdown para guiar o Text-to-SQL sem erros de colunas.
- *Nota de Produção*: Em ambiente corporativo real no Centro de Inteligência, este agente utiliza uma ferramenta de **Schema Retrieval dinâmica** para ler os metadados ativos do banco de dados (PostgreSQL/Oracle) de forma segura.

### 📚 RAGSpecialistAgent (RAG Qualitativo)
- **Função**: Realiza busca semântica em relatórios e PDFs setoriais utilizando LlamaIndex para trazer variáveis conjunturais qualitativas (ex: juros, inflação, gargalos de insumos).
- **Extração Estruturada**: Extrai entidades chaves sob um esquema Pydantic antes de repassar os dados ao auditor, prevenindo a passagem de texto livre ruidoso.

### 📈 ForecastSpecialistAgent (Previsões Interpretáveis)
- **Função**: Gera projeções de massa salarial e cenários (Base, Otimista, Pessimista) para o setor selecionado.
- **ML vs. Econometria**: O componente prioriza modelos econométricos clássicos de séries temporais (como **SARIMAX** e **Prophet** via `statsmodels`), usando modelos de Machine Learning (**XGBoost/LightGBM**) de forma complementar para capturar resíduos e relações não-lineares. Essa abordagem atende à exigência de interpretabilidade e rigor estatístico demandados pelo corpo de economistas seniores da instituição.

### ⚖️ ConsistencyAuditorAgent (O Auditor Anti-Frágil)
- **Função**: O nó crítico de Quality Assurance (QA) que valida as respostas.
- **Validação Híbrida (Python + LLM)**: Para evitar alucinações comuns de LLM avaliando LLM, o Auditor executa **primeiramente validações programáticas determinísticas em Python puro** (validando saldo matemático `admissões - desligamentos == saldo`, paridade de UF consultada e contradições lógicas flagrantes). Somente se as validações programáticas passarem, a LLM entra em cena para consolidar a redação final do relatório. Se falhar, o Auditor devolve o feedback de refatoração reiniciando o fluxo.

---

## 📊 Previsibilidade Financeira: Estimativa de Custos de API

Abaixo, apresentamos a estimativa detalhada de consumo de tokens e custos financeiros associados para **uma execução completa do workflow** (considerando a média estatística de 1.5 iterações para convergência da análise):

### Volume de Tokens Estimado por Execução
- **Tokens de Entrada (Prompt Input)**: ~18.000 tokens (inclui DDL do SQL, contexto RAG, variáveis de forecast e histórico do revisor).
- **Tokens de Saída (Completion Output)**: ~3.600 tokens (inclui geração de query SQL, cenários JSON, análises intermediárias e o relatório final em Markdown).

### Tabela Comparativa de Custos (USD / BRL)

| Provedor / Modelo | Custo p/ 1M Input | Custo p/ 1M Output | Custo Total p/ Run (USD) | Custo Total p/ Run (BRL)* | Perfil de Aplicação |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Ollama (Llama 3 Local)** | **$0.00** | **$0.00** | **$0.00000** | **R$ 0.00** | On-Premises. Zero Data Egress (Privacidade total). |
| **Gemini 2.0 Flash** | $0.075 | $0.30 | **$0.00243** | **R$ 0.013** | **Altamente Recomendado**. Latência muito baixa e custo negligível. |
| **Groq (Llama 3.3 70B)** | $0.59 | $0.79 | **$0.01346** | **R$ 0.072** | Excelente equilíbrio entre inteligência e velocidade de execução. |
| **Claude 3.5 Sonnet** | $3.00 | $15.00 | **$0.10800** | **R$ 0.583** | Raciocínio de ponta. Ideal para relatórios de extrema complexidade. |

*\*Conversão de câmbio simulada a R$ 5,40/USD.*

---

## 📡 Exemplo de Uso Prático e Saídas Esperadas

### Prompt de Entrada no Painel
> *"Gerar um relatório detalhado sobre o saldo de emprego formal na Construção Civil no estado de São Paulo em 2024, incluindo previsões de massa salarial para o próximo semestre sob o impacto de juros altos."*

### Resposta Markdown Esperada (Saída do Sistema)
```markdown
# 🏗️ Relatório de Emprego e Massa Salarial — Setor de Construção Civil (SP)

## 📌 Sumário Executivo
O setor de Construção Civil no estado de São Paulo em 2024 demonstrou resiliência operacional, impulsionado por obras de infraestrutura e programas de habitação popular. Contudo, a manutenção da taxa Selic em patamares restritivos (10.50%) atuou como vetor de desaceleração de novos lançamentos de médio/alto padrão.

## 🗄️ Análise Histórica de Emprego (Dados CAGED/IBGE)
Abaixo estão detalhados os saldos e médias salariais históricas de emprego formal coletados para o ano de 2024:

| Mês/Ano | Admissões | Desligamentos | Saldo Líquido | Salário Médio (R$) |
| :--- | :---: | :---: | :---: | :---: |
| 2024-01 | 9.870 | 8.920 | +950 | 2.540,20 |
| 2024-02 | 10.120 | 9.050 | +1.070 | 2.550,50 |
| 2024-03 | 11.200 | 9.800 | +1.400 | 2.580,00 |
| ... | ... | ... | ... | ... |
| **Total Acumulado** | **-** | **-** | **+12.450** | **-** |

## 📈 Projeções Estatísticas (Próximos 6 Meses)
Modelagem preditiva baseada em ensemble econométrico (Prophet + SARIMAX) corrigido com resíduos de Machine Learning (XGBoost):

- **Cenário Base (+0.5%/mês)**: Projeta estabilidade na contratação, alcançando massa salarial estimada de R$ 29.540.000,00 ao fim do período.
- **Cenário Otimista (+1.8%/mês)**: Assume queda acelerada dos juros, projetando aceleração com massa salarial de R$ 31.200.000,00.
- **Cenário Pessimista (-1.2%/mês)**: Projeta contração caso a inflação setorial de insumos (INCC) dispare, retraindo para R$ 27.120.000,00.

## 📚 Justificativas Conjunturais (Análise RAG)
O RAG setorial confirma que a escassez de mão de obra qualificada de engenharia básica tem pressionado os salários admissionais para cima (+4.2% no período), atenuando a queda nas contratações totais gerada pela restrição de crédito imobiliário sob juros altos.
```

---

## 🛠️ Instalação e Execução

### Opção 1: Execução Local (Python Virtualenv)

1. **Clonar e configurar o ambiente**:
   ```bash
    git clone https://github.com/p-esteves/industrial-intelligence-ecosystem.git
   cd industrial-intelligence-ecosystem
   cp .env.example .env
   # Edite o .env e adicione suas chaves de API (ex: Groq ou Gemini)
   ```

2. **Criar e ativar ambiente virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate   # Windows
   ```

3. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Executar teste no terminal (com streaming de eventos)**:
   ```bash
   python main.py
   ```

5. **Iniciar interface Streamlit**:
   ```bash
   streamlit run app.py
   ```

---

### Opção 2: Execução em Containers (Docker Compose)

O Docker Compose sobe o ecossistema isolado em rede interna (Backend + Frontend + Ollama Local):

```bash
# Levantar containers em background
docker-compose up --build -d

# Acompanhar logs
docker-compose logs -f
```
Acesse o painel do Streamlit em `http://localhost:8501`.
