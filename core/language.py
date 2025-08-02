from typing import Dict

from main import Config  # или импорт Config, если он в отдельном файле

class LanguageManager:
    texts: Dict[str, Dict[str, str]] = {
        "ru": {
            "language_set_ru": "Выбран русский язык.",
            "language_set_ua": "Выбран украинский язык.",
            "select_language": "Выберите язык:",
            "menu_title": "📋 Главное меню",
            "menu_description": "Управляй контрактами и настройками через команды ниже.",
            "contract_added": "Контракт **{name}** на сумму **{amount} USD** добавлен.",
            "invalid_amount": "Сумма должна быть положительным числом.",
            "contract_not_found": "Контракт не найден.",
            "contract_updated_success": "Контракт **{name}** обновлён. Новая сумма: **{amount} USD**.",
            "no_permission": "У вас нет прав на редактирование этого контракта.",
            "contract_deleted_success": "Контракт **{name}** успешно удалён.",
            "no_contracts_found": "Контракты не найдены.",
            "select_contract": "Выберите контракт из списка:",
            "report_template": (
                "**📄 Отчёт по контракту \"{name}\"**\n"
                "💰 Сумма контракта: {amount} USD\n"
                "👤 Старший группы: @{leader}\n"
                "👥 Участники:\n{participants}\n"
                "🏦 В фонд семьи: {fund} USD (50%)\n"
                "💸 Каждому участнику: {per_user} USD"
            ),
            "language_changed": "Язык изменён на {language}.",
            "participants_added": "Участники добавлены в контракт **{name}**.",
            "edit_participants_prompt": "Отправьте теги участников через пробел.",
            "participants_empty": "Список участников не может быть пустым.",
        },
        "ua": {
            "language_set_ru": "Обрано російську мову.",
            "language_set_ua": "Обрано українську мову.",
            "select_language": "Оберіть мову:",
            "menu_title": "📋 Головне меню",
            "menu_description": "Керуй контрактами та налаштуваннями за допомогою команд нижче.",
            "contract_added": "Контракт **{name}** на суму **{amount} USD** додано.",
            "invalid_amount": "Сума повинна бути додатнім числом.",
            "contract_not_found": "Контракт не знайдено.",
            "contract_updated_success": "Контракт **{name}** оновлено. Нова сума: **{amount} USD**.",
            "no_permission": "У вас немає прав для редагування цього контракту.",
            "contract_deleted_success": "Контракт **{name}** успішно видалено.",
            "no_contracts_found": "Контракти не знайдені.",
            "select_contract": "Оберіть контракт зі списку:",
            "report_template": (
                "**📄 Звіт по контракту \"{name}\"**\n"
                "💰 Сума контракту: {amount} USD\n"
                "👤 Старший групи: @{leader}\n"
                "👥 Учасники:\n{participants}\n"
                "🏦 До сімейного фонду: {fund} USD (50%)\n"
                "💸 Кожному учаснику: {per_user} USD"
            ),
            "language_changed": "Мову змінено на {language}.",
            "participants_added": "Учасники додані до контракту **{name}**.",
            "edit_participants_prompt": "Надішліть теги учасників через пробіл.",
            "participants_empty": "Список учасників не може бути порожнім.",
        }
    }

    def get_text(self, key: str, lang: str) -> str:
        return self.texts.get(lang, self.texts[Config.DEFAULT_LANGUAGE]).get(key, f"[{key}]")
