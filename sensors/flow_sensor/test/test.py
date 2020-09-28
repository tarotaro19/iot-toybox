import sys
import time
import RPi.GPIO as GPIO

class Pulse:
    count = 0

def event_callback(gpio_pin):
    Pulse.count+=1
    print("detect pulse : count - " + str(Pulse.count))

def main():
    GPIO_INPUT_PIN = 14
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_INPUT_PIN, GPIO.IN)
    GPIO.add_event_detect(GPIO_INPUT_PIN, GPIO.RISING, callback=event_callback, bouncetime=1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nbreak')
        GPIO.remove_event_detect(GPIO_INPUT_PIN)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
