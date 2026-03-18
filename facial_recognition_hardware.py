import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import RPi.GPIO as GPIO
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
# Start with door closed
set_servo_angle(0)
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
   if authorized_face_detected and not servo_open:
       print("[SERVO] Opening door")
       set_servo_angle(90)
       servo_open = True
       servo_open_time = time.time()
   if servo_open and (time.time() - servo_open_time) >= SERVO_CLOSE_DELAY:
       print("[SERVO] Auto closing")
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
