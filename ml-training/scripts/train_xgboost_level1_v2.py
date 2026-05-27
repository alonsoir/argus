import pandas as pd
import numpy as np
import hashlib
import json
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve, classification_report, confusion_matrix
import xgboost as xgb

# ── Regla de oro: Wednesday BLIND ──────────────────────────────────────────
BASE = '/vagrant/ml-training/datasets/CIC-IDS-2017/MachineLearningCVE'
WEDNESDAY_PATH = f'{BASE}/Wednesday-workingHours.pcap_ISCX.csv'
WEDNESDAY_MD5_EXPECTED = 'bf0dd7e9d991987df4e13ea58a1b409c'

def verify_wednesday_seal():
    with open(WEDNESDAY_PATH, 'rb') as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    assert md5 == WEDNESDAY_MD5_EXPECTED, f'Wednesday md5 MISMATCH: {md5}'
    print(f'[SEAL] Wednesday md5 OK: {md5}')

verify_wednesday_seal()

# ── Features level1 (23) — docs/xgboost/features.md ───────────────────────
LEVEL1_FEATURES = [
    ' Flow Duration',
    ' Total Fwd Packets',
    ' Total Backward Packets',
    'Total Length of Fwd Packets',
    ' Total Length of Bwd Packets',
    ' Fwd Packet Length Max',
    ' Fwd Packet Length Min',
    ' Fwd Packet Length Mean',
    ' Fwd Packet Length Std',
    'Bwd Packet Length Max',
    ' Bwd Packet Length Mean',
    ' Bwd Packet Length Std',
    'Flow Bytes/s',
    ' Flow Packets/s',
    ' Flow IAT Mean',
    ' Flow IAT Std',
    ' Flow IAT Max',
    ' Flow IAT Min',
    'Fwd IAT Total',
    ' Fwd IAT Mean',
    'Bwd IAT Total',
    ' SYN Flag Count',
    ' ACK Flag Count',
]

LABEL_COL = ' Label'
OUTPUT_DIR = '/vagrant/ml-detector/models/production/level1'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Cargar train files (Tue + Thu + Fri) ──────────────────────────────────
TRAIN_FILES = [
    f'{BASE}/Tuesday-WorkingHours.pcap_ISCX.csv',
    f'{BASE}/Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv',
    f'{BASE}/Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv',
    f'{BASE}/Friday-WorkingHours-Morning.pcap_ISCX.csv',
    f'{BASE}/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv',
    f'{BASE}/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv',
]

print('[LOAD] Cargando train files...')
dfs = []
for path in TRAIN_FILES:
    df = pd.read_csv(path, low_memory=False)
    dfs.append(df)
    print(f'  {os.path.basename(path)}: {len(df)} rows')

train_full = pd.concat(dfs, ignore_index=True)
print(f'[LOAD] Total train: {len(train_full)} rows')

# ── Limpiar ────────────────────────────────────────────────────────────────
train_full[LABEL_COL] = train_full[LABEL_COL].str.strip()
train_full['binary_label'] = (train_full[LABEL_COL] != 'BENIGN').astype(int)

# Reemplazar inf/nan
train_full[LEVEL1_FEATURES] = train_full[LEVEL1_FEATURES].replace([np.inf, -np.inf], np.nan)
train_full[LEVEL1_FEATURES] = train_full[LEVEL1_FEATURES].fillna(0)

X = train_full[LEVEL1_FEATURES].values.astype(np.float32)
y = train_full['binary_label'].values

n_benign = int((y == 0).sum())
n_attack = int((y == 1).sum())
scale_pos_weight = n_benign / n_attack
print(f'[CLASS] benign={n_benign} | attack={n_attack} | scale_pos_weight={scale_pos_weight:.4f}')

# ── Split temporal: 80% train / 20% validation (stratificado) ─────────────
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)
print(f'[SPLIT] train={len(X_train)} | val={len(X_val)}')

# ── Entrenar XGBoost con early stopping en validation ─────────────────────
dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=LEVEL1_FEATURES)
dval   = xgb.DMatrix(X_val,   label=y_val,   feature_names=LEVEL1_FEATURES)

params = {
    'objective':        'binary:logistic',
    'eval_metric':      ['logloss', 'aucpr'],
    'max_depth':        6,
    'eta':              0.05,
    'subsample':        0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 5,
    'scale_pos_weight': scale_pos_weight,
    'tree_method':      'hist',
    'seed':             42,
    'nthread':          4,
}

