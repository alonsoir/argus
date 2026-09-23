# Prompt de continuidad — aRGus NDR, DAY277 → DAY278

Sesión DAY277 cerrada. Hoy: revisión medida de RECIDIVISM-D276 (4 defectos corregidos, commit
`ad01395d` en `docs/ml-heads-grieta-b`, ya en origin) + preflight completo del experimento
end-to-end. Mañana: **ejecutar el experimento** siguiendo el guion de abajo, fase a fase.

Reglas de trabajo (se mantienen):
- Medir, no votar. Cada predicción se escribe ANTES de medir.
- Comandos separados, o cada salida a su propio fichero. Nunca `grep -rn` desde la raíz: `git grep` o ruta concreta.
- Los patchers/scripts los ejecuta Alonso en su VM Vagrant.
- El botón de copiar del chat NO es fiable para ficheros: pasar scripts como bloque `cat > fichero <<'EOF'`.
- Si un paso no da lo esperado: parar ahí, pegar la salida, no seguir a la siguiente fase.

---

## 1. Qué se cerró en DAY277 (commit ad01395d)

| ID | Defecto | Estado |
|---|---|---|
| H4 | Regresión D276: `compute_penalty_timeout()` devolvía 0 para "deshabilitado" y "permanente"; `add_batch()` emitía `timeout 0` (optional con valor 0 es truthy) ⇒ con `enabled=false` **toda IP quedaba bloqueada para siempre** | Corregido: `std::optional<uint32_t>`, nullopt = timeout del set |
| H2 | `strike_states_[ip]` (operator[]) en `flush_internal()` insertaba `{strikes=0}` saltándose `max_tracked_ips` | Corregido: `find()` de solo lectura |
| H5 | `strike_durations_sec` vacío ⇒ `size()-1` da la vuelta ⇒ acceso fuera de rango | Corregido: guarda + saneado |
| H6 | Flush fallido conserva `pending_ips_`; cada reintento volvía a sumar un strike ⇒ una sola detección podía llegar al máximo | Corregido: `pending_penalty_` (penalty una vez por IP pendiente, se vacía con `pending_ips_`) |

**Decisión de política (Alonso, DAY277): NUNCA bloqueo permanente automático.** Las IPs de botnets
suelen ser víctimas (equipos comprometidos, CGNAT). `permanent_after_strikes` → `max_penalty_after_strikes`
+ `max_penalty_sec` (2073600 s = 24 días). Clave antigua aceptada como fallback. Drop permanente = acción manual del admin.

**Medido:** techo del kernel ipset v7.17 = **2147483 s**; por encima ipset **rechaza** (no recorta) y
tumba el `restore` entero. `kIpsetMaxTimeoutSec` + validación en `set_recidivism_config()` (el sistema
arranca siempre, cada corrección deja ERROR visible) + cinturón en `add_batch()`.

**Concurrencia verificada:** todo acceso a `strike_states_`/`pending_penalty_` ocurre bajo `mutex_`
(`flush()` → `flush_internal()`; `set_recidivism_config` toma el lock). `compute_penalty_timeout` sigue
público por testabilidad (decisión: no renombrar a `_locked` mientras no haga falta).

**Tests (sobre binarios recompilados):** unit 92/92, e2e 4/4 contra ipset real.

## 2. Deuda registrada / pendiente de registrar en BACKLOG

- **DEBT-RECIDIVISM-OVERFLOW-RETRY-001 (H3)** — si el volcado de overflow falla, se reintenta en cada IP
  nueva bajo lock. Diseño acordado: (1) volcar `strike_states_` SIEMPRE en parada; (2) en arranque:
  comprobar escritura de `overflow_log_path` (si falla: arrancar igual con aviso visible), generar informe
  y "email" simulado = `.eml` con la lista adjunta en `outbox/` del pipeline + WARN, rotar el fichero ya
  reportado; (3) en caliente, reintento con backoff, no por IP. **Patcher pendiente.**
- **DEBT-MAKEFILE-TEST-STALE-BINARY-001** — `test-firewall(-e2e)` solo corren `ctest`, no compilan. Dieron
  verde sobre binarios viejos. Siempre `make firewall-build` antes.
- **DEBT-IPSET-COMMENT-FLAG-IMPLICIT-001** — la extensión `comment` del set depende de que el texto
  descriptivo `"comment"` del JSON no esté vacío (`main.cpp:530`).
