Leo los 8 dictámenes. Sintetizo el consenso antes de escribir nada:

**Q1:** 6/8 (ChatGPT, DeepSeek, Kimi, Qwen, Claude, Mistral) — Vault RNG suficiente para FEDER. Grok/Gemini piden mezcla entropy para prod. **Decisión: Vault para FEDER, mezcla entropy como DEBT post-FEDER.**

**Q2:** 8/8 — Cache tmpfs no viola ADR-020. TTL 1h dev, 15min prod. **Consenso total.**

**Q3:** 8/8 — etcd bootstrap especial sin barrera. **Consenso total.**

**Q4:** 6/8 — backend `file` suficiente para dev FEDER. Grok pide Raft ahora. **Decisión: file para FEDER, Raft post-FEDER.**

**Q5:** Divergencia interesante — Kimi dice rotación manual orquestada para FEDER (sin automática), DeepSeek protocolo 5 pasos, Qwen cooldown=grace_period. **Decisión: rotación manual para FEDER, protocolo coordinado post-FEDER.**

**Q6:** 8/8 — stage separado. **Consenso total.**

**Q7:** 8/8 — por familia. **Consenso total.**

**Preguntas adicionales del Consejo a responder:**
- AQ1 ChatGPT: timeout agresivo 5s → DeepSeek OA3 ya lo dice, adoptamos
- AQ2 ChatGPT: stampede → jitter + staggered startup
- AQ3 ChatGPT: auditoría → fingerprint + key_version en metadata
- AQ4 ChatGPT: heartbeat posterior a crypto_ready → sí, necesario
- Grok: ¿HSM/TPM? → No en hardware FEDER inicial (miniPC ~300€)
- Grok: ¿tamaño clúster? → 6 componentes + etcd

Ahora creo todo el paquete de documentos de una vez:

