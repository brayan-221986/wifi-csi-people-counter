# WiFi CSI People Counter — Fase 1: Validación de captura CSI

## Objetivo de la fase

Verificar que el sistema de captura CSI funciona correctamente:

```
ESP32 TX  ── WiFi ──>  ESP32 RX  ── UART ──>  PC
  (active_sta)          (active_ap)            (serial_monitor.py)
```

No se implementa ML, dataset, ni procesamiento de CSI. Solo se valida que el flujo de datos es estable y observable.

## Hardware requerido

- 2× ESP32 (cualquier modelo con WiFi)
- 2× cables USB-UART (para conectar cada ESP32 al PC)
- 1× PC con Linux

## Conexión

1. Conecta cada ESP32 al PC mediante cable USB-UART
2. El ESP32 **RX** (active_ap) crea un AP WiFi con SSID `CSI-AP`
3. El ESP32 **TX** (active_sta) se conecta automáticamente a `CSI-AP`
4. El ESP32 TX envía paquetes UDP a 20 paq/s → el RX captura CSI

## Instalación

### Dependencias del sistema

```bash
sudo apt-get install -y git wget flex bison gperf python3 python3-pip \
    python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util
```

### PlatformIO (gestión de firmware)

```bash
pip install platformio
```

### Herramientas Python

```bash
pip install -r tools/requirements.txt
```

## Compilar y flashear

### 1. ESP32 RX (active_ap)

```bash
cd firmware/active_ap
pio run --target menuconfig   # configurar CSI (opcional)
pio run --target upload
pio run --target monitor      # verificar que inicia como AP
```

### 2. ESP32 TX (active_sta)

```bash
cd firmware/active_sta
pio run --target menuconfig   # configurar SSID (CSI-AP) y PACKET_RATE
pio run --target upload
pio run --target monitor      # verificar que se conecta y envía tráfico
```

> **Nota:** Conecta un ESP32 a la vez para evitar conflictos de puerto serial.
>
> **Nota sobre baudrate:** El RX usa 115200 baud por defecto. Para aumentar a 921600 (recomendado para CSI a >20 paq/s):
> ```bash
> cd firmware/active_ap
> pio run --target menuconfig   # Component config → ESP-TOOL... → UART console baud rate → 921600
> pio run --target upload
> ```

## Ejecutar el monitor serial

```bash
python tools/serial_monitor.py --port /dev/ttyUSB0 --baud 921600
```

Filtra y muestra solo líneas que contienen `CSI_DATA`. Las líneas se imprimen sin modificar.

### Estadísticas en tiempo real

```bash
python tools/csi_stats.py --port /dev/ttyUSB0 --baud 921600
```

Muestra CSI/s, throughput estimado y detecta pérdidas de conexión.

## Cómo validar que CSI funciona

1. El ESP32 RX debe imprimir líneas `CSI_DATA` por el serial
2. El monitor serial en el PC debe mostrar esas líneas en tiempo real
3. Los valores CSI (entre corchetes) deben cambiar visiblemente al mover una persona cerca de los ESP32
4. El sistema debe mantenerse estable durante al menos 5 minutos

## Criterio de éxito

- [ ] RX (active_ap) inicia automáticamente como AP
- [ ] TX (active_sta) se conecta automáticamente al AP
- [ ] TX genera tráfico UDP continuo
- [ ] RX imprime `CSI_DATA` continuamente por UART
- [ ] PC recibe y muestra `CSI_DATA`
- [ ] Valores CSI cambian con movimiento humano
- [ ] Captura estable ≥ 5 minutos

## Estructura del proyecto

```
firmware/
├── active_ap/        # Firmware ESP32 RX (Access Point + CSI)
│   └── components/
│       └── esp32-csi-tool/   # Submodule (StevenMHernandez)
└── active_sta/       # Firmware ESP32 TX (Station + UDP)

tools/
├── serial_monitor.py  # Visualización en tiempo real
├── csi_stats.py       # Diagnóstico de throughput
└── requirements.txt   # Dependencias Python

captures/             # Reservado para futuras capturas
```

## Formato de salida CSI_DATA

Cada línea CSI_DATA tiene el formato CSV con 26 campos:

```
CSI_DATA,role,mac,rssi,rate,sig_mode,mcs,bandwidth,...,len,[valores CSI]
```

No se modifica el formato original de ESP32-CSI-Tool. El array CSI contiene pares I/Q (imaginario + real) como enteros con signo separados por espacios.
