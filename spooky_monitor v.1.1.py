import asyncio
import re
import sys
import os
import configparser
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from winotify import Notification, audio

# ============================================================
# ЦВЕТА И КРАСОЧНЫЕ ФУНКЦИИ
# ============================================================
from colorama import init
from colorama import Fore, Style
from pybeaut import Colorate, Colors

init(autoreset=True)

# ============================================================
# НАСТРОЙКИ
# ============================================================
BOT_USERNAME = "@SpookyTimeBot"
CHECK_INTERVAL = 10
BOT_RESPONSE_TIMEOUT = 15
EVENT_HELL = "Адская Резня"
EVENT_BIKINI = "Бикини Боттом"

# ============================================================
# КОНФИГ ФАЙЛ
# ============================================================
CONFIG_FILE = "spooky_monitor.config"
config = configparser.ConfigParser()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None, None
    config.read(CONFIG_FILE)
    if 'telegram' not in config:
        return None, None
    return config['telegram'].get('api_id'), config['telegram'].get('api_hash')

def save_config(api_id, api_hash):
    config['telegram'] = {
        'api_id': str(api_id),
        'api_hash': api_hash
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

# ============================================================
# МЕНЮ
# ============================================================
def clear_screen():
    print("\033[2J\033[H", end="")

def print_header():
    banner = "          SPOOKYTIME EVENT MONITOR           "
    alignment = "{:>50}".format(banner)
    print()
    print(Colorate.Horizontal(Colors.blue_to_purple, banner))
    print()

def choose_event():
    while True:
        clear_screen()
        print_header()
        print(Fore.WHITE + "[1] 🔥 Адская Резня")
        print("[2] 🏝 Бикини Боттом")
        print("[0] Выход (СТОП)" + Fore.RESET)
        print()
        choice = input("Выберите ивент: ").strip()
        if choice == "1":
            return EVENT_HELL
        if choice == "2":
            return EVENT_BIKINI
        if choice == "0":
            print(Fore.YELLOW + "\nПрограмма остановлена." + Fore.RESET)
            sys.exit(0)
        print(Fore.RED + "\nНеверный выбор!" + Fore.RESET)
        input("Нажмите Enter...")

# ============================================================
# УВЕДОМЛЕНИЕ
# ============================================================
def send_notification(event_name, anarch_number, status, remaining):
    try:
        toast = Notification(
            app_id="SpookyTime Event Monitor",
            title=Colorate.Horizontal(Colors.blue_to_purple, f"🎉 {event_name} FOUND!"),
            msg=Colorate.Horizontal(Colors.blue_to_purple, f"Анархия: {anarch_number}\nСтатус: {status}\nДо деактивации: {remaining}")
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as e:
        print(Fore.RED + f"[ERROR] Notification failed: {e}" + Fore.RESET)

# ============================================================
# ЛОГИ
# ============================================================
def now():
    return Colorate.Horizontal(Colors.blue_to_purple, datetime.now().strftime("%H:%M:%S"))

# ============================================================
# ПАРСЕР ВРЕМЕНИ
# ============================================================
def parse_remaining(text):
    patterns = [
        r"до деактивации:\s*([^\n]+)",
        r"до удаления\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "неизвестно"

# ============================================================
# ПАРСИНГ ОДНОЙ АНАРХИИ
# ============================================================
def parse_anarchy_block(block):
    number_match = re.search(r"Анархия\s+(\d+)", block, flags=re.IGNORECASE)
    if not number_match:
        return None
    anarch_number = number_match.group(1)

    event_match = re.search(r"\[[0-9]+\]\s*(.+)", block)
    if not event_match:
        return None
    event_name = event_match.group(1).strip()
    event_name = re.sub(r"^[^\wА-Яа-яЁё]+", "", event_name).strip()

    status_match = re.search(r"Статус:\s*([^\n]+)", block, flags=re.IGNORECASE)
    if status_match:
        status_full = status_match.group(1).strip()
        status = status_full.split(",", 1)[0].strip() if "," in status_full else status_full
    else:
        status = "Неизвестно"

    remaining = parse_remaining(block)
    return {
        "anarchy": anarch_number,
        "event": event_name,
        "status": status,
        "remaining": remaining,
        "raw": block
    }

# ============================================================
# ПАРСИНГ ВСЕГО ОТВЕТА
# ============================================================
def parse_events(text):
    blocks = re.split(r"(?=Анархия\s+\d+:)", text, flags=re.IGNORECASE)
    results = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parsed = parse_anarchy_block(block)
        if parsed:
            results.append(parsed)
    return results

# ============================================================
# ПОИСК НУЖНОГО ИВЕНТА
# ============================================================
def find_target_events(events, target_event):
    result = []
    for event in events:
        event_name = event["event"].lower()
        target = target_event.lower()
        if target in event_name:
            result.append(event)
    return result

# ============================================================
# ПОЛУЧЕНИЕ ОТВЕТА
# ============================================================
async def request_events(client):
    try:
        old_messages = await client.get_messages(BOT_USERNAME, limit=1)
        old_id = old_messages[0].id if old_messages else 0

        await client.send_message(BOT_USERNAME, "/events")

        for _ in range(BOT_RESPONSE_TIMEOUT * 2):
            await asyncio.sleep(0.5)
            messages = await client.get_messages(BOT_USERNAME, limit=5)
            for message in messages:
                if message.id > old_id and not message.out and message.text:
                    return message.text
        return ""
    except FloodWaitError as e:
        print(Fore.YELLOW + f"[{now()}] FloodWait: ждём {e.seconds} сек." + Fore.RESET)
        await asyncio.sleep(e.seconds)
        return ""
    except Exception as e:
        print(Fore.RED + f"[{now()}] Ошибка: {e}" + Fore.RESET)
        return ""

# ============================================================
# ПОКАЗ РЕЗУЛЬТАТА
# ============================================================
def print_event(event, target_event):
    print()
    print(Fore.GREEN + "╔══════════════════════════════════════════════╗" + Fore.RESET)
    print(Fore.GREEN + "║              🎉 ИВЕНТ НАЙДЕН                 ║" + Fore.RESET)
    print(Fore.GREEN + "╚══════════════════════════════════════════════╝" + Fore.RESET)
    print()
    print(f"Анархия:           {event['anarchy']}")
    print(f"Ивент:             {event['event']}")
    print(f"Статус:            {event['status']}")
    print(f"До деактивации:    {event['remaining']}")
    print()

# ============================================================
# МОНИТОРИНГ
# ============================================================
async def monitor(client, target_event):
    clear_screen()
    print_header()
    print(Fore.WHITE + f"Выбран ивент: {target_event}" + Fore.RESET)
    print(Fore.LIGHTBLACK_EX + f"Проверка каждые {CHECK_INTERVAL} секунд" + Fore.RESET)
    print()

    known_events = set()

    while True:
        print(Fore.CYAN + f"[{now()}] Проверка..." + Fore.RESET)
        text = await request_events(client)
        if not text:
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        all_events = parse_events(text)
        target_events = find_target_events(all_events, target_event)

        if not target_events:
            print(Fore.YELLOW + f"[{now()}] {target_event} не найден." + Fore.RESET)
        else:
            current_events = set()
            for event in target_events:
                event_key = (event["anarchy"], event["event"])
                current_events.add(event_key)

                print()
                print(Fore.WHITE + f"  Анархия {event['anarchy']} | {event['event']} | {event['status']} | {event['remaining']}" + Fore.RESET)
                if event_key not in known_events:
                    print(Fore.GREEN + "  >>> НОВЫЙ ИВЕНТ!" + Fore.RESET)
                    send_notification(event["event"], event["anarchy"], event["status"], event["remaining"])

            known_events = current_events

        print(Fore.LIGHTBLACK_EX + f"[{now()}] Следующая проверка через {CHECK_INTERVAL} сек..." + Fore.RESET)
        await asyncio.sleep(CHECK_INTERVAL)

# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    clear_screen()
    print_header()

    api_id, api_hash = load_config()

    if api_id and api_hash:
        print(Fore.GREEN + "[✓] API ID и Hash загружены из файла" + Fore.RESET)
        print(Fore.LIGHTBLACK_EX + "Нажмите Enter для начала мониторинга..." + Fore.RESET)
        input()
        target_event = choose_event()

        print(Fore.YELLOW + "Подключение к Telegram..." + Fore.RESET)
        client = TelegramClient("spooky_monitor", api_id, api_hash)
        try:
            await client.start()
            print(Fore.GREEN + "[✓] Telegram успешно подключён!" + Fore.RESET)
            await monitor(client, target_event)
        finally:
            await client.disconnect()
    else:
        print("Для работы нужен Telegram API ID и API HASH.")
        print("Они будут сохранены в файл spooky_monitor.config")
        print()

        while True:
            try:
                api_id = int(input("Введите API ID: ").strip())
                break
            except ValueError:
                print(Fore.RED + "API ID должен быть числом." + Fore.RESET)

        api_hash = input("Введите API HASH: ").strip()
        if not api_hash:
            print(Fore.RED + "API HASH не может быть пустым." + Fore.RESET)
            return

        save_config(api_id, api_hash)

        target_event = choose_event()

        print(Fore.YELLOW + "Подключение к Telegram..." + Fore.RESET)
        client = TelegramClient("spooky_monitor", api_id, api_hash)
        try:
            await client.start()
            print(Fore.GREEN + "[✓] Telegram успешно подключён!" + Fore.RESET)
            await monitor(client, target_event)
        finally:
            await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Fore.YELLOW + "Выход..." + Fore.RESET)