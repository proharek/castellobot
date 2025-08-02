import subprocess
import time

# Путь к файлу бота
MAIN_SCRIPT = "main.py"

while True:
    print("🛡️ Watchdog: запускаю бота...")
    try:
        process = subprocess.Popen(["python3", MAIN_SCRIPT])
        process.wait()
        print("⚠️ Бот завершился. Перезапуск через 5 секунд...")
        time.sleep(5)
    except Exception as e:
        print(f"❌ Ошибка Watchdog: {e}")
        time.sleep(5)
