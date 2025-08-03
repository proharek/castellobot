import sqlite3
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_path: str = "contracts.db"):
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
                CREATE TABLE IF NOT EXISTS user_languages (
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
                ",".join(contract["participants"]),
                contract["timestamp"]
            ))

    def get_contract_by_name(self, name: str):
        cursor = self.conn.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "amount": row[1],
                "author_id": row[2],
                "author_name": row[3],
                "participants": row[4].split(",") if row[4] else [],
                "timestamp": row[5]
            }

    def get_all_contracts(self):
        cursor = self.conn.execute("SELECT * FROM contracts")
        return [{
            "name": row[0],
            "amount": row[1],
            "author_id": row[2],
            "author_name": row[3],
            "participants": row[4].split(",") if row[4] else [],
            "timestamp": row[5]
        } for row in cursor.fetchall()]

    def update_contract(self, contract: dict):
        self.add_contract(contract)

    def delete_contract_by_name(self, name: str):
        with self.conn:
            self.conn.execute("DELETE FROM contracts WHERE name = ?", (name,))

    def set_user_language(self, user_id: int, language: str):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO user_languages (user_id, language)
                VALUES (?, ?)
            """, (user_id, language))

    def get_user_language(self, user_id: int) -> str:
        cursor = self.conn.execute("SELECT language FROM user_languages WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else "ru"

    def save_report(self, report: dict):
        with self.conn:
            self.conn.execute("""
                INSERT INTO reports (contract_name, author_id, author_name, participants, amount, fund, per_user, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report["contract_name"],
                report["author_id"],
                report["author_name"],
                ",".join(report["participants"]),
                report["amount"],
                report["fund"],
                report["per_user"],
                report["timestamp"]
            ))

    def get_reports_by_days(self, days: int):
        date_threshold = datetime.utcnow() - timedelta(days=days)
        cursor = self.conn.execute("""
            SELECT * FROM reports WHERE timestamp >= ?
        """, (date_threshold.isoformat(),))
        rows = cursor.fetchall()
        return [{
            "contract_name": row[1],
            "author_id": row[2],
            "author_name": row[3],
            "participants": row[4].split(",") if row[4] else [],
            "amount": row[5],
            "fund": row[6],
            "per_user": row[7],
            "timestamp": row[8]
        } for row in rows]
