#!/usr/bin/env python3
# d337_parquet_sin_numpy.py — [PARQUET-SIN-NUMPY-D337] validate_roundtrip.py sin numpy (usa filas_ts.py) y el Makefile
# corre test_filas_ts.py en test-parquet, antes del roundtrip. Se ejecuta desde la raíz del repo; filas_ts.py y
# test_filas_ts.py tienen que estar ya en scripts/parquet/ con su sha256. Comprueba el sha256 de partida de cada
# fichero, cada ancla las veces exactas y no escribe nada si algo falla; al final, el sha256 de llegada.
import hashlib, sys

def sha(b): return hashlib.sha256(b).hexdigest()

NUEVOS = {
    "scripts/parquet/filas_ts.py": "c26d32f17137c79dc549ae8737dadf386b4f9e2d19b2a481740605d39da60631",
    "scripts/parquet/test_filas_ts.py": "2870a816fe6f3508e78b347709232e95d379bb90991da48515996f60bb890d0c",
}

VR_VIEJO_IMPORTS = """import time
import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq
from schemas import schema_firewall
"""
VR_NUEVO_IMPORTS = """import time
import pyarrow.parquet as pq
from schemas import schema_firewall
from filas_ts import fallos_ts  # [PARQUET-SIN-NUMPY-D337] sin numpy, solo pyarrow.compute
"""
VR_VIEJO_CHECK = """# [PARQUET-ALLROWS-D296] DEBT-PARQUET-VALIDATOR-FIRST-ROW-001: TODAS las filas, no solo la [0]
TS_MIN_NS = 1_700_000_000_000_000_000   # 2023-11-14; por debajo = reloj monotonico u otro error (DAY294, DAY296)
TS_FUTURE_MARGIN_NS = 300 * 10**9      # ninguna fila puede venir mas de 300 s del futuro

def check_all_rows(name, col, ms_multiple=False):
    n = len(col)
    nul = col.null_count
    check(nul == 0, f"{name}: {nul} de {n} filas con timestamp_utc_ns nulo")
    a = pc.drop_null(col).to_numpy()
    if len(a) == 0:
        return
    hi = time.time_ns() + TS_FUTURE_MARGIN_NS
    for mask, what in ((a < TS_MIN_NS, f"< {TS_MIN_NS} (reloj monotonico?)"),
                       (a > hi, "del futuro (> ahora + 300 s)")):
        if mask.any():
            i = int(np.argmax(mask))
            check(False, f"{name}: {int(mask.sum())} de {n} filas con timestamp_utc_ns {what}; primera: fila {i} = {int(a[i])}")
    if ms_multiple:
        mask = (a % 1_000_000) != 0
        if mask.any():
            i = int(np.argmax(mask))
            check(False, f"{name}: {int(mask.sum())} de {n} filas no son multiplo de 1_000_000 (ms->ns fallida); primera: fila {i} = {int(a[i])}")
"""
VR_NUEVO_CHECK = """# [PARQUET-ALLROWS-D296] DEBT-PARQUET-VALIDATOR-FIRST-ROW-001: TODAS las filas, no solo la [0].
# [PARQUET-SIN-NUMPY-D337] La comprobación (con TS_MIN_NS y TS_FUTURE_MARGIN_NS) está en filas_ts.py, solo con
# pyarrow.compute; sus tests, en test_filas_ts.py (make test-parquet los corre antes que esto).
def check_all_rows(name, col, ms_multiple=False):
    for msg in fallos_ts(name, col, time.time_ns(), ms_multiple):
        check(False, msg)
"""
MK_VIEJO = """test-parquet: parquet-convert
\t@vagrant ssh -c "cd /vagrant/scripts/parquet && python3 validate_roundtrip.py"
"""
MK_NUEVO = """# [PARQUET-SIN-NUMPY-D337] test_filas_ts.py (en el defender, con numpy bloqueado): las comprobaciones de
# timestamp_utc_ns de filas_ts.py, que validate_roundtrip.py usa, sin numpy; también contra una función que lo acepta
# todo. Va antes del roundtrip y después de parquet-convert, que es quien instala pyarrow.
test-parquet: parquet-convert
\t@vagrant ssh -c "cd /vagrant/scripts/parquet && python3 test_filas_ts.py"
\t@vagrant ssh -c "cd /vagrant/scripts/parquet && python3 validate_roundtrip.py"
"""

CAMBIOS = {
    "scripts/parquet/validate_roundtrip.py": (
        "98db6b4a3e1d1f73494b4e932614ade9e08117329bd7ba83a43f7b634b959459",
        [(VR_VIEJO_IMPORTS, VR_NUEVO_IMPORTS, 1), (VR_VIEJO_CHECK, VR_NUEVO_CHECK, 1)]),
    "Makefile": (
        "93d9b0569266d8abdd714cb2aeb97ceeb59a586644840574e328ed91bb917ac3",
        [(MK_VIEJO, MK_NUEVO, 1)]),
}

errores = []
for f, esperado in NUEVOS.items():
    try:
        s = sha(open(f, "rb").read())
    except OSError as e:
        errores.append(f"{f}: {e}"); continue
    if s != esperado:
        errores.append(f"{f}: sha256 {s}, se esperaba {esperado}")

nuevo = {}
for f, (esperado, anclas) in CAMBIOS.items():
    b = open(f, "rb").read()
    if sha(b) != esperado:
        errores.append(f"{f}: sha256 de partida {sha(b)}, se esperaba {esperado}"); continue
    t = b.decode("utf-8")
    for viejo, nuevo_txt, veces in anclas:
        n = t.count(viejo)
        if n != veces:
            errores.append(f"{f}: ancla encontrada {n} veces, se esperaban {veces}: {viejo.splitlines()[0]!r}")
            continue
        t = t.replace(viejo, nuevo_txt)
    nuevo[f] = t.encode("utf-8")

if errores:
    print("❌ no se escribe nada:")
    for e in errores: print("   " + e)
    sys.exit(1)
for f, b in nuevo.items():
    open(f, "wb").write(b)
    print(f"✅ {f}  sha256 de llegada {sha(b)}")
