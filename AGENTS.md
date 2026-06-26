# AGENTS.md — Reglas para el agente

## FASE ACTUAL
Validación de pipeline con modelo en vivo (inferencia en tiempo real).

## OBJETIVO
```
ESP32 TX → WiFi → ESP32 RX → CSI → UART 460800 → PC → predict.py → PREDICTION
```

## CRITERIO DE ÉXITO
1. ✅ RX inicia automáticamente
2. ✅ TX conecta automáticamente
3. ✅ TX genera tráfico UDP a 20 Hz
4. ✅ RX imprime CSI_DATA (460800 baud)
5. ✅ PC visualiza CSI_DATA y predice

## HISTORIAL DE SESIONES

### Sesión 1 — Validación de captura CSI
- Pipeline CSI probada: 25 Hz, 100% líneas limpias a 460800 baud.
- Analizado dataset: 16 archivos, mixed 128/384 subcarriers.
- Corrupción CSI era PC-side (no firmware).
- vTaskDelay bug corregido en sockets_component.h.

### Sesión 2 — Entrenamiento de modelo
- `tools/train_model.py` creado: parsea dataset (filtra líneas 128-length), extrae amplitud desde pares I/Q.
- Sliding window: 25 líneas, step 10 → 252/256 ventanas train/test.
- Features: 58 amplitudes × 4 stats (mean/var/min/max) + 4 global = 236.
- RF + XGBoost (clasificador y regresor), split por sesión (s1 train/s2 test).
- Mejor modelo: XGBoost classifier, 58% accuracy (4 buckets: 0/1-2/3-5/6-7).
- `model.pkl` exportado, `tools/live_predict.py` creado.

### Sesión 3 — Pipeline completa (11 Jun 2026)
- **TX revivido**: full erase + esptool direct reflash resolvió problema de firmware corrupto. TX output: `ssn:0, winSize:64` (BA debug de ESP-IDF).
- **RX reconfirmado**: firmware active_ap con `CONFIG_ESP_CONSOLE_UART_CUSTOM=y` y `BAUDRATE=460800`.
- **CSI_DATA fluyendo**: RX imprime líneas con 128 subcarriers (LLTF-only, metadata dice 384).
- **fixed live_predict.py**: filtro `csi_len != '128'` removido — el campo metadata reporta `data->len` (384) no `data_len` (128). Ahora parsea por valores reales en brackets.
- **Pipeline extremo a extremo verificada**: TX → UDP → RX → CSI → UART → PC → model.pkl → PREDICTION.
- **Limitación**: modelo entrenado en modo STA en laboratorio diferente; predice "0" consistentemente en entorno actual (AP mode).

## PROBLEMAS CONOCIDOS
1. **Modelo no sensible al entorno actual**: necesita reentrenarse con datos del entorno vivo (o recolectar nuevo dataset etiquetado en AP mode).
2. **TX output ruidoso**: WiFi BA debug messages (`ssn:0, winSize:64`) saturan USB0. No afecta funcionalidad pero es molesto.
3. **RX baud rate**: bootloader a 115200, app cambia a 460800 → ~0.5s de basura al inicio.

## PRÓXIMOS PASOS
1. Probar estabilidad ≥ 5 min.
2. Recolectar CSI en vivo con etiquetas para reentrenar modelo.
3. Si modelo no mejora, experimentar con features (más estadísticas, ventanas más grandes).
