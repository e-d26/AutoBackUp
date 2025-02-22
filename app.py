from flask import Flask, render_template, redirect, url_for, send_from_directory, request, flash
import subprocess
import os
from werkzeug.utils import secure_filename
import uuid
import json
from my_config import BACKUP_LOCATION, DEVICE_IMAGES_PATH, JSON_PATH
from backup_system import start_backup_thread
from device_manager import DeviceManager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = DEVICE_IMAGES_PATH
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SECRET_KEY'] = 'super secret key'

device_manager = DeviceManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_connected_device_info():
    try:
        adb_devices_output = subprocess.check_output(["adb", "devices", "-l"], text=True)
        for line in adb_devices_output.splitlines():
            if "device" in line and not line.startswith("List of devices"):
                parts = line.split()
                serial = parts[0]
                vendor_id, product_id = None, None
                for part in parts:
                    if "vendor:" in part:
                        vendor_id = part.split(":")[1]
                    if "product:" in part:
                        product_id = part.split(":")[1]
                return serial, vendor_id, product_id
    except Exception as e:
        print(f"Error getting connected device info: {e}")
    return None, None, None

@app.route("/", methods=['GET', 'POST'])
def index():
    devices = device_manager.get_all_devices()
    return render_template("index.html", devices=devices, device_images_path=DEVICE_IMAGES_PATH)

@app.route("/start_backup/<int:vendor_id>/<int:product_id>")
def start_backup(vendor_id, product_id):
    device = device_manager.get_device(vendor_id, product_id)
    if device:
        start_backup_thread(device, device_manager)
        device.backup_status = "Backing Up"
    return redirect(url_for("index"))

@app.route('/' + DEVICE_IMAGES_PATH + '/<path:filename>')
def send_image(filename):
    return send_from_directory(DEVICE_IMAGES_PATH, filename)

@app.route("/add_device", methods=['GET', 'POST'])
def add_device():
    if request.method == 'POST':
        serial, vendor_id, product_id = get_connected_device_info()
        if not vendor_id or not product_id:
            flash("Could not retrieve vendor ID or product ID. Ensure the device is connected.")
            return redirect(url_for("index"))
        
        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        device = device_manager.get_device(int(vendor_id), int(product_id))

        phone_id = str(uuid.uuid4())
        phone_name = request.form.get("phone_name")
        image_filename = filename

        json_data = {
            "phone_id": phone_id,
            "phone_name": phone_name,
            "backup_location": "/sdcard/Documents/BackupConfig",
            "image_filename": image_filename,
            "folders_to_backup": []
        }
        json_string = json.dumps(json_data, indent=4)
        if device:
            if device.push_json(json_string):
                device_manager.add_device(int(vendor_id), int(product_id))
                flash("Device successfully added and picture upload!")
            else:
                flash("Could not upload JSON config file! Ensure adb is working.")

            return redirect(url_for("index"))
    return render_template("add_device.html")

@app.before_first_request
def start_monitoring():
    device_manager.start_monitoring()

@app.teardown_appcontext
def shutdown_session(exception=None):
    device_manager.stop_monitoring()
    print("Closing the program")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
