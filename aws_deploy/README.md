# Deploy WiFi-CSI Dashboard en AWS EC2

## 1. Subir archivos a EC2

```bash
# Desde tu PC (donde tienes este proyecto)
scp -r aws_deploy/app.py aws_deploy/templates aws_deploy/requirements.txt \
    ubuntu@YOUR_SERVER_IP:/var/www/html/wifi-csi/
```

## 2. Iniciar servidor en EC2

```bash
# Entrar a EC2
ssh ubuntu@YOUR_SERVER_IP

# Ir a la carpeta
cd /var/www/html/wifi-csi

# Instalar Flask (sin sudo, --user)
pip3 install --user flask

# Ejecutar con screen (se mantiene al cerrar SSH)
screen -S wifi-dash
python3 app.py

# Presiona Ctrl+A luego Ctrl+D para salir de screen
# Para volver: screen -r wifi-dash
```

Dashboard en: **http://YOUR_SERVER_IP:5000**

## 3. Enviar predicciones desde tu PC

```bash
python3 tools/live_predict.py /dev/ttyUSB1 460800 \
    --aws-url http://YOUR_SERVER_IP:5000
```

Cada predicción se enviará automáticamente al dashboard.

## Comandos útiles

| Acción | Comando |
|--------|---------|
| Volver a screen | `screen -r wifi-dash` |
| Ver screens activos | `screen -ls` |
| Detener servidor | `Ctrl+C` dentro de screen, luego `exit` |
| Ver logs | `screen -r wifi-dash` (o mirar salida en vivo) |

## Notas

- Sin sudo ni root — todo corre como usuario `ubuntu`
- Puerto 5000 debe estar abierto en Security Group de AWS
- Los datos se persisten en `predictions.json` (se pierden al reiniciar app)
- Para producción con Apache2 + mod_wsgi se necesita acceso root
