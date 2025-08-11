import sqlite3
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str = "database.sqlite"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    name TEXT PRIMARY KEY,
                    amount REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_name TEXT NOT NULL,
                    author_id INTEGER NOT NULL,
                    author_name TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    amount REAL NOT NULL,
                    fund REAL NOT NULL,
                    per_user REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ru'
                )
            """)

    def load_contracts_from_file(self, filename: str) -> None:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for contract in data:
                    self._add_contract(contract)
        except FileNotFoundError:
            pass

    def _add_contract(self, contract: Dict[str, Any]) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT OR IGNORE INTO contracts (name, amount)
                VALUES (?, ?)
            """, (contract["name"], contract["amount"]))

    def get_contract_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_contracts(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM contracts")
        return [dict(row) for row in cursor.fetchall()]

    def save_report(self, report: Dict[str, Any]) -> None:
        participants_json = json.dumps(report["participants"], ensure_ascii=False)
        with self.conn:
            self.conn.execute("""
                INSERT INTO reports (
                    contract_name, author_id, author_name,
                    participants, amount, fund, per_user, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report["contract_name"],
                report["author_id"],
                report["author_name"],
                participants_json,
                report["amount"],
                report["fund"],
                report["per_user"],
                report["timestamp"]
            ))

    def get_reports_by_days(self, days: int) -> List[Dict[str, Any]]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        cursor = self.conn.execute("""
            SELECT * FROM reports WHERE timestamp >= ?
        """, (cutoff_iso,))
        rows = cursor.fetchall()
        reports = []
        for row in rows:
            report = dict(row)
            report["participants"] = json.loads(report["participants"])
            reports.append(report)
        return reports

    def delete_reports_older_than(self, days: int) -> int:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        with self.conn:
            # Сначала считаем сколько удалим
            cursor = self.conn.execute("SELECT COUNT(*) FROM reports WHERE timestamp < ?", (cutoff_iso,))
            count = cursor.fetchone()[0]
            self.conn.execute("DELETE FROM reports WHERE timestamp < ?", (cutoff_iso,))
            return count

    def delete_reports_by_date(self, date_str: str) -> int:
        """
        Удаляет отчёты за конкретный день.
        date_str должен быть в формате YYYY-MM-DD
        """
        start_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        with self.conn:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM reports WHERE timestamp >= ? AND timestamp < ?",
                (start_iso, end_iso)
            )
            count = cursor.fetchone()[0]
            self.conn.execute(
                "DELETE FROM reports WHERE timestamp >= ? AND timestamp < ?",
                (start_iso, end_iso)
            )
            return count

    def set_user_language(self, user_id: int, language: str) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO users (user_id, language) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET language=excluded.language
            """, (user_id, language))

    def get_user_language(self, user_id: int) -> str:
        cursor = self.conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row["language"]
        return "ru"  # По умолчанию
