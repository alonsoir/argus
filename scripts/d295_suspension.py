#!/usr/bin/env python3
"""DAY295 paso 2: REALTIME, MONOTONIC y BOOTTIME a traves de una suspension del portatil.
  record <csv> <segundos>  muestrea cada 0,5 s (correr en el defender, fuera de /vagrant)
  analyze <csv>            totales, deriva B-M y R-M, y pares con hueco o salto"""
import sys
import time


def record(path, dur):
    fin = time.clock_gettime(time.CLOCK_MONOTONIC) + dur
    with open(path, "w") as f:
        f.write("realtime_ns,monotonic_ns,boottime_ns\n")
        while time.clock_gettime(time.CLOCK_MONOTONIC) < fin:
            r = time.clock_gettime_ns(time.CLOCK_REALTIME)
            m = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            b = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
            f.write(f"{r},{m},{b}\n")
            f.flush()
            time.sleep(0.5)


def analyze(path):
    with open(path) as f:
        rows = [tuple(int(x) for x in l.split(",")) for l in f.read().splitlines()[1:] if l]
    if len(rows) < 2:
        print(f"ABORTA: {len(rows)} muestras")
        sys.exit(1)
    r0, m0, b0 = rows[0]
    r1, m1, b1 = rows[-1]
    print(f"muestras={len(rows)}")
    print(f"total: dR={(r1 - r0) / 1e9:.3f} s  dM={(m1 - m0) / 1e9:.3f} s  dB={(b1 - b0) / 1e9:.3f} s")
    print(f"B-M: inicio={(b0 - m0) / 1e9:.6f} s  fin={(b1 - m1) / 1e9:.6f} s  cambio={((b1 - m1) - (b0 - m0)) / 1e9:.6f} s")
    print(f"R-M: cambio={((r1 - m1) - (r0 - m0)) / 1e9:.6f} s")
    print("pares anomalos (algun delta > 2 s, o |dR-dM| > 0,1 s):")
    n = 0
    for i in range(1, len(rows)):
        dr = (rows[i][0] - rows[i - 1][0]) / 1e9
        dm = (rows[i][1] - rows[i - 1][1]) / 1e9
        db = (rows[i][2] - rows[i - 1][2]) / 1e9
        if max(dr, dm, db) > 2 or abs(dr - dm) > 0.1:
            n += 1
            if n <= 30:
                hora = time.strftime("%H:%M:%S", time.gmtime(rows[i][0] / 1e9))
                print(f"  i={i} R={hora}Z  dR={dr:.3f}  dM={dm:.3f}  dB={db:.3f}")
    print(f"anomalos={n}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "record":
        record(sys.argv[2], float(sys.argv[3]))
    elif len(sys.argv) == 3 and sys.argv[1] == "analyze":
        analyze(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)
