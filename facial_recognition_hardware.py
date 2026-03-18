import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import RPi.GPIO as GPIO
import threading
import json
import os

# --- SERVO SETUP ------------------------------------------------------------
SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_servo_angle(angle):
    duty = 1 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

# --- KEYPAD SETUP -----------------------------------------------------------
ROW_PINS = [23, 22, 27, 17]
COL_PINS = [24, 25, 5]

KEYS = [
    ["9", "6", "3"],
    ["8", "5", "2"],
    ["7", "4", "1"],
    ["#", "0", "*"]
]

for row in ROW_PINS:
    GPIO.setup(row, GPIO.OUT)
    GPIO.output(row, GPIO.HIGH)

for col in COL_PINS:
    GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	    
def read_keypad():
    for r, row in enumerate(ROW_PINS):
        GPIO.output(row, GPIO.LOW)
        for c, col in enumerate(COL_PINS):
            if GPIO.input(col) == GPIO.LOW:
                GPIO.output(row, GPIO.HIGH)
                time.sleep(0.3)
                return KEYS[r][c]
        GPIO.output(row, GPIO.HIGH)
    return None

# --- PIN / CONFIG ------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_PIN = "11111"

def load_pin():
    if not os.path.exists(CONFIG_FILE):
        save_pin(DEFAULT_PIN)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f).get("pin", DEFAULT_PIN)

def save_pin(pin):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"pin": pin}, f)

# --- FACE RECOGNITION SETUP -------------------------------------------------
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())
known_face_encodings = data["encodings"]
known_face_names = data["names"]

if len(known_face_encodings) == 0:
    raise RuntimeError("No face encodings loaded. Re-run model_training.py")

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": 'RGB888', "size": (640, 480)},
    buffer_count=4
)
picam2.configure(config)
picam2.start()
time.sleep(2)

cv_scaler = 2
face_locations = []
face_encodings = []
face_names = []
frame_count = 0
start_time = time.time()
fps = 0

authorized_names = ["Tyrese"]
servo_open = False
servo_open_time = 0
SERVO_CLOSE_DELAY = 15

set_servo_angle(0)

# --- MENU SYSTEM -------------------------------------------------------------
in_menu = False
menu_lock = threading.Lock()

def print_menu():
    print("\n" + "="*30)
    print("      LOCKBOX MENU")
    print("="*30)
    print("1. Open LockBox")
    print("2. Change PIN")
    print("3. Troubleshoot")
    print("4. About")
    print("="*30)
    print("Enter option (1-4): ")

def open_lockbox():
    global servo_open, servo_open_time
    print("\n[LOCKBOX] Opening...")
    set_servo_angle(90)
    servo_open = True
    servo_open_time = time.time()
    print("[LOCKBOX] Door open. Will auto-close in 15 seconds.")
    print("Press # to close early.")
    
def change_pin():
    current_pin = load_pin()
    print("\n[CHANGE PIN] Enter new 5-digit PIN:")
    new_pin = ""
    while len(new_pin) < 5:
        key = read_keypad()
        if key and key.isdigit():
            new_pin += key
            print(f"  {'*' * len(new_pin)}", end='\r')
        time.sleep(0.1)

    print(f"\n[CHANGE PIN] Confirm new PIN:")
    confirm_pin = ""
    while len(confirm_pin) < 5:
        key = read_keypad()
        if key and key.isdigit():
            confirm_pin += key
            print(f"  {'*' * len(confirm_pin)}", end='\r')
        time.sleep(0.1)

    if new_pin == confirm_pin:
        save_pin(new_pin)
        print("\n[CHANGE PIN] PIN changed successfully!")
    else:
        print("\n[CHANGE PIN] PINs do not match. Try again.")

def troubleshoot():
    print("\n[TROUBLESHOOT] Testing servo...")
    print("  Moving to 90 degrees...")
    set_servo_angle(90)
    time.sleep(2)
    print("  Moving back to 0 degrees...")
    set_servo_angle(0)
    print("[TROUBLESHOOT] Servo test complete.")

