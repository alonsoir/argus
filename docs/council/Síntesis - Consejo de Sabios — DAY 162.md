Correcto — DAY 162. Empiezo la síntesis del Consejo y los documentos.

## Síntesis del Consejo DAY 162 — Veredicto unánime

Los 8 modelos convergen en los mismos puntos sin disidencia relevante:

**Consenso absoluto (8/8):**
1. `enterprise_vendor.key` fuera de la VM a Vault — es el paso cero, no negociable
2. Pubkey hardcodeada en CMakeLists debe eliminarse — inyectarla desde CI como secreto efímero
3. "Rotación simultánea" es un anti-patrón distribuido — la solución es **rotación coordinada con ventana dual-key** (grace period)
4. **CryptoEpoch** como mecanismo de coordinación vía etcd — numerado, monotónico, con ACK de todos los componentes
5. Hot-reload sin reinicio del proceso — `CryptoProvider::reload()` con semántica RCU
6. `test-e2e-vault` con Vault dev es insuficiente para producción — necesita Vault HA (Raft, 3 nodos)
7. **Automatización Jenkins viene en último lugar** — automatizar antes de tener recovery determinista es peligroso
8. Nuevo ADR requerido: "Crypto Epoch Coordination"

**Riesgos críticos identificados por el Consejo:**
- Split-brain criptográfico si un componente rota y otro no
- Bootstrap paradox: ¿cómo se autentica Jenkins con Vault para el primer keypair?
- Vault como SPOF sin caché local de fallback
- Token hasta 2027 viola zero-trust (vida demasiado larga)
- Sin revocación: compromiso de token requiere recompilar
- Sin métricas `crypto_epoch` → operación ciega

**Roadmap consensuado (orden obligatorio):**

| Fase | Pieza | Bloquea |
|------|-------|---------|
| 0 | `vendor.key` → Vault + eliminar pubkey de CMake | todo |
| 1 | `plugin-loader` lee pubkey de Vault con caché local + hot-reload RCU | Fase 2+ |
| 2 | CryptoEpoch en etcd + health semántico por componente | Fase 3+ |
| 3 | Ventana dual-key en ZMQ (grace period ≥ 2× max_clock_skew) | Fase 4+ |
| 4 | `test-e2e-rotation` con Vault HA + tráfico real + caos | Fase 5+ |
| 5 | Runbook manual + métricas + circuit breaker | Fase 6 |
| 6 | Jenkins automation (generación → Vault → epoch bump → ACK) | producción |
| 7 | SPIFFE/Vault Agent (distribución sin token estático) | enterprise-grade |

**Veto unánime del Consejo:** No se autoriza merge a main ni rotación automática hasta que Fases 0-4 estén implementadas y verdes en EMECAS.

---

Ahora genero los documentos. Primero el BACKLOG:

