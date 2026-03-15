import RPi.GPIO as GPIO
import time
SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setwarnings(False)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)
def set_angle(angle):
   duty = 1 + (angle / 18)
   pwm.ChangeDutyCycle(duty)
   time.sleep(0.8)
   pwm.ChangeDutyCycle(0)
   time.sleep(0.5)
print("Testing servo sweep...")
for angle in [0, 45, 90, 135, 180]:
   print(f"Moving to {angle} degrees")
   set_angle(angle)
print("Sweeping back...")
for angle in [180, 135, 90, 45, 0]:
   print(f"Moving to {angle} degrees")
   set_angle(angle)
pwm.stop()
GPIO.cleanup()
print("Done")
