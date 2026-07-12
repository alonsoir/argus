# PROMPT DE CONTINUIDAD — DAY 216 → 217
## Rama `fix/verdict-multihead-honest` · **EL PLAN HA CAMBIADO**

> Memoria de sesión. Claude no recuerda entre ventanas. La fuente de verdad del PLAN
> sigue siendo el PLAN. Aquí sólo el estado operativo.

---

## ⚠️ AL ABRIR — LEE ESTO PRIMERO

**DAY 216 no cerró commit 2. Lo APARCÓ, y con razón.**

👉 **LEE `docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md` ANTES DE TOCAR NADA.**
Ese documento es el hallazgo de hoy. No está resumido aquí porque no cabe.

**En una frase:** el modelo L1 es perfecto sobre CIC-IDS2017 (200/200 DDoS, 0 FP), pero
el pipeline no detecta NADA (0/100 ataques sintéticos). La causa está PROBADA:
`ml-detector/src/feature_extractor.cpp` entrega 6 de 23 features rotas (duplicadas y una
constante a `0.0f`). **No hay tres cabezas rotas: hay un extractor que rompe tres cabezas.**

---

## 🔴 EL EXTRACTOR ES P0 ABSOLUTO

**Por delante de `correlation_v2`, del grafo y de MITRE.** Decisión Alonso DAY 216:
*"no tiene sentido trabajar aguas abajo si aguas arriba tenemos estos problemas"*.

**Commit 2 (noisy-OR) SE APARCA.** No se pierde — se retoma cuando las cabezas discriminen.
Combinar señales de cabezas sin señal es andamiaje sin edificio.

---

## 📦 ESTADO DEL ÁRBOL — NADA COMMITEADO HOY

```
Rama: fix/verdict-multihead-honest (up to date con origin)
Último commit: 8e03a264 (config P0, DAY 215)

MODIFICADO SIN COMMITEAR (el parche de instrumentación, 9 contadores):
  ml-detector/include/zmq_handler.hpp
  ml-detector/src/zmq_handler.cpp
  ⟹ SALVADO EN: docs/day216_instrumentation.patch  (7281 B)

STASH — NO LO PIERDAS:
  stash@{0}: On master: commit2-noisy-or WIP   ← header + tests de commit 2, VÁLIDOS
  stash@{1}: WIP on day204/emecas-plus-plus-target
  stash@{2}: WIP on main
  ⚠️ stash@{0} dice "On master" pero se creó desde otra rama. El pop funciona igual.

SIN TRACKEAR:
  docs/day216_instrumentation.patch   ← COMMITEAR ESTE FICHERO
  temporal/                            ← basura, revisar
```

**Decisión Alonso: el parche va a FICHERO, no a rama.** Evita choques en el merge.

---

## ▶️ PRIMER COMANDO DEL DÍA

```zsh
git -C ml-detector status --short          # confirmar hpp + cpp modificados
git -C ml-detector stash list              # confirmar stash@{0}
ls -la docs/day216_instrumentation.patch   # confirmar el parche (7281 B)
```

Y entonces, la pregunta que abre DAY 217:

```zsh
# ¿el protobuf TIENE los campos que faltan?
grep -n "init_win\|subflow\|act_data" ml-detector/proto/network_security.proto
```

- **Si los tiene** → el arreglo es local a `feature_extractor.cpp`.
- **Si NO los tiene** → hay que subir al **sniffer** (`sniffer/src/userspace/feature_extractor.cpp`),
  que según `rf_23_features.json:extraction_info` **sí produce las 83 features de
  CIC-IDS2017**. El dato puede existir y perderse en el camino al protobuf.

Ese `grep` decide el alcance de la reparación entera.

---

## 🔧 CÓMO REPRODUCIR LAS MEDICIONES DE HOY

**El pipeline requiere `etcd-server` ARRANCADO o el detector aborta** (`❌ [etcd] Failed
to initialize - REQUIRED for ml-detector`).

