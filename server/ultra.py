#!/usr/bin/python3
# ultra.py — HC-SR04 con BCM11=TRIG y BCM8=ECHO (SPI deshabilitado)
# Incluye pull-down en ECHO y timeouts para evitar bloqueos.

import RPi.GPIO as GPIO
import time
from statistics import median

TRIG_BCM = 11   # TRIG  (pin físico 23)
ECHO_BCM = 8    # ECHO  (pin físico 24) → usar divisor 2:1 a 3.3V
SPEED_SOUND = 340.0
ECHO_TIMEOUT = 0.12
SAMPLES = 5

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_BCM, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ECHO_BCM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def _pulse_once(timeout=ECHO_TIMEOUT):
    # Pulso de ~10-12 us
    GPIO.output(TRIG_BCM, GPIO.LOW);  time.sleep(0.000005)
    GPIO.output(TRIG_BCM, GPIO.HIGH); time.sleep(0.000012)
    GPIO.output(TRIG_BCM, GPIO.LOW)

    t0 = time.time()
    while not GPIO.input(ECHO_BCM):
        if time.time() - t0 > timeout:
            return None
    t1 = time.time()
    while GPIO.input(ECHO_BCM):
        if time.time() - t1 > timeout:
            return None
    t2 = time.time()

    return (t2 - t1) * SPEED_SOUND / 2.0  # metros

def checkdist():
    """Devuelve distancia en metros (o None si no hay lectura)."""
    vals = []
    for _ in range(SAMPLES):
        d = _pulse_once()
        if d is not None:
            vals.append(d)
        time.sleep(0.02)
    return median(vals) if vals else None

if __name__ == '__main__':
    try:
        print("Leyendo ultrasonido… (Ctrl+C para salir)")
        while True:
            d = checkdist()
            if d is None:
                print("Sin lectura (Vcc=5V, GND común, TRIG=BCM11, ECHO=BCM8 con divisor 2:1)")
            else:
                print(f"{d*100:.2f} cm")
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup((TRIG_BCM, ECHO_BCM))
