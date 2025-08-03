import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict

class DatabaseManager:
    def __init__(self, db_path: str = "data.sqlite"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.init_tables()

    def init_tables(self):
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
            CREATE TABLE IF NOT EXISTS languages (
                user_id INTEGER PRIMARY KEY,
                language TEXT
            )
        """)
        cursor.execute("""
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
        self.conn.commit()

    def add_contract(self, contract: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO contracts (name, amount, author_id, author_name, participants, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            contract["name"],
            contract["amount"],
            contract["author_id"],
            contract["author_name"],
            ",".join(contract.get("participants", [])),
            contract["timestamp"]
        ))
        self.conn.commit()

    def get_contract_by_name(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contracts WHERE name = ?", (name,))
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
        return None

    def get_all_contracts(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contracts")
        rows = cursor.fetchall()
        return [{
            "name": row[0],
            "amount": row[1],
            "author_id": row[2],
            "author_name": row[3],
            "participants": row[4].split(",") if row[4] else [],
            "timestamp": row[5]
        } for row in rows]

    def update_contract(self, contract: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE contracts
            SET amount = ?, participants = ?, timestamp = ?
            WHERE name = ?
        """, (
            contract["amount"],
            ",".join(contract.get("participants", [])),
            contract["timestamp"],
            contract["name"]
        ))
        self.conn.commit()

    def delete_contract_by_name(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM contracts WHERE name = ?", (name,))
        self.conn.commit()

    def set_user_language(self, user_id: int, language: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO languages (user_id, language)
            VALUES (?, ?)
        """, (user_id, language))
        self.conn.commit()

    def get_user_language(self, user_id: int) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT language FROM languages WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else "ru"

    def save_report(self, report: Dict):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM reports WHERE contract_name = ?
        """, (report["contract_name"],))
        if cursor.fetchone():
            return  # Уже сохранён

        cursor.execute("""
            INSERT INTO reports (contract_name, author_id, author_name, participants, amount, fund, per_user, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report["contract_name"],
            report["author_id"],
            report["author_name"],
            ",".join(report.get("participants", [])),
            report["amount"],
            report["fund"],
            report["per_user"],
            report["timestamp"]
        ))
        self.conn.commit()

    def get_reports_by_days(self, days: int) -> List[Dict]:
        cursor = self.conn.cursor()
        since = datetime.utcnow() - timedelta(days=days)
        cursor.execute("""
            SELECT contract_name, author_id, author_name, participants, amount, fund, per_user, timestamp
            FROM reports
            WHERE timestamp >= ?
        """, (since.isoformat(),))
        rows = cursor.fetchall()
        return [{
            "contract_name": row[0],
            "author_id": row[1],
            "author_name": row[2],
            "participants": row[3].split(",") if row[3] else [],
            "amount": row[4],
            "fund": row[5],
            "per_user": row[6],
            "timestamp": row[7]
        } for row in rows]
