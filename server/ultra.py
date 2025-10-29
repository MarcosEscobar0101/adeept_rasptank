#!/usr/bin/python3
# Ultrasonic (BCM23=TRIG, BCM24=ECHO) con timeouts y media robusta

import RPi.GPIO as GPIO
import time
from statistics import median

# Pines (BCM)
Tr = 23  # TRIG  (físico 16)
Ec = 24  # ECHO  (físico 18)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(Tr, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(Ec, GPIO.IN)

def pulse_distance(timeout_s=0.03):
    """Mide una vez con timeouts; devuelve distancia en metros o None"""
    # pulso ~10-15us
    GPIO.output(Tr, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(Tr, GPIO.HIGH)
    time.sleep(0.000015)
    GPIO.output(Tr, GPIO.LOW)

    t0 = time.time()
    # esperar flanco de subida en ECHO
    while not GPIO.input(Ec):
        if time.time() - t0 > timeout_s:
            return None
    t1 = time.time()
    # esperar flanco de bajada en ECHO
    while GPIO.input(Ec):
        if time.time() - t1 > timeout_s:
            return None
    t2 = time.time()

    # velocidad del sonido ~340 m/s
    return (t2 - t1) * 340.0 / 2.0

def checkdist(samples=5):
    """Devuelve la mediana en metros de varias mediciones válidas"""
    vals = []
    for _ in range(samples):
        d = pulse_distance()
        if d is not None:
            vals.append(d)
        time.sleep(0.01)
    if not vals:
        return None
    return median(vals)

if __name__ == '__main__':
    try:
        while True:
            d = checkdist()
            if d is None:
                print("Sin lectura")
            else:
                print(f"{d*100:.2f} cm")
            time.sleep(0.2)
    finally:
        GPIO.cleanup((Tr, Ec))