- **DEBT-AUTONOMY-WHITELIST-BYPASSES-BLACKLIST-001 (H7)** — la cadena autónoma se engancha en INPUT pos 1
  con ACCEPT para 10/8, 172.16/12, 192.168/16 antes de su DROP ⇒ en modo autónomo un host interno
  comprometido (movimiento lateral) NO se bloquea. `whitelist_cidrs` no puede vaciarse (el loader lo rechaza).
- **DEBT-DATASET-CIC-LAB-PROVENANCE-001** — no consta el comando `tcprewrite` que generó `_0125_50k_lab.pcap`.
- Del DAY276: **DEBT-IPSET-ADD-EXIST-001** (auditoría de callers: hecha, solo `flush_internal` construye
  `IPSetEntry`) y **DEBT-RING-CONSUMER-SATURATION-001** (redacción pendiente de revisar por Alonso:
  "empeora con hardware real" es hipótesis, no medida).
- Higiene: `ipset_wrapper.cpp.old` / `.hpp.old` versionados; `.orig*` sin versionar en el árbol.

## 3. Hechos del preflight (medidos)

- Set de bloqueo: **`ml_defender_blacklist_test`** (hash:ip, timeout por defecto 3600, `max_elements 1000`,
  con `comment`). Cadena iptables: **`ML_DEFENDER_TEST`**. Whitelist ipset: `ml_defender_whitelist`.
- En el camino de bloqueo NO hay filtro de IPs privadas; `whitelist_cidrs` solo actúa en modo autónomo (H7).
- Log del firewall: **`/vagrant/logs/lab/firewall-agent.log`**, abierto en `>>` (acumula corridas ⇒ usar offset).
- Defender: `eth1` 192.168.56.20 (08:00:27:b1:57:70), `eth2` **192.168.100.1 (08:00:27:6f:63:da)**, ambas PROMISC.
- Pcap del flood: **`/vagrant/datasets/cicddos2019/_0125_50k_lab.pcap`** — 50 000 paquetes UDP,
  **origen único 192.168.100.50** → destino 192.168.100.1 / MAC de `eth2` de la defender ⇒ netfilter INPUT
  lo procesa ⇒ los contadores del DROP miden el efecto real. Replay usado en DAY273: `--pps=100 --intf1=eth1`
  desde `client` (~500 s).
- 192.168.100.50 es probablemente la propia VM `client` ⇒ **Neris primero**, y `ipset flush` al acabar.
- Neris (`test-replay-neris` / `ctu-start`) va con IPs originales (147.32.x), sin reescribir ⇒ como control
  mide decisiones (qué entra al set), no el DROP. `ctu-start` además alimenta el grafo cross-sensor.
- `tcpdump -r` sobre ficheros sin extensión `.pcap` da `Permission denied` (probable AppArmor); leer los `.pcap` sin sudo.
- Script de instantáneas creado: **`/vagrant/scripts/d277_snap_blacklist.sh`** (CSV: `entry`, `set_size`, `ipt_rule`).

## 4. Predicciones (escritas antes de medir)

- **Neris (control):** pocas o ninguna IP en el set. Si se llena ⇒ falsos positivos ⇒ parar y analizar.
- **P1:** 192.168.100.50 entra en el set en los primeros segundos del replay CICDDoS.
- **P2 (hipótesis clave):** el sniffer (XDP) ve paquetes ANTES del DROP de netfilter ⇒ la IP bloqueada se
  sigue detectando ⇒ cada flush exitoso vacía la cola y la siguiente detección es un strike nuevo ⇒
  **`strikes` sube durante un único ataque continuo** hasta 6 (timeout ≈ 2073600) en segundos/minutos.
  Si se confirma: decisión de semántica pendiente (propuesta: reincidencia = volver DESPUÉS de cumplir la condena).
- **P3:** los paquetes de la regla `match-set ml_defender_blacklist_test` crecen durante el replay (DROP real).
- **P4:** nunca aparece `timeout 0`.
- **Grafo:** previsiblemente los bloqueos NO aparecen en el grafo (el firewall no lo alimenta) — sería hallazgo.

## 5. Guion (comandos)

