# DAY304 — Deprecar el subsistema RAG (lista de cierre con predicción)

Rama: `chore/deprecar-rag-security` (desde main `4feb3900`). Una rama, dos bloques de commits, UN solo EMECAS al final.
Historia de git intacta: solo commits nuevos que borran; nada se reescribe.

## Alcance

**Muere:** `rag/` (rag-security), `rag-ingester/`, `common-rag-ingester/`, submódulo `third_party/llama.cpp`
(solo lo usa rag), y todo lo que los nombra fuera de los históricos.

**Sobrevive (no se toca su lógica):**
- `plugin-loader/` y `plugins/`: usuarios vivos medidos = sniffer, ml-detector, firewall-acl-agent.
  `PLUGIN_MODE_READONLY` y TEST-INTEG-4b/4e/SIGN se quedan; solo se reescriben comentarios/textos que nombran rag.
- RAG Logger de ml-detector (`rag_logger.enabled=false` desde D285), `rag_logger_config.json`,
  `requires_rag_threshold`, `CTX_RAG_ARTIFACTS`: código vivo apagado por config → rama propia después.
- `/vagrant/logs/rag/...` (rutas del RAG Logger): fuera de alcance por lo mismo.

**Fuera, otra rama (DEBT-REPO-RESIDUOS-001):** `site/` (19 MB), `emecas++.md` / `emecas+++.md` (1,2 MB).

## Medidas de partida (DAY304, sobre main 4feb3900)

