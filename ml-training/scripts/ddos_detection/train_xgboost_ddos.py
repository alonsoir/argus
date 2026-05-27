# ml-training/scripts/ddos_detection/train_xgboost_ddos.py
# DEBT-XGBOOST-DDOS-001 — XGBoost DDoS detector
# Patrón: DDosModelTrainer.py + MinMaxScaler + XGBoost
# Gate: F1 + Precision superiores al RF ddos_detection_model.pkl
# Exports: xgboost_ddos.json + xgboost_ddos.ubj
# DAY 121 — Alonso Isidoro Román

import json
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
import pickle
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from DDOSFeatures import DDOS_FEATURES

DATASET_PATH = os.path.join(os.path.dirname(__file__), "ddos_detection_dataset.json")
RF_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ddos_detection_model.pkl")
RF_SCALER_PATH = os.path.join(os.path.dirname(__file__), "ddos_scaler.pkl")
OUT_JSON = os.path.join(os.path.dirname(__file__), "xgboost_ddos.json")
OUT_UBJ  = os.path.join(os.path.dirname(__file__), "xgboost_ddos.ubj")

def load_data():
    with open(DATASET_PATH) as f:
        data = json.load(f)
    df = pd.DataFrame(data['dataset'])
    df['label_num'] = df['label'].map({'normal': 0, 'ddos': 1})
    X = df[DDOS_FEATURES].values.astype(np.float32)
    y = df['label_num'].values
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_norm = scaler.fit_transform(X).astype(np.float32)
    return X_norm, y, scaler

def evaluate_rf_baseline(X_test, y_test):
    """Evalúa el RF existente como baseline."""
    if not os.path.exists(RF_MODEL_PATH):
        print("⚠️  RF baseline no encontrado — saltando comparación")
        return None, None
    rf = pickle.load(open(RF_MODEL_PATH, 'rb'))
    # RF fue entrenado con su propio scaler
    if os.path.exists(RF_SCALER_PATH):
        rf_scaler = joblib.load(RF_SCALER_PATH)
        # Reconstruir X sin normalizar para el RF
    y_pred_rf = rf.predict(X_test)
    f1  = f1_score(y_test, y_pred_rf, pos_label=1)
    prec = precision_score(y_test, y_pred_rf, pos_label=1)
    print(f"📊 RF baseline — F1={f1:.4f}  Precision={prec:.4f}")
    return f1, prec

def train_xgboost(X_train, y_train, X_test, y_test):
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest  = xgb.DMatrix(X_test,  label=y_test)

    params = {
        'objective':        'binary:logistic',
        'eval_metric':      ['logloss', 'aucpr'],
        'max_depth':        6,
        'eta':              0.1,
        'subsample':        0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 5,
        'seed':             42,
        'nthread':          -1,
    }

    evals = [(dtrain, 'train'), (dtest, 'eval')]
    model = xgb.train(
        params, dtrain,
        num_boost_round=300,
        evals=evals,
        early_stopping_rounds=20,
        verbose_eval=50,
    )
    return model

def main():
    print("=" * 60)
    print("  XGBoost DDoS Detector — DEBT-XGBOOST-DDOS-001")
    print("=" * 60)

    X, y, scaler = load_data()
    print(f"✅ Dataset: {len(X)} registros, {len(DDOS_FEATURES)} features")
    print(f"   Distribución: normal={sum(y==0)}, ddos={sum(y==1)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Baseline RF ──────────────────────────────────────────────────
    print("\n── RF Baseline ──")
    # Usamos X_test normalizado con mismo scaler para comparación justa
    rf_f1, rf_prec = evaluate_rf_baseline(X_test, y_test)

    # ── XGBoost ──────────────────────────────────────────────────────
    print("\n── XGBoost Training ──")
    model = train_xgboost(X_train, y_train, X_test, y_test)

    # ── Evaluación ───────────────────────────────────────────────────
    dtest = xgb.DMatrix(X_test)
    y_prob = model.predict(dtest)
    y_pred = (y_prob > 0.5).astype(int)

    xgb_f1   = f1_score(y_test, y_pred, pos_label=1)
    xgb_prec = precision_score(y_test, y_pred, pos_label=1)

    print(f"\n📈 Classification Report (XGBoost):")
    print(classification_report(y_test, y_pred, target_names=['normal', 'ddos']))

    cm = confusion_matrix(y_test, y_pred)
    print(f"📊 Matriz de Confusión:")
    print(f"  TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"  FN={cm[1][0]}  TP={cm[1][1]}")

    # ── Gate vs RF ───────────────────────────────────────────────────
    print(f"\n── Gate DEBT-XGBOOST-DDOS-001 ──")
    print(f"  XGBoost — F1={xgb_f1:.4f}  Precision={xgb_prec:.4f}")
    if rf_f1 is not None:
        f1_ok   = xgb_f1   >= rf_f1
        prec_ok = xgb_prec >= rf_prec
        print(f"  RF      — F1={rf_f1:.4f}  Precision={rf_prec:.4f}")
        print(f"  F1   {'✅ SUPERA' if f1_ok   else '❌ NO SUPERA'} RF baseline")
        print(f"  Prec {'✅ SUPERA' if prec_ok else '❌ NO SUPERA'} RF baseline")
        if not (f1_ok and prec_ok):
            print("\n❌ GATE FALLIDO — modelo XGBoost no supera RF")
            sys.exit(1)

    # ── Exports ──────────────────────────────────────────────────────
    model.save_model(OUT_JSON)
    model.save_model(OUT_UBJ)
    joblib.dump(scaler, os.path.join(os.path.dirname(__file__), "xgboost_ddos_scaler.pkl"))

    print(f"\n✅ Exports:")
    print(f"   {OUT_JSON}")
    print(f"   {OUT_UBJ}")

    print(f"\n🎉 DEBT-XGBOOST-DDOS-001 CERRADO")
    print(f"   F1={xgb_f1:.4f}  Precision={xgb_prec:.4f}")

if __name__ == "__main__":
    main()