def about():
    print("\n" + "="*30)
    print("         ABOUT LOCKBOX")
    print("="*30)
    print("  Ver:     1.0.0")
    print("  Name:    LockBox")
    print("  Origin:  ATU Galway")
    print("  Creator: Tyrese Mumia")
    print("="*30)
    
def handle_menu_input(key):
    global in_menu, servo_open, servo_open_time
    if key == "1":
        open_lockbox()
    elif key == "2":
        change_pin()
        in_menu = False
    elif key == "3":
        troubleshoot()
        in_menu = False
    elif key == "4":
        about()
        in_menu = False
    elif key == "#":
        if servo_open:
            print("\n[LOCKBOX] Closing early...")
            set_servo_angle(0)
            servo_open = False
        in_menu = False
        print("\n[MENU] Exited.")
    print_menu() if in_menu else None

def keypad_loop():
    global in_menu, servo_open, servo_open_time
    entered_pin = ""
    current_pin = load_pin()
    print("\n[LOCKBOX] Enter PIN to access menu:")

    while True:
        key = read_keypad()

        if key:
            with menu_lock:
                if not in_menu:
                    # PIN entry mode
                    if key == "#":
                        entered_pin = ""
                        print("\n[PIN] Cleared. Enter PIN:")
                    elif key.isdigit():
                        entered_pin += key
                        print(f"  {'*' * len(entered_pin)}", 
end='\r')

                        if len(entered_pin) == 5:
                            current_pin = load_pin()
                            if entered_pin == current_pin:
                                print("\n[PIN] Correct! Access granted.")
                                in_menu = True
                                print_menu()
                            else:
                                print("\n[PIN] Incorrect. Try again:")
                            entered_pin = ""
                else:
 # Menu mode
                    handle_menu_input(key)

        # Auto close servo check
        if servo_open and (time.time() - servo_open_time) >= SERVO_CLOSE_DELAY:
            print("\n[LOCKBOX] Auto closing...")
            set_servo_angle(0)
            servo_open = False
            in_menu = False
            print("\n[LOCKBOX] Enter PIN to access menu:")

        time.sleep(0.05)

# --- FACE RECOGNITION FUNCTIONS ----------------------------------------------
def process_frame(frame):
    global face_locations, face_encodings, face_names
    global servo_open, servo_open_time

    resized_frame = cv2.resize(frame, (0, 0), fx=(1/cv_scaler), fy=(1/cv_scaler))
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model='large')

    face_names = []
    authorized_face_detected = False

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
            if name in authorized_names:
                 authorized_face_detected = True
        face_names.append(name)

    with menu_lock:
        if authorized_face_detected and not servo_open:
            print("\n[FACE] Authorized face detected - opening door")
            set_servo_angle(90)
            servo_open = True
            servo_open_time = time.time()

        if servo_open and (time.time() - servo_open_time) >= SERVO_CLOSE_DELAY:
            print("\n[FACE] Auto closing door")
            set_servo_angle(0)
            servo_open = False

    return frame

def draw_results(frame):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
        cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), (244, 42, 3), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)

        if name in authorized_names:
            cv2.putText(frame, "Authorized", (left + 6, bottom + 23), font, 0.6, (0, 255, 0), 1)

    status = "OPEN" if servo_open else "CLOSED"
    color = (0, 255, 0) if servo_open else (0, 0, 255)
    cv2.putText(frame, f"Door: {status}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    if servo_open:
        remaining = int(SERVO_CLOSE_DELAY - (time.time() - servo_open_time))
        cv2.putText(frame, f"Closing in: {remaining}s", (10, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    return frame

def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps

# --- START KEYPAD THREAD -----------------------------------------------------
keypad_thread = threading.Thread(target=keypad_loop, daemon=True)
keypad_thread.start()

# --- MAIN CAMERA LOOP --------------------------------------------------------
while True:
    frame = picam2.capture_array()
    processed_frame = process_frame(frame)
    display_frame = draw_results(processed_frame)
    current_fps = calculate_fps()

    cv2.putText(display_frame, f"FPS: {current_fps:.1f}",
                (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow('Video', display_frame)

    if cv2.waitKey(1) == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
set_servo_angle(0)
pwm.stop()
GPIO.cleanup()
    
        










