class LanguageManager:
    def __init__(self):
        self.texts = {
            "language_set_ru": {
                "ru": "Язык установлен: Русский",
                "ua": "Мова встановлена: Російська"
            },
            "language_set_ua": {
                "ru": "Язык установлен: Украинский 🇺🇦",
                "ua": "Мова встановлена: Українська 🇺🇦"
            },
            "contract_added": {
                "ru": "Контракт «{name}» на сумму {amount} USD успешно добавлен.",
                "ua": "Контракт «{name}» на суму {amount} USD успішно додано."
            },
            "invalid_amount": {
                "ru": "❌ Укажи сумму больше нуля.",
                "ua": "❌ Вкажи суму більше нуля."
            },
            "contract_not_found": {
                "ru": "❌ Контракт не найден.",
                "ua": "❌ Контракт не знайдено."
            },
            "no_permission": {
                "ru": "❌ У тебя нет прав на это действие.",
                "ua": "❌ У тебе немає прав на цю дію."
            },
            "contract_updated_success": {
                "ru": "Контракт «{name}» обновлён. Новая сумма: {amount} USD.",
                "ua": "Контракт «{name}» оновлено. Нова сума: {amount} USD."
            },
            "contract_deleted_success": {
                "ru": "Контракт «{name}» удалён.",
                "ua": "Контракт «{name}» видалено."
            },
            "select_contract": {
                "ru": "Выбери контракт для отчёта:",
                "ua": "Вибери контракт для звіту:"
            },
            "no_contracts_found": {
                "ru": "❌ Контракты не найдены.",
                "ua": "❌ Контракти не знайдено."
            },
            "report_template": {
                "ru": (
                    "💰 Сумма контракта: {amount} USD\n"
                    "👤 Старший группы: @{leader}\n"
                    "👥 Участники:\n{participants}\n"
                    "🏦 В фонд семьи: {fund} USD (50%)\n"
                    "💸 Каждому участнику: {per_user} USD"
                ),
                "ua": (
                    "💰 Сума контракту: {amount} USD\n"
                    "👤 Старший групи: @{leader}\n"
                    "👥 Учасники:\n{participants}\n"
                    "🏦 У сімейний фонд: {fund} USD (50%)\n"
                    "💸 Кожному учаснику: {per_user} USD"
                )
            },
            "select_language": {
                "ru": "Выберите язык интерфейса:",
                "ua": "Виберіть мову інтерфейсу:"
            },
            "menu_title": {
                "ru": "📋 Главное меню",
                "ua": "📋 Головне меню"
            },
            "menu_description": {
                "ru": "Выберите действие из меню ниже:",
                "ua": "Виберіть дію з меню нижче:"
            },
            "report_saved": {
                "ru": "📜 Отчёт сохранён.",
                "ua": "📜 Звіт збережено."
            },
            "report_not_found": {
                "ru": "❌ Отчёты не найдены.",
                "ua": "❌ Звіти не знайдено."
            },
            "reportdays_summary": {
                "ru": (
                    "📊 Контракты за последние {days} дней:\n"
                    "🔢 Всего контрактов: {count}\n"
                    "💵 Общая сумма: {total} USD\n"
                    "{per_user}"
                ),
                "ua": (
                    "📊 Контракти за останні {days} днів:\n"
                    "🔢 Всього контрактів: {count}\n"
                    "💵 Загальна сума: {total} USD\n"
                    "{per_user}"
                )
            },
            "no_reports_found": {
                "ru": "❌ Нет сохранённых отчётов.",
                "ua": "❌ Немає збережених звітів."
            }
        }

    def get_text(self, key: str, lang: str) -> str:
        if key not in self.texts:
            return "⚠️ Текст не найден."
        return self.texts[key].get(lang) or self.texts[key].get("ru") or "⚠️ Текст не найден."