```bash
python3 << 'PYEOF'
import os
os.makedirs('docs/consejo', exist_ok=True)
os.makedirs('docs/adr', exist_ok=True)

# ── 1. SÍNTESIS CONSEJO DAY 149 ────────────────────────────────────
sintesis = '''# CONSEJO DE SABIOS — SÍNTESIS DAY 149
## Arquitectura CI/CD Criptográfica — Consenso 8/8

**Fecha:** 12 Mayo 2026 | **DAY:** 149
**Participantes:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral

---

## VEREDICTO GLOBAL

**ARQUITECTURA APROBADA.** El diseño ha cruzado un umbral importante: ya no es
"crypto para un pipeline" sino un sistema distribuido con raíz de confianza
operacional explícita. La dirección es correcta. El mayor riesgo ya no es
criptográfico — ahora es complejidad operacional emergente.

---

## DECISIONES CONSENSUADAS (Q1–Q7)

### Q1 — Vault RNG: 6/8 Vault suficiente para FEDER
**DECISIÓN:** `vault write sys/tools/random bytes=32` como única fuente de
entropy en FEDER. Vault ya implementa NIST SP 800-90A (CTR_DRBG/Hash_DRBG)
alimentado por `getrandom()` + `/dev/urandom` + CPU RDRAND si disponible.
Mezcla manual de entropy externa = cargo cult cryptography si Vault ya hace
el mixing correcto.
**DISIDENCIA:** Grok/Gemini recomiendan mezcla HKDF(Vault_output, getrandom())
para prod con hardware HSM/TPM disponible.
**DEUDA:** DEBT-VAULT-ENTROPY-MIXING-001 — mezcla entropy para prod post-FEDER.
Aplica cuando el modelo de amenaza incluya adversario que controla el kernel
del host Vault.

### Q2 — Cache tmpfs: 8/8 no viola ADR-020
**DECISIÓN:** Cache cifrada en tmpfs con TTL configurable. No viola el principio
TODO O NADA porque tmpfs no sobrevive reboot. Si Vault está caído y cache tiene
seed con TTL válido → componente arranca con log WARN explícito. Si Vault caído
Y cache vacía → exit(1). El principio se mantiene post-reboot.
**CONDICIONES:** TTL 1h dev, 15min prod. Permisos 0700. mlock() sobre material
derivado (no sobre seed). Registro en etcd "started_with_cache".
**ADDENDUM Kimi:** "La cache tmpfs es la respuesta correcta. No dejes que la
pureza del principio mate la utilidad del sistema en un hospital a las 3 AM."

### Q3 — etcd bootstrap huevo/gallina: 8/8
**DECISIÓN:** etcd-server es el único componente que arranca sin barrera etcd.
Obtiene su seed directamente de Vault (sin pasar por la barrera). Registra
su propio crypto_ready. Todos los demás componentes esperan la barrera.
**FLUJO:**
  1. Vault online
  2. etcd-server: Vault → seed → keypair → self-register crypto_ready
  3. Resto: Vault → seed → keypair → etcd register crypto_ready
  4. etcd confirma ALL crypto_ready → broadcast pipeline_open
  5. Componentes abren ZeroMQ
**AXIOMA:** etcd-server es el trust anchor operacional. Si es comprometido,
se asume compromiso total del pipeline.

### Q4 — Vault backend file en dev: 6/8
**DECISIÓN:** Backend `file` suficiente para dev y FEDER. Raft post-FEDER.
Dev prioriza simplicidad y EMECAS. Prod prioriza disponibilidad.
**CONDICIÓN:** provision_crypto.sh debe ser idempotente — si seeds ya existen
en Vault, no las regenera sin flag --force.
**DEUDA:** DEBT-VAULT-HA-001 — Vault HA con backend raft para producción real.
**DISIDENCIA:** Grok recomienda migrar a Raft desde ahora para eliminar
diferencias dev/prod. Rechazado para FEDER: overhead no justificado.

### Q5 — Rotación coordenada: consenso con matiz Kimi
**DECISIÓN:** Rotación MANUAL orquestada para FEDER (Kimi, adoptado).
No automática. Un `make rotate-crypto` que orquesta:
  1. etcd notifica rotation_pending
  2. Componentes drenan colas con seed vieja
  3. etcd confirma all_drained
  4. Micro-ventana offline (~segundos)
  5. Nueva seed activa atómicamente
  6. Pipeline online
Rotación automática continua = post-FEDER con protocolo completo de 5 fases.
**Las seeds ChaCha20 NO usan dual-valid window** (no hay handshake como TLS).
ADR-004 cooldown aplica solo a HMAC keys de pseudonimización.

### Q6 — provision_crypto.sh stage separado: 8/8
**DECISIÓN:** Stage separado "Provision Crypto" en Jenkinsfile. Condicional
(solo corre si PROVISION_CRYPTO=true o primera instalación). Genera artifact
de auditoría firmado. Si falla → pipeline ABORT. Stages siguientes no ejecutan.

### Q7 — Seed families en Vault: 8/8
**DECISIÓN:** Paths por familia.
```
argus/dev/families/family_A/seed    ← sniffer↔ml-detector
argus/dev/families/family_B/seed    ← ml-detector↔firewall
argus/dev/families/family_C/seed    ← firewall↔rag-ingester
argus/dev/components/etcd/seed      ← etcd bootstrap especial
argus/prod/families/...
```
Cada componente lee solo el path de su familia. Vault policy restrictiva:
componentes no pueden listar otros paths.
`derive_keypair(family_seed, component_id, channel_id)` via libsodium
`crypto_kdf_derive_from_key()` para obtener keypairs distintas por extremo
manteniendo raíz de familia común.

---

## RESPUESTAS A PREGUNTAS ADICIONALES DEL CONSEJO

### AQ1 (ChatGPT) — ¿Timeouts si Vault responde lento?
**ADOPTADO:** Timeout agresivo 5s en vault_client (DeepSeek OA3). Comportamiento:
- 0-5s: espera Vault
- 5s timeout: intenta cache tmpfs inmediatamente
- Cache OK: arranca con WARN
- Cache vacía: exit(1) inmediato
Un "slow Vault" puede ser peor que un Vault caído — bloquea todo el arranque
y puede causar que systemd mate el proceso por TimeoutStartSec.

### AQ2 (ChatGPT) — ¿Stampede al reiniciar N componentes?
**ADOPTADO:** Jitter aleatorio en vault_client antes de la llamada inicial.
```cpp
// common/vault_client.cpp
std::this_thread::sleep_for(
    std::chrono::milliseconds(
        component_index * 500 + rand() % 1000
    )
);
```
Stagger de 500ms por componente + jitter 0-1s. 6 componentes = máximo
4s de arranque escalonado. Vault no ve burst simultáneo.

### AQ3 (ChatGPT) — ¿Auditoría derivación criptográfica?
**ADOPTADO:** Cada componente registra en etcd al registrar crypto_ready:
```json
{
  "component": "sniffer",
  "crypto_ready": true,
  "key_version": "v1",
  "family": "family_A",
  "vault_path": "argus/dev/families/family_A",
  "derivation_timestamp": "2026-05-12T09:00:00Z",
  "fingerprint": "sha256:8a3f..."
}
```
NO se loguea material sensible. Solo fingerprint del material derivado.

### AQ4 (ChatGPT) — ¿Heartbeat posterior a crypto_ready?
**ADOPTADO:** etcd necesita heartbeat periódico post-crypto_ready. Si un
componente muere silenciosamente, el lease expira y etcd detecta la ausencia.
El pipeline debe alertar si ANY componente pierde heartbeat. No fuerza
apagado del pipeline (el componente puede reiniciarse), pero alerta.

### Grok — ¿HSM/TPM en nodos prod?
**RESPUESTA:** No en hardware FEDER inicial (miniPC ~300€, Raspberry Pi 4/5
~80€). HSM/TPM es post-FEDER cuando el modelo de despliegue madure hacia
infraestructura dedicada hospitalaria. Documentado en roadmap.

### Grok — ¿Tamaño del clúster objetivo?
**RESPUESTA:** 6 componentes C++20 (sniffer, ml-detector, firewall-acl-agent,
etcd-server, rag-ingester, rag-security) + Vault + Jenkins en servidor central.
Single-node edge en FEDER. Multi-node post-FEDER.

---

## DEUDAS REGISTRADAS (DAY 149)

| ID | Descripción | Prioridad |
|---|---|---|
| DEBT-VAULT-ENTROPY-MIXING-001 | Mezcla entropy externa post-FEDER | P2 |
| DEBT-VAULT-HA-001 | Vault HA backend raft para prod | P1 |
| DEBT-CRYPTO-STAMPEDE-001 | Jitter startup vault_client | P1 |
| DEBT-CRYPTO-AUDIT-FINGERPRINT-001 | Fingerprint en etcd crypto_ready | P1 |
| DEBT-CRYPTO-HEARTBEAT-001 | Heartbeat periódico post-crypto_ready | P1 |
| DEBT-PARQUET-TIMESTAMP-NS-001 | firewall-acl-agent ms→ns en origen | P2 |
| DEBT-VAULT-PROVISION-PROD-001 | Cerrada DAY 149 | ✅ |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | Cerrada DAY 149 | ✅ |

---

*Consejo de Sabios — DAY 149 — 12 Mayo 2026*
*Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral*
'''
open('docs/consejo/DAY149-sintesis-consenso.md', 'w').write(sintesis)
print("docs/consejo/DAY149-sintesis-consenso.md creado")

