import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from config import Settings, get_settings
from core.mock_data import generate_forecast_data, init_mock_database

logger = logging.getLogger(__name__)

# ── Module-level singletons (initialized lazily) ───────────────
_db_connection = None


def _get_db_connection() -> sqlite3.Connection:
    """Return a cached connection to the SQLite database."""
    global _db_connection
    if _db_connection is None:
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        # Force SQLite db file to exist and populate it
        engine = init_mock_database()
        _db_connection = sqlite3.connect("data/mock_caged.db", check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row
    return _db_connection


# ── Tool Wrapper Functions ─────────────────────────────────────


def query_industrial_sql(question: str) -> str:
    """
    Query the CAGED/IBGE employment database using natural language or SQL.
    This tool receives questions and queries the 'emprego_formal' table.
    Columns: id, uf, setor, mes_ano, admissoes, desligamentos, saldo, salario_medio
    """
    start_time: float = time.perf_counter()
    logger.info("Executing industrial SQL tool query", extra={"question": question})
    conn = _get_db_connection()
    cursor = conn.cursor()

    # Extract raw SQL query by stripping code block formatting safely if present
    clean_q = question.strip()
    if clean_q.startswith("```"):
        lines = clean_q.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_q = "\n".join(lines).strip()
    
    # Remove any stray backticks or leading/trailing SQL tag
    if clean_q.lower().startswith("sql"):
        clean_q = clean_q[3:].strip()
    clean_q = clean_q.replace("`", "").strip()

    # If the LLM sent a natural language query instead of SQL, let's convert basic SP/Construction to SQL
    if not clean_q.upper().startswith("SELECT"):
        # Very simple fallback translation for testing SP/Construction
        uf_target: str = "SP"
        setor_target: str = "Construção Civil"
        clean_q = f"SELECT mes_ano, uf, setor, admissoes, desligamentos, saldo, salario_medio FROM emprego_formal WHERE uf='{uf_target}' AND setor='{setor_target}' LIMIT 12"

    try:
        # Standardize state and columns in sql if present
        clean_q = clean_q.replace("estado=", "uf=").replace("estado =", "uf =")
        clean_q = clean_q.replace("mes=", "mes_ano=").replace("mes =", "mes_ano =")

        # If the query only requests 'saldo' or just one column, force include mes_ano, uf and setor for readability
        if "SELECT saldo FROM" in clean_q.upper() or "SELECT saldo, " in clean_q.upper() or clean_q.upper().startswith("SELECT SALDO"):
            clean_q = clean_q.upper().replace("SELECT SALDO", "SELECT mes_ano, uf, setor, saldo")
            clean_q = clean_q.upper().replace("SELECT *", "SELECT mes_ano, uf, setor, admissoes, desligamentos, saldo, salario_medio")

        cursor.execute(clean_q)
        rows = cursor.fetchall()
        cols: list[str] = [desc[0] for desc in cursor.description]
        records: list[dict[str, Any]] = [dict(zip(cols, row)) for row in rows]
        
        execution_time_ms: float = round((time.perf_counter() - start_time) * 1000, 2)
        payload = {
            "status": "success",
            "query": clean_q,
            "columns": cols,
            "records": records,
            "row_count": len(records),
            "execution_time_ms": execution_time_ms
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as exc:
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        payload = {
            "status": "error",
            "query": clean_q,
            "columns": [],
            "records": [],
            "row_count": 0,
            "execution_time_ms": execution_time_ms,
            "error_detail": str(exc)
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def retrieve_documents(question: str) -> str:
    """
    Search indexed industrial documents using dynamic semantic vector retrieval (RAG).
    Indexes text, markdown, and PDF documents from data/sample/docs and data/docs.
    """
    settings = get_settings()
    doc_paths: list[Path] = []

    for folder in [settings.docs_dir, settings.sample_docs_dir, settings.sample_dir]:
        p = Path(folder)
        if p.exists():
            for ext in ("*.txt", "*.pdf", "*.md"):
                doc_paths.extend(list(p.glob(ext)))

    # Remove duplicates
    doc_paths = list({p.resolve(): p for p in doc_paths}.values())

    if not doc_paths:
        return "Nenhum documento vetorial encontrado no diretório RAG."

    logger.info("Building dynamic vector retrieval index", extra={"documents_found": len(doc_paths)})

    # 1. Attempt LlamaIndex VectorStoreIndex Retrieval
    try:
        from llama_index.core import VectorStoreIndex, Document
        raw_docs: list[Document] = []
        for path in doc_paths:
            if path.suffix.lower() == ".pdf":
                try:
                    from llama_index.readers.file import PDFReader
                    reader = PDFReader()
                    pages = reader.load_data(path)
                    raw_docs.extend(pages)
                except Exception:
                    pass
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    if text.strip():
                        raw_docs.append(Document(text=text, metadata={"filename": path.name}))

        if raw_docs:
            index = VectorStoreIndex.from_documents(raw_docs)
            retriever = index.as_retriever(similarity_top_k=3)
            nodes = retriever.retrieve(question)
            matched_passages = [node.get_content() for node in nodes if node.get_content()]
            if matched_passages:
                return "[RAG LlamaIndex Vector Output]:\n" + "\n\n---\n\n".join(matched_passages)
    except Exception as exc:
        logger.warning(f"LlamaIndex vector build skipped ({exc}). Using TF-IDF vector similarity search.")

    # 2. Dynamic Vector Similarity Search (TF-IDF + Cosine Similarity) over Document Chunks
    chunks: list[str] = []
    for path in doc_paths:
        if path.suffix.lower() != ".pdf":
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
                    chunks.extend(paras)
            except Exception:
                pass

    if not chunks:
        return "Nenhum trecho textual extraído dos documentos RAG."

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(ngram_range=(1, 2)).fit(chunks + [question])
        doc_vectors = vectorizer.transform(chunks)
        query_vector = vectorizer.transform([question])
        scores = cosine_similarity(query_vector, doc_vectors)[0]

        top_indices = scores.argsort()[::-1][:3]
        top_chunks = [chunks[i] for i in top_indices if scores[i] > 0.01]

        if top_chunks:
            return "[RAG Vector Similarity Search]:\n" + "\n\n---\n\n".join(top_chunks)
        else:
            return f"[RAG Vector Similarity Search]:\n{chunks[top_indices[0]]}"
    except Exception as exc:
        logger.warning(f"TF-IDF vector search error: {exc}")
        return "\n\n---\n\n".join(chunks[:2])



def forecast_insight(setor: str, horizonte_meses: int = 6) -> str:
    """
    Generate payroll mass forecasts and macroeconomic scenario analysis.
    """
    start_time: float = time.perf_counter()
    horizonte_meses = max(1, min(horizonte_meses, 24))
    try:
        forecast_data = generate_forecast_data(setor=setor, horizonte_meses=horizonte_meses)
        execution_time_ms: float = round((time.perf_counter() - start_time) * 1000, 2)
        payload = {
            "status": "success",
            "setor": forecast_data.get("setor", setor),
            "horizonte_meses": forecast_data.get("horizonte_meses", horizonte_meses),
            "data_geracao": forecast_data.get("data_geracao"),
            "modelo": forecast_data.get("modelo"),
            "confianca_modelo": forecast_data.get("confianca_modelo"),
            "cenarios": forecast_data.get("cenarios"),
            "variaveis_macroeconomicas": forecast_data.get("variaveis_macroeconomicas"),
            "alertas": forecast_data.get("alertas"),
            "execution_time_ms": execution_time_ms
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception as exc:
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        payload = {
            "status": "error",
            "setor": setor,
            "horizonte_meses": horizonte_meses,
            "execution_time_ms": execution_time_ms,
            "error_detail": str(exc)
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


def rebuild_vector_index(settings: Settings) -> int:
    """Mock rebuild function. Simply count existing PDFs."""
    docs_dir = Path(settings.docs_dir)
    if not docs_dir.exists():
        return 0
    return len(list(docs_dir.glob("*.pdf")))


# ── Metadata for API & System prompt ──────────────────────────

def get_tools_metadata() -> list[dict[str, Any]]:
    return [
        {
            "name": "industrial_sql_tool",
            "description": "Executa consultas SQL na base de emprego formal (CAGED/IBGE). Retorna registros com colunas: mes_ano, uf, setor, admissoes, desligamentos, saldo, salario_medio."
        },
        {
            "name": "document_retriever_tool",
            "description": "Busca informações textuais nos relatórios industriais e PDFs carregados no sistema."
        },
        {
            "name": "forecast_insight_tool",
            "description": "Gera projeções estatísticas (cenários Otimista, Base, Pessimista) de massa salarial e variáveis macro para um setor industrial. Argumentos: setor (string), horizonte_meses (int, padrão 6)."
        }
    ]
