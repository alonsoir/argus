# Prompt de continuidad DAY305 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY298-DAY304) para crear el contexto. Base en el repo:
`docs/ml-heads/prompt_day305.md` (este), `docs/ml-heads/day304_deprecar_subsistema_rag.md` (lista de cierre v4),
`docs/BACKLOG.md` (sección "Cierre DAY304").

## Estado al cerrar DAY304 (22-oct-2026)

- PR #146 `chore/deprecar-rag-security` fusionada en main: merge `772ff15e`. Rama borrada (local y remota).
  239 ficheros, +286 / −27 380 líneas. Historia de git intacta (solo commits nuevos, sin `--amend`).
- Retirado el subsistema RAG entero: rag-security (`rag/`, submódulo llama.cpp + `.git/modules`, TinyLlama),
  rag-ingester, common-rag-ingester, `ml-training/scripts/rag_shield/`, `contrib/*/pca_pipeline/` (7 IAs),
  `shared/indices/`, `tools/legacy/test_reducer.cpp`. En `vagrant up` ya no se compilan llama.cpp ni FAISS
  (+BLAS/LAPACK) ni corre la provisión SQLite del día 40.
- Sobrevive intacto: plugin-loader y plugins (READONLY), ONNX Runtime, XGBoost, RAG Logger de ml-detector (apagado).
- El pipeline son 4 componentes: etcd-server, ml-detector, sniffer, firewall-acl-agent. Gates ajustados:
  test-provision-1 CHECK 5 (4 units), post-up-verify (4 `seed.bin`), LAB-E2E (umbral 4), pipeline-status 4/4.
- Certificado: EMECAS+++ `PROFILE=production` desde cero, 28/28 hitos, rc=0, **2h16m**
  (`logs/lab/emecas/emecas_20261022_101530.log`). La 1.ª corrida (`emecas_20261022_093547.log`) cayó a los 28 min
  en `post-up-verify` (`grep -q '^6$$'` de seeds) → commit B6 `2b0e45ee`.
- Disco recuperado en el Mac ≈ 1,4 GB.
- VMs encendidas tras el EMECAS: defender, client, suricata (zeek y wazuh `not created`). Apagar con
  `vagrant halt` si no se usan. Al levantar: `make up` (5 VMs) o las 3 de EMECAS; luego `make lab-clock-step`.

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR. Comandos exactos y
completos, en orden, diciendo dónde se ejecuta cada uno (Mac / defender / client), y con la salida redirigida a
fichero + `; cat`. Ficheros generados como descarga con sha256. Nada de `printf >>` sobre ficheros del repo:
parcheadores que validen TODO antes de escribir NADA (línea + contenido exacto, cuentas exactas, abortar si no
cuadra). `git grep`, nunca `grep -rn .` en la raíz. awk con `LC_ALL=C`. El JSON es la ley. Compilar siempre en
producción y el pipeline completo. EMECAS con
`nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &`
y vigilado con `bash scripts/emecas/emecas_watch.sh 60` (logs en `logs/lab/emecas/`). Ramas pequeñas; EMECAS cuando
el Mac no se usa. No se mantiene código deprecado "para recordarlo": se borra.

## Lecciones de DAY304 que aplican ya

- **Medir quién CUENTA, no solo quién nombra.** Al quitar un componente, buscar además los gates con cuentas fijas:
  `^N$`, `grep -q "N"`, `-lt N`, textos "esperados N", "N/N". Dos casi tumban el EMECAS (CHECK 5 y post-up-verify).
- **Antes de relanzar un EMECAS, medir el target que falló contra la VM viva** (un minuto en vez de dos horas).
- **Buscar también la palabra suelta** (`rag`, `RAG`), no solo patrones con barra o guion: así salieron la sección RAG
  de monitor_lab.sh y "RAG Security System" en la cabecera del Vagrantfile.
- **Al quitar líneas del `.gitignore`, mirar lo que aparece como `??`** antes del commit (rag_shield, shared/indices).
- **`$?` tras una tubería es el del último programa** (`| cut` siempre 0). Sin tubería cuando importa el rc.
- **Exclusiones de git con comodín necesitan `/*`** (`contrib/*/pca_pipeline/*`).
- **Inventarios con glob medido, no con lista de memoria** (salió una 7.ª IA, `chatgpt5`).
- Puntos ciegos de patrones de ruta: `${vagrant_root}/rag/config` no casa con `/vagrant/rag/` ni con `[^/]rag/`.

## Orden decidido por Alonso

1. **Interruptor de cabezas** (DEBT-HEADS-SWITCH-001; decisiones DAY300 en el BACKLOG): encender/apagar cada
   cabeza desde configuración (etcd), en caliente, con el estado en el log.
2. **Caducidad de flujos** (DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001): la memoria está
   acotada (16 × 10 000, LRU); lo roto son los rasgos de los flujos largos. Medir primero RAM por flujo con la
   tabla llena y la batería de la etapa 2 antes/después. Predicción: no hará falta reentrenar.
3. **Rama RAG Logger de ml-detector** (DEBT-RAG-LOGGER-BRANCH-001): decidir su futuro (retirar o mantener) con
   todo lo que cuelga de él (lista en el BACKLOG).
4. **Residuos del repo** (DEBT-REPO-RESIDUOS-001, ampliada DAY304).
5. **REA, al final**: auditoría manual del sniffer con predicción escrita; luego fase asíncrona en Jenkins.
   Revisar antes la licencia de REA.

## Deudas abiertas que conviene tener a mano

DEBT-PIPELINE-STATUS-LIVENESS-001 (sigue: estado por registro/heartbeat), DEBT-MAKE-PREFLIGHT-001 (ampliada:
cuentas fijas), DEBT-VAGRANT-EARLY-FW-BUILD-001 (CMake Error de crypto_transport en cada `vagrant up`, ruido),
DEBT-SECRET-IN-HISTORY-001 (`rag-ingester/config/etcd_encryption.key` en la historia; sin copia viva),
DEBT-APPARMOR-FIREWALL-BIN-NAME-001, DEBT-FW-LEGACY-LINK-DIR-001, DEBT-BUILD-INCREMENTAL-001,
DEBT-EMECAS-SENSOR-VMS-001, DEBT-LAB-ESTABLE-LECTOR-001 (mitigada), DEBT-SYNTH-E2E-FAIL-FAST-001,
DEBT-VAULT-COMMON-BUILD-001, DEBT-PROVISION-LIBS-PROFILE-001, DEBT-SANITIZERS-PREPROD-001,
DEBT-GIT-BUILD-ARTIFACTS-001 (queda plugin-loader/build-enterprise).
