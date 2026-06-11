#!/usr/bin/env python3
"""
csi_stats.py — Diagnóstico en tiempo real del flujo CSI.
Mide CSI/s, throughput estimado, y detecta pérdidas de conexión.
"""

import argparse
import serial
import sys
import signal
import time
import threading

class CSIStats:
    def __init__(self):
        self.count = 0
        self.lock = threading.Lock()
        self.running = True

    def increment(self):
        with self.lock:
            self.count += 1

    def reset_count(self):
        with self.lock:
            c = self.count
            self.count = 0
            return c

    def stop(self):
        self.running = False


def reporter(stats: CSIStats, interval: float = 1.0):
    """Imprime estadísticas cada `interval` segundos."""
    while stats.running:
        time.sleep(interval)
        c = stats.reset_count()
        if c > 0:
            print(f"\r  CSI/s: {c:4d}  |  {c // interval:4d} paq/s  |  {c * 200:6d} bytes/s (~{c * 200 / 1024:.1f} KB/s)    ", end="", file=sys.stderr)
        else:
            print(f"\r  CSI/s:    0  |  SIN DATOS  |  ¿Conexión perdida?                     ", end="", file=sys.stderr)
        sys.stderr.flush()


def main():
    parser = argparse.ArgumentParser(
        description="Estadísticas en tiempo real del flujo CSI"
    )
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0",
                        help="Puerto serial (default: /dev/ttyUSB0)")
    parser.add_argument("-b", "--baud", type=int, default=921600,
                        help="Baudrate (default: 921600)")
    parser.add_argument("-i", "--interval", type=float, default=1.0,
                        help="Intervalo de reporte en segundos (default: 1.0)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error abriendo {args.port}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Conectado a {args.port} a {args.baud} baud", file=sys.stderr)
    print(f"Reportando cada {args.interval}s (Ctrl+C para salir)", file=sys.stderr)
    print("---", file=sys.stderr)

    stats = CSIStats()

    t = threading.Thread(target=reporter, args=(stats, args.interval), daemon=True)
    t.start()

    try:
        while True:
            line = ser.readline()
            if not line:
                continue
            try:
                text = line.decode("utf-8", errors="replace").strip()
            except UnicodeDecodeError:
                continue
            if "CSI_DATA" in text:
                stats.increment()
    except serial.SerialException as e:
        print(f"\nError de conexión: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.", file=sys.stderr)
    finally:
        stats.stop()
        if ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
