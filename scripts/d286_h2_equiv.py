#!/usr/bin/env python3
"""DAY286 H2: equivalencia offline (CSV del lector) <-> implementacion (vratio en el log).
Uso: d286_h2_equiv.py ddos_windows.csv ml-detector.log > salida.txt"""
import csv, re, sys

ALPHA, ALPHA_ANOM, K, W, FLOOR, EVICT = 0.1, 0.1 / 60.0, 5.0, 30, 10.0, 3600
KV = re.compile(r"(\w+)=([^,\s]+)")
NEED = ("event", "victim", "proto", "d_pkts", "window_ms", "seq")

# 1. CSV: filas de la corrida actual (desde el ultimo reinicio de 'win')
rows, last_win, start = [], None, 0
with open(sys.argv[1], newline="") as f:
    for x in csv.DictReader(f):
        w = int(x["win"])
        if last_win is not None and w < last_win:
            start = len(rows)
        last_win = w
        rows.append(x)
rows = [r for r in rows[start:] if int(r["window_ms"]) > 0]
by_win = {}
for r in rows:
    by_win.setdefault(int(r["win"]), []).append(r)
print(f"csv: ventanas de la corrida={len(by_win)} filas={len(rows)} "
      f"win {min(by_win) if by_win else '-'}..{max(by_win) if by_win else '-'}")

# 2. Recalculo offline (misma formula que victim_ewma_step)
state, expect = {}, {}
for win in sorted(by_win):
    for r in by_win[win]:
        key = (r["dst_ip"], r["proto"])
        pps = int(r["d_pkts"]) * 1000.0 / int(r["window_ms"])
        ewma, last, seen = state.get(key, (0.0, 0, 0))
        prior = 0.0
        if seen > 0:
            gap = win - last if win > last else 1
            if gap <= EVICT:
                prior = ewma * (1.0 - ALPHA) ** (gap - 1)
        ratio = pps / max(prior, FLOOR)
        a = ALPHA_ANOM if (seen >= W and ratio >= K) else ALPHA
        state[key] = ((1.0 - a) * prior + a * pps, win, seen + 1)
        expect[(win, key)] = ratio

# 3. Log: [VICTIM-WINDOW] y [DDOS-V2] por event
vw, v2, n_vw_partial = {}, {}, 0
with open(sys.argv[2], errors="replace") as f:
    for line in f:
        if "[VICTIM-WINDOW]" in line:
            d = dict(KV.findall(line.split("[VICTIM-WINDOW]", 1)[1]))
            if all(k in d for k in NEED):
                vw[d["event"]] = d
            else:
                n_vw_partial += 1
        elif "[DDOS-V2]" in line:
            d = dict(KV.findall(line.split("[DDOS-V2]", 1)[1]))
            if "event" in d and "vratio" in d:
                v2[d["event"]] = float(d["vratio"])
print(f"lineas [VICTIM-WINDOW] sin campos de ventana (no comparadas)={n_vw_partial}")

# 4. Comparacion
n_join = n_cmp = n_bad = n_nocsv = n_zero_ok = n_zero_bad = 0
max_diff, bad = 0.0, []
n_fast = 0
for ev, d in vw.items():
    if ev.startswith("fast-alert-"):
        n_fast += 1
        continue
    if ev not in v2:
        continue
    n_join += 1
    got = v2[ev]
    if int(d["window_ms"]) <= 0:
        continue
    if int(d["d_pkts"]) == 0:
        if abs(got) < 1e-9:
            n_zero_ok += 1
        else:
            n_zero_bad += 1
        continue
    k = (int(d["seq"]), (d["victim"], d["proto"]))
    if k not in expect:
        n_nocsv += 1
        continue
    n_cmp += 1
    diff = abs(got - expect[k])
    max_diff = max(max_diff, diff)
    if diff > 0.001 + 2e-6 * abs(expect[k]):
        n_bad += 1
        if len(bad) < 5:
            bad.append(f"  event={ev} seq={k[0]} {k[1]} log={got:.4f} offline={expect[k]:.4f}")

print(f"fast alerts excluidas={n_fast}")
print(f"eventos con ambas lineas={n_join}")
print(f"comparados (d_pkts>0)={n_cmp} discrepancias={n_bad} max_diff={max_diff:.6f}")
print(f"victima ausente en la ventana: vratio=0 en {n_zero_ok}, distinto de 0 en {n_zero_bad}")
print(f"sin fila en el CSV (tope del CSV o ventana fuera de la corrida)={n_nocsv}")
for b in bad:
    print(b)

# 5. Contexto: el ratio del flood por ventana (192.168.100.1/UDP)
fk = ("192.168.100.1", "17")
serie = []
for w in sorted(by_win):
    if (w, fk) not in expect:
        continue
    pk = next(int(r["d_pkts"]) for r in by_win[w] if (r["dst_ip"], r["proto"]) == fk)
    if pk >= 50:
        serie.append((w, expect[(w, fk)]))
print(f"\nflood {fk}: {len(serie)} ventanas >= 50 pkts; primeras 12 y cada 20:")
print("  " + " ".join(f"{w}:{r:.2f}" for i, (w, r) in enumerate(serie) if i < 12 or i % 20 == 0))
