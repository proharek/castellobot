import json
import os
from typing import List, Optional, Dict

CONTRACTS_FILE = os.path.join(os.path.dirname(__file__), "..", "contracts_data.json")

class DatabaseManager:
    def __init__(self):
        self.contracts: List[Dict] = []
        self.load_contracts_from_file()

    def load_contracts_from_file(self) -> None:
        """Загрузить список контрактов из JSON-файла."""
        if not os.path.exists(CONTRACTS_FILE):
            self.contracts = []
            return
        try:
            with open(CONTRACTS_FILE, "r", encoding="utf-8") as f:
                self.contracts = json.load(f)
        except Exception as e:
            print(f"[DatabaseManager] Ошибка загрузки contracts_data.json: {e}")
            self.contracts = []

    def save_contracts_to_file(self) -> None:
        """Сохранить текущий список контрактов в JSON-файл."""
        try:
            with open(CONTRACTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.contracts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DatabaseManager] Ошибка сохранения contracts_data.json: {e}")

    def add_contract(self, contract: Dict) -> None:
        """Добавить контракт (должен содержать 'name' и 'amount')."""
        if any(c['name'] == contract['name'] for c in self.contracts):
            raise ValueError("Контракт с таким названием уже существует")
        self.contracts.append(contract)
        self.save_contracts_to_file()

    def update_contract(self, contract: Dict) -> bool:
        """Обновить контракт по имени. Возвращает True если обновлено, False если не найден."""
        for i, c in enumerate(self.contracts):
            if c['name'] == contract['name']:
                self.contracts[i] = contract
                self.save_contracts_to_file()
                return True
        return False

    def delete_contract_by_name(self, name: str) -> bool:
        """Удалить контракт по имени. Возвращает True если удалено, False если не найден."""
        for i, c in enumerate(self.contracts):
            if c['name'] == name:
                del self.contracts[i]
                self.save_contracts_to_file()
                return True
        return False

    def get_all_contracts(self) -> List[Dict]:
        """Вернуть список всех контрактов."""
        return self.contracts.copy()

    def get_contract_by_name(self, name: str) -> Optional[Dict]:
        """Вернуть контракт по имени или None если не найден."""
        for c in self.contracts:
            if c['name'] == name:
                return c
        return None
