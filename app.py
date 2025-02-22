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
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}  # what file ext are allowed
app.config['SECRET_KEY'] = 'super secret key'  # Required for flash messages and sessions

device_manager = DeviceManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/", methods=['GET', 'POST'])  # modified to handle the post request
def index():
    devices = device_manager.get_all_devices()
    return render_template("index.html", devices=devices, device_images_path=DEVICE_IMAGES_PATH)

@app.route("/start_backup/<int:vendor_id>/<int:product_id>")
def start_backup(vendor_id, product_id):
    device = device_manager.get_device(vendor_id, product_id)
    if device:
        start_backup_thread(device, device_manager)  # Pass device_manager instance
        device.backup_status = "Backing Up"
    return redirect(url_for("index"))

@app.route('/' + DEVICE_IMAGES_PATH + '/<path:filename>')
def send_image(filename):
    return send_from_directory(DEVICE_IMAGES_PATH, filename)

@app.route("/add_device", methods=['GET', 'POST'])  # Modified route and method
def add_device():
    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        product_id = request.form.get('product_id')
        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        device = device_manager.get_device(int(vendor_id), int(product_id))

        # Create JSON data.
        phone_id = str(uuid.uuid4())
        phone_name = request.form.get("phone_name")
        image_filename = filename  # save the image name

        json_data = {
            "phone_id": phone_id,
            "phone_name": phone_name,
            "backup_location": "/sdcard/Documents/BackupConfig",
            "image_filename": image_filename,
            "folders_to_backup": []  # add folders to back up here
        }
        # create json file
        json_string = json.dumps(json_data, indent=4)
        if device:
            if device.push_json(json_string):  # add the device to config
                device_manager.add_device(int(vendor_id), int(product_id))
                flash("Device sucessfully added and picture upload!")
            else:
                flash("Could not upload JSON config file! Ensure adb is working.")

            return redirect(url_for("index"))
    return render_template("add_device.html")

@app.before_request
def start_monitoring():
    if not hasattr(device_manager, 'status_thread'):
        device_manager.start_monitoring()

@app.teardown_appcontext
def shutdown_session(exception=None):
    device_manager.stop_monitoring()
    print("Closing the program")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
