import os
import re
import numpy as np
from glob import glob
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, confusion_matrix, r2_score
from sklearn.preprocessing import StandardScaler
from scipy.stats import skew, kurtosis
import xgboost as xgb
import pickle

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'datos')
WINDOW_SIZE = 25
WINDOW_STEP = 10
N_CLASSES = 8

def bucket_label(label):
    return label

def parse_line(line):
    try:
        parts = line.strip().split(',')
        if len(parts) < 26:
            return None
        label = int(parts[-1]) if parts[-1].strip().isdigit() else None
        rssi = int(parts[3])
        noise_floor = int(parts[14])
        csi_len = parts[24].strip()
        if csi_len != '128':
            return None
        csi_str = parts[25]
        if not csi_str.startswith('['):
            return None
        raw = csi_str[1:].strip()
        if raw.endswith(']'):
            raw = raw[:-1]
        values = np.array([int(v) for v in raw.split()], dtype=np.float32)
        if len(values) < 28:
            return None
        sub = values[12:]  # skip 12 header bytes
        if len(sub) < 4:
            return None
        if len(sub) % 2 == 1:
            sub = sub[:-1]
        pairs = sub.reshape(-1, 2)
        amp = np.sqrt(pairs[:, 0]**2 + pairs[:, 1]**2)
        return amp, rssi, noise_floor, label
    except (ValueError, IndexError):
        return None

def parse_file(path):
    with open(path) as f:
        lines = f.readlines()
    parsed = []
    for line in lines[1:]:
        r = parse_line(line)
        if r is not None:
            parsed.append(r)
    return parsed

def extract_windows(data, label):
    blabel = bucket_label(label)
    X, y = [], []
    for start in range(0, len(data) - WINDOW_SIZE + 1, WINDOW_STEP):
        window = data[start:start + WINDOW_SIZE]
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
        X.append(feat)
        y.append(blabel)
    return np.array(X), np.array(y)

def main():
    print("=== CSI People Counter — Training ===")
    print(f"Window: {WINDOW_SIZE} lines, step {WINDOW_STEP}")
    print()

    files = sorted(glob(os.path.join(DATA_DIR, '*.csv')))
    print(f"Found {len(files)} files\n")

    train_data, test_data = {}, {}

    for f in files:
        basename = os.path.basename(f)
        m = re.match(r'csi_p(\d+)_s(\d+)_', basename)
        if not m:
            continue
        label = int(m.group(1))
        session = int(m.group(2))

        lines = parse_file(f)
        if not lines:
            print(f"  SKIP {basename}: no valid lines")
            continue

        d = train_data if session == 1 else test_data
        d.setdefault(label, []).extend(lines)
        print(f"  {basename}: p={label} s={session} lines={len(lines)}")

    def build_dataset(data_dict):
        Xs, ys = [], []
        for label, lines in sorted(data_dict.items()):
            wins, labs = extract_windows(lines, label)
            Xs.append(wins)
            ys.append(labs)
        if not Xs:
            return np.empty((0, 0)), np.empty(0)
        return np.vstack(Xs), np.concatenate(ys)

    X_train, y_train = build_dataset(train_data)
    X_test, y_test = build_dataset(test_data)
    n_feat = X_train.shape[1]

    print(f"\nTrain: {len(X_train)} windows, {n_feat} features")
    print(f"Test:  {len(X_test)} windows")
    print(f"Train dist: {dict(zip(*np.unique(y_train, return_counts=True)))}")
    print(f"Test  dist: {dict(zip(*np.unique(y_test, return_counts=True)))}")
    print()

    # Scale
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # === Random Forest (classification) ===
    print("--- RF Classifier ---")
    rf = RandomForestClassifier(n_estimators=300, max_depth=15, n_jobs=-1, random_state=42)
    rf.fit(X_train_s, y_train)
    p = rf.predict(X_test_s)
    acc = accuracy_score(y_test, p)
    print(f"  Acc={acc:.4f}")
    print(f"  CM:\n{confusion_matrix(y_test, p)}")

    # === Random Forest (regression, round to nearest int) ===
    print("\n--- RF Regressor ---")
    rfr = RandomForestRegressor(n_estimators=300, max_depth=15, n_jobs=-1, random_state=42)
    rfr.fit(X_train_s, y_train)
    p_reg = np.round(rfr.predict(X_test_s)).clip(0, 7).astype(int)
    acc_r = accuracy_score(y_test, p_reg)
    print(f"  Acc={acc_r:.4f}")
    print(f"  CM:\n{confusion_matrix(y_test, p_reg)}")

    # === XGBoost (classification) ===
    print("\n--- XGB Classifier ---")
    xgbc = xgb.XGBClassifier(n_estimators=400, max_depth=8, learning_rate=0.08,
                              subsample=0.8, colsample_bytree=0.8,
                              eval_metric='merror', random_state=42, n_jobs=-1)
    xgbc.fit(X_train_s, y_train, eval_set=[(X_test_s, y_test)], verbose=False)
    p_xgb = xgbc.predict(X_test_s)
    acc_x = accuracy_score(y_test, p_xgb)
    print(f"  Acc={acc_x:.4f}")
    print(f"  CM:\n{confusion_matrix(y_test, p_xgb)}")

    # === XGBoost (regression) ===
    print("\n--- XGB Regressor ---")
    xgbr = xgb.XGBRegressor(n_estimators=400, max_depth=8, learning_rate=0.08,
                              subsample=0.8, colsample_bytree=0.8,
                              random_state=42, n_jobs=-1)
    xgbr.fit(X_train_s, y_train, eval_set=[(X_test_s, y_test)], verbose=False)
    p_xgbr = np.round(xgbr.predict(X_test_s)).clip(0, N_CLASSES - 1).astype(int)
    acc_xr = accuracy_score(y_test, p_xgbr)
    print(f"  Acc={acc_xr:.4f}")
    print(f"  CM:\n{confusion_matrix(y_test, p_xgbr)}")

    # Pick best
    results = {
        'rf_clf': (rf, acc), 'rf_reg': (rfr, acc_r),
        'xgb_clf': (xgbc, acc_x), 'xgb_reg': (xgbr, acc_xr),
    }
    best_name = max(results, key=lambda k: results[k][1])
    best_model, best_acc = results[best_name]
    print(f"\n=== Best: {best_name} (Acc={best_acc:.4f}) ===")

    model_path = os.path.join(os.path.dirname(__file__), '..', 'model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': best_model,
            'scaler': scaler,
            'model_name': best_name,
            'window_size': WINDOW_SIZE,
            'n_classes': N_CLASSES,
            'is_regressor': 'reg' in best_name,
        }, f)
    print(f"Exported to {model_path}")

if __name__ == '__main__':
    main()
