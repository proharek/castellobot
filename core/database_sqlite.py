import sqlite3
import json
from datetime import datetime, timedelta
from typing import List

class DatabaseManager:
    def __init__(self, db_path="data.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                name TEXT PRIMARY KEY,
                amount REAL,
                author_id INTEGER,
                author_name TEXT,
                participants TEXT,
                timestamp TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_languages (
                user_id INTEGER PRIMARY KEY,
                language TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                contract_name TEXT,
                author_id INTEGER,
                author_name TEXT,
                participants TEXT,
                amount REAL,
                fund REAL,
                per_user REAL,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def add_contract(self, contract):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO contracts VALUES (?, ?, ?, ?, ?, ?)
        """, (
            contract["name"],
            contract["amount"],
            contract["author_id"],
            contract["author_name"],
            json.dumps(contract["participants"]),
            contract["timestamp"]
        ))
        self.conn.commit()

    def get_contract_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": json.loads(row[4]),
                "timestamp": row[5]
            }
        return None

    def get_all_contracts(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contracts")
        rows = cursor.fetchall()
        return [{
            "name": row[0],
            "amount": row[1],
            "author_id": row[2],
            "author_name": row[3],
            "participants": json.loads(row[4]),
            "timestamp": row[5]
        } for row in rows]

    def update_contract(self, contract):
        self.add_contract(contract)

    def delete_contract_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM contracts WHERE name = ?", (name,))
        self.conn.commit()

    def set_user_language(self, user_id, language):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_languages VALUES (?, ?)
        """, (user_id, language))
        self.conn.commit()

    def get_user_language(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT language FROM user_languages WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else "ru"

    def save_report(self, report):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["contract_name"],
            report["author_id"],
            report["author_name"],
            json.dumps(report["participants"]),
            report["amount"],
            report["fund"],
            report["per_user"],
            report["timestamp"]
        ))
        self.conn.commit()

    def get_reports_by_days(self, days: int) -> List[dict]:
        cursor = self.conn.cursor()
        cutoff = datetime.utcnow() - timedelta(days=days)
        cursor.execute("SELECT * FROM reports WHERE timestamp >= ?", (cutoff.isoformat(),))
        rows = cursor.fetchall()
        return [{
            "contract_name": row[0],
            "author_id": row[1],
            "author_name": row[2],
            "participants": json.loads(row[3]),
            "amount": row[4],
            "fund": row[5],
            "per_user": row[6],
            "timestamp": row[7]
        } for row in rows]
