import RPI.GPIO as GPIO
import time

GPIO setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)

def measure_distance()
	#Trigger ultrasonic pulse
	GPIO.output(14, GPIO.HIGH)
	time.sleep(0.00001)
	GPIO.output(14, GPIO.LOW)

	#Measure time for the echo
	while GPIO.input(15) == 0:
		Start_time = time.time()
	while GPIO.input(15) == 1:
		end_time = time.time()
		
	#calculate distance in cm
	elapsed_time = end_time - start_time
	distance = (elapsed_time * 34300) / 2
	return distance
	
try:
	while True:
		dist = measure_distance()
		print(f"Distance: {dist: .2f} cm")
		 
		if dist < 3:
			print("You've got mail")
		else:
			print("No mail yet")
