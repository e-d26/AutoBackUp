import threading
import time
import json
import os
import subprocess
import re

class Device:
    def __init__(self, vendor_id, product_id):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.serial = None  # get the serial id
        self.name = None
        self.status = "Offline"
        self.backup_status = "Unknown"  # "Up-to-date", "Needs Backup", "Backing Up"
        self.backup_progress = 0  # 0-100 for percentage
        self.image_filename = None  # Filename in static/device_images/
        self.phone_id = None  # Extracted from JSON
        self.device = None
        self.identified = False  # New var

    def connect(self):
        self.serial = self.get_serial()
        if (self.serial):
            self.status = "Online"
            try:  # get the device name
                if self.check_json():
                    temp_file = "temp_phone_info.json"
                    self.pull_json(temp_file)

                    with open(temp_file, "r") as f:
                        phone_info = json.load(f)

                    self.phone_id = phone_info.get("phone_id")
                    self.name = phone_info.get("phone_name")
                    self.image_filename = phone_info.get("image_filename")
                    self.identified = True  # Device has now been successfully identified

                    os.remove(temp_file)  # remove temp
                else:
                    self.identified = False  # json does not exist
            except:
                print("Failed to load device name")
        else:
            self.status = "Offline"

    def disconnect(self):
        self.status = "Offline"
        self.backup_status = "Unknown"
        self.backup_progress = 0
        self.device = None

    def get_serial(self):
        try:
            # Use adb devices command to get the list of connected devices
            adb_devices_output = subprocess.check_output(["adb", "devices"], text=True)
            # Find the line containing the serial and the device status
            for line in adb_devices_output.splitlines():
                match = re.match(r"(\w+)\s+device", line)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"Error getting serial: {e}")
            return None

    def check_json(self):
        # Check if the phone_info.json exists on the device
        check_command = f"adb -s {self.serial} shell 'ls {JSON_PATH}'"
        result = subprocess.run(check_command, shell=True, capture_output=True, text=True)
        # If the command was successful (return code 0) and the file exists (no "No such file" in output)
        return result.returncode == 0 and "No such file" not in result.stderr

    def pull_json(self, temp_file):
        pull_command = f"adb -s {self.serial} pull {JSON_PATH} {temp_file}"
        result = subprocess.run(pull_command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error pulling JSON file: {result.stderr}")
        return result.returncode == 0

    def push_json(self, json_string):
        # Create a temporary file to store the JSON data
        temp_file = "temp_phone_info.json"
        try:
            # Write the JSON string to the temporary file
            with open(temp_file, "w") as f:
                f.write(json_string)

            # Push the temporary file to the device using adb push command
            push_command = f"adb -s {self.serial} push {temp_file} {JSON_PATH}"
            result = subprocess.run(push_command, shell=True, capture_output=True, text=True)

            # Check the result of the adb push command
            if result.returncode != 0:
                print(f"Error pushing JSON file: {result.stderr}")
                return False  # Indicate failure

            # If the push command was successful, return True
            return True  # Indicate success
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False  # Indicate failure
        finally:
            # Remove the temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)


class DeviceManager:
    def __init__(self):
        self.devices = {}  # dict of Device objects. key = vendor_id, product_id tuple.
        self.lock = threading.Lock()  # protecting this object
        self.running = True

    def add_device(self, vendor_id, product_id):
        with self.lock:
            self.devices[(vendor_id, product_id)] = Device(vendor_id, product_id)

    def remove_device(self, vendor_id, product_id):
        with self.lock:
            if (vendor_id, product_id) in self.devices:
                self.devices.pop((vendor_id, product_id))

    def get_device(self, vendor_id, product_id):
        with self.lock:
            return self.devices.get((vendor_id, product_id))

    def update_device_status(self):
        while self.running:
            with self.lock:
                for device in self.devices.values():
                    device.connect()
            time.sleep(5)  # Check every 5 seconds

    def start_monitoring(self):
        self.status_thread = threading.Thread(target=self.update_device_status)
        self.status_thread.daemon = True  # Exit when the main thread exits
        self.status_thread.start()

    def stop_monitoring(self):
        self.running = False
        self.status_thread.join()  # Wait for the thread to finish

    def get_all_devices(self):
        with self.lock:
            return list(self.devices.values())
