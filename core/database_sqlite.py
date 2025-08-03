import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict

CONTRACTS_FILE = "contracts_data.json"

class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._connect()
        self._create_tables()
        self.contracts_cache = []
        self.load_contracts_from_file()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def _create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_languages (
            user_id INTEGER PRIMARY KEY,
            language TEXT
        )
        """)
        self.cursor.execute("""
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

    # --- Язык ---
    def set_user_language(self, user_id: int, language: str):
        self.cursor.execute(
            "INSERT OR REPLACE INTO user_languages (user_id, language) VALUES (?, ?)",
            (user_id, language)
        )
        self.conn.commit()

    def get_user_language(self, user_id: int) -> str:
        self.cursor.execute(
            "SELECT language FROM user_languages WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        return row["language"] if row else "ru"

    # --- Контракты (JSON + кэш) ---
    def load_contracts_from_file(self):
        if os.path.exists(CONTRACTS_FILE):
            try:
                with open(CONTRACTS_FILE, "r", encoding="utf-8") as f:
                    self.contracts_cache = json.load(f)
            except:
                self.contracts_cache = []
        else:
            self.contracts_cache = []

    def save_contracts_to_file(self):
        with open(CONTRACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.contracts_cache, f, ensure_ascii=False, indent=2)

    def add_contract(self, contract: dict):
        self.contracts_cache.append(contract)
        self.save_contracts_to_file()

    def update_contract(self, updated: dict):
        for i, c in enumerate(self.contracts_cache):
            if c["name"] == updated["name"]:
                self.contracts_cache[i] = updated
                break
        self.save_contracts_to_file()

    def delete_contract_by_name(self, name: str):
        self.contracts_cache = [c for c in self.contracts_cache if c["name"] != name]
        self.save_contracts_to_file()

    def get_all_contracts(self) -> List[dict]:
        return self.contracts_cache

    def get_contract_by_name(self, name: str) -> Optional[dict]:
        for c in self.contracts_cache:
            if c["name"] == name:
                return c
        return None

    # --- Отчёты (SQLite) ---
    def save_report(self, report: dict):
        self.cursor.execute("""
        INSERT INTO reports (
            contract_name, author_id, author_name,
            participants, amount, fund, per_user, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        self.conn.commit()

    def get_reports_by_days(self, days: int) -> List[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        self.cursor.execute("SELECT * FROM reports WHERE timestamp >= ?", (cutoff.isoformat(),))
        rows = self.cursor.fetchall()
        return [self._row_to_report(row) for row in rows]

    def delete_reports_older_than(self, days: int):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        self.cursor.execute("DELETE FROM reports WHERE timestamp < ?", (cutoff.isoformat(),))
        self.conn.commit()

    def _row_to_report(self, row: sqlite3.Row) -> dict:
        return {
            "contract_name": row["contract_name"],
            "author_id": row["author_id"],
            "author_name": row["author_name"],
            "participants": row["participants"].split(",") if row["participants"] else [],
            "amount": row["amount"],
            "fund": row["fund"],
            "per_user": row["per_user"],
            "timestamp": row["timestamp"]
        }
