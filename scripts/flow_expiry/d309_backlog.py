#!/usr/bin/env python3
"""DAY309 — anade al final de docs/BACKLOG.md la seccion DAY309 (resultado medido del registro de tests).

Valida TODO antes de escribir NADA: sha256 de partida, que no exista ya una seccion "## DAY309", que el fichero
termine en salto de linea, sha256 de llegada del resultado calculado en memoria. Escritura atomica.

Uso (desde la raiz del repo):
    python3 scripts/flow_expiry/d309_backlog.py --check
    python3 scripts/flow_expiry/d309_backlog.py --apply
"""
import hashlib
import os
import sys

FICHERO = "docs/BACKLOG.md"
SHA_PARTIDA = "e4df755aaf6cac5cc6cbf1407b61461da4eccd9a05a1bc7f71d2509acadd5c3d"
SHA_LLEGADA = "97bf1c04a2b2030be0f6870001237f188c3c4c08796999100aef5c7e41e738e1"

SECCION = """
## DAY309 (27-oct-2026) — rama feat/sniffer-flow-expiry, registro de tests

Parcheador: `scripts/flow_expiry/d309_registrar_tests.py` ([TESTS-REG-D309], solo sniffer/CMakeLists.txt, 4 lineas
add_test). Medido en el defender y desde el Mac: pipeline-build production con 0 diagnosticos; make test-components
PROFILE=production con flow_uid 9, sniffer 23 (antes 19), ml-detector 15, autonomia 3, firewall 82 = 132, 0 fallos.

### DEBT-SNIFFER-TESTS-NOT-REGISTERED-001 — CERRADA DAY309
El inventario completo de sniffer/CMakeLists.txt (cada add_executable contra su add_test) daba 5 tests sin registrar,
no 3: los tres de la deuda, test_proto3_embedded_serialization y test_payload_analyzer. Registrados los cuatro que
pasan: test_sharded_flow_full_contract (3), test_ring_consumer_protobuf (4), test_sharded_flow_multithread (6) y
test_proto3_embedded_serialization (3). test_payload_analyzer queda fuera (DEBT-SNIFFER-PAYLOAD-ANALYZER-001).
Notas medidas al registrarlos:
- test_proto3_embedded_serialization solo enlaza network_security.pb.cc: comprueba el comportamiento de protobuf y que
  existan y se serialicen los campos v2 del .proto, no el arreglo de send_ransomware_features que dice vigilar; su
  comentario nombra el rag_logger, ya retirado. Se registra porque salta si alguien vuelve a tocar esos campos.
- test_sharded_flow_multithread imprime Duration y Throughput pero no los afirma (sus aserciones son de cuentas).
  ShardDistribution no mide el reparto entre shards, solo que los 1000 flujos se recuperan (el reparto sigue en
  DEBT-SNIFFER-FLOWKEY-HASH-001). Las lineas "142/142 features" y "Shards: 16" son texto fijo, no medidas.
- Los fixtures de los tres tests de DAY46 fijan idle_timeout_ns = 120 s (valor heredado del renombrado del paso 2);
  ninguno depende de la caducidad. El defecto del codigo sigue en 300 s (flow_table_params.hpp).
- El target test-hardening del Makefile (compila y lanza a mano los tres de DAY46) se queda: entrada directa a ese
  subconjunto.

### DEBT-SNIFFER-PAYLOAD-ANALYZER-001 — ABIERTA
test_payload_analyzer (18 pruebas, nunca en ctest) falla 4 de 18: 10 nota de rescate, 11 API criptografica, 12
direccion .onion, 13 mayusculas/minusculas. Causa leida en el codigo: el commit 00a67a6a hizo perezosa la busqueda de
patrones (solo con entropia > 7,0 o cabecera PE) y esas pruebas usan texto plano, de entropia baja: siguen afirmando
el contrato anterior. La prueba de tiempo se llama test_performance_under_10us pero su umbral es 250 us; medido en el
defender: 160-199 us en 6 corridas sobre 512 B aleatorios (entropia alta: rama cara, 53 patrones con tolower byte a
byte). Margen ~25 %: fragil en ctest con la VM cargada. En produccion (ring_consumer.cpp, Layer 1.5) solo corre con
verbosidad BASIC o superior ([PAYLOAD-VERBOSE-D290]) y su resultado solo llega a la linea [Payload] Suspicious del log
(TODO: llevarlo al protobuf); con verbose, cada payload de entropia alta (TLS) pagaria ~180 us por evento en el hilo
del consumidor. Su futuro (arreglar test y aserto de tiempo, conectarlo o borrarlo) se decide con la reescritura de la
cabeza ransomware, la unica que podria consumirlo.

### DEBT-REPO-RESIDUOS-001 — ampliada DAY309
sniffer/include/payload_analyzer.hpp.v1.0 y sniffer/src/userspace/payload_analyzer.cpp.v1.0 (version anterior a la
busqueda perezosa) estan trackeados: se borran (la historia de git los conserva).

### DEBT-SNIFFER-FLOW-EXPIRY-001 — EN CURSO (esta rama)
Registro de tests hecho DAY309. Quedan: bateria de la etapa 2 (ddos_v2) y E2E antes/despues, con una corrida que deje
inactivos mas de idle_timeout_s flujos que luego vuelven (las corridas de DAY292-294 duran 210 y 450 s y no ejercitan
la caducidad); EMECAS+++ production; PR.

### Lecciones DAY309
Antes de predecir lo que mide un test, leer el codigo que prueba y no solo el test: la prediccion de la prueba de tiempo
(1-50 us) fallo porque su payload aleatorio toma la rama cara. Un inventario se saca contra el fichero (cada
add_executable con su add_test), no se hereda de la lista de una deuda.
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


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
    texto = actual.decode("utf-8")
    errores = []
    if "\n## DAY309" in texto:
        errores.append("ya existe una seccion '## DAY309'")
    if not texto.endswith("\n"):
        errores.append("el fichero no termina en salto de linea")
    if errores:
        print("ABORTA:")
        for e in errores:
            print("  " + e)
        return 5
    nb = (texto + SECCION).encode("utf-8")
    if sha(nb) != SHA_LLEGADA:
        print(f"ABORTA: sha256 de llegada inesperado\n  es:       {sha(nb)}\n  esperado: {SHA_LLEGADA}")
        return 6
    print(f"{FICHERO}: {texto.count(chr(10))} -> {(texto + SECCION).count(chr(10))} lineas; secciones nuevas:")
    for l in SECCION.splitlines():
        if l.startswith("#"):
            print("  + " + l)
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
