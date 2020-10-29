import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711

class WeightSensor:
    GPIO_SCK = 5
    GPIO_DOUT = 6

    def __init__(self):
        self.hx = HX711(self.GPIO_SCK, self.GPIO_DOUT)
        self.hx.set_reading_format("MSB", "MSB")
        
    def init_sensor(self, output_per_gram, offset):
        self.hx.set_reference_unit(output_per_gram)
        self.hx.reset()
        self.hx.tare()
        self.hx.set_offset(offset)

    def get_value(self, times=5):
        try:
            val = self.hx.get_weight(5)
            self.hx.power_down()
            self.hx.power_up()
            time.sleep(0.1)
        except:
            print('get sensor value error!!!!')
            val = 0
        return val
         
        
    

    
