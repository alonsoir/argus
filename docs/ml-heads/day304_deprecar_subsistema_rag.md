# DAY304 — Deprecar el subsistema RAG (lista de cierre con predicción)

Rama: `chore/deprecar-rag-security` (desde main `4feb3900`). Una rama, dos bloques de commits, UN solo EMECAS al final.
Historia de git intacta: solo commits nuevos que borran; nada se reescribe (ni `--amend`).

v3 (antes del EMECAS): las 15 piezas hechas, lo medido, cada predicción fallada y lo que queda para otras ramas.

## Alcance (sin cambios respecto a v1)

**Muere:** `rag/` (rag-security), `rag-ingester/`, `common-rag-ingester/`, submódulo `third_party/llama.cpp`,
`ml-training/scripts/rag_shield/`, `contrib/*/pca_pipeline/` (7 IAs), `shared/indices/`, `tools/legacy/test_reducer.cpp`,
y todo lo que los nombra fuera de los históricos. En el `vagrant up`: llama.cpp, TinyLlama, FAISS (+BLAS/LAPACK) y la
provisión SQLite del día 40.

**Sobrevive (lógica intacta):** `plugin-loader/` y `plugins/` (usuarios vivos: sniffer, ml-detector, firewall-acl-agent;
`PLUGIN_MODE_READONLY`, TEST-INTEG-4b/4e/SIGN), ONNX Runtime (ml-detector), XGBoost.

**Fuera, rama RAG Logger de ml-detector:** RAG Logger (`rag_logger.enabled=false`), `rag_logger_config.json`,
`CTX_RAG_ARTIFACTS`, `/vagrant/logs/rag`, clave HMAC `/secrets/rag/log_hmac_key` (`etcd-server.json` + su test de
etcd-client), `scripts/explore_rag_logs.sh` (habla de "FAISS readiness"), `day15_automated_test.sh`, `test_rag_logger.sh`,
`tsan/run_tsan_test.sh`, `.PHONY` muertos `rag-log-*`/`test-rag-*` del Makefile (líneas 21-23, 27).

**Fuera, DEBT-REPO-RESIDUOS-001:** `site/`, `emecas*.md`, `.md` de cierre sueltos en la raíz (`Cierre day255 …`),
`scripts/test_rag_logger.sh.backup` trackeado, `.gitignore` con líneas pegadas (`logs/# ONNX models…`) y una línea
`rm --cached ml-detector/build-asan/ml-detector` usada como patrón.

## Decisiones de Alonso (DAY304)

1. `contrib/*/pca_pipeline/`: se borran (dependían de `common-rag-ingester`).
2. Scripts de parche históricos: se quedan, excluidos del criterio.
3. `DEBT-COMPILER-WARNINGS-CLEANUP-001.md`, `contract-validation/day48/`, `tsan-reports/day48/`: históricos, excluidos.
4. `.git/modules/third_party`: se borra (no es historia de aRGus).
5. `ml-training/scripts/rag_shield/` (lista blanca de comandos RAG): se borra. "Mantener código deprecado para
   recordarlo es absurdo."

## Commits (15, sobre `4feb3900`)

