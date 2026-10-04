"""
SQL storage & analysis layer.

The cleaned dataset is persisted into a real SQLite database file
(data/spine_analytics.db) so that the platform executes genuine SQL -
not pandas dressed up as SQL. sqlite3 is stdlib, keeping the stack
dependency-light while still being a real relational engine.
"""
import os
import re
import sqlite3

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "spine_analytics.db")
DB_PATH = os.path.abspath(DB_PATH)
TABLE_NAME = "patients"

_FORBIDDEN = re.compile(
    r"\b(drop|delete|update|insert|alter|attach|detach|pragma|vacuum|replace)\b",
    re.IGNORECASE,
)


def get_connection():
    return sqlite3.connect(DB_PATH)


def store_dataframe(df: pd.DataFrame, table_name: str = TABLE_NAME):
    """(Re)write the dataframe into SQLite, replacing any prior table."""
    conn = get_connection()
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
    finally:
        conn.close()


def run_query(sql: str, table_name: str = TABLE_NAME):
    """
    Execute a read-only analytical SQL query against the stored dataset.
    Only SELECT statements are permitted - this endpoint is exposed to the
    dashboard's "Quick SQL" console, so destructive statements are blocked.
    """
    sql_stripped = sql.strip().rstrip(";")
    if not sql_stripped.lower().startswith("select"):
        raise ValueError("Only SELECT queries are permitted.")
    if _FORBIDDEN.search(sql_stripped):
        raise ValueError("Query contains a disallowed keyword.")
    if ";" in sql_stripped:
        raise ValueError("Multiple statements are not permitted.")

    conn = get_connection()
    try:
        cursor = conn.execute(sql_stripped)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
        return {"columns": columns, "rows": result, "row_count": len(result)}
    finally:
        conn.close()


def example_queries(table_name: str = TABLE_NAME):
    """
    A curated set of queries demonstrating COUNT, AVG, MIN, MAX, GROUP BY,
    HAVING, ORDER BY, CASE, filtering, and category comparison - run for
    real against the SQLite table and returned with their live results.
    Each entry degrades gracefully (result omitted, error captured) if the
    active dataset doesn't contain the expected columns.
    """
    queries = [
        {
            "title": "Patient count & average pain score by risk category",
            "description": "GROUP BY + COUNT + AVG",
            "sql": (
                f"SELECT risk_category, COUNT(*) AS patient_count, "
                f"ROUND(AVG(pain_score), 2) AS avg_pain_score "
                f"FROM {table_name} GROUP BY risk_category ORDER BY patient_count DESC"
            ),
        },
        {
            "title": "Activity levels with above-average spondylolisthesis",
            "description": "GROUP BY + AVG + HAVING",
            "sql": (
                f"SELECT activity_level, ROUND(AVG(degree_spondylolisthesis), 2) AS avg_spondy, "
                f"COUNT(*) AS n "
                f"FROM {table_name} GROUP BY activity_level "
                f"HAVING AVG(degree_spondylolisthesis) > 10 "
                f"ORDER BY avg_spondy DESC"
            ),
        },
        {
            "title": "Age range & BMI extremes per risk category",
            "description": "MIN + MAX + GROUP BY",
            "sql": (
                f"SELECT risk_category, MIN(age) AS min_age, MAX(age) AS max_age, "
                f"MIN(bmi) AS min_bmi, MAX(bmi) AS max_bmi "
                f"FROM {table_name} GROUP BY risk_category"
            ),
        },
        {
            "title": "High-risk smokers vs non-smokers",
            "description": "Filtering + CASE + comparison between categories",
            "sql": (
                f"SELECT smoking_status, "
                f"COUNT(CASE WHEN risk_category = 'High' THEN 1 END) AS high_risk_count, "
                f"COUNT(*) AS total, "
                f"ROUND(100.0 * COUNT(CASE WHEN risk_category = 'High' THEN 1 END) / COUNT(*), 1) AS high_risk_pct "
                f"FROM {table_name} GROUP BY smoking_status ORDER BY high_risk_pct DESC"
            ),
        },
        {
            "title": "Pain-level segmentation via CASE",
            "description": "CASE expression bucketing a continuous column",
            "sql": (
                f"SELECT CASE "
                f"WHEN pain_score < 3 THEN 'Mild' "
                f"WHEN pain_score < 6 THEN 'Moderate' "
                f"ELSE 'Severe' END AS pain_band, "
                f"COUNT(*) AS patient_count "
                f"FROM {table_name} GROUP BY pain_band ORDER BY patient_count DESC"
            ),
        },
        {
            "title": "Top 10 oldest patients in the High risk category",
            "description": "Filtering + ORDER BY + LIMIT",
            "sql": (
                f"SELECT patient_id, age, bmi, pain_score, degree_spondylolisthesis "
                f"FROM {table_name} WHERE risk_category = 'High' "
                f"ORDER BY age DESC LIMIT 10"
            ),
        },
        {
            "title": "Occupation load compared across risk categories",
            "description": "GROUP BY two dimensions + COUNT",
            "sql": (
                f"SELECT occupation_load, risk_category, COUNT(*) AS n "
                f"FROM {table_name} GROUP BY occupation_load, risk_category "
                f"ORDER BY occupation_load, risk_category"
            ),
        },
    ]

    results = []
    for q in queries:
        entry = dict(q)
        try:
            entry["result"] = run_query(q["sql"], table_name)
            entry["error"] = None
        except Exception as exc:  # missing columns on a custom dataset, etc.
            entry["result"] = None
            entry["error"] = str(exc)
        results.append(entry)
    return results