| Medida | Valor |
|---|---|
| Makefile, patrón K6 (5 términos) | 35 líneas (30 en main^1 + 5 añadidas por PR #145; delta explicado) |
| Makefile, rag-ingester | 41 líneas |
| Vagrantfile, rag | 6 (modelos `rag/models` 503-504, logs 542, alias 573-585) |
| `rag/` trackeado | 73 ficheros |
| Disco recuperable en el Mac | rag 617 MB + llama.cpp 350 MB + rag-ingester 34 MB + common 0,4 MB ≈ 1,0 GB |
| Trackeado de rag + rag-ingester + common | 1,0 MB |
| rag-ingester en arranque/estado | fuera desde DAY284 (`d284_patch_rag_ingester_off.py`) |
| `pipeline-status` hoy | 5 componentes: etcd-server, rag-security, ml-detector, sniffer, firewall |
| `check_e2e_pipeline.py` | no nombra rag |
| Hueco sin explicar | DAY303 midió 27 en el Makefile; main^1 da 30. No afecta al trabajo (se parte de main). |

## Bloque A — rag-security (commits pequeños, en este orden)

| Commit | Contenido |
|---|---|
| A1 Makefile | `.PHONY` 56/64; `RAG_BUILD_DIR` 155; targets rag-build/clean/start/stop/status/logs/attach (2376-2409); dependencia en `pipeline-build` (1006) y `build-unified` (1815); `rag-start` en pipeline-start (928, 943); `pipeline-stop` (958); `pipeline-status` (967); ctest (1293); logs (817); bucles de semillas (915, 2471, 2661, 2663, 2734: quitar solo rag-security); clean-host (1170-1172, 1197: quitar rag/build*); E2E 1416 (quitar rag-security, umbral `-lt 5` → `-lt 4`); TEST-INTEG-4e (529: solo texto); mensajes 6/6 obsoletos (274, 307, 1454) → 4/4 |
| A2 Vagrantfile + llama.cpp | quitar descarga de modelos, logs y alias de rag; `git submodule deinit` + `git rm third_party/llama.cpp` + `.gitmodules`; `.gitignore` (llama y rag/*); README (Install: llama.cpp/TinyLlama) |
| A3 systemd/etcd-server | `git rm etcd-server/config/ml-defender-rag-security.service`; `install-systemd-units.sh`; `set-build-profile.sh` (`/vagrant/rag`); `After=` de rag-security en `ml-defender-rag-ingester.service` (el fichero muere en B, pero A debe quedar coherente) |
| A4 Hardening | `security/apparmor/argus.rag-security` y `tools/apparmor/ml-defender-rag-security` (git rm); `tools/apparmor-promote.sh`; reglas `deny` de rag-security en `argus.etcd-server` (55) y `argus.sniffer` (82, 86); hardened-x86/arm64 `setup-apparmor`, `setup-falco`, `setup-filesystem`; `tools/prod/build-x86.sh`, `check-permissions.sh`, `deploy-hardened.sh`; `tools/provision.sh` |
| A5 Scripts | `scripts/pipeline_health.sh`; `scripts/emecas/emecas_frescura.sh`; `git rm scripts/verify_rag_ecosystem.sh verify_rag_etcd_accurate.sh verify_rag_etcd_fixed.sh`; `scripts/apply_hardening_flags.sh`; `scripts/monitor_lab.sh` (113); comentario en `scripts/parquet/schemas/firewall.py` (7) |
| A6 Tests y CI | cadena "rag-security" en `common/tests/test_crypto_autonomy.cpp:119` y `libs/seed-client/tests/test_seed_client.cpp:187` (sustituir por componente vivo); comentarios/textos de `plugins/test-message/test_integ_4e.cpp` (4, 24) sin tocar lógica; `.github/workflows/ci.yml:108` |
| A7 Código y docs vivos | `git rm -r rag/`; `.gitignore` 90-96 y 216; README (3); CLAUDE.md (38, 50, 247) |

## Bloque B — rag-ingester y common-rag-ingester

| Commit | Contenido |
|---|---|
| B1 Makefile | las 41 líneas: `.PHONY` 29/63; config dir 45; `RAG_INGESTER_*` 136/149/156; ayuda 188; TEST-INTEG-4b 523 (solo texto); `rag-ingester-start` 724-730; target build 733-746 y `rag-ingester-build` 1066; `rag-ingester-clean` 1125 y `clean-components` 1156; `build-active` 873; logs 817; semillas 915, 2471, 2661, 2663, 2734; `pipeline-stop` 958; `pipeline-build` 1006, `build-unified` 1815; clean-host 1170-1172, 1184, 1191; `ldd` 1770-1771; TSAN day48 2258-2338 |
| B2 systemd/hardening | `git rm etcd-server/config/ml-defender-rag-ingester.service`; `install-systemd-units.sh`; `set-build-profile.sh` (`/vagrant/rag-ingester`); `security/apparmor/argus.rag-ingester` y `tools/apparmor/ml-defender-rag-ingester` (git rm); `tools/apparmor-promote.sh`; menciones en `argus.etcd-server` y `argus.sniffer`; hardened-x86/arm64 (apparmor, falco, filesystem); `tools/prod/*`; `tools/provision.sh` |
| B3 Scripts | `scripts/pipeline_health.sh`; `scripts/emecas/emecas_frescura.sh`; `scripts/tsan-integration-test.sh`; `scripts/analyze-tsan-reports.py` |
| B4 Referencias en componentes vivos (MEDIR antes, ver Bloque 0) | `crypto-transport/include/crypto_transport/contexts.hpp`; `etcd-server/include/etcd_server/secrets_manager.hpp` y tests `test_hmac_integration.cpp`, `test_secrets_manager_grace_period.cpp`; `etcd-client/tests/test_hmac_integration_client.cpp`; `etcd-server/config/etcd-server.json` (`/secrets/rag/log_hmac_key`); `etcd-server/config/ml-defender-ml-detector.service`; comentarios en `plugin-loader/include/plugin_loader/plugin_api.h` (65, 71), `plugins/test-message/test_integ_4b.cpp`, `ml-detector/include/csv_event_writer.hpp`, `correlation-engine/include/correlation_engine/bronze_dir_watcher.hpp`; `contrib/safe-path/tests/test_safe_path.cpp`; `tools/generate_synthetic_events.cpp`; `common/tests/test_crypto_autonomy.cpp`; `libs/seed-client/tests/test_seed_client.cpp`; `contrib/audit/audit.mk` |
| B5 Código | `git rm -r rag-ingester/ common-rag-ingester/` (incluye `common-rag-ingester/build` versionado); `git rm -r contrib/*/pca_pipeline/` (decisión 1); `.gitignore`; CLAUDE.md (248); `ml-detector/docs/feature_schema.md` |

## Bloque 0 — medidas pendientes antes de B4 (predicción escrita)

1. `contexts.hpp`: contiene un contexto HKDF por componente; el de rag-ingester se puede quitar sin
   afectar al de ml-detector (`CTX_RAG_ARTIFACTS` se queda: lo usa el RAG Logger).
2. `secrets_manager.hpp` y `etcd-server.json`: `/secrets/rag/log_hmac_key` no lo lee ningún componente
   vivo; los tests de etcd-server/etcd-client lo usan como ruta de ejemplo → se cambian a
   `/secrets/ml-detector/log_hmac_key` y la entrada rag sale de `etcd-server.json`.
3. `ml-defender-ml-detector.service`: nombra rag-ingester en `After=`/`Wants=` → se quita.
4. `test_safe_path.cpp` y `generate_synthetic_events.cpp`: rutas de ejemplo → se adaptan.

## Decisiones de Alonso (DAY304)

1. `contrib/*/pca_pipeline/` (ds, gemini, glm, qwen; Día 35-36): **se borran en B5**. Dependen de
   `common-rag-ingester`; sin él no compilan. La historia de git los conserva.
2. Scripts de parche históricos: **se quedan y se excluyen del criterio de HECHO**
   (`scripts/d284_patch_rag_ingester_off.py`, `scripts/higiene-adr-day198.sh`,
   `tools/update-day158-docs.sh`, `tools/update_day156.py`).
3. `DEBT-COMPILER-WARNINGS-CLEANUP-001.md`, `contract-validation/day48/`, `tsan-reports/day48/`:
   **históricos; se quedan y se excluyen**.

## Criterio de HECHO

1. `git grep` vacío (patrón y exclusiones cerrados):
   ```
   git grep -n -E 'rag-security|rag_security|rag-ingester|rag_ingester|rag-start|rag-build|RAG_BUILD_DIR|RAG_INGESTER|/vagrant/rag/|(^|[^-_a-zA-Z/])rag/|third_party/llama|libllama' -- . \
     ':!docs' ':!site' ':!emecas*.md' ':!scripts/timebase' ':!tsan-reports' \
     ':!contract-validation/day48' ':!DEBT-COMPILER-WARNINGS-CLEANUP-001.md' \
     ':!scripts/d284_patch_rag_ingester_off.py' ':!scripts/higiene-adr-day198.sh' \
     ':!tools/update-day158-docs.sh' ':!tools/update_day156.py'
   ```
2. Una sola ejecución EMECAS+++ `PROFILE=production` desde cero, rc=0, con:
   - `pipeline-status` 4/4 (etcd-server, ml-detector, sniffer, firewall);
   - TEST-INTEG-4b, TEST-INTEG-4e y TEST-INTEG-SIGN PASSED (plugin-loader intacto);
   - E2E de restauración del lab (antigua 1416) PASA con umbral 4;
   - `clean-host-builds` PASA; `emecas_frescura` sin rag.
3. Limitación declarada: los cambios en `vagrant/hardened-*` y `tools/prod/` no los ejecuta EMECAS;
   se verifican con `bash -n` y el `git grep`.

## Predicciones del EMECAS final

- Verde a la primera: sí.
- Duración: menor que DAY303 (2h33m) al no compilar rag-security, llama.cpp ni rag-ingester; predicción ≈ 2h10m (±15 min).
- Hitos: cambia el número (salen los de rag); se compara hito a hito con `emecas_20261021_084020.log`.

## Después de esta rama

- DEBT-PIPELINE-STATUS-LIVENESS-001 (estado por registro/heartbeat, no solo proceso).
- Rama RAG Logger de ml-detector (+ `rag_logger_config.json`, `CTX_RAG_ARTIFACTS`, `/vagrant/logs/rag`).
- DEBT-REPO-RESIDUOS-001 (`site/`, `emecas*.md`).
