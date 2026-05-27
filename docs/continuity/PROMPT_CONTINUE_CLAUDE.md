# PROMPT DE CONTINUIDAD — DAY 167
## aRGus NDR | 2026-05-27

---

## Estado al entrar en DAY 167

### Rama activa
`main` — merge enterprise completado DAY 166

### EMECAS++ completo — todos los actos verdes
- test-all: ✅ (6 suites, 0 fallos)
- test-e2e-synthetic-full: ✅ delta=100/100
- test-e2e-synthetic-firewall: ✅ 546 eventos, 0 crypto_errors
- **Acto I (arranque nominal con Vault):** ✅ fingerprint estable, crypto_errors==0
- **Acto II (rotación controlada bajo tráfico):** ✅ epoch_id antes/después distintos, 0 drops
- **Acto III (vault-fault-inject token revocation):** ✅ cache RCU activa, zero downtime
- **Keypair efímero activo:** `c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90`

### Crypto lifecycle — todas las fases verdes
| Fase | Estado |
|------|--------|
| FASE 0 — vendor.key → Vault (Modelo B) | ✅ |
| FASE 1 — CryptoProviderHandle RCU | ✅ |
| FASE 2a — HttpEtcdRegistrar real | ✅ |
| FASE 2b — CryptoEpochCoordinator | ✅ |
| FASE 3 — Wire header epoch_id (13/13) | ✅ |
| FASE 4 — test-e2e-rotation (live Actos II+III) | ✅ |
| **EMECAS++ Enterprise (3 actos)** | ✅ CERRADO DAY 166 |

### Consejo de Sabios DAY 166 — contexto
- B1 (VaultProvider retry/cache) era gratis — caché inline preexistente confirmada por grep
- Acto III no requirió código nuevo: `get_material()` ya tenía `cached_material_.has_value()`
- `DEBT-VAULT-RECONNECT-001` cerrada sin escribir una línea de C++
- Próximo foco del Consejo: ADR-048 Fase F2 (NTP + community_id + Suricata)

---

## Deudas abiertas — ordenadas por prioridad

### P0 — ADR-048 Fase F2 prerequisitos (bloqueantes para datasets UEx)
| ID | Descripción | Estimación |
|----|-------------|-----------|
| DEBT-ARGUSPP-NTP-001 | NTP+chrony en todos los nodos. Health-check rechaza arranque si offset >1s. Gate P0 del correlation-engine. | 1 sesión |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | Habilitar community_id en Suricata y Zeek desde configuración inicial. Primary key del join cross-tool. | 1 sesión |

### P1 — Post-merge CI/CD
| ID | Descripción | Estimación |
|----|-------------|-----------|
| BACKLOG-CI-ENTERPRISE-001 | Jenkins gate `make emecas++` en Jenkinsfile.dev. `agent any`. Stage Enterprise después de Unit Tests. | 1 sesión |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS. eve.json → rag-security → servidor. AppArmor obligatorio. | 2 sesiones |

### P2 — ADR-048 correlación
| ID | Descripción |
|----|-------------|
| DEBT-ARGUSPP-CORRELATION-001 | Correlation-engine v1.0 C++20. CrisisWindow disparador. Esquema Arrow con columnas opcionales 4 fuentes. |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek. conn/dns/ssl/files.log → servidor. community_id prerequisito. |

### P3 — No bloquea
| ID | Descripción |
|----|-------------|
| DEBT-FIREWALL-BUILD-LEGACY-001 | firewall-acl-agent/build ruta antigua (seed_client header faltante). No bloquea — build-debug funciona. |

---

## Reglas permanentes (recordatorio para DAY 167)

- Edición ficheros en VM: siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- ZMQ slow joiner: publisher `bind()` ANTES de subscriber `connect()`
- `epoch_id` en wire header: seleccionar clave ANTES de descifrar
- `vendor.key` NUNCA en disco, NUNCA en repo — solo en Vault
- EMECAS++ tiene 3 actos. Enterprise ⊃ OSS — EMECAS++ verde implica EMECAS verde.
- NTP/chrony es P0 gate para correlation-engine (ADR-046 v3 + ADR-048)
- Gate ODR pre-merge: `make PROFILE=production all` antes de cualquier merge a main
- BACKLOG-RESEARCH-KALMAN-001.md está en docs/experiments, pendiente entrada en docs/BACKLOG.md

---

## Wire header (recordatorio)
```
[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]
  bytes 0-3      bytes 4-5         bytes 6-7     bytes 8+
```
epoch_id=0: community. epoch_id>0: enterprise.

---

## Próximos pasos sugeridos (sin orden prescriptivo)

1. **`make emecas`** — verificar que main sigue verde tras el merge
2. **BACKLOG-CI-ENTERPRISE-001** — añadir stage `make emecas++` en Jenkinsfile.dev (~30 líneas)
3. **DEBT-ARGUSPP-NTP-001** — provision.sh: instalar chrony, health-check offset >1s → exit 1
4. Consultar Consejo si el orden NTP→community_id→Suricata es el óptimo para ADR-048 Fase F2

---

*Generado al cierre de DAY 166 — 2026-05-27 · main*