| Commit | Hash | Contenido |
|---|---|---|
| A0 | `0a3f9028` | esta lista (v1) |
| A1 | `45aa5244` | Makefile sin rag-security: pipeline 4/4, E2E umbral 4 (3429 → 3379 líneas) |
| A2 | `a2d0f79a` | fuera llama.cpp (submódulo, build en `vagrant up`, TinyLlama), alias, `.gitignore`, README |
| A3 | `d268d55d` | systemd y `set-build-profile` sin rag-security |
| A4 | `995d5c6a` | AppArmor, Falco, filesystem x86/arm64, `tools/prod`, `provision.sh` |
| A5 | `a8553729` | scripts (frescura EMECAS, `pipeline_health`, `apply_hardening_flags`…); fuera `verify_rag_*` |
| A5b | `2995826d` | `monitor_lab.sh` sin la sección RAG (A5 dejó una llamada huérfana) |
| A6 | `c7cc8544` | tests y CI (lógica de TEST-INTEG-4e intacta) |
| A7 | `14c5a3f9` | `git rm -r rag/` y `rag_shield/`; CLAUDE.md; comentario de ml-detector |
| B1 | `9867a6a4` | Makefile sin rag-ingester (3378 → 3313); **test-provision-1 CHECK 5: 6 → 4 units** |
| B2 | `d3f3e73b` | systemd, hardening, `tools/prod`, `provision.sh`; resto `${vagrant_root}/rag/config` |
| B2v | `740fb7c1` | Vagrantfile sin FAISS/BLAS/LAPACK ni SQLite; fuera "RAG Security System" de la cabecera |
| B3 | `aca8b17b` | scripts sin rag-ingester; fuera `verify_libraries.sh`, `install_faiss_*.sh` |
| B4 | `be08df34` | componentes vivos: solo comentarios, textos y nombre de ejemplo en tests (`log-consumer`); CI |
| B5 | `ded541eb` | `git rm` de rag-ingester, common-rag-ingester, `shared/indices`, 7 `pca_pipeline`, `test_reducer` |

## Criterio de HECHO

1. **`git grep` vacío — CUMPLIDO** (`rc=1`, DAY304 09:26), patrón ampliado (sin distinguir mayúsculas):
   ```
   git grep -c -i -E 'rag-security|rag_security|rag-start|rag-build|RAG_BUILD_DIR|/vagrant/rag/|(^|[^-_a-zA-Z/])rag/|[}"]/rag/|third_party/llama|libllama|rag-ingester|rag_ingester|RAG_INGESTER|common-rag-ingester|pca_pipeline|faiss|shared/indices|CsvEventLoader' -- . \
     ':!docs' ':!site' ':!emecas*.md' ':!scripts/timebase' ':!tsan-reports' ':!contract-validation/day48' \
     ':!DEBT-COMPILER-WARNINGS-CLEANUP-001.md' ':!scripts/d284_patch_rag_ingester_off.py' ':!scripts/higiene-adr-day198.sh' \
     ':!tools/update-day158-docs.sh' ':!tools/update_day156.py' ':!scripts/explore_rag_logs.sh' ':!Cierre day255 reparacion ddos.md'
   ```
2. **Un solo EMECAS+++ `production` desde cero, rc=0**, con:
   - `test-provision-1` PASA (CHECK 4 sin rag-ingester; CHECK 5 cuenta 4 units);
   - `pipeline-status` 4/4 (etcd-server, ml-detector, sniffer, firewall);
   - TEST-INTEG-4b, 4e y SIGN PASSED (plugin-loader intacto);
   - ctest de etcd-server con `test_hmac_integration` PASA (cadena `log-consumer`);
   - E2E de restauración del lab PASA con umbral 4; `clean-host-builds` PASA;
   - `emecas_frescura` PASA sin rag ni rag-ingester.
3. **Limitación declarada:** `vagrant/hardened-*` y `tools/prod/` no los ejecuta EMECAS: verificados con `bash -n` y grep.

## Predicciones del EMECAS (escritas antes de lanzarlo)

- Verde a la primera: sí.
- Duración: se mantiene la predicción de v1, ≈ 2h10m (±15 min), comparada con DAY303 (2h33m). Ya no se compilan
  llama.cpp ni FAISS en el `vagrant up`, ni rag-security ni rag-ingester en el build: espero quedar por debajo,
  pero no corrijo la cifra escrita.
- Hitos: menos que en DAY303 (salen los de rag); se comparan uno a uno con `emecas_20261021_084020.log`.

## Medidas de partida y resultados

