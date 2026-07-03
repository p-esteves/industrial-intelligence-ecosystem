from __future__ import annotations

import json
from core.tools import query_industrial_sql


def test_sql_cleaning_markdown_blocks():
    """Verify that query_industrial_sql extracts queries correctly from Markdown code blocks."""
    # A mocked SQL query inside markdown block
    query_with_markdown = "```sql\nSELECT mes_ano, uf, setor, saldo FROM emprego_formal WHERE uf='SP' AND setor='Construção Civil' LIMIT 5\n```"
    result_str = query_industrial_sql(query_with_markdown)
    payload = json.loads(result_str)
    
    # Check that execution returned a success or valid query execution (even if table is empty/mocked)
    assert payload["status"] == "success"
    assert "SELECT" in payload["query"]
    assert "```" not in payload["query"]


def test_sql_cleaning_plain_query_with_sql_keyword():
    """Verify that query_industrial_sql does NOT corrupt queries containing 'sql' as a substring/keyword."""
    # Run a query with 'desligamentos' (which contains letters 'sql' in different order? No, but let's test a word containing sql like caged_sql)
    # The database table doesn't have a column named caged_sql, but we can verify that the text 'sql' is not stripped from a string literal.
    literal_query = "SELECT mes_ano FROM emprego_formal WHERE uf='SP' AND setor='Construção Civil' -- test comment with sql word"
    result_str = query_industrial_sql(literal_query)
    payload = json.loads(result_str)
    
    assert "sql" in payload["query"]  # Should preserve the word 'sql' in the comment or query!