```bash
cat >> docs/BACKLOG.md << 'ENDBACKLOG'

---

## CRYPTO LIFECYCLE ENTERPRISE (DAY 162 — Consejo de Sabios)

**Contexto:** DAY 161 implementó plugin-loader validate_or_abort(), CryptoProvider::create() factoría, test-e2e-vault y DEBT-EMECAS-DUAL-COMPILATION-001. El Consejo identificó que el ciclo de vida criptográfico enterprise completo requiere 8 fases adicionales antes de ser production-ready.

### FASE 0 — P0 — INMEDIATA (DAY 162-163)

**BACKLOG-CRYPTO-VENDOR-KEY-001** (P0)
- Mover `enterprise_vendor.key` de la VM a Vault KV (`secret/argus/enterprise/vendor-key`)
- Eliminar pubkey hardcodeada de `plugin-loader/CMakeLists.txt`
- Inyectarla desde Jenkins como secreto efímero via `-DARGUS_VENDOR_PUBKEY_HEX=...`
- Nunca en git. Nunca en binarios community.
- **Bloqueante para todo lo demás.**

### FASE 1 — P0 (DAY 163-164)

**BACKLOG-CRYPTO-HOT-RELOAD-001** (P0)
- `plugin-loader` lee pubkey de Vault en runtime con caché local
- `CryptoProvider::reload()` con semántica RCU (Read-Copy-Update)
- Threads en vuelo usan keypair activo mientras se carga el nuevo
- Sin lock global. Sin downtime.

### FASE 2 — P1 (DAY 164-165)

**BACKLOG-CRYPTO-EPOCH-001** (P1) → nuevo ADR-045
- Implementar `CryptoEpoch` monotónico en etcd (`/argus/crypto/epoch/<component_id>`)
- Protocolo de 6 fases: generate → pre-distribute → ACK-ready → commit → ACK-active → cleanup
- Rollback automático si convergencia no alcanzada en T segundos
- Cada componente expone: `crypto_epoch_local`, `crypto_epoch_target`, `rotation_state`

### FASE 3 — P1 (DAY 165-166)

**BACKLOG-CRYPTO-DUAL-KEY-ZMQ-001** (P1)
- Ventana dual-key en CryptoTransport: acepta Keyₙ y Keyₙ₊₁ durante grace period
- `grace_period ≥ 2× max_clock_skew + deploy_time`
- `key_ring[epoch]` con ventana deslizante de 2 epochs
- Property tests: encrypt(msg, epoch) descifra con epoch y epoch+1, pero no epoch+2
- **ADR-013 compliance obligatoria**

### FASE 4 — P1 (DAY 166-167)

**BACKLOG-CRYPTO-E2E-ROTATION-001** (P1)
- `test-e2e-rotation`: Vault HA (Raft, 3 nodos, Docker Compose)
- Tráfico ZMQ real durante la rotación
- Criterio: throughput no cae >5%, sin desconexiones >3s
- Inyección de caos: Vault down, nodo retrasado, partición de red
- **Gate obligatorio antes de cualquier PR de automatización**

### FASE 5 — P2 (DAY 167-168)

**BACKLOG-CRYPTO-OPERABILITY-001** (P2)
- Runbook manual: `argusctl crypto rotate --epoch=N+1`
- Métricas: `argus_crypto_epoch`, `argus_crypto_rotation_latency_seconds`, `argus_crypto_handshake_failures_total`, `argus_crypto_seed_age_seconds`
- Circuit breaker: si handshake_failures > umbral → auto-revert a epoch-1
- Alerta temprana: si token enterprise expira en <30 días → WARN/CRIT logs

### FASE 6 — P2 (DAY 168+)

**BACKLOG-CRYPTO-JENKINS-AUTOMATION-001** (P2)
- Pipeline Jenkins: generación → Vault → epoch bump → espera ACK → gate E2E
- OIDC efímero para Jenkins → Vault (no token estático)
- Rollback automático si gate falla
- **Solo después de Fases 0-5 verdes**

### FASE 7 — P3 (post-FEDER)

**BACKLOG-CRYPTO-SPIFFE-001** (P3)
- Vault Agent / SPIFFE para distribución sin token estático
- AppRole con wrapped secret-id (single-use, TTL corto)
- Eliminación de toda distribución manual de secretos

### Riesgos críticos pendientes (veto del Consejo)

1. **Split-brain criptográfico** — sin Fase 3, una rotación parcial rompe ZMQ silenciosamente
2. **Bootstrap paradox** — pendiente definir cómo Jenkins se autentica con Vault para el primer keypair
3. **Vault como SPOF** — sin caché local firmada, caída de Vault = parada criptográfica
4. **Token de larga vida** — token hasta 2027 viola zero-trust; migrar a lease <24h post-FEDER
5. **Sin revocación** — compromiso de token requiere recompilar; pendiente CRL lógica

### Decisiones del Consejo

- Veto unánime (8/8): no mergear a main ni habilitar rotación automática hasta Fases 0-4 verdes
- ADR-045 "Crypto Epoch Coordination" requerido antes de cualquier PR de Fase 2
- "Rotación simultánea" es anti-patrón; implementar siempre "rotación coordinada con solapamiento"
- Automatización Jenkins: última pieza, no primera

ENDBACKLOG
echo "OK: BACKLOG actualizado"
```