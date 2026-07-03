from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv

from config import get_settings
from workflow import IndustrialMultiAgentWorkflow
from events import AgentThoughtEvent, OrchestratorThoughtEvent

# Setup terminal logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


async def run_multiagent_system():
    settings = get_settings()
    logger.info(f"=== Centro de Inteligência Industrial ===")
    logger.info(f"Provedor LLM ativo: {settings.llm_provider.upper()}")
    
    # Initialize the Workflow
    workflow = IndustrialMultiAgentWorkflow(timeout=180.0, verbose=False)
    
    # Query test case mimicking Observatory demand
    query = (
        "Gerar um Relatório sobre impacto do setor de Construção Civil "
        "com dados históricos de emprego em SP e forecast para o próximo semestre."
    )
    
    logger.info(f"Submetendo Consulta: '{query}'\n")
    logger.info("=== Streaming dos Eventos de Raciocínio (Thought Tree) ===")
    
    # Execute the workflow with event streaming
    handler = workflow.run(query=query)
    
    # Stream and display thought events in real time
    async for event in handler.stream_events():
        if isinstance(event, OrchestratorThoughtEvent):
            print(f"\n[ORCHESTRATOR PLAN] {event.message}")
            for sub in event.subtasks:
                print(f"  - {sub}")
        elif isinstance(event, AgentThoughtEvent):
            print(f"\n[{event.agent.upper()}] Ação: {event.action}")
            print(f"  Raciocínio: {event.thought}")
            # print output summary
            out_summary = event.output[:150] + "..." if len(event.output) > 150 else event.output
            print(f"  Saída: {out_summary}")
            
    # Wait for completion and print result
    result = await handler
    
    print("\n" + "=" * 60)
    print("=== RELATÓRIO FINAL APROVADO E INTEGRADO ===")
    print("=" * 60)
    print(result.get("report"))
    print("=" * 60)
    print(f"Número de iterações do fluxo de consistência: {result.get('iteration')}")
    print(f"Status final: {result.get('verdict').get('approved')}")


if __name__ == "__main__":
    # Run the async main loop
    asyncio.run(run_multiagent_system())
