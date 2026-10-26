#!/usr/bin/env python3
# DAY308 paso 2 — documentacion: resultado del paso (seccion 6 de docs/ml-heads/day308_paso2_diseno.md, escrita
# despues de medir; las secciones 1-5 no se tocan) y seccion "DAY308 — paso 2" al final de docs/BACKLOG.md
# (DEBT-SNIFFER-FLOWTABLE-CONFIG-001 cerrada, avance de DEBT-SNIFFER-FLOW-EXPIRY-001, barrido en rama propia,
# correccion del total de tests, errata del commit 1612f037, lecciones). Solo anade texto al final de los dos ficheros.
# Valida TODO antes de escribir NADA (sha256 de partida y de llegada, anclas unicas). Reconoce "ya aplicado".
# Conserva los permisos de cada fichero.
# Uso (Mac, raiz del repo): python3 scripts/flow_expiry/d308_docs_paso2.py --check | --apply
import hashlib, os, shutil, sys

EDITS = {'docs/ml-heads/day308_paso2_diseno.md': {'antes': 'c6cbf763c60c1d5dc70c3c05d9768c636fd946da41f26924d6f58851930fd426', 'despues': 'c3c3a97f7228470e9aac6e22a72dc903912c136c83f76a47195f155189d3c5e7', 'rep': [('   el parser de `flow_table` (ausente, no entero, fuera de rango, reglas cruzadas → defecto y aviso).\n4. `make pipeline-build PROFILE=production`, `make test-components PROFILE=production`, tests sin registrar, paridad\n   en los dos perfiles, instrumento de limpieza después, y E2E del lab con la línea `[FLOW-TABLE]`.\n', '   el parser de `flow_table` (ausente, no entero, fuera de rango, reglas cruzadas → defecto y aviso).\n4. `make pipeline-build PROFILE=production`, `make test-components PROFILE=production`, tests sin registrar, paridad\n   en los dos perfiles, instrumento de limpieza después, y E2E del lab con la línea `[FLOW-TABLE]`.\n\n## 6. Resultado (escrito DESPUÉS de medir; las secciones 1-5 se dejan como se escribieron antes)\n\nCommit del paso: `97e48add` (`feat(sniffer): DAY308 paso 2 — caducidad de la tabla de flujos, configurada en\nflow_table`). Medidas en el defender.\n\n### 6.1 Decisiones de Alonso\n\nP1: `idle_timeout_s` 300 s, también como defecto en el código. P2: `cleanup_interval_ms` 1 000 y `log_interval_s` 60,\ncon el mismo criterio: el JSON se lee siempre; si un campo falta, no es entero o está fuera de rango, se aplica el\ndefecto escrito en el código (igual al del JSON) y se avisa. P3: aviso `[CONFIG-OBSOLETO]`, y la línea `[FLOW-TABLE]`\ndel arranque dice el valor de cada campo y de dónde sale (JSON o defecto, y por qué). P4: fuera\n`d307_paridad_rasgos.cpp`.\n\n### 6.2 Cambio sobre el diseño, antes de escribir el parche\n\nLos parámetros (`flow_table_params.hpp`, sin JSON) se separan del lector (`flow_table_config.hpp`, con jsoncpp): el\n`ShardedFlowManager` incluye solo los parámetros, para que los tests y los instrumentos que lo enlazan no necesiten\njsoncpp. El lector sigue el patrón de `heads_config.hpp` (DAY305): sin estado y probado suelto.\n\n### 6.3 Medidas\n\n| | Antes | Paso 2 |\n|---|---|---|\n| Limpieza, 80 000 flujos, nada caducado (por pasada) | 8,7-9,1 ms | 1,2 µs |\n| Limpieza, 8 000 caducados | 1,49-1,57 s | 2,5-2,6 ms |\n| Limpieza, 72 000 caducados | 6,0-6,1 s | 32 ms |\n| Paridad sin banderas (contra `antes.tsv`) | — | idéntica (`fbc2b693…`) |\n| Paridad con banderas de producción (contra el paso 1) | — | 0 eventos distintos |\n| Tests del sniffer en ctest | 18 | 19 (`test_flow_expiry`) |\n| Tests sin registrar (4 / 6 / 3) | pasan | pasan |\n\n`test_flow_expiry`: 26 pruebas; detecta las cuatro mutaciones probadas (sin guarda en `should_expire`, tope roto,\ndesalojo sin contar, limpieza que no para en la cola).\n\n**E2E del lab** (pipeline completo, 7 minutos, tráfico de fondo): la línea `[FLOW-TABLE]` del arranque con los seis\ncampos de origen `(JSON)`; ningún `[CONFIG-DEFAULT] flow_table` ni `[CONFIG-OBSOLETO]`; 7 líneas periódicas con\n`marcas_futuras=0` y `desalojos_lru=0` en todas; vivos de 22 a 72; 12 y 13 caducados en las líneas 6 y 7 (los\nprimeros flujos en pasar 300 s sin paquetes); `max_lock_us` entre 10 y 277.\n\n**`marcas_futuras=0` mide la suposición de §1:** la marca del paquete (`bpf_ktime_get_ns`) y la hora de la tabla\n(`steady_clock`) son el mismo reloj.\n\n### 6.4 Predicciones\n\n- **Se cumplieron:** paridad en los dos perfiles; caducados exactos; limpieza con 8 000 y 72 000 caducados (2-5 ms y\n  20-40 ms predichos); E2E (orígenes JSON, `marcas_futuras=0`, `desalojos_lru=0`, caducados hacia la 6.ª línea).\n- **Fallaron:**\n  - **Limpieza sin caducados (2-4 µs predichos, 1,2 µs medidos).** Apliqué el factor del defender en trabajo con\n    memoria a una pasada que solo mira la cola de 16 shards.\n  - **Antes de la limpieza con 72 000 caducados (2,7-4,5 s predichos, 6 s medidos).** El mismo error en sentido\n    contrario: `list::remove` persigue punteros por memoria, y ahí la VM castiga más que el factor del microbanco\n    (×3,4).\n  - **"83 de 83" en `make test-components`: mal planteada.** El "82" del log es el número de tests del firewall, no\n    el total (9 + 19 + 15 + 3 + 82 = 128). La regla de comprobación de DAY307 (`grep \'out of 82\'`) solo miraba al\n    firewall: se corrige comprobando las cinco líneas de resumen, cada una con su número esperado, y que todas digan\n    `0 tests failed`.\n- **Diferencia con el diseño:** el instrumento de limpieza llena la tabla a la mitad (80 000 flujos), no entera, para\n  que la LRU no desaloje y los caducados esperados sean exactos.\n\n### 6.5 Siguiente en la rama\n\nBatería de la etapa 2 (ddos_v2) y E2E antes/después; registrar en ctest los tres tests sin registrar\n(DEBT-SNIFFER-TESTS-NOT-REGISTERED-001); EMECAS+++ production; PR.\n')]}, 'docs/BACKLOG.md': {'antes': 'db8e8c67b22e8a084e58541d5eab937b92b949871bacf03eba0f61dd5d545f52', 'despues': 'e4df755aaf6cac5cc6cbf1407b61461da4eccd9a05a1bc7f71d2509acadd5c3d', 'rep': [('predecir RAM, medir el sizeof (el alineamiento de __int128 rellena). Una prueba de mutacion dice que ve cada\nherramienta: el instrumento de paridad no veia marcas repetidas; el test si. Las secciones escritas antes de medir no\nse reescriben: el resultado va aparte.\n', 'predecir RAM, medir el sizeof (el alineamiento de __int128 rellena). Una prueba de mutacion dice que ve cada\nherramienta: el instrumento de paridad no veia marcas repetidas; el test si. Las secciones escritas antes de medir no\nse reescriben: el resultado va aparte.\n\n## DAY308 — paso 2 (rama feat/sniffer-flow-expiry)\n\nDocumento: `docs/ml-heads/day308_paso2_diseno.md` (diseno antes de medir, resultado en la seccion 6). Commit 97e48add.\n\n### DEBT-SNIFFER-FLOWTABLE-CONFIG-001 — CERRADA DAY308\nLa tabla de flujos se configura en un solo sitio, la seccion flow_table de sniffer.json (shards, max_flows_per_shard,\nidle_timeout_s 300, active_timeout_s 0 = sin tope, cleanup_interval_ms 1000, log_interval_s 60), con defectos iguales\nen el codigo (flow_table_params.hpp), [CONFIG-DEFAULT] por campo y linea [FLOW-TABLE] con el valor y el origen. Fuera\nkernel_space.flow_timeout_seconds, processing.feature_extraction.flow_timeout_seconds y user_space ([CONFIG-OBSOLETO]\nsi vuelven).\n\n### DEBT-SNIFFER-FLOW-EXPIRY-001 — EN CURSO (esta rama)\nPasos 1 (estadisticos incrementales) y 2 (caducidad) hechos DAY308. Caducidad: limpieza por inactividad desde la cola\nde la LRU (80000 flujos, 72000 caducados: 6,0 s -> 32 ms en el defender), tope de duracion activa perezoso (desactivado\npor defecto), should_expire con guarda, contadores en la linea [FLOW-TABLE]. E2E: marcas_futuras=0 (mismo reloj).\nQuedan: bateria de la etapa 2 (ddos_v2) y E2E antes/despues, registrar los 3 tests en ctest, EMECAS+++, PR.\n\n### Barrido de idle_timeout_s y active_timeout_s — rama propia (decision DAY308)\nLos defectos (300 s, sin tope) son seguros, no optimos. El valor optimo se mide con una herramienta de barrido fuera de\nlinea (pcap -> ShardedFlowManager real + foto DDoS, varios valores) en tres ejes: memoria y flujos vivos, efecto en la\npuntuacion y decisiones de ddos_v2 (entrenada sin caducidad, con corridas cortas) en ataque, ataque largo y benigno, y\ncoste de la limpieza. Va junto a DEBT-DDOS-V2-LONG-ATTACK-001.\n\n### Correccion de metodo — total de tests de make test-components\nEl "out of 82" que se comprobaba desde DAY307 es el numero de tests del firewall, no el total. Hay cinco lineas de\nresumen (flow_uid 9, sniffer 19, ml-detector 15, autonomia 3, firewall 82 = 128): se comprueban las cinco, cada una con\nsu numero esperado, y que todas digan 0 tests failed.\n\n### Errata del commit 1612f037 (paso 1)\nSu mensaje dice "0 B por paquete (antes ~47)" y "copia ... 7,9 ms": son cifras de otra maquina. En el defender, DAY307\nmidio ~30 B por paquete (292 MB a 10 M paquetes) y 7,7 ms. Las cifras correctas estan en day308_paso1_diseno.md.\n\n### Lecciones DAY308 (paso 2)\nUn factor entre maquinas medido en un tipo de trabajo no vale para otro: la persecucion de punteros (list::remove) pago\nx3,4 en la VM; mirar 16 colas apenas paga nada. Un resumen de herramienta se lee entero antes de convertirlo en regla.\n')]}}


