# PROMPT DE CONTINUIDAD — DAY 166
## aRGus NDR | 2026-05-27

---

## Estado al entrar en DAY 166

### Rama activa
`feature/day161-enterprise-crypto-integration` — commit `2389f7d3` (docs DAY 165)

### EMECAS++ OSS del día anterior — todos verdes
- test-all: ✅ (6 suites, 0 fallos)
- test-e2e-synthetic-full: ✅ delta=100/100
- test-e2e-synthetic-firewall: ✅ 540 eventos, 0 crypto_errors
- **Keypair efímero activo:** `a2abfe43e349e86ddeb4a22496b007919c87bdb0f5dc88c17b57cabf0d61331f`

### Fases enterprise completadas
| Fase | Estado |
|------|--------|
| FASE 0 — vendor.key → Vault (Modelo B) | ✅ |
| FASE 1 — CryptoProviderHandle RCU | ✅ |
| FASE 2a — HttpEtcdRegistrar real | ✅ |
| FASE 2b — CryptoEpochCoordinator | ✅ |
| FASE 3 — Wire header epoch_id (13/13) | ✅ |
| FASE 4 — test-e2e-rotation FakeEtcdServer (5/5) | ✅ 60% |
| **EMECAS++ Enterprise (3 actos)** | ⏳ PENDIENTE |

### Consejo de Sabios DAY 165 — decisiones finales de Alonso
1. **Arquitectura:** (C) targets anidados — `make emecas++` depende de `make emecas`
2. **Vault dev:** suficiente con evidencia de retry/cache
3. **Live rotation:** obligatoria en gate (mayoría 7/8)
4. **Test negativo epoch_id:** P0 bloqueante pre-merge (mayoría 6/8)
5. **Jenkins:** post-merge P1
6. **Naming:** EMECAS++ oficial

### Definición EMECAS++ real (decisión Alonso DAY 165)
No se mergea hasta tener los **tres actos** verdes y reproducibles:

**Acto I — Arranque nominal:** todos los componentes se autentican contra Vault, reciben claves, cifran/descifran, tráfico fluye. Medición: `events_processed`, `crypto_errors==0`, `epoch_id` correcto.

**Acto II — Rotación controlada (5 min o forzada):** pipeline sigue corriendo, `CryptoEpochCoordinator` detecta nuevo epoch, `CryptoProviderHandle` hot-reload RCU, wire header actualiza `epoch_id`. Medición: continuo sin gaps, `crypto_errors==0`, `epoch_id` antes/después distintos.

**Acto III — Vault falla en un componente aleatorio:** componente afectado sigue con clave anterior (caché RCU), notifica (log estructurado + señal Jenkins), resto funciona con clave nueva. Al recuperar Vault: componente recibe nueva clave, la aplica. Zero downtime. Datos válidos para paper arXiv.

---

## 🔑 HALLAZGO CRÍTICO AL CIERRE DE DAY 165 — VaultProvider tiene caché

**Se ejecutaron estos comandos al final de la sesión:**
```bash
vagrant ssh -c "grep -A 20 'retry\|cache\|reconnect\|fallback' /vagrant/common/vault_provider.cpp"
vagrant ssh -c "grep -A 20 'retry\|timeout\|reconnect' /vagrant/common/vault_transport.cpp"
```

**Resultado:** VaultProvider ya tiene retry/cache completamente implementado:

- `get_material()` — línea 1: `if (cached_material_.has_value()) return cached_material_.value()`. Si hay material en caché, nunca toca Vault. Funciona en silencio aunque Vault esté caído.
- `ERROR_VAULT_DOWN` → dispara `autonomy_.on_vault_unreachable()` → estado AUTONOMOUS. El pipeline no muere, notifica.
- `refresh()` — maneja recuperación completa: `on_vault_restored()` → RECONCILING → `on_reconciliation_ok()` → NORMAL.

**Implicación:** B1 (el bloqueante más incierto) es gratis. El Acto III no requiere implementación nueva, solo demostrar el comportamiento que ya existe.

**Bloqueantes actualizados:**
| Bloqueante | Estado |
|------------|--------|
| B1 — VaultProvider retry/cache | ✅ Ya implementado (confirmado DAY 165) |
| B2 — test-e2e-vault completo (Acto I) | ⏳ Pendiente |
| B3 — Notificación hacia Jenkins (Acto III) | ⏳ Pendiente — log estructurado ya existe, falta canal Jenkins |
| B4 — Script inyección fallo controlado (Acto III) | ⏳ Pendiente — revocar token Vault o iptables por proceso |

---

## Objetivo de DAY 166

Con B1 resuelto gratis, el plan es:

1. **Completar test-e2e-vault** → Acto I verificado
2. **Implementar DEBT-CRYPTO-NEGATIVE-TEST-001** → test epoch_id inválido (~20 líneas)
3. **Script inyección fallo Vault** → B4 resuelto (revocar token vault dev por componente)
4. **Definir canal notificación** → B3 (log estructurado + señal hacia Jenkins)
5. **Implementar `make emecas++`** con los 3 actos
6. **Ejecutar EMECAS++ completo** — estabilizar y recoger datos

---

## Deudas abiertas P0 pre-merge

| ID | Prioridad | Descripción |
|----|-----------|-------------|
| BACKLOG-EMECAS-ENTERPRISE-001 | P0 | Protocolo EMECAS++ 3 actos |
| BACKLOG-CRYPTO-E2E-ROTATION-001 | P0 | Live rotation con pipeline activo (Acto II) |
| DEBT-CRYPTO-NEGATIVE-TEST-001 | P0 | Test negativo epoch_id=0xFFFF, ~20 líneas |
| DEBT-VAULT-RECONNECT-001 | ✅ RESUELTO | VaultProvider retry/cache ya implementado |

## Deudas post-merge P1
| ID | Descripción |
|----|-------------|
| BACKLOG-CI-ENTERPRISE-001 | Jenkins gate `make emecas++` |

## Deudas P3
| ID | Descripción |
|----|-------------|
| DEBT-FIREWALL-BUILD-LEGACY-001 | firewall-acl-agent/build ruta antigua |

---

## Reglas permanentes (recordatorio)

- Edición ficheros en VM: siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- ZMQ slow joiner: publisher `bind()` ANTES de subscriber `connect()`
- `CPPHTTPLIB_OPENSSL_SUPPORT`: via CMake `target_compile_definitions`, nunca `#define` inline
- `epoch_id` en wire header: seleccionar clave ANTES de descifrar (no oracle de padding)
- Vault dev suficiente para gate de merge (Vault HA → hardware RPi5/N100)
- `vendor.key` NUNCA en disco, NUNCA en repo — solo en Vault
- VaultProvider ya tiene caché RCU — el Acto III no requiere implementación nueva

---

## Wire header (recordatorio)
```
[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]
  bytes 0-3      bytes 4-5         bytes 6-7     bytes 8+
```
epoch_id=0: community. epoch_id>0: enterprise.

---

*Generado al cierre de DAY 165 — 2026-05-26 · commit 2389f7d3*