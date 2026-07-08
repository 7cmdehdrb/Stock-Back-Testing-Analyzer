import sqlite3
import os

db_path = 'c:\\python\\Stock-Back-Testing-Analyzer\\stock_cache.db'
if not os.path.exists(db_path):
    print("No DB file found")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t[0]};")
            print(t[0], "count:", cursor.fetchone()[0])
        conn.close()
    except Exception as e:
        print('Error:', e)
