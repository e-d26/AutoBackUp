import time
import threading
import os
import json
import subprocess

from my_config import BACKUP_LOCATION, JSON_PATH
from device_manager import DeviceManager, Device

def backup_device(device: Device, device_manager: DeviceManager):
    """
    Performs the backup for a specific device, handling deduplication and progress updates.
    """
    device.backup_status = "Backing Up"
    device.backup_progress = 0

    try:
        # Load phone config
        temp_file = "temp_phone_info.json"
        device.pull_json(temp_file)

        with open(temp_file, "r") as f:
            phone_info = json.load(f)

        phone_name = phone_info.get("phone_name")

        backup_dir = os.path.join(BACKUP_LOCATION, phone_name) #Using the phone_name
        os.makedirs(backup_dir, exist_ok=True)

        folders_to_backup = phone_info.get("folders_to_backup")

        # Backup each of the folders
        total_folders = len(folders_to_backup)
        current_folder = 0

        for folder_config in folders_to_backup:
            current_folder += 1

            source_folder = folder_config.get("source")
            destination_folder = folder_config.get("destination")

            dest_path = os.path.join(backup_dir, destination_folder)
            os.makedirs(dest_path, exist_ok=True)

            # Get the destination folder for the backup

            # Copy all the files over with shell scripts.
            adb_command = f"adb -s {device.serial} pull {source_folder} {dest_path}"
            result = subprocess.run(adb_command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error pulling JSON file: {result.stderr}")

            # calculate progress
            device.backup_progress = (current_folder / total_folders) * 100
            print(f"The progress is {device.backup_progress}")

        device.backup_status = "Up-to-date"
        device.backup_progress = 100

    except Exception as e:
        device.backup_status = "Error"
        print(f"Backup failed: {e}")

def start_backup_thread(device, device_manager):
    """Starts the backup in a background thread."""
    thread = threading.Thread(target=backup_device, args=(device, device_manager))
    thread.daemon = True  # Important: allows main thread to exit even if backup is running
    thread.start()