def die(m):
    print("ABORTA: " + m)
    sys.exit(1)

def sha_b(b):
    return hashlib.sha256(b).hexdigest()

def sha(p):
    return sha_b(open(p, "rb").read())

if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    die("uso: --check | --apply")
APPLY = sys.argv[1] == "--apply"
if not (os.path.isfile("Makefile") and os.path.isdir("sniffer/src/userspace")):
    die("no estoy en la raiz del repo")
for p in EDITS:
    if not os.path.isfile(p):
        die(f"falta {p}")
if all(sha(p) == e["despues"] for p, e in EDITS.items()):
    print("[YA APLICADO] documentacion del paso 2 hecha. Nada que hacer.")
    sys.exit(0)
nuevos = {}
for p, e in EDITS.items():
    s = sha(p)
    if s != e["antes"]:
        die(f"{p} sha256 {s} no es el de partida (estado mixto o fichero cambiado)")
    t = open(p, encoding="utf-8").read()
    for a, b in e["rep"]:
        if t.count(a) != 1:
            die(f"{p}: ancla x{t.count(a)} (esperado 1): {a[:60]!r}")
        t = t.replace(a, b)
    if sha_b(t.encode("utf-8")) != e["despues"]:
        die(f"{p}: el resultado no tendria el sha256 esperado")
    nuevos[p] = (t, len(e["rep"]))
for p, (_, n) in nuevos.items():
    print(f"[OK] editar {p} ({n} bloques)")
if not APPLY:
    print("[CHECK] todo valida; nada escrito. Repite con --apply.")
    sys.exit(0)
for p, (t, _) in nuevos.items():
    tmp = p + ".d308tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    shutil.copymode(p, tmp)
    os.replace(tmp, p)
if any(sha(p) != e["despues"] for p, e in EDITS.items()):
    die("verificacion posterior fallida")
print("[APLICADO] documentacion del paso 2.")
