#!/usr/bin/env python3
# scripts/parquet/test_filas_ts.py — [PARQUET-SIN-NUMPY-D337] tests de fallos_ts (filas_ts.py) en el defender, con
# numpy BLOQUEADO (sys.modules['numpy'] = None antes de importar pyarrow): si filas_ts.py, pyarrow.compute o lo que
# usa validate_roundtrip.py necesitaran numpy, esto falla aunque numpy siga instalado. Cada caso de rechazo se vuelve a
# correr contra una función que lo acepta todo, y tiene que fallar ahí. Sin -I: pyarrow está en ~vagrant/.local.
# Uso: python3 scripts/parquet/test_filas_ts.py   (Makefile: make test-parquet, antes del roundtrip)
import os, re, sys
sys.modules["numpy"] = None   # import numpy -> ImportError
aqui = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, aqui)
import pyarrow as pa
import filas_ts
from filas_ts import TS_MIN_NS, TS_FUTURE_MARGIN_NS

AHORA = 1_764_000_000_000_000_000          # 2025-11-24, fijo: el test no depende del reloj
BIEN = AHORA - 3_600 * 10**9               # hace una hora, múltiplo de 1 ms
HI = AHORA + TS_FUTURE_MARGIN_NS


def col(*trozos):
    return pa.chunked_array([list(t) for t in trozos], type=pa.int64())


# (nombre, columna, ms_multiple, mensajes esperados). Lista vacía = acepta; si no, rechaza con esos mensajes exactos.
CASOS = [
    ("columna buena, un trozo", col([BIEN, BIEN + 1_000_000]), True, []),
    ("columna buena, tres trozos", col([BIEN], [], [BIEN + 5_000_000, BIEN]), True, []),
    ("en el límite inferior (TS_MIN_NS)", col([TS_MIN_NS]), True, []),
    ("en el límite del futuro (ahora + 300 s)", col([HI]), True, []),
    ("sin múltiplo de ms pero ms_multiple=False", col([BIEN + 1]), False, []),
    ("toda la columna nula: solo el aviso de nulos", col([None, None]), True,
     ["x: 2 de 2 filas con timestamp_utc_ns nulo"]),
    ("columna vacía", col([]), True, []),
    ("un nulo entre filas buenas", col([BIEN, None, BIEN]), True,
     ["x: 1 de 3 filas con timestamp_utc_ns nulo"]),
    ("reloj monotonico (DAY294): 1 ns por debajo del mínimo (sin ms_multiple)", col([BIEN, TS_MIN_NS - 1]), False,
     [f"x: 1 de 2 filas con timestamp_utc_ns < {TS_MIN_NS} (reloj monotonico?); primera: fila 1 = {TS_MIN_NS - 1}"]),
    ("negativos y cero", col([BIEN], [-1_000_000, 0]), True,
     [f"x: 2 de 3 filas con timestamp_utc_ns < {TS_MIN_NS} (reloj monotonico?); primera: fila 1 = -1000000"]),
    ("1 ns del futuro (sin ms_multiple)", col([HI + 1, BIEN]), False,
     [f"x: 1 de 2 filas con timestamp_utc_ns del futuro (> ahora + 300 s); primera: fila 0 = {HI + 1}"]),
    ("ms->ns fallida (sin el * 1e6)", col([BIEN, BIEN + 1, BIEN + 999_999]), True,
     [f"x: 2 de 3 filas no son multiplo de 1_000_000 (ms->ns fallida); primera: fila 1 = {BIEN + 1}"]),
    ("negativo que no es múltiplo de ms", col([-1]), True,
     [f"x: 1 de 1 filas con timestamp_utc_ns < {TS_MIN_NS} (reloj monotonico?); primera: fila 0 = -1",
      "x: 1 de 1 filas no son multiplo de 1_000_000 (ms->ns fallida); primera: fila 0 = -1"]),
    ("el índice no cuenta los nulos ni los trozos (sin ms_multiple)", col([None, BIEN], [None, TS_MIN_NS - 1]), False,
     ["x: 2 de 4 filas con timestamp_utc_ns nulo",
      f"x: 1 de 4 filas con timestamp_utc_ns < {TS_MIN_NS} (reloj monotonico?); primera: fila 1 = {TS_MIN_NS - 1}"]),
    ("extremos de int64", col([-2**63, 2**63 - 1]), True,
     [f"x: 1 de 2 filas con timestamp_utc_ns < {TS_MIN_NS} (reloj monotonico?); primera: fila 0 = {-2**63}",
      f"x: 1 de 2 filas con timestamp_utc_ns del futuro (> ahora + 300 s); primera: fila 1 = {2**63 - 1}",
      f"x: 2 de 2 filas no son multiplo de 1_000_000 (ms->ns fallida); primera: fila 0 = {-2**63}"]),
]


def correr(f):
    casos = fallos = rechazos = rechazos_vistos = 0
    for nombre, c, ms, esperado in CASOS:
        casos += 1
        try:
            obtenido = f("x", c, AHORA, ms)
        except Exception as e:   # un fallo de pyarrow o de numpy cuenta como fallo del caso
            obtenido = [f"EXCEPCIÓN {type(e).__name__}: {e}"]
        ok = obtenido == esperado
        if esperado:
            rechazos += 1
            if not obtenido:
                rechazos_vistos += 1
        fallos += not ok
        yield nombre, ok, obtenido, esperado
    correr.resumen = (casos, fallos, rechazos, rechazos_vistos)


total = 0
for nombre, ok, obtenido, esperado in correr(filas_ts.fallos_ts):
    print(("✅ " if ok else "❌ ") + nombre)
    if not ok:
        print(f"     esperado: {esperado}\n     obtenido: {obtenido}")
casos, fallos, rechazos, _ = correr.resumen
print(f"{casos - fallos}/{casos} casos")
total += fallos

# Ni filas_ts.py ni validate_roundtrip.py importan numpy (el bloqueo de arriba ya lo prueba para filas_ts; esto,
# para el validador, que es un script y no se importa).
for f in ("filas_ts.py", "validate_roundtrip.py"):
    with open(os.path.join(aqui, f), encoding="utf-8") as fh:
        importa = [l for l in fh if re.match(r"\s*(import|from)\s+numpy\b", l)]
    print(("❌ " if importa else "✅ ") + f"{f} no importa numpy")
    total += bool(importa)

with open(os.path.join(aqui, "validate_roundtrip.py"), encoding="utf-8") as fh:
    usa = sum(1 for l in fh if re.match(r"\s*from filas_ts import ", l))
print(("✅ " if usa == 1 else "❌ ") + "validate_roundtrip.py usa filas_ts")
total += usa != 1

# Contra una función que lo acepta todo, cada rechazo tiene que dar ❌.
list(correr(lambda *a, **k: []))
_, _, esperados, vistos = correr.resumen
if vistos == esperados:
    print(f"✅ contra una función que lo acepta todo fallan los {esperados} casos de rechazo")
else:
    print(f"❌ contra una función que lo acepta todo fallan {vistos} de los {esperados} casos de rechazo")
    total += 1

print("✅ test-parquet-filas" if total == 0 else f"❌ test-parquet-filas: {total} fallos")
sys.exit(1 if total else 0)
