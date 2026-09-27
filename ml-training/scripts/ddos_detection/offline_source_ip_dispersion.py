#!/usr/bin/env python3
"""
offline_source_ip_dispersion.py

Análogo OFFLINE de la feature serve `source_ip_dispersion` de la cabeza DDoS de aRGus,
computado sobre CICDDoS2019 (CICFlowMeter-V3, 88 cols) para comparar distribuciones
offline-vs-serve (grieta B, DAY263+).

Definición serve MEDIDA (ml_defender_features.cpp:64-73, time_window_aggregator.cpp:60-61):
    disp = min( log2(unique_ips + 1) / log2(event_count + 2), 1.0 )
    - unique_ips = |{ src_ip } ∪ { dst_ip }| en un SOLO set (NO solo origen, pese al nombre).
    - ventana global SLIDING de 30 s, sin clave de agrupación.
    - ring buffer con cap 10000 eventos → ventana efectiva = [t-30s, t] ∩ últimos 10000 eventos.
    - event_count == 0        -> 0.0
    - (serve) !aggregator_     -> MISSING_FEATURE_SENTINEL (-9999). OFFLINE nunca ocurre:
      aquí SIEMPRE hay ventana. Esa asimetría es material para la horquilla (a)/(b).

Serve alimenta el aggregator por PAQUETE; un CSV es por-flujo. Aproximación (conmutable):
    - --event-unit packet (default): cada flujo aporta `Total Fwd + Bwd Packets` eventos,
      todos con el mismo (src,dst) y colocados en su Timestamp. Fiel a serve; el cap muerde
      en unidades de paquete.
    - --event-unit flow: cada flujo = 1 evento (peso 1). Para MEDIR el sesgo de no expandir.

    - --read-at end (default): la feature se lee en Timestamp + Flow Duration.
      --read-at start: se lee en Timestamp. (CICFlowMeter Timestamp suele ser INICIO;
      el script imprime diagnóstico para que lo confirmes por medición.)

HUECO de fidelidad conocido (paper): al colapsar los paquetes de un flujo a un instante se
pierde el interleaving de llegada entre flujos. uniqueness y event_count salen ajustados
(los paquetes de un flujo comparten IPs; el conteo se clampa a 10000 en el borde), pero la
MEMBRESÍA exacta de los últimos-10000 bajo flood difiere de serve en el flujo-frontera.

NUNCA usa `grep`. Lee solo las columnas necesarias. Parser de fecha EXPLÍCITO día-mes.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

WINDOW_NS = 30 * 1_000_000_000          # 30 s en ns (serve: now - 30'000'000'000ULL)
DEFAULT_CAP = 10_000                     # max_events del ring buffer (ambos lados)
TS_FMT_US = "%Y-%d-%m %H:%M:%S.%f"       # día-mes, µs (formato ÚNICO validado en los 18 CSV)
TS_FMT_S = "%Y-%d-%m %H:%M:%S"           # respaldo para filas sin fracción de segundo

# Nombres CICFlowMeter (con espacio de relleno a la izquierda -> se stripean al leer).
COL_SRC = "Source IP"
COL_DST = "Destination IP"
COL_TS = "Timestamp"
COL_FWD = "Total Fwd Packets"
COL_BWD = "Total Backward Packets"
COL_DUR = "Flow Duration"       # microsegundos en CICFlowMeter
COL_LABEL = "Label"


def parse_timestamps(raw: pd.Series) -> pd.Series:
    """Parseo día-mes EXPLÍCITO. Nunca infiere (pandas invertiría día<->mes)."""
    ts = pd.to_datetime(raw, format=TS_FMT_US, errors="coerce")
    missing = ts.isna()
    if missing.any():
        # Reintento explícito para filas sin `.ffffff`; sigue siendo día-mes.
        ts2 = pd.to_datetime(raw[missing], format=TS_FMT_S, errors="coerce")
        ts.loc[missing] = ts2
    return ts


def load_flows(csv_path: Path, nrows=None) -> pd.DataFrame:
    # Cabecera cruda para localizar columnas por nombre stripeado (hay relleno a la izda).
    header = pd.read_csv(csv_path, nrows=0)
    stripped = {c.strip(): c for c in header.columns}

    def col(name):
        if name not in stripped:
            sys.exit(f"[FATAL] columna ausente: {name!r}. Presentes: {list(stripped)[:12]}...")
        return stripped[name]

    want = [COL_SRC, COL_DST, COL_TS, COL_FWD, COL_BWD, COL_DUR, COL_LABEL]
    usecols = [col(w) for w in want]
    df = pd.read_csv(csv_path, usecols=usecols, nrows=nrows, low_memory=False)
    df.columns = [c.strip() for c in df.columns]

    n_raw = len(df)
    df["_ts"] = parse_timestamps(df[COL_TS])
    n_bad_ts = int(df["_ts"].isna().sum())
    df = df.dropna(subset=["_ts"]).copy()

    # Infinity/NaN están confinados a cols 22-23 (no las usamos), pero guardamos por si acaso.
    for c in (COL_FWD, COL_BWD, COL_DUR):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=[COL_FWD, COL_BWD, COL_DUR]).copy()

    # pandas 2.x puede parsear a datetime64[us]; forzar ns o la ventana saldría 1000x menor.
    df["_ts_ns"] = df["_ts"].astype("datetime64[ns]").astype("int64")
    df["_pkts"] = (df[COL_FWD].astype("int64") + df[COL_BWD].astype("int64")).clip(lower=0)
    df["_dur_ns"] = (df[COL_DUR].astype("int64").clip(lower=0)) * 1000  # µs -> ns

    print(f"  filas CSV                : {n_raw}")
    print(f"  descartadas por Timestamp: {n_bad_ts}")
    print(f"  descartadas por num/flujo: {n_raw - n_bad_ts - len(df)}")
    print(f"  flujos usables           : {len(df)}")
    return df


def diagnose(df: pd.DataFrame):
    ts = df["_ts_ns"].to_numpy()
    span_s = (ts.max() - ts.min()) / 1e9
    print("\n[diag] rango temporal")
    print(f"  min = {df['_ts'].min()}   max = {df['_ts'].max()}   span = {span_s:,.1f} s")
    order = np.argsort(ts, kind="stable")
    monotone = np.all(np.diff(ts[order]) >= 0)  # trivial; medimos vs orden de fichero:
    file_monotone = bool(np.all(np.diff(ts) >= 0))
    print(f"  Timestamp monótono en orden de fichero: {file_monotone} "
          f"(pista de si Timestamp es inicio de flujo y el CSV va en orden de llegada)")
    dur = df["_dur_ns"].to_numpy()
    print(f"  Flow Duration: mediana={np.median(dur)/1e9:.4f}s  "
          f"p99={np.percentile(dur,99)/1e9:.4f}s  max={dur.max()/1e9:.2f}s")
    pk = df["_pkts"].to_numpy()
    print(f"  paquetes/flujo: mediana={np.median(pk):.0f}  p99={np.percentile(pk,99):.0f}  "
          f"suma={pk.sum():,}")
    if COL_LABEL in df:
        vc = df[COL_LABEL].value_counts()
        print("  labels:", dict(vc.head(6)))


def compute_dispersion(df: pd.DataFrame, event_unit: str, read_at: str, cap: int):
    """Two-pointer O(N) sobre el stream de eventos ordenado por tiempo de colocación."""
    n = len(df)

    # Codifica IPs a enteros compactos (src y dst comparten el mismo espacio de códigos).
    codes, _ = pd.factorize(pd.concat([df[COL_SRC], df[COL_DST]], ignore_index=True),
                            sort=False)
    src_code = codes[:n]
    dst_code = codes[n:]

    place_ns = df["_ts_ns"].to_numpy()
    if read_at == "end":
        read_ns = place_ns + df["_dur_ns"].to_numpy()
    elif read_at == "start":
        read_ns = place_ns.copy()
    else:
        sys.exit(f"[FATAL] --read-at desconocido: {read_at}")

    if event_unit == "packet":
        weight = df["_pkts"].to_numpy().astype("int64")
    elif event_unit == "flow":
        weight = np.ones(n, dtype="int64")
    else:
        sys.exit(f"[FATAL] --event-unit desconocido: {event_unit}")

    # Orden de EVENTOS por tiempo de colocación (llegada aproximada).
    ev_order = np.argsort(place_ns, kind="stable")
    ev_place = place_ns[ev_order]
    ev_src = src_code[ev_order]
    ev_dst = dst_code[ev_order]
    ev_w = weight[ev_order]
    # cumw[k] = suma de pesos de los primeros k eventos.
    cumw = np.zeros(n + 1, dtype="int64")
    cumw[1:] = np.cumsum(ev_w)

    # Orden de LECTURAS por tiempo de lectura.
    rd_order = np.argsort(read_ns, kind="stable")
    rd_time = read_ns[rd_order]

    disp = np.empty(n, dtype="float64")
    evcount_out = np.empty(n, dtype="int64")
    uniq_out = np.empty(n, dtype="int64")
    cap_bound = np.zeros(n, dtype=bool)

    ip_count = {}          # ip_code -> nº de flujos en ventana que lo tocan
    n_unique = 0
    R = 0                  # eventos con place <= t (exclusivo)
    L = 0                  # inicio de ventana (índice de evento)

    inv_log2 = 1.0

    for j in range(n):
        t = rd_time[j]
        # Avanza R: incorpora eventos con place <= t.
        while R < n and ev_place[R] <= t:
            for ip in (ev_src[R], ev_dst[R]):
                c = ip_count.get(ip, 0)
                if c == 0:
                    n_unique += 1
                ip_count[ip] = c + 1
            R += 1
        # Frontera por CAP (últimos `cap` en unidad de peso) y por TIEMPO (>= t-30s).
        cap_floor = cumw[R] - cap
        time_floor = t - WINDOW_NS
        while L < R and (cumw[L + 1] <= cap_floor or ev_place[L] < time_floor):
            for ip in (ev_src[L], ev_dst[L]):
                c = ip_count[ip] - 1
                if c == 0:
                    del ip_count[ip]
                    n_unique -= 1
                else:
                    ip_count[ip] = c
            L += 1

        packets_in = int(cumw[R] - cumw[L])
        event_count = min(packets_in, cap)
        cap_bound[rd_order[j]] = packets_in >= cap
        uniq = n_unique

        if event_count == 0:
            d = 0.0
        else:
            d = math.log2(uniq + 1) / math.log2(event_count + 2)
            if d > 1.0:
                d = 1.0

        oi = rd_order[j]
        disp[oi] = d
        evcount_out[oi] = event_count
        uniq_out[oi] = uniq

    out = df.copy()
    out["source_ip_dispersion"] = disp
    out["_event_count"] = evcount_out
    out["_unique_ips"] = uniq_out
    out["_cap_bound"] = cap_bound
    return out


def report(out: pd.DataFrame, event_unit, read_at, cap):
    d = out["source_ip_dispersion"].to_numpy()
    pct = np.percentile(d, [0, 1, 5, 25, 50, 75, 95, 99, 100])
    print(f"\n[dispersion] event-unit={event_unit} read-at={read_at} cap={cap}")
    print(f"  n={len(d)}  media={d.mean():.4f}  std={d.std():.4f}")
    labs = ["min", "p1", "p5", "p25", "p50", "p75", "p95", "p99", "max"]
    print("  percentiles: " + "  ".join(f"{l}={v:.4f}" for l, v in zip(labs, pct)))
    print(f"  clamp @1.0 : {(d >= 1.0).mean()*100:.2f}%   ==0.0: {(d == 0.0).mean()*100:.2f}%")
    print(f"  cap mordió : {out['_cap_bound'].mean()*100:.2f}% de las lecturas")
    print(f"  event_count: mediana={int(out['_event_count'].median())}  "
          f"max={int(out['_event_count'].max())}")
    # Histograma de texto (10 bins en [0,1]).
    hist, edges = np.histogram(d, bins=10, range=(0, 1))
    top = hist.max() or 1
    print("  histograma:")
    for k in range(10):
        bar = "#" * int(40 * hist[k] / top)
        print(f"   [{edges[k]:.1f},{edges[k+1]:.1f}) {hist[k]:>8} {bar}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path, help="CSV de CICDDoS2019 (empezar por 03-11/Portmap.csv)")
    ap.add_argument("--event-unit", choices=["packet", "flow"], default="packet")
    ap.add_argument("--read-at", choices=["end", "start"], default="end")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP,
                    help="max_events del ring buffer (serve=10000; bajar para probar el cap)")
    ap.add_argument("--nrows", type=int, default=None, help="limitar filas (iterar barato)")
    ap.add_argument("--out", type=Path, default=None,
                    help="parquet de salida con la columna source_ip_dispersion por flujo")
    args = ap.parse_args()

    print(f"[load] {args.csv}")
    df = load_flows(args.csv, nrows=args.nrows)
    if len(df) == 0:
        sys.exit("[FATAL] 0 flujos usables.")
    diagnose(df)
    out = compute_dispersion(df, args.event_unit, args.read_at, args.cap)
    report(out, args.event_unit, args.read_at, args.cap)

    if args.out:
        keep = [COL_SRC, COL_DST, COL_TS, COL_LABEL,
                "source_ip_dispersion", "_event_count", "_unique_ips", "_cap_bound"]
        out[keep].to_parquet(args.out, index=False)
        print(f"\n[out] escrito {args.out}  ({len(out)} filas)")


if __name__ == "__main__":
    main()