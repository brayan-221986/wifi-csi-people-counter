#!/usr/bin/env python3
"""
serial_monitor.py — Lee el puerto serial del ESP32 RX y muestra
líneas CSI_DATA en tiempo real. Sin parseo, sin guardar.
"""

import argparse
import serial
import sys
import signal

def main():
    parser = argparse.ArgumentParser(
        description="Monitor serial del ESP32 RX — muestra líneas CSI_DATA en tiempo real"
    )
    parser.add_argument("-p", "--port", default="/dev/ttyUSB0",
                        help="Puerto serial (default: /dev/ttyUSB0)")
    parser.add_argument("-b", "--baud", type=int, default=921600,
                        help="Baudrate (default: 921600)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error abriendo {args.port}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Conectado a {args.port} a {args.baud} baud", file=sys.stderr)
    print(f"Mostrando líneas CSI_DATA (Ctrl+C para salir)", file=sys.stderr)
    print("---")

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
                print(text)
                sys.stdout.flush()
    except serial.SerialException as e:
        print(f"\nError de conexión: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.", file=sys.stderr)
    finally:
        if ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
