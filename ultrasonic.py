import RPi.GPIO as GPIO
import time
TRIG = 16
ECHO = 20
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
def get_distance():
   GPIO.output(TRIG, False)
   time.sleep(0.05)
   GPIO.output(TRIG, True)
   time.sleep(0.00001)
   GPIO.output(TRIG, False)
   timeout_start = time.time()
   while GPIO.input(ECHO) == 0:
       pulse_start = time.time()
       if time.time() - timeout_start > 0.1:
           print("Timeout waiting for ECHO to go HIGH - check wiring")
           return None
   timeout_start = time.time()
   while GPIO.input(ECHO) == 1:
       pulse_end = time.time()
       if time.time() - timeout_start > 0.1:
           print("Timeout waiting for ECHO to go LOW - object too far?")
           return None
   pulse_duration = pulse_end - pulse_start
   distance = pulse_duration * 17150
   return round(distance, 2)
print("Testing ultrasonic sensor (Ctrl+C to stop)...")
try:
   while True:
       dist = get_distance()
       if dist is not None:
           print(f"Distance: {dist} cm")
       time.sleep(0.5)
except KeyboardInterrupt:
   GPIO.cleanup()
   print("Done")
