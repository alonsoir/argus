# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 231

## Punto de entrada (léeme primero)

Al arrancar, **mide el estado, no lo asumas**:

```
git log --oneline -5 main
git branch
vagrant status
```

Estado esperado tras DAY 230: `fix/sniffer-ip-byte-order` (PR #127) y
`feat/suricata-to-graph` (PR #128) **mergeadas a main**; una sola rama, el
repo entrando en su tramo de cierre. Las ramas `feat/suricata-to-graph` y
`feat-prerebase-backup` deberían estar borradas. Si `git log` no muestra los
dos merges en main, esa es la primera tarea antes que ninguna otra.

## El ⚪️ que ordena el día

**DEBT-SNIFFER-IP-BYTE-ORDER-001 está ARREGLADA EN CÓDIGO
(test_ip_format 6/6 + EMECAS+++ verde), pero el E2E CON DATOS REALES sigue
PENDIENTE.** Nadie ha visto todavía un bronce nuevo con IPs `147.32.84.x`
reales, ni la convergencia aRGus↔Suricata en el mismo `NetworkFlow`. EMECAS
verde **no** cierra esto: su `test_bronze_to_kuzu_circuit` firma con clave
constante y datos de fixture — es ciego al byte order. El cierre real llega
provocando tráfico real al grafo (paso 2 del plan de cierre, script MITRE).
**No marcar la deuda "cerrada" hasta medir eso.**

## Invariantes (no negociar)

- **Medir, no votar.** Cada afirmación se traza a salida de comando. HECHO ≠
  SOSPECHADO. Verde en un test sintético no es verde en el sistema.
- **Un día, una batalla.** Elegir una y cerrarla; no abrir tres frentes.
- **Via Appia.** Construir para durar; un criterio que no puede ponerse rojo
  no mide nada.
- No `grep -rn` desde la raíz (arrastra build/.git/.venv — un grep así corrió
  toda una noche sin acabar); usar `git grep`. No encadenar comandos de salida
  grande en el mismo bloque del terminal.

## Qué se cerró en DAY 230

1. **Hallazgo de paper, medido.** El crosscheck de paridad de `community_id`
   disparó `exit 2` durante ~5 meses etiquetado como "cobertura asimétrica
   esperada" (ruido). Medido en `logs/lab/cid-xcheck-anomalies.tsv` (42.838
   líneas, mtime 2-jun, ~14k anomalías): las filas de aRGus llevaban IPs
   invertidas (`165.84.32.147` = host Neris del CTU-13 swapeado) mientras
   Suricata+Zeek acordaban las correctas (`147.32.84.165`). Dos puertas
   cerradas: el bug llegó al oráculo (`community_id_log.cpp` comparte la
   corrupción de IP) y el 3-way corrió de verdad. CAVEAT: el anomalies.tsv es
   PRE-fix → prueba que el bug era real, NO verifica el arreglo. Es página de
   paper.
2. **DEBT-VM-SENSOR-NO-TOOLCHAIN-001 pagada y probada desde cero.** Bloque
   `ADAPTER_TOOLCHAIN` en el Vagrantfile raíz (suricata/zeek/wazuh),
   verificación por invocación (`g++ -fsyntax-only` sobre `#include`, no
   `test -f`). Probado en EMECAS: `Setting up build-essential` en la VM
   `suricata` recreada de cero.
3. **emecas:1262** `vagrant up` → `vagrant up defender client suricata` (antes
   levantaba solo `defender` por el `autostart:false` de los sensores, así que
   el gate nunca ejercitaba la VM de sensor ni el toolchain).
4. **#127** fix→main. **#128** feat rebasada sobre main (byte order heredado,
   `ip_host_to_buffer` verificado en las 4 llamadas de `ring_consumer.cpp`) +
   EMECAS+++ verde → main.

## Deudas abiertas relevantes

- **DEBT-SNIFFER-IP-BYTE-ORDER-001** — ARREGLADA EN CÓDIGO, E2E CON DATOS
  REALES PENDIENTE (paso 2 MITRE). *El ⚪️ del día.*
- **DEBT-SENSOR-VMS-IN-ROOT-VAGRANTFILE-001** (DAY 230) — las 3 VMs de sensor
  viven en el Vagrantfile raíz; separarlas exige resolver la red interna
  compartida (`ml_defender_gateway_lan`) que el crosscheck necesita. Futuro,
  NO cierre.
- **DEBT-SURICATA-VM-DUPLICADA-001** (DAY 230) — dos VMs `suricata` (raíz vs
  `experiments/suricata-comparative/`) con provisioning independiente. Medir
  si la de experiments/ necesita el mismo toolchain y lo tiene.
- **DEBT-BRONZE-KEY-PROVISIONING-001** — dos fuentes de verdad para la clave
  HMAC: aRGus firma con clave de etcd (runtime), el consumidor del
  correlation-engine lee de env. Con bronce plano + consumidor de clave única,
  hay que unificar. Sin resolver.
- **Telemetría D4** — los ~104k eventos dns/http/tls de Suricata (98,7% del
  volumen) siguen descartados; no llegan al grafo. Alonso ratificó DAY 230 que
  "que toda la información de Suricata acabe en el grafo" es la misión.

## Batalla candidata para DAY 231

**Recomendación: paso 2 del plan de cierre — script MITRE → tráfico real →
grafo.** Cierra tres cosas de una: (a) el ⚪️ del byte order (bronce con IPs
reales + convergencia aRGus↔Suricata en el mismo `NetworkFlow`); (b) es el
siguiente paso natural del cierre; (c) hace observable el movimiento lateral
(Wazuh, arista Host↔Flow inferencial) que un replay de pcap no produce.

Primer paso barato: localizar el mecanismo de generación de tráfico real
—¿existe ya?— con `git grep -il mitre`, `ls experiments/`, y mirar el
`client-setup` (clona atomic-red-team).

Alternativas, si se prefiere otro frente:

- **Telemetría D4 al grafo** (la misión "toda la info"). Muro a medir ANTES de
  mapear: `validate()` exige `community_id` como requisito duro de
  correlation_v1 y los dns/http/tls pueden no llevarlo → decidir Opción A
  (aceptar `TelemetryEvent` sin cid) o sintetizar. Medida barata:
  `tools/eval/eve_field_coverage.py` (cobertura de community_id por tipo de
  evento).
- **is_external_ip / is_new_external_ip** (`fast_detector.cpp`). ¿El fast path
  sigue clasificando interno como externo? Usa `evt.dst_ip` numérico, el fix
  de ayer no lo tocó. Lectura barata, correctness viva; si está roto, abre otra
  batalla.

## Recordatorio de tono de trabajo

Alonso pilota; mide contra fichero y pégalo, no votes de memoria. Fichero
completo, no `sed -n`. `git add` explícito por fichero (nunca `-A`/`-u`: se
cuela scratch). A las horas malas, parar antes que forzar un merge o un rebase.