from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure root of project is in python path
sys.path.append(str(Path(__file__).resolve().parent))

import nest_asyncio
try:
    nest_asyncio.apply()
except ValueError:
    pass  # Fix for Streamlit Cloud uvloop crash

from config import get_settings
from workflow.workflow import IndustrialMultiAgentWorkflow
from events import AgentThoughtEvent

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get settings
settings = get_settings()

# --- Page Configuration ---
st.set_page_config(
    page_title="Centro de Inteligência Industrial - Sistema Multi-Agente (LlamaIndex Workflows)",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium Custom Styling (CSS) ---
st.markdown(
    """
    <style>
    /* Main Background Gradient */
    .stApp {
        background: linear-gradient(135deg, #09090e 0%, #11111f 50%, #0c152b 100%);
        color: #e2e8f0;
    }

    /* Sidebar Gradient & Borders */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d16 0%, #05050a 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }

    /* Titles and Headers */
    .brand-title {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    
    .brand-subtitle {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-bottom: 1.5rem;
    }

    /* Custom Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }
    
    .badge-provider {
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border-color: rgba(99, 102, 241, 0.3);
    }

    .badge-status {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border-color: rgba(16, 185, 129, 0.3);
    }

    /* Expander / Step Styling */
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(99, 102, 241, 0.1) !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }
    
    /* Report Container Custom Styling */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
        padding: 1.5rem 2.5rem !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3) !important;
        margin-top: 1.5rem !important;
    }

    /* Header bar */
    .header-bar {
        border-bottom: 2px solid rgba(99, 102, 241, 0.1);
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Content ---
with st.sidebar:
    st.markdown('<div class="brand-title">🏭 Centro de Inteligência</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">MAS - LlamaIndex Workflows</div>', unsafe_allow_html=True)
    
    # Provedor LLM Badge
    llm_provider = settings.llm_provider.upper()
    llm_model = getattr(settings, f"{settings.llm_provider}_model", "Standard Model")
    
    st.markdown(f'<span class="badge badge-provider">🧠 Provider: {llm_provider}</span>', unsafe_allow_html=True)
    st.caption(f"Model: `{llm_model}`")
    
    st.divider()
    
    # Preset Macro Queries
    st.subheader("💡 Perguntas Sugeridas")
    queries = [
        "Qual o saldo de emprego formal em SP no setor de Construção Civil em 2024 e qual a projeção para os próximos 6 meses?",
        "Faça uma análise de cenários de massa salarial na Indústria de Transformação comparando os cenários macroeconômicos e o impacto da Selic",
        "Qual o cenário de massa salarial para o setor de Extrativa Mineral sob taxas de câmbio instáveis?",
    ]
    
    for i, q in enumerate(queries):
        if st.button(q, key=f"preset_{i}", width="stretch"):
            st.session_state.user_query = q
            st.rerun()

    st.divider()
    
    # Restart Session
    if st.button("🔄 Reiniciar Fluxo", width="stretch"):
        if "user_query" in st.session_state:
            del st.session_state.user_query
        if "workflow_results" in st.session_state:
            del st.session_state.workflow_results
        st.rerun()


# --- Main Dashboard Layout ---

st.markdown(
    """
    <div class="header-bar">
        <h1>📊 Sistema Multi-Agente (LlamaIndex Workflows)</h1>
        <p style="color: #94a3b8; font-size: 1.1rem; margin-top:-0.5rem;">
            Colaboração orientada a eventos, raciocínio em etapas e auto-correção editorial via LlamaIndex Workflows.
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Input Box
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

user_input = st.text_area(
    "Digite sua consulta analítica macroeconômica:", 
    value=st.session_state.user_query,
    placeholder="Ex: Qual o saldo de emprego em SP no setor de Construção Civil e as projeções de massa salarial?",
    height=100
)

col_run, col_clear = st.columns([1, 8])

run_workflow = False
with col_run:
    if st.button("🚀 Executar Workflow", type="primary", width="stretch"):
        st.session_state.user_query = user_input
        run_workflow = True

with col_clear:
    if st.button("Limpar", width="stretch"):
        st.session_state.user_query = ""
        if "workflow_results" in st.session_state:
            del st.session_state.workflow_results
        st.rerun()


# Helper to render individual thought event
def render_agent_thought(event: AgentThoughtEvent):
    agent_icon = "🕵️‍♂️"
    if "Data" in event.agent:
        agent_icon = "🗄️"
    elif "Statistical" in event.agent:
        agent_icon = "📈"
    elif "Economic" in event.agent:
        agent_icon = "📚"
    elif "Chief" in event.agent:
        agent_icon = "⚖️"
        
    title = f"{agent_icon} {event.agent} — {event.action}"
    
    with st.expander(title, expanded=True):
        st.markdown(f"**Raciocínio:**\n{event.thought}")
        
        output = event.output
        if output:
            if output.strip().startswith("[") or output.strip().startswith("{"):
                try:
                    js_data = json.loads(output)
                    with st.expander("🔍 Visualizar Dados Brutos (JSON)", expanded=False):
                        st.json(js_data, expanded=False)
                except Exception:
                    st.code(output, language="json")
            else:
                with st.expander("🔍 Ver Detalhes", expanded=False):
                    st.code(output, language="markdown")


# --- Execution Phase ---
if run_workflow and st.session_state.user_query.strip():
    # Clear thoughts on new run
    st.session_state.thoughts = []
    
    st.subheader("🌲 Árvore de Pensamento do Workflow (Thought Tree)")
    status_placeholder = st.empty()
    tree_container = st.container()
    
    async def run_and_stream():
        wf = IndustrialMultiAgentWorkflow(timeout=120.0, verbose=True)
        handler = wf.run(query=st.session_state.user_query)
        
        async for event in handler.stream_events():
            if isinstance(event, AgentThoughtEvent):
                # Update status
                status_placeholder.info(f"✓ Agent **{event.agent}** completed execution step...")
                # Save to session state
                st.session_state.thoughts.append(event)
                # Render in container
                with tree_container:
                    render_agent_thought(event)
                    
        result = await handler
        return result

    try:
        with st.status("🔗 Conectando ao Workflow LlamaIndex...", expanded=True) as status:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(run_and_stream())
            status.update(label="✅ Workflow LlamaIndex finalizou a execução com sucesso!", state="complete")
            status_placeholder.empty()
            
        st.session_state.workflow_results = result
        st.rerun()  # Rerun to clean up status widgets and render results cleanly
        
    except Exception as e:
        st.error(f"Ocorreu um erro ao executar o workflow dos agentes: {e}")
        logger.exception("Workflow execution error")


# --- Persistent Thought Tree Rendering ---
if "thoughts" in st.session_state and st.session_state.thoughts and not (run_workflow and st.session_state.user_query.strip()):
    st.subheader("🌲 Árvore de Pensamento do Workflow (Thought Tree)")
    for thought in st.session_state.thoughts:
        render_agent_thought(thought)


# --- Results Section ---
if "workflow_results" in st.session_state:
    results = st.session_state.workflow_results
    
    st.divider()
    st.subheader("📄 Relatório Técnico Final de Análise")
    
    verdict = results.get("verdict", {"approved": False, "feedback": ""})
    approved = verdict.get("approved", False)
    
    # Feedback notification
    if approved:
        st.success(
            f"🎉 O Chief Editor (ConsistencyAuditorAgent) validou e APROVOU o relatório final. "
            f"O sistema convergiu em {results.get('iteration', 1)} ciclo(s) de auto-correção e consistência automática."
        )
    else:
        st.warning(
            f"⚠️ O Chief Editor Revisor REJEITOU o rascunho anterior. "
            f"O fluxo foi encerrado pela trava de segurança (limite de 5 iterações atingido).\n\n"
            f"**Feedback do Revisor:** {verdict.get('feedback')}"
        )
        
    # Render final report Markdown inside styled block
    report_markdown = results.get("report", "*Nenhum relatório foi gerado.*")
    
    with st.container(border=True):
        st.markdown(report_markdown)
    
    # Download Button
    st.download_button(
        label="📥 Baixar Relatório (Markdown)",
        data=report_markdown,
        file_name="relatorio_analise_industrial.md",
        mime="text/markdown",
        width="stretch"
    )
    
    # Section to display SQL metrics or Forecast plots below the report
    st.divider()
    st.subheader("🔍 Dados Técnicos Coletados no Fluxo")
    
    tab_sql, tab_forecast = st.tabs(["🗄️ Dados Históricos (SQL)", "📈 Cenários Macro (Forecast)"])
    
    with tab_sql:
        sql_data = results.get("sql_data", "")
        if sql_data and (sql_data.startswith("[") or sql_data.strip().startswith("{")):
            try:
                # SQL tool payload contains status, records, columns, etc.
                sql_payload = json.loads(sql_data)
                records = sql_payload.get("records", [])
                if records:
                    df_sql = pd.DataFrame(records)
                    st.dataframe(df_sql, width="stretch")
                    # Add Download CSV button
                    csv = df_sql.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Dados Históricos (CSV)",
                        data=csv,
                        file_name="dados_historicos_emprego.csv",
                        mime="text/csv",
                        width="stretch"
                    )
                else:
                    st.info("Nenhum registro encontrado para a consulta.")
            except Exception:
                st.code(sql_data, language="json")
        else:
            st.info("Nenhum dado SQL bruto carregado ou formato inválido.")
            
    with tab_forecast:
        forecast_data = results.get("forecast_data", "")
        if forecast_data:
            try:
                # Direct JSON load of the Pydantic structured output
                forecast_dict = json.loads(forecast_data)
                
                # Render parameters
                if "variaveis_macroeconomicas" in forecast_dict and forecast_dict["variaveis_macroeconomicas"]:
                    st.subheader("📋 Variáveis Macroeconômicas de Contorno")
                    st.json(forecast_dict["variaveis_macroeconomicas"], expanded=False)
                
                # Line chart
                scenarios_df = {}
                periods = []
                projections_list = []
                
                for scenario_name, scenario_info in forecast_dict.get("cenarios", {}).items():
                    proj = scenario_info.get("projecoes", [])
                    if proj:
                        if not periods:
                            periods = [p["periodo"] for p in proj]
                        scenarios_df[scenario_info["cenario"]] = [p["massa_salarial_estimada"] for p in proj]
                        
                        # Add projections to table format
                        for p in proj:
                            projections_list.append({
                                "Cenário": scenario_info.get("cenario", scenario_name.capitalize()),
                                "Período": p["periodo"],
                                "Massa Salarial Estimada (R$)": p["massa_salarial_estimada"],
                                "Empregados Estimados": p.get("empregados_estimados", 0),
                                "Salário Médio Estimado (R$)": p.get("salario_medio_estimado", 0.0)
                            })
                
                if periods and scenarios_df:
                    chart_df = pd.DataFrame(scenarios_df, index=periods)
                    st.subheader("📈 Projeções de Massa Salarial (Gráfico)")
                    st.line_chart(chart_df, height=300)
                    
                if projections_list:
                    df_proj = pd.DataFrame(projections_list)
                    st.subheader("📋 Projeções Detalhadas (Tabela)")
                    st.dataframe(df_proj, width="stretch")
                    # Add Download CSV button
                    csv_proj = df_proj.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Projeções (CSV)",
                        data=csv_proj,
                        file_name="projecoes_massa_salarial.csv",
                        mime="text/csv",
                        width="stretch"
                    )
            except Exception as exc:
                st.error(f"Erro ao processar as projeções estatísticas: {exc}")
                st.code(forecast_data, language="json")
        else:
            st.info("Nenhuma projeção estatística bruta carregada.")
