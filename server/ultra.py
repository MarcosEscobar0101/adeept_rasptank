#!/usr/bin/python3
# ultra.py — Lectura de ultrasonido con RPi.GPIO (BCM23=TRIG, BCM25=ECHO)
# Seguro en Bookworm: timeouts, pull-down y mediana de muestras

import RPi.GPIO as GPIO
import time
from statistics import median

# ==== CONFIGURA TUS PINES (modo BCM) ====
TRIG_BCM = 23   # TRIG -> pin físico 16
ECHO_BCM = 25   # ECHO -> pin físico 22 (usa divisor 2:1 para 3.3V!)
# ========================================

# Parámetros
SPEED_SOUND = 340.0           # m/s
ECHO_TIMEOUT = 0.12           # s (tiempo máx esperando flancos)
SETTLE_TIME = 0.2             # s (asentamiento al iniciar)
SAMPLES = 5                   # nº de lecturas para la mediana

def _setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    # TRIG en LOW
    GPIO.setup(TRIG_BCM, GPIO.OUT, initial=GPIO.LOW)
    # ECHO como entrada con pull-down para evitar flotación
    GPIO.setup(ECHO_BCM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def _pulse_distance_once(timeout=ECHO_TIMEOUT):
    """Devuelve una distancia en metros o None si hubo timeout."""
    # Pulso de ~10-12us en TRIG
    GPIO.output(TRIG_BCM, GPIO.LOW); time.sleep(0.000005)
    GPIO.output(TRIG_BCM, GPIO.HIGH); time.sleep(0.000012)
    GPIO.output(TRIG_BCM, GPIO.LOW)

    # Esperar flanco de subida en ECHO
    t0 = time.time()
    while not GPIO.input(ECHO_BCM):
        if time.time() - t0 > timeout:
            return None
    t1 = time.time()

    # Esperar flanco de bajada en ECHO
    while GPIO.input(ECHO_BCM):
        if time.time() - t1 > timeout:
            return None
    t2 = time.time()

    # Distancia: (tiempo ida y vuelta * velocidad) / 2
    return (t2 - t1) * SPEED_SOUND / 2.0

def distance_m(samples=SAMPLES):
    """Medición robusta: mediana de varias muestras. Retorna metros o None."""
    vals = []
    for _ in range(samples):
        d = _pulse_distance_once()
        if d is not None:
            vals.append(d)
        time.sleep(0.02)
    if not vals:
        return None
    return median(vals)

# API simple que usan otros módulos:
def checkdist():
    """Compatibilidad con código existente: devuelve distancia (m) o None."""
    return distance_m()

if __name__ == '__main__':
    # Autotest por consola
    try:
        _setup_gpio()
        time.sleep(SETTLE_TIME)
        print("Leyendo ultrasonido… (Ctrl+C para salir)")
        while True:
            d = distance_m()
            if d is None:
                print("Sin lectura (revisa Vcc=5V, GND común, TRIG=BCM23, "
                      "ECHO=BCM25 con divisor a 3.3V)")
            else:
                print(f"{d*100:.2f} cm")
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            GPIO.cleanup((TRIG_BCM, ECHO_BCM))
        except Exception:
            GPIO.cleanup()
