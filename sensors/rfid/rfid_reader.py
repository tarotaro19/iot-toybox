import logging
import time
import sys
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from mfrc522 import MFRC522
        
def main():
    reader = SimpleMFRC522()
    #mfrc522_mod = MFRC522()

    ### read data
    try:
        while True:
            print("Hold a tag near the reader")
            id, text = reader.read()
            print("ID: %s\nText: %s" % (id,text))
            time.sleep(5)
    except KeyboardInterrupt:
        GPIO.cleanup()
        raise

    '''
    ### write data
    try:
        print("Hold a tag near the reader")
        write_text = 'test test'
        id, text = reader.write(write_text)
        print("Write result - ID: %s\nText: %s" % (id,text))
        GPIO.cleanup()
    except :
        print('error')
   '''
         
if __name__ == "__main__":
    main()
