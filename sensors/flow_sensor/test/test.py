import sys
import time
import RPi.GPIO as GPIO
import threading
import itertools
import math
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

pulse_count = 0
lock = threading.Lock()
graph_x = []
graph_y = []

    
def event_callback(gpio_pin):
    global pulse_count
    global lock

    lock.acquire()
    pulse_count+=1
    lock.release()
    #print("detect pulse : count - " + str(pulse_count))


def draw_graph():
    plt.cla()
    plt.title('pulse count of flow sensor')
    plt.xlabel('time[sec]') 
    plt.ylabel('pulse [pulse/sec]')
    plt.ylim([0, 150])
    data_length = len(graph_x)
    if data_length > 10:
        plt.plot(graph_x[data_length-10:], graph_y[data_length-10:])
    else:
        plt.plot(graph_x, graph_y)
    plt.pause(0.1)
    
def main():
    global pulse_count
    global lock
    
    GPIO_INPUT_PIN = 14
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_INPUT_PIN, GPIO.IN)
    GPIO.add_event_detect(GPIO_INPUT_PIN, GPIO.RISING, callback=event_callback, bouncetime=1)

    fig = plt.figure(figsize=(10, 6))

    #graph_thread = threading.Thread(target=draw_graph)
    #graph_thread.start()

    time_count = 0
    try:
        while True:
            time.sleep(1)
            print("pulse count - " + str(pulse_count) + "[count/sec]")
            graph_x.append(time_count)
            graph_y.append(pulse_count)
            draw_graph()
            
            lock.acquire()
            pulse_count = 0
            lock.release()
            time_count+=1
            
    except KeyboardInterrupt:
        print('\nbreak')
        GPIO.remove_event_detect(GPIO_INPUT_PIN)
        GPIO.cleanup()

if __name__ == "__main__":
    main()
