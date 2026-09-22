#!/usr/bin/env python3
"""ddos_signature_l1.py -- prototipo nivel 1 de firma de ataque: tamano medio
de paquete por victima/protocolo, a partir de ddos_windows.csv (sin tocar el
kernel; usa lo que el pipeline ya escribe).

Columnas esperadas (segun ejemplo real): win,ts_ms,window_ms,dst_ip,proto,d_pkts,d_bytes

Uso:
    python3 ddos_signature_l1.py /vagrant/logs/lab/ddos_windows.csv
    python3 ddos_signature_l1.py ddos_windows.csv --rate-threshold 50 --top 15

No decide umbrales de "esto es un ataque": los umbrales de --rate-threshold y
los cortes de tamano son de exploracion (medir, no votar) -- imprime la
distribucion real para decidir con datos, no los asume.
"""
import argparse
import csv
import sys
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser(description="Nivel 1: tamano medio de paquete por victima/proto")
    ap.add_argument("csv_path")
    ap.add_argument("--rate-threshold", type=float, default=0.0,
                    help="pkts/s minimo de la ventana para entrar en el resumen (0 = todas)")
    ap.add_argument("--top", type=int, default=15, help="cuantas victimas listar")
    args = ap.parse_args()

    # (dst_ip, proto) -> stats acumulados
    agg = defaultdict(lambda: {"pkts": 0, "bytes": 0, "windows": 0,
                               "min_avg": None, "max_avg": None, "min_rate": None, "max_rate": None})
    skipped_zero_window = 0
    total_rows = 0

    with open(args.csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"dst_ip", "proto", "d_pkts", "d_bytes", "window_ms"} - set(reader.fieldnames or [])
        if missing:
            print("ERROR: faltan columnas en el CSV: %s (tiene: %s)"
                  % (sorted(missing), reader.fieldnames), file=sys.stderr)
            return 2

        for row in reader:
            total_rows += 1
            window_ms = int(row["window_ms"])
            if window_ms == 0:
                # fila baseline (ver seccion 4 de la continuidad): se descarta
                skipped_zero_window += 1
                continue

            d_pkts = int(row["d_pkts"])
            d_bytes = int(row["d_bytes"])
            if d_pkts <= 0:
                continue

            rate = d_pkts / (window_ms / 1000.0)  # pkts/s en esa ventana
            if rate < args.rate_threshold:
                continue

            avg_size = d_bytes / d_pkts
            key = (row["dst_ip"], row["proto"])
            a = agg[key]
            a["pkts"] += d_pkts
            a["bytes"] += d_bytes
            a["windows"] += 1
            a["min_avg"] = avg_size if a["min_avg"] is None else min(a["min_avg"], avg_size)
            a["max_avg"] = avg_size if a["max_avg"] is None else max(a["max_avg"], avg_size)
            a["min_rate"] = rate if a["min_rate"] is None else min(a["min_rate"], rate)
            a["max_rate"] = rate if a["max_rate"] is None else max(a["max_rate"], rate)

    print("filas leidas: %d  (descartadas window_ms=0: %d)" % (total_rows, skipped_zero_window))
    print("umbral de tasa aplicado: %.1f pkts/s" % args.rate_threshold)
    print("victimas/proto que superan el umbral: %d" % len(agg))
    print()

    if not agg:
        print("Nada por encima del umbral -- baja --rate-threshold o revisa el CSV.")
        return 0

    rows = sorted(agg.items(), key=lambda kv: -kv[1]["pkts"])[:args.top]
    print("%-16s %-5s %10s %12s %9s %14s %16s"
          % ("dst_ip", "proto", "pkts", "bytes", "ventanas", "tam.medio(B)", "rate pkts/s (min-max)"))
    for (dst_ip, proto), a in rows:
        avg_overall = a["bytes"] / a["pkts"]
        print("%-16s %-5s %10d %12d %9d %14.1f %8.1f-%.1f"
              % (dst_ip, proto, a["pkts"], a["bytes"], a["windows"], avg_overall,
                 a["min_rate"], a["max_rate"]))

    print()
    print("Lectura: tam.medio(B) muy por encima de ~100-150B en UDP suele ser")
    print("respuesta de amplificacion (DNS/NTP/SSDP) mas que flood puro; pero")
    print("es una hipotesis a contrastar con estos numeros, no una regla fija.")
    print("Si min-max de tam.medio varia mucho entre ventanas de la misma")
    print("victima, la 'firma' no es estable y hace falta mas señal (nivel 2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())