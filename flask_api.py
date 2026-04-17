from flask import Flask, jsonify, request
import RPi.GPIO as GPIO
import time
import threading
import json
import os
import requests
import base64
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

# --- CONFIG ------------------------------------------------------------------
BACKEND_URL = "http://50.17.122.196:3000"
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

# --- SERVO SETUP -------------------------------------------------------------
SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

servo_open = False
servo_lock = threading.Lock()

def set_servo_angle(angle):
    duty = 2.5 + (angle / 18)
    for _ in range(3):
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.3)
        pwm.ChangeDutyCycle(0)
        time.sleep(0.1)
# --- ULTRASONIC SETUP --------------------------------------------------------
TRIG = 16
ECHO = 20
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.1)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    start = time.time()
    stop = time.time()
    while GPIO.input(ECHO) == 0:
        start = time.time()
    while GPIO.input(ECHO) == 1:
        stop = time.time()
    elapsed = stop - start
    distance = (elapsed * 34300) / 2
    return round(distance, 1)

# --- CAMERA SETUP -----------------------------------------------------------
@app.route('/camera/snapshot', methods=['GET'])
def camera_snapshot():
    try:
        cam = Picamera2()
        cam.configure(cam.create_still_configuration(
            main={"format": 'RGB888', "size": (640, 480)}
        ))
        cam.start()
        time.sleep(1)
        frame = cam.capture_array()
        cam.stop()
        cam.close()
        time.sleep(0.5)

        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        return jsonify({"image": image_base64})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- PIN HELPERS -------------------------------------------------------------
def load_pin():
    if not os.path.exists(CONFIG_FILE):
        return "11111"
    with open(CONFIG_FILE, "r") as f:
        return json.load(f).get("pin", "11111")

def save_pin(pin):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"pin": pin}, f)

# --- ROUTES ------------------------------------------------------------------

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "lock": "open" if servo_open else "closed"
    })

@app.route('/lock/open', methods=['POST'])
def open_lock():
    global servo_open
    with servo_lock:
        set_servo_angle(90)
        servo_open = True
    return jsonify({"message": "Lock opened"})

@app.route('/lock/close', methods=['POST'])
def close_lock():
    global servo_open
    with servo_lock:
        set_servo_angle(0)
        servo_open = False
    return jsonify({"message": "Lock closed"})

@app.route('/mail/status', methods=['GET'])
def mail_status():
    try:
        distance = get_distance()
        mail_present = distance < 20
        return jsonify({
            "mail_present": mail_present,
            "distance_cm": distance
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pin/change', methods=['POST'])
def change_pin():
    data = request.get_json()
    new_pin = data.get("pin", "")
    if len(new_pin) != 5 or not new_pin.isdigit():
        return jsonify({"error": "PIN must be 5 digits"}), 400
    save_pin(new_pin)
    return jsonify({"message": "PIN updated successfully"})

@app.route('/pin/verify', methods=['POST'])
def verify_pin():
    data = request.get_json()
    entered = data.get("pin", "")
    current = load_pin()
    if entered == current:
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

# --- START -------------------------------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
