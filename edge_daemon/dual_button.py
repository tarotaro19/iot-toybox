import logging
import time
import sys
import RPi.GPIO as GPIO

### Logger
logger = logging.getLogger("DualButton")
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(name)s\t%(funcName)s\t%(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

class DualButton:
    GPIO_BLUE_BUTTON = 23
    GPIO_RED_BUTTON =24

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.GPIO_BLUE_BUTTON, GPIO.IN)
        GPIO.setup(self.GPIO_RED_BUTTON, GPIO.IN)

    def button_callback(self, gpio_pin):
        if gpio_pin == self.GPIO_BLUE_BUTTON:
            self.callback_blue_button()
        elif gpio_pin == self.GPIO_RED_BUTTON:
            self.callback_red_button()
        
    def init(self, callback_blue_button, callback_red_button):
        logger.info('init')
        self.callback_blue_button = callback_blue_button
        self.callback_red_button = callback_red_button
        GPIO.add_event_detect(self.GPIO_BLUE_BUTTON, GPIO.FALLING, callback=self.button_callback, bouncetime=500)
        GPIO.add_event_detect(self.GPIO_RED_BUTTON, GPIO.FALLING, callback=self.button_callback, bouncetime=500)


blue_count = 0
red_count = 0
def callback_blue_button():
    global blue_count 
    blue_count = blue_count+1
    logger.info("press blue button - " + str(blue_count))

def callback_red_button():
    global red_count
    red_count = red_count+1
    logger.info("press red button - " + str(red_count))
        
def main():
    dual_button = DualButton()
    dual_button.init(callback_blue_button, callback_red_button)
    while True:
        time.sleep(1)
         
if __name__ == "__main__":
    main()
