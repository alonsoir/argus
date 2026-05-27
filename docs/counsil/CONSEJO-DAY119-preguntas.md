cat > /tmp/consejo_day119.md << 'MDEOF'
# Consejo de Sabios — DAY 119 — Preguntas y Síntesis

**Fecha:** 2026-04-16
**Rama:** feature/adr026-xgboost
**Commit cierre:** 6055c54d
**Estado:** make test-all VERDE · 6/6 RUNNING

---

## Resumen ejecutivo DAY 119

DAY 119 fue una sesión de consolidación de infraestructura. El objetivo era
verificar que el Vagrantfile reproducía el entorno desde cero (vagrant destroy).
Resultado: el Vagrantfile estaba desactualizado en múltiples puntos críticos.
Se han corregido todos y se ha establecido la secuencia canónica de construcción.

### Problemas encontrados y resueltos

| # | Problema | Causa raíz | Fix |
|---|----------|------------|-----|
| 1 | pip timeout descargando xgboost (131 MB) | Sin --timeout + sin fallback | `--timeout=300` + fallback apt + `find_lib_path()` robusto |
| 2 | libsodium 1.0.18 (bookworm) vs 1.0.19 requerida | No estaba en Vagrantfile | Bloque build-from-source antes de ONNX |
| 3 | tmux ausente → pipeline no arranca | No estaba en paquetes base | Añadido a línea 206 Vagrantfile |
| 4 | xxd ausente | No estaba en paquetes base | Añadido a línea 206 Vagrantfile |
| 5 | pipeline-build sin dependencias de libs | Makefile incompleto | `crypto-transport-build + etcd-client-build + plugin-loader-build` explícitos |
| 6 | plugin_xgboost con firmas API incorrectas | Skeleton DAY 118 usaba API antigua | Reescrito con `PluginResult plugin_init(const PluginConfig*)` etc. |
| 7 | /usr/lib/ml-defender/plugins/ no creado | No estaba en Vagrantfile | Bloque mkdir + build + deploy ambos plugins |
| 8 | plugin_test_message no desplegado | No estaba en Vagrantfile ni Makefile | Bloque Vagrantfile + target Makefile |
| 9 | TEST-INTEG-SIGN falla tras vagrant destroy | pubkey hardcodeada != keypair regenerado | `make sync-pubkey` — target robusto que lee pubkey activa y recompila |
| 10 | install-systemd-units y set-build-profile sin target Makefile | Scripts directos, no en Makefile | Targets añadidos |

### Secuencia canónica post `vagrant destroy + up` (nueva — DAY 119)
make up                    # vagrant up defender + client
make sync-pubkey           # lee pubkey activa → CMakeLists.txt → recompila plugin-loader
make set-build-profile     # activa symlinks build-active (PROFILE=debug por defecto)
make install-systemd-units # instala 6 units en /etc/systemd/system/
make sign-plugins          # firma Ed25519 todos los plugins (ADR-025)
make test-provision-1      # CI gate PHASE 3 — 8/8 checks
make pipeline-start        # arranca 6 componentes via tmux
make pipeline-status       # verificar 6/6 RUNNING
make plugin-integ-test     # verificar 6/6 PASSED incluyendo TEST-INTEG-SIGN
### Deuda nueva registrada

- **DEBT-XGBOOST-APT-001** — verificar versión apt python3-xgboost en bookworm (no bloqueante)

### Lección operacional crítica DAY 119

> El Vagrantfile y el Makefile son la única fuente de verdad.
> Compilar o instalar manualmente en la VM sin actualizar estas fuentes
> garantiza que el próximo `vagrant destroy` romperá el entorno.
> Cada dependencia instalada a mano = deuda técnica de infraestructura.

---

## Preguntas al Consejo

### Q1 — Robustez de sync-pubkey

El target `make sync-pubkey` lee la pubkey activa desde la VM y actualiza
`plugin-loader/CMakeLists.txt` en macOS antes de recompilar. ¿Veis algún
vector de fallo en este mecanismo? ¿Debería también actualizar el Continuity
Prompt automáticamente o dejamos eso como proceso manual?

### Q2 — Vagrantfile como fuente de verdad vs Makefile

El Vagrantfile provisiona dependencias del sistema (libsodium, XGBoost, plugins).
El Makefile gestiona el build de componentes propios. ¿Estáis de acuerdo con
esta separación de responsabilidades, o hay casos donde una dependencia debería
estar en ambos?

### Q3 — Secuencia de reconstrucción desde cero

La secuencia canónica DAY 119 tiene 9 pasos entre `make up` y `make plugin-integ-test`.
¿Debería existir un target `make bootstrap` que encadene toda la secuencia
para el caso "primer clone"? ¿Qué riesgos veis en automatizarlo completamente?

### Q4 — plugin_xgboost Fase 2 (feature extraction)

El skeleton está compilando y firmado. El TODO pendiente es extraer features
del `MessageContext` en `plugin_process_message`. La Opción B (unanimidad DAY 118)
dice que ml-detector pre-procesa `float32[]` antes de invocar el plugin.
¿Cuál es el contrato mínimo que debe cumplir `ctx->payload` para que el plugin
pueda construir el `DMatrix` de XGBoost sin asumir nada del llamador?

### Q5 — Reproducibilidad tras vagrant destroy

Mañana (DAY 120) repetiremos `vagrant destroy + vagrant up` desde cero para
validar que la secuencia es completamente reproducible. ¿Hay algún punto ciego
que el Consejo anticipe que puede fallar todavía?

---

## Pubkey activa DAY 119
`9ac7b8c5ce2d970f77a5fcfcc3b8463b66082db50636a9e81da3cdbb7b2b8019`

## Seed activo DAY 119
`75deaca96768b5d973a4339faf2325c058969bf93c00c0d21eef703a2ab91360`
INVARIANTE-SEED-001: todos los seed.bin DEBEN ser idénticos.

---

*"Via Appia Quality — un escudo, nunca una espada."*
MDEOF