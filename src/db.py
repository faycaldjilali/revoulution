
import sqlite3
import pandas as pd
from .config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def read_sql(query: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