| Medida | Valor |
|---|---|
| Makefile, patrón rag-security | 35 → 0 (A1); 30 en main^1 + 5 de PR #145 |
| Makefile, rag-ingester/SQLite/`shared/indices` | 61 → 0 (B1) (la v1 decía 41: era otro patrón) |
| Ficheros trackeados borrados | 81 (A7) + 94 (B5) + sueltos (unidades, perfiles, scripts, instaladores) |
| Disco recuperado en el Mac | rag 616 MB + llama.cpp 350 MB + `.git/modules` 205 MB + rag-ingester 33 MB + `contrib/claude` 75 MB + `shared` 135 MB + rag_shield 4,5 MB ≈ 1,4 GB |

## Predicciones que fallaron hoy (y qué se aprendió)

| # | Predicción | Medido | Lección |
|---|---|---|---|
| 1 | `contexts.hpp` tiene contexto HKDF de rag-ingester | solo un comentario | — |
| 2 | Los tests HMAC usan config en memoria | test de integración contra etcd-server real → clave fuera de alcance | — |
| 3 | Vagrantfile: 6 líneas de rag | 13 (compilación de llama.cpp en `vagrant up`) | — |
| 4 | Grep de llama limpio | "llama" casa con "llamada" | buscar `llama\.cpp|libllama|tinyllama` |
| 5 | Informe de `provision.sh` solo con mis líneas | 2 cuentas más ("6 componentes") | — |
| 6 | Inventario A5 completo | `rag/CMakeLists.txt` suelto, sin barra delante | usar el patrón del criterio, no uno parcial |
| 7 | Informe de `monitor_lab` vacío | sección RAG entera; llamada huérfana (A5b) | buscar también la palabra suelta `rag` |
| 8 | Restos sin trackear de `rag_shield` vacíos | 4,5 MB, que el `.gitignore` excluía | al quitar líneas del `.gitignore`, mirar lo que aparece |
| 9 | Exclusión `contrib/*/pca_pipeline` | git exige `contrib/*/pca_pipeline/*` | — |
| 10 | (A3) cambiar el instalador de systemd basta | **CHECK 5 de test-provision-1 contaba 6 units**: el EMECAS habría caído | **medir quién CUENTA, no solo quién nombra** |
| 11 | SQLite lo usa algo vivo | solo rag-ingester | — |
| 12 | (A4) patrón de HECHO cubre todo | punto ciego `${vagrant_root}/rag/config` | pasada extra `[}"]/rag/` |
| 13 | Textos de cuenta de systemd/AppArmor | 3 más con "6" (A3/A4) | — |
| 14 | `explore_rag_logs.sh` nombra rag-ingester | habla de FAISS; es del RAG Logger | — |
| 15 | `rag-security/` en la raíz no existe | `config/` vacío creado por `provision.sh` (ruta inexistente + `mkdir -p`) | — |
| 16 | 6 IAs en `contrib` | 7 (`chatgpt5`) | medir con glob, no con lista de memoria |
| 17 | `shared/` sin trackear | 2 `.faiss` trackeados, 135 MB | — |
| 18 | `rc` del criterio con `| cut` | `$?` era el de `cut` | sin tubería cuando importa el `rc` |
| 19 | 17 commits en la rama | 15 (error aritmético mío) | — |

Hueco sin explicar: DAY303 midió 27 líneas en el Makefile y main^1 da 30 (no afecta: se parte de main).

## Hallazgo de seguridad

`rag-ingester/config/etcd_encryption.key` estaba trackeado. B5 lo borra del árbol, pero **sigue en la historia de git**
(no se reescribe). Si esa clave, o una derivada, la usa algún componente vivo o algún entorno, hay que rotarla.
Comprobación pendiente: que ningún JSON/fichero vivo tenga el mismo contenido.

## Después de esta rama

- DEBT-PIPELINE-STATUS-LIVENESS-001 (estado por registro/heartbeat, no solo proceso).
- Rama RAG Logger de ml-detector (lista de "Fuera, rama RAG Logger" arriba).
- DEBT-REPO-RESIDUOS-001 (lista de arriba).
