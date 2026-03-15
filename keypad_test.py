import RPi.GPIO as GPIO
import time
ROW_PINS = [23, 22, 27, 17]
COL_PINS = [24, 25, 5]
KEYS = [
   ["*", "#", "0"],
   ["7", "9", "8"],
   ["4", "6", "5"],
   ["1", "3", "2"]
]
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for row in ROW_PINS:
   GPIO.setup(row, GPIO.OUT)
   GPIO.output(row, GPIO.HIGH)
for col in COL_PINS:
   GPIO.setup(col, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print("Press keys on your keypad (Ctrl+C to quit)...")
try:
   while True:
       for r, row in enumerate(ROW_PINS):
           GPIO.output(row, GPIO.LOW)
           for c, col in enumerate(COL_PINS):
               if GPIO.input(col) == GPIO.LOW:
                   print(f"Key pressed: {KEYS[r][c]}")
                   time.sleep(0.3)
           GPIO.output(row, GPIO.HIGH)
       time.sleep(0.05)
except KeyboardInterrupt:
   GPIO.cleanup()
   print("Done")
