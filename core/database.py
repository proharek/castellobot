import sqlite3
import json
from typing import Optional, List
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    name TEXT PRIMARY KEY,
                    amount REAL,
                    author_id INTEGER,
                    author_name TEXT,
                    participants TEXT,
                    timestamp TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # === Контракты ===

    def add_contract(self, contract: dict):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO contracts (name, amount, author_id, author_name, participants, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                contract["name"],
                contract["amount"],
                contract["author_id"],
                contract["author_name"],
                json.dumps(contract.get("participants", [])),
                contract["timestamp"]
            ))

    def get_contract_by_name(self, name: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            return {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            }
        return None

    def get_all_contracts(self) -> List[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM contracts")
        rows = cur.fetchall()
        return [
            {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            }
            for row in rows
        ]

    def update_contract(self, contract: dict):
        with self.conn:
            self.conn.execute("""
                UPDATE contracts
                SET amount = ?, participants = ?, timestamp = ?
                WHERE name = ?
            """, (
                contract["amount"],
                json.dumps(contract.get("participants", [])),
                contract["timestamp"],
                contract["name"]
            ))

    def delete_contract_by_name(self, name: str):
        with self.conn:
            self.conn.execute("DELETE FROM contracts WHERE name = ?", (name,))

    # === Язык пользователя ===

    def set_user_language(self, user_id: int, lang: str):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO users (user_id, language)
                VALUES (?, ?)
            """, (user_id, lang))

    def get_user_language(self, user_id: int) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else "ru"

    # === Отчёты ===

    def save_report(self, report: dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO reports (contract_name, author_id, author_name, participants, amount, fund, per_user, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

    def get_reports_by_days(self, days: int) -> List[dict]:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT contract_name, author_id, author_name, participants, amount, fund, per_user, timestamp
            FROM reports
            WHERE timestamp >= ?
        """, (cutoff,))
        rows = cur.fetchall()
        return [
            {
                "contract_name": row[0],
                "author_id": row[1],
                "author_name": row[2],
                "participants": json.loads(row[3]),
                "amount": row[4],
                "fund": row[5],
                "per_user": row[6],
                "timestamp": row[7]
            }
            for row in rows
        ]