### Fase 0 — build, tests, arranque
[Mac]
```bash
git grep -n -E '^FIREWALL_(CFG|BIN|BUILD_DIR)\s*[:?]?=' -- Makefile
```
(¿`FIREWALL_CFG` es el `firewall.json` del repo o una copia en `/etc/ml-defender/...`? Si es copia, comprobar
que lleva `max_penalty_after_strikes`/`max_penalty_sec`.)
```bash
make pipeline-build > /tmp/d278_build.txt 2>&1; tail -3 /tmp/d278_build.txt
```
```bash
make emecas > /tmp/d278_emecas.txt 2>&1; tail -15 /tmp/d278_emecas.txt
```
[defender]
```bash
wc -l < /vagrant/logs/lab/firewall-agent.log > /vagrant/logs/lab/d278_fwlog_offset.txt
```
[Mac]
```bash
make pipeline-start VERBOSE=1
```
```bash
make pipeline-status
```
[defender]
```bash
tail -n +$(( $(cat /vagrant/logs/lab/d278_fwlog_offset.txt) + 1 )) /vagrant/logs/lab/firewall-agent.log | grep -E 'Recidivism config|recidivism\.'
```
Esperado: EMECAS verde; todo RUNNING; una línea `Recidivism config aplicada (nunca permanente)` con
`max_penalty_sec=2073600 steps=5 max_penalty_after_strikes=6`; ningún ERROR `recidivism.*`.

### Fase 1 — punto de partida
[defender]
```bash
sudo ipset list ml_defender_blacklist_test -t
```
```bash
sudo iptables -L INPUT -n --line-numbers
```
```bash
sudo iptables -Z ML_DEFENDER_TEST; sudo iptables -L ML_DEFENDER_TEST -v -n -x
```
Esperado: 0 entradas; Header con `timeout 3600` y `comment`; `ML_DEFENDER_TEST` enganchada en INPUT y
SIN cadena de autonomía; regla `match-set ml_defender_blacklist_test` con contadores a 0.

### Fase 2 — Neris (control + grafo)
[defender, terminal aparte]
```bash
INTERVAL=5 /vagrant/scripts/d277_snap_blacklist.sh /vagrant/logs/lab/d278_snaps_neris.csv
```
[Mac]
```bash
make ctu-start > /tmp/d278_ctu.txt 2>&1; tail -20 /tmp/d278_ctu.txt
```
Ctrl-C en las instantáneas. [defender]
```bash
grep ',entry,' /vagrant/logs/lab/d278_snaps_neris.csv | cut -d, -f3 | sort -u > /tmp/d278_neris_ips.txt; wc -l < /tmp/d278_neris_ips.txt; head -20 /tmp/d278_neris_ips.txt
```
Limpieza:
```bash
sudo ipset flush ml_defender_blacklist_test; sudo iptables -Z ML_DEFENDER_TEST
```

### Fase 3 — flood CICDDoS2019
[defender, terminal aparte]
```bash
INTERVAL=5 /vagrant/scripts/d277_snap_blacklist.sh /vagrant/logs/lab/d278_snaps_cic1.csv
```
[client] (~500 s)
```bash
sudo tcpreplay --pps=100 --intf1=eth1 --stats=30 /vagrant/datasets/cicddos2019/_0125_50k_lab.pcap
```
Ctrl-C en las instantáneas. [defender]
```bash
grep ',entry,' /vagrant/logs/lab/d278_snaps_cic1.csv | awk -F, '{print $1, $3, $4, $5}' | uniq -f3 > /tmp/d278_cic1_timeline.txt; cat /tmp/d278_cic1_timeline.txt
```
```bash
grep 'match-set' /vagrant/logs/lab/d278_snaps_cic1.csv | tail -3
```
```bash
tail -n +$(( $(cat /vagrant/logs/lab/d278_fwlog_offset.txt) + 1 )) /vagrant/logs/lab/firewall-agent.log | grep -c -E 'castigo maximo|Batch flush failed'
```
Contrastar P1–P4.

### Fase 4 — reincidencia real (depende de P2)
- P2 confirmada ⇒ la IP ya está en el tope; decidir semántica de reincidencia antes de medir nada más.
- P2 refutada ⇒ esperar a que caduque la entrada, repetir fase 3 a `d278_snaps_cic2.csv`; la IP debe
  volver con el SIGUIENTE escalón (no 60 s; `quiet_period_reset` = 72 h no ha pasado).

### Fase 5 — grafo
Mirar cómo consulta Kuzu `scripts/ctu_start.sh`, y contar filas por sensor (aRGus / Suricata / Zeek en la
BD de red; Wazuh en su BD host propia). Comprobar si algún bloqueo aparece en el grafo (previsión: no).

## 6. Después del experimento
1. Patcher de H3 (volcado en parada + informe/`.eml` en arranque + backoff en caliente).
2. Si P2 se confirma: decidir y aplicar la semántica de reincidencia, con test.
3. Registrar formalmente en BACKLOG la deuda de la sección 2.
4. Con datos del experimento: medir eficacia de la cabeza DDoS para actualizar el paper (arXiv:2604.04952)
   con cifras honestas.