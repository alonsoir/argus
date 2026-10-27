#!/usr/bin/env python3
"""DAY309 [TESTS-REG-D309] — registra en ctest cuatro tests del sniffer que se compilaban sin add_test.

DEBT-SNIFFER-TESTS-NOT-REGISTERED-001: test_sharded_flow_full_contract (3), test_ring_consumer_protobuf (4),
test_sharded_flow_multithread (6), y ademas test_proto3_embedded_serialization (3), hallado en el inventario
completo de DAY309. test_payload_analyzer NO se registra (4 de 18 fallan desde 00a67a6a: deuda propia).

Toca un solo fichero: sniffer/CMakeLists.txt. Inserta una linea add_test justo antes de la linea message() de
cada test. Valida TODO antes de escribir NADA: sha256 de partida, cada ancla presente una sola vez, ningun
add_test previo de esos tests, sha256 de llegada del resultado calculado en memoria. Escritura atomica.

Uso (desde la raiz del repo):
    python3 scripts/flow_expiry/d309_registrar_tests.py --check
    python3 scripts/flow_expiry/d309_registrar_tests.py --apply
"""
import hashlib
import os
import sys

FICHERO = "sniffer/CMakeLists.txt"
SHA_PARTIDA = "b4f8747ec05649f05cee088932562af9b619f296841df670676cee2eeebd4920"
SHA_LLEGADA = "447344f882151da0be9668abbd3fcaf491930ba132c51783cfdeb6ea8d8ddd98"
TAG = "  # [TESTS-REG-D309] DEBT-SNIFFER-TESTS-NOT-REGISTERED-001"

# (test, ancla = inicio de su linea message(), unica en el fichero)
TESTS = [
    ("test_sharded_flow_full_contract",
     'message(STATUS "🧪 Unit Test: test_sharded_flow_full_contract configured'),
    ("test_ring_consumer_protobuf",
     'message(STATUS "🧪 Unit Test: test_ring_consumer_protobuf configured'),
    ("test_proto3_embedded_serialization",
     'message(STATUS "🧪 Unit Test: test_proto3_embedded_serialization configured'),
    ("test_sharded_flow_multithread",
     'message(STATUS "🧪 Unit Test: test_sharded_flow_multithread configured'),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def linea_add_test(t):
    return f"add_test(NAME {t} COMMAND {t}){TAG}\n"


def transformar(texto):
    errores = []
    lineas = texto.splitlines(keepends=True)
    for t, ancla in TESTS:
        if f"add_test(NAME {t} " in texto:
            errores.append(f"{t}: ya tiene add_test")
        n = sum(1 for l in lineas if l.startswith(ancla))
        if n != 1:
            errores.append(f"{t}: ancla encontrada {n} veces (se espera 1): {ancla!r}")
    if errores:
        return None, errores
    salida = []
    for l in lineas:
        for t, ancla in TESTS:
            if l.startswith(ancla):
                salida.append(linea_add_test(t))
        salida.append(l)
    return "".join(salida), []


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        return 2
    modo = sys.argv[1]
    if not os.path.isfile(FICHERO):
        print(f"ABORTA: no existe {FICHERO} (lanzar desde la raiz del repo)")
        return 3
    actual = open(FICHERO, "rb").read()
    s = sha(actual)
    if s == SHA_LLEGADA:
        print(f"YA APLICADO: {FICHERO} sha256={s}")
        return 0
    if s != SHA_PARTIDA:
        print(f"ABORTA: sha256 de partida inesperado en {FICHERO}\n  es:       {s}\n  esperado: {SHA_PARTIDA}")
        return 4
    nuevo, errores = transformar(actual.decode("utf-8"))
    if errores:
        print("ABORTA:")
        for e in errores:
            print("  " + e)
        return 5
    nb = nuevo.encode("utf-8")
    if sha(nb) != SHA_LLEGADA:
        print(f"ABORTA: sha256 de llegada inesperado\n  es:       {sha(nb)}\n  esperado: {SHA_LLEGADA}")
        return 6
    n_antes = actual.decode("utf-8").count("\nadd_test(") + actual.decode("utf-8").count("\n  add_test(")
    n_despues = nuevo.count("\nadd_test(") + nuevo.count("\n  add_test(")
    print(f"{FICHERO}: add_test {n_antes} -> {n_despues}")
    for t, _ in TESTS:
        print(f"  + {linea_add_test(t).rstrip()}")
    if modo == "--check":
        print(f"CHECK OK: partida {SHA_PARTIDA[:12]}… -> llegada {SHA_LLEGADA[:12]}… (nada escrito)")
        return 0
    tmp = FICHERO + ".d309.tmp"
    with open(tmp, "wb") as f:
        f.write(nb)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, FICHERO)
    final = sha(open(FICHERO, "rb").read())
    if final != SHA_LLEGADA:
        print(f"ERROR: tras escribir, sha256={final} (esperado {SHA_LLEGADA})")
        return 7
    print(f"APLICADO: {FICHERO} sha256={final}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
