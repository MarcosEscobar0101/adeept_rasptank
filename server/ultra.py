#!/usr/bin/python3
import RPi.GPIO as GPIO, time
from statistics import median

Tr = 23  # TRIG (BCM)
Ec = 24  # ECHO (BCM)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(Tr, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(Ec, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def pulse_distance(timeout_s=0.12):
    # Pulso de ~10-15us
    GPIO.output(Tr, GPIO.LOW)
    time.sleep(0.000005)
    GPIO.output(Tr, GPIO.HIGH)
    time.sleep(0.000012)
    GPIO.output(Tr, GPIO.LOW)

    # Esperar flanco de subida con timeout
    t0 = time.time()
    while not GPIO.input(Ec):
        if time.time() - t0 > timeout_s:
            return None
    t1 = time.time()

    # Esperar flanco de bajada con timeout
    while GPIO.input(Ec):
        if time.time() - t1 > timeout_s:
            return None
    t2 = time.time()

    return (t2 - t1) * 340.0 / 2.0  # metros

def checkdist(samples=5):
    vals = []
    for _ in range(samples):
        d = pulse_distance()
        if d is not None:
            vals.append(d)
        time.sleep(0.02)
    if not vals:
        return None
    return median(vals)

if __name__ == '__main__':
    # Tiempo de asentamiento
    time.sleep(0.2)
    try:
        while True:
            d = checkdist()
            if d is None:
                print("Sin lectura (revisa Vcc=5V, GND común, divisor en ECHO, cableado TRIG/ECHO)")
            else:
                print(f"{d*100:.2f} cm")
            time.sleep(0.3)
    finally:
        GPIO.cleanup((Tr, Ec))
