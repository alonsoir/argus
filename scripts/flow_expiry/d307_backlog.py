#!/usr/bin/env python3
# DAY307 — BACKLOG: cabecera "Ultima actualizacion" a DAY 307 y seccion "Cierre DAY307" al final.
# Comprueba sha256 de partida, la cabecera exacta y el salto final; sha256 de llegada. Reconoce "ya aplicado".
# Uso (Mac, raiz del repo, en la rama feat/sniffer-flow-expiry): python3 scripts/flow_expiry/d307_backlog.py --check|--apply
import hashlib, os, sys
P = "docs/BACKLOG.md"
ANTES = "26d9c489ec7f958b8281a54e85478d7eae741e00ce27561e76922d41c01ac8a7"
DESPUES = "66772d6ed93294bd672b92abe1c7b04d63a2264566a7397b3f818280da6eee66"
CAB_VIEJA = "*\u00daltima actualizaci\u00f3n: DAY 305 \u2014 2026-10-23*"
CAB_NUEVA = "*\u00daltima actualizaci\u00f3n: DAY 307 \u2014 2026-10-25*"
SECCION = '\n## Cierre DAY307 (25-oct-2026) — rama feat/sniffer-flow-expiry (en curso)\n\nDocumento: `docs/ml-heads/day307_tabla_flujos.md`. Herramientas: `scripts/flow_expiry/`. Regla de la rama (Alonso):\ncada paso se mide antes y despues. Ningun commit del dia cambia lo que sale del sniffer (paridad byte a byte en\n300000 eventos, d307_paridad_rasgos.cpp, sha256 64471c1e...).\n\nHecho (commits 290f342d, 62b3c204, 0f5e5a8e, 73d27542, bdf2506b): include canonico de sharded_flow_manager.cpp\n(incluia _fix3.hpp, ODR latente desde Day 45) y fuera 9 residuos _fix*/_original; fuera la clase FlowManager y\nscripts/verify_integration.sh; fuera TimeWindowManager por flujo y la clase FeatureExtractor (sin lector vivo);\nfuera el mecanismo feature_groups de sniffer.json y sus dos JSON; fuera el calculo de los 5 rasgos DDoS en populate\n(ring_consumer los sobrescribia siempre con la foto en lock). Medido: RAM por flujo 1697 -> 658 B (tabla llena\n265 -> 103 MB); populate por evento 121 -> 92,7 us de media (flujos de 501+ paquetes 289 -> 216 us).\n\n### DEBT-SNIFFER-FLOW-EXPIRY-001 — EN CURSO (esta rama)\nMedido DAY307: el estado de un flujo que nunca esta inactivo crece ~30 B por paquete sin limite (10 M paquetes =\n292 MB un solo flujo) y la copia por evento es O(n) (7,7 ms a 1 M paquetes). Pendiente: paso 1 (estadisticos\nincrementales en FlowStatistics, con diseno y tolerancia de paridad escritos antes del codigo), limpieza periodica\ndesde la cola de la LRU (hoy cleanup_expired_flows no se llama y es O(n^2)), guarda en should_expire (resta sin\nsigno), decision sobre tope de duracion activa, bateria de la etapa 2 y E2E antes/despues.\n\n### DEBT-SNIFFER-FLOWTABLE-CONFIG-001 — ampliada DAY307 (esta rama)\nsniffer.json declara tres timeouts de flujo (kernel_space.flow_timeout_seconds,\nprocessing.feature_extraction.flow_timeout_seconds, bloque user_space con flow_table_size 1000000 y\ngc_interval_seconds 60) y ninguno se aplica: la tabla real es 16 x 10000 escrita en ring_consumer.cpp:131 y no\ncaduca. La configuracion de la tabla ira en un solo sitio del JSON, validada y registrada en el log, y los campos\nque mienten se quitan en el mismo cambio.\n\n### DEBT-SNIFFER-TESTS-NOT-REGISTERED-001 — ABIERTA (esta rama)\ntest_ring_consumer_protobuf (4), test_sharded_flow_multithread (6) y test_sharded_flow_full_contract (3) se\ncompilan pero no tienen add_test: test-components no los ejecuta nunca. Pasan los tres (a mano, DAY307).\nMisma familia que DEBT-MLDETECTOR-TESTS-NOT-BUILT-001.\n\n### DEBT-SNIFFER-FLOW-UNIDIRECTIONAL-001 — ABIERTA (decision de diseno)\nring_consumer.cpp construye la FlowKey con los campos del paquete y FlowKey no normaliza el sentido: cada sentido\nde una conversacion es un flujo propio. dpkts, bwd_* y los rasgos backward salen siempre a 0; el SYN-ACK de la\nrespuesta cae en el flujo inverso. ddos_v2 se entreno asi: cambiarlo exige medir y probablemente reentrenar.\n\n### DEBT-SNIFFER-FLOWKEY-HASH-001 — ABIERTA\nFlowKey::Hash combina los campos con XOR y desplazamientos (debil). Afecta al reparto entre shards. Medir el\nreparto antes de cambiarlo.\n\n### DEBT-SNIFFER-CONFIG-CEREMONIAL-001 — ABIERTA (rama propia)\nLa configuracion del sniffer es en buena parte ceremonial: campos sin consumidor, defectos aplicados en silencio\ncon get(campo, defecto) (contra la regla DAY291/DAY300), dos modelos de configuracion (SnifferConfig y\nStrictSnifferConfig, con campos que nunca se rellenan) y 20 validate_*_section vacios. Auditoria campo a campo de\nsniffer.json: consumido / no consumido / leido en silencio; un solo modelo.\n\n### DEBT-REPO-RESIDUOS-001 — ampliada DAY307\nscripts/timebase/__pycache__/ sin trackear ni ignorado; commit-message.txt (buffer de commits con -F, ya no se usa);\nday290_patch_ddos_snap.py nombra ficheros borrados en DAY307.\n\n### Lecciones DAY307\nCon LTO el hash del .o no compara codigo (guarda ubicaciones fuente): comparar el preprocesado. git log -S cuenta\napariciones; para una linea, git log -G. Un inventario no se trunca. En un bucle con | grep, $? es el del grep.\nLos logs de ctest llevan colores ANSI dentro de la linea. Una prediccion de tiempo medio pesa eventos, no\nconversaciones.\n'

def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha(b):
    return hashlib.sha256(b).hexdigest()

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
if not os.path.isfile(P):
    die("no estoy en la raiz del repo")
s = sha(open(P, "rb").read())
if s == DESPUES:
    print("[YA APLICADO] nada que hacer.")
    sys.exit(0)
if s != ANTES:
    die(f"{P} sha256 {s} no es el de partida")
t = open(P, encoding="utf-8").read()
if t.count(CAB_VIEJA) != 1 or not t.endswith("\n"):
    die("cabecera o salto final no son los esperados")
n = t.replace(CAB_VIEJA, CAB_NUEVA, 1) + SECCION
if sha(n.encode("utf-8")) != DESPUES:
    die("el resultado no tendria el sha256 esperado")
print(f"[OK] {P}: cabecera DAY 307 y seccion Cierre DAY307 ({SECCION.count(chr(10))} lineas)")
if sys.argv[1] == "--check":
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)
tmp = P + ".d307tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(n)
os.replace(tmp, P)
if sha(open(P, "rb").read()) != DESPUES:
    die("verificacion posterior fallida")
print("[APLICADO] BACKLOG actualizado.")
