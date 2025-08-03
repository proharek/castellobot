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

    # Загрузка контрактов из JSON-файла (для инициализации)
    def load_contracts_from_file(self, filename: str) -> None:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for contract in data:
                    self.add_contract(contract)
        except FileNotFoundError:
            pass

    # Сохранение контрактов в JSON-файл (не обязательно, если используешь БД)
    def save_contracts_to_file(self, filename: str) -> None:
        contracts = self.get_all_contracts()
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(contracts, f, ensure_ascii=False, indent=2)

    # Добавление контракта
    def add_contract(self, contract: Dict[str, Any]) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO contracts (name, amount)
                VALUES (?, ?)
            """, (contract["name"], contract["amount"]))

    # Обновление контракта
    def update_contract(self, contract: Dict[str, Any]) -> None:
        with self.conn:
            self.conn.execute("""
                UPDATE contracts SET amount = ? WHERE name = ?
            """, (contract["amount"], contract["name"]))

    # Удаление контракта по названию
    def delete_contract_by_name(self, name: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM contracts WHERE name = ?", (name,))

    # Получение контракта по названию
    def get_contract_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM contracts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    # Получение всех контрактов
    def get_all_contracts(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM contracts")
        return [dict(row) for row in cursor.fetchall()]

    # Сохранение отчёта
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

    # Получение отчётов за последние N дней
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

    # Установка языка пользователя
    def set_user_language(self, user_id: int, language: str) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO users (user_id, language) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET language=excluded.language
            """, (user_id, language))

    # Получение языка пользователя
    def get_user_language(self, user_id: int) -> str:
        cursor = self.conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row["language"]
        return "ru"  # Язык по умолчанию

    # Удаление отчётов старше N дней
    def delete_reports_older_than(self, days: int) -> int:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        with self.conn:
            cursor = self.conn.execute("DELETE FROM reports WHERE timestamp < ?", (cutoff_iso,))
            return cursor.rowcount