```zsh
make etcd-server-start
vagrant ssh -c 'sudo truncate -s 0 /vagrant/logs/lab/ml-detector.log'   # ¡SIEMPRE! (el log usa >>)
make ml-detector-start
vagrant ssh -c 'pgrep -af ml-detector'    # NO SIGAS SI SALE VACÍO

# BENIGN (ruido uniforme):
vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10"
# ATTACK (DDoS signature):
vagrant ssh -c "sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10 --attack"

sleep 65      # el volcado sale cada stats_interval (60s)
vagrant ssh -c 'grep -A 14 "DBG DEUDA-3" /vagrant/logs/lab/ml-detector.log | tail -15'
vagrant ssh -c 'grep "DBG-L1" /vagrant/logs/lab/ml-detector.log | awk "{print \$NF}" | sort | uniq -c | sort -rn | head'

vagrant ssh -c 'tmux kill-session -t ml-detector'   # MÁTALO al acabar
```

`make test-e2e-synthetic-full` sale ❌ si el firewall no corre — **da igual**: los
`fprintf` se escriben en `process_event`, mucho antes del firewall. El dato ya está.

---

## 🩸 TRAMPAS QUE COSTARON TIEMPO HOY (no repetirlas)

- **`grep --include='*.json'` SIN comillas simples** ⟹ zsh intenta expandir el glob, no
  encuentra, y **ABORTA EL COMANDO ENTERO**. Pasó 5 veces seguidas. Comillas SIEMPRE.
- **`fprintf` dentro del `while` sin `last_stats_report_ = now`** ⟹ **128 MB de log en
  minutos.** El volcado va DENTRO del `if (now - last_stats_report_ >= stats_interval)`
  Y hay que actualizar `last_stats_report_`. (Bug de Claude, cazado midiendo.)
- **`-Werror=format=`**: mezclar `%llu` y `%.2f` en un `fprintf` con los argumentos
  agrupados al final = desalineo. **Un `fprintf` por clase de formato.**
- **El detector NO es systemd**: vive en tmux (`make ml-detector-start`, Makefile :661).
  `journalctl -u ml-detector` sale vacío SIN error. Su stderr va a
  `/vagrant/logs/lab/ml-detector.log` (`2>&1` ya está en la receta, :662).
- **El binario está en `build-debug/`, no en `build/`.**
- **`Error 124` = timeout(1).** En `test-e2e-synthetic-full:1340` hay un
  `timeout 60 bash -c 'until grep -q "Injection complete" ...'` — si el detector no corre,
  el `until` espera a nadie.
- **Localizar por CONTENIDO, no por número de línea.** El parche desplazó todo.

---

## 📋 LO QUE HAY QUE COMMITEAR

- `docs/debt/DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001.md` ← el hallazgo
- `docs/day216_instrumentation.patch` ← la instrumentación (9 contadores)
- Anexo DAY 216 al **PLAN DE CAMPAÑA** (fuente de verdad — Alonso, no regenerar)
- `docs/BACKLOG.md`: alta de DEBT-FEATURE-EXTRACTOR-L1-BROKEN-001 (P0) y de
  DEBT-STATS-E2E-COUNTERS-001 (menor: `check_e2e_pipeline.py` reporta `received 0` con
  100 eventos procesados de verdad).

**Commits limpios: código y docs SEPARADOS.**

---

## 🎯 DECISIONES DE DISEÑO QUE SOBREVIVEN A HOY

- **Traffic = GUARD, no término del producto** (decisión Alonso DAY 216, opción (a)).
  Evita que traffic sea portero Y votante. Con una sola cabeza de sospecha (`internal`),
  el noisy-OR colapsa a `P = r·susp_prob` — una identidad. **Razón adicional para aparcar
  commit 2.**
- **`ddos`/`ransomware` entran a `reliability = 0.0`.** Factor neutro (`1 − 0·s = 1`).
  Honesto, no envenena. Reconectar = cambiar UN peso.
- **`l3_combined_seal` necesita clave propia** en config. Reutilizar `level3_internal` es
  el mismo número haciendo dos trabajos en escalas distintas.
- **La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.**
- **MITRE es imprescindible y va DESPUÉS del extractor.** Sin ataques etiquetados por
  técnica no hay forma de fundamentar `reliability`. Pero con las cabezas ciegas, MITRE
  tampoco mediría nada.

---

## FEDER
Go/no-go **~1 agosto 2026**. Deadline **22 septiembre 2026**.
Posición Alonso DAY 216: *"no pienso entregar nada que no esté bien fundamentado. El
pipeline tiene que funcionar bien."*