print('[TRAIN] Iniciando entrenamiento XGBoost...')
evals_result = {}
model = xgb.train(
    params,
    dtrain,
    num_boost_round=1000,
    evals=[(dtrain, 'train'), (dval, 'val')],
    early_stopping_rounds=50,
    evals_result=evals_result,
    verbose_eval=100,
)
print(f'[TRAIN] Best iteration: {model.best_iteration}')

# ── Calibrar threshold en VALIDATION (nunca en test) ──────────────────────
print('[THRESHOLD] Calibrando en validation set...')
y_val_proba = model.predict(dval)

precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_proba)

# Buscar threshold mínimo con Precision >= 0.99 y Recall >= 0.95
PRECISION_GATE = 0.99
RECALL_MIN     = 0.95

best_threshold = None
best_f1 = 0.0

for p, r, t in zip(precisions, recalls, thresholds):
    if p >= PRECISION_GATE and r >= RECALL_MIN:
        f1 = 2 * p * r / (p + r)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = t

if best_threshold is None:
    # Fallback: máxima Precision >= 0.99 aunque Recall sea menor
    print('[THRESHOLD] WARNING: no se encontró threshold con Recall>=0.95, buscando solo Precision>=0.99...')
    for p, r, t in zip(precisions, recalls, thresholds):
        if p >= PRECISION_GATE:
            f1 = 2 * p * r / (p + r)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = t

if best_threshold is None:
    print('[THRESHOLD] CRÍTICO: no existe threshold con Precision>=0.99 en validation.')
    print('[THRESHOLD] Mostrando curva de tradeoff para diagnóstico:')
    for p, r, t in zip(precisions[::500], recalls[::500], thresholds[::500]):
        print(f'  threshold={t:.4f}  precision={p:.4f}  recall={r:.4f}')
    sys.exit(1)

print(f'[THRESHOLD] Calibrado: threshold={best_threshold:.6f} | precision={precisions[list(thresholds).index(best_threshold)]:.4f} | recall={recalls[list(thresholds).index(best_threshold)]:.4f}')

# Métricas en validation con threshold calibrado
y_val_pred = (y_val_proba >= best_threshold).astype(int)
print('[VALIDATION] Reporte con threshold calibrado:')
print(classification_report(y_val, y_val_pred, target_names=['BENIGN','ATTACK']))
cm = confusion_matrix(y_val, y_val_pred)
print(f'[VALIDATION] Confusion matrix:\n{cm}')

# ── Exportar modelo ────────────────────────────────────────────────────────
model_json_path = f'{OUTPUT_DIR}/xgboost_cicids2017_v2.json'
model_ubj_path  = f'{OUTPUT_DIR}/xgboost_cicids2017_v2.ubj'
threshold_path  = f'{OUTPUT_DIR}/xgboost_cicids2017_v2_threshold.json'

model.save_model(model_json_path)
model.save_model(model_ubj_path)
print(f'[EXPORT] Modelo guardado: {model_json_path}')
print(f'[EXPORT] Modelo guardado: {model_ubj_path}')

threshold_meta = {
    'threshold':          float(best_threshold),
    'calibration_set':    'validation_20pct_stratified',
    'precision_gate':     PRECISION_GATE,
    'recall_min':         RECALL_MIN,
    'val_precision':      float(precisions[list(thresholds).index(best_threshold)]),
    'val_recall':         float(recalls[list(thresholds).index(best_threshold)]),
    'val_f1':             float(best_f1),
    'best_iteration':     int(model.best_iteration),
    'scale_pos_weight':   float(scale_pos_weight),
    'features':           LEVEL1_FEATURES,
    'wednesday_md5_seal': WEDNESDAY_MD5_EXPECTED,
    'train_files':        [os.path.basename(p) for p in TRAIN_FILES],
}
with open(threshold_path, 'w') as f:
    json.dump(threshold_meta, f, indent=2)
print(f'[EXPORT] Threshold meta: {threshold_path}')

print()
print('=' * 60)
print('ENTRENAMIENTO COMPLETADO')
print(f'Threshold calibrado: {best_threshold:.6f}')
print(f'Val Precision: {threshold_meta["val_precision"]:.4f}')
print(f'Val Recall:    {threshold_meta["val_recall"]:.4f}')
print('Siguiente paso: python3 evaluate_wednesday_v2.py')
print('=' * 60)
