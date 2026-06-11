import os, sys, pickle, time, json
import numpy as np
import serial
try:
    import requests
except ImportError:
    requests = None

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model.pkl')

with open(MODEL_PATH, 'rb') as f:
    pkg = pickle.load(f)

model = pkg['model']
scaler = pkg['scaler']
window_size = pkg['window_size']
n_classes = pkg.get('n_classes', 8)
is_regressor = pkg.get('is_regressor', False)

BUCKET_LABELS = {
    4: {0: '0', 1: '1-2', 2: '3-5', 3: '6-7'},
    8: {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7'},
}

def parse_line(line):
    try:
        parts = line.strip().split(',')
        if len(parts) < 26:
            return None
        rssi = int(parts[3])
        noise_floor = int(parts[14])
        csi_str = parts[25]
        if not csi_str.startswith('['):
            return None
        raw = csi_str[1:].strip()
        if raw.endswith(']'):
            raw = raw[:-1]
        values = np.array([int(v) for v in raw.split()], dtype=np.float32)
        if len(values) != 128:
            return None
        sub = values[12:]
        if len(sub) != 116:
            return None
        pairs = sub.reshape(-1, 2)
        amp = np.sqrt(pairs[:, 0]**2 + pairs[:, 1]**2)
        return amp, rssi, noise_floor
    except (ValueError, IndexError):
        return None

def extract_features_from_window(window):
    amps = np.array([w[0] for w in window])
    rssis = np.array([w[1] for w in window])
    nfs = np.array([w[2] for w in window])
    mu = amps.mean(axis=0)
    va = amps.var(axis=0)
    mn = amps.min(axis=0)
    mx = amps.max(axis=0)
    feat = np.concatenate([mu, va, mn, mx,
                           [rssis.mean(), rssis.var(),
                            nfs.mean(), nfs.var()]])
    return feat

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB1'
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 460800
    aws_url = None
    for i, a in enumerate(sys.argv):
        if a == '--aws-url' and i + 1 < len(sys.argv):
            aws_url = sys.argv[i + 1].rstrip('/')

    ser = serial.Serial(port, baud, timeout=0.1)
    time.sleep(2)
    ser.reset_input_buffer()

    buffer = []
    last_prediction_time = 0
    label_map = BUCKET_LABELS.get(n_classes, BUCKET_LABELS[8])

    print(f"Listening on {port} at {baud} baud")
    print(f"Window: {window_size} lines, {n_classes} classes")
    if aws_url:
        print(f"AWS URL: {aws_url}")
    print("Predictions (every ~1s):")
    print()

    while True:
        line = ser.readline()
        if not line:
            continue
        try:
            text = line.decode('utf-8', errors='replace').strip()
        except:
            continue
        parsed = parse_line(text)
        if parsed is None:
            continue
        buffer.append(parsed)
        if len(buffer) >= window_size:
            feat = extract_features_from_window(buffer[-window_size:])
            feat_s = scaler.transform(feat.reshape(1, -1))
            if is_regressor:
                pred_raw = model.predict(feat_s)[0]
                pred = int(np.round(pred_raw).clip(0, n_classes - 1))
            else:
                pred = int(model.predict(feat_s)[0])
            label = label_map.get(pred, str(pred))
            ts = time.strftime('%H:%M:%S')
            print(f"{ts}  PREDICTION,{label}")
            sys.stdout.flush()
            if aws_url and requests:
                try:
                    requests.post(f"{aws_url}/api/predict", json={'prediction': int(pred), 'timestamp': ts}, timeout=2)
                except Exception:
                    pass
            buffer = buffer[-window_size:]  # keep last window_size for overlap

if __name__ == '__main__':
    main()
