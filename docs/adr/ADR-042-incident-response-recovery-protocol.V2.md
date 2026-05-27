# ADR-042 — Incident Response & Recovery Protocol (IRP)
**Estado:** DRAFT v2 — DAY 135
**Autor:** Alonso Isidoro Román
**Revisión:** Consejo de Sabios 8/8 (DAY 135) — segunda ronda pendiente
**Relacionado:** ADR-025, ADR-025-EXT-001, ADR-030, ADR-039

---

## Motivación

Dos incidentes distintos, un mismo patrón arquitectónico sin resolver:

**Incidente Tipo A — OS comprometido (DAY 135):**
`argus-apt-integrity.service` detecta que `/etc/apt/sources.list` ha sido
modificado. Sin este ADR: poweroff silencioso, hospital sin protección,
admin sin información, sin herramientas de recuperación.

**Incidente Tipo B — Plugin defectuoso o malicioso (Hugo Vázquez Caramés):**
Plugin Ed25519-firmado con comportamiento anómalo en producción.
Hay que sacarlo ASAP sin parar el pipeline ni dejar la red sin protección.

**El patrón común:**
Emergencias de integridad que generan emergencias de disponibilidad
si no existe protocolo de respuesta. aRGus no puede elegir entre
seguridad y disponibilidad — debe gestionar ambas.

**Lección del Consejo DAY 135 (Gemini — "Paradoja del suicidio"):**
Un poweroff inmediato sin aislamiento previo de red es un vector de DoS
trivial: un atacante que conoce el mecanismo puede apagar el nodo a
voluntad tocando `sources.list`. La respuesta correcta es
**aislar primero, recopilar evidencia, poweroff después**.

---

## Principios de diseño

**P1 — El sistema nunca muere en silencio.**
Toda acción defensiva va precedida de notificación al exterior.
Si no hay red, evidencia en disco local. Si hay red, admin alertado
en segundos via múltiples canales (webhook + syslog remoto + cola local).

**P2 — La acción defensiva es proporcional al incidente.**
OS comprometido → aislar red → forensics → poweroff.
Plugin defectuoso → unload + rollback a versión anterior.
Pipeline degradado → modo safe + alerta (DEBT-IRP-C-001).

**P3 — El admin tiene herramientas, no un sistema negro.**
Safe mode (initramfs read-only) recopila evidencia con dignidad forense,
la firma, la envía, y confirma al admin con referencia trazable.
El admin opera en local — sin ejecución remota desde sistema comprometido.

**P4 — El hospital no queda indefenso.**
Si existe nodo standby: verificar integridad del standby ANTES de promover.
Standby comprometido no se promueve (OQ-5 Consejo: riesgo de amplificación).
Si no hay standby: SLA de restauración es el tiempo crítico a minimizar.
Documentar explícitamente en manual de operaciones.

**P5 — Forensics primero, diagnóstico después.**
La evidencia se recopila antes de cualquier intento de recuperación.
Limpiar el nodo antes de recopilar = destruir la escena del crimen.

**P6 — Reintegración verificada, nunca automática.**
Un nodo restaurado no vuelve a la flota sin pasar
`argus-post-recovery-check` completo + aprobación manual del admin.
(Brecha nueva identificada por Qwen y Kimi — Consejo DAY 135)

---

## Arquitectura

### Tres capas por incidente

```
┌─────────────────────────────────────────────────────┐
│  CAPA 1 — DETECCIÓN + GRITO                         │
│  Múltiples canales: webhook + syslog + cola local   │
│  Nunca silencioso. Nunca bloqueante.                │
├─────────────────────────────────────────────────────┤
│  CAPA 2 — ACCIÓN DEFENSIVA PROPORCIONAL             │
│  Aislar red → Verificar standby → Poweroff          │
│  Plugin unload → RF fallback → Rollback             │
├─────────────────────────────────────────────────────┤
│  CAPA 3 — RECUPERACIÓN ASISTIDA                     │
│  initramfs read-only → Forensics → Firma → Envío   │
│  Post-recovery check → Quarantine → Reintegración  │
└─────────────────────────────────────────────────────┘
```

---

## Incidente Tipo A — OS comprometido (apt sources)

### Capa 1: Detección + Grito (múltiples canales)

```bash
# argus-irp-notify — store-and-forward, nunca bloqueante
QUEUE="/var/lib/argus/irp-queue"
mkdir -p "$QUEUE"

PAYLOAD="{\"incident\":\"IRP-A\",\"node\":\"$(hostname)\",
  \"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
  \"severity\":\"CRITICAL\",
  \"message\":\"APT sources integrity violation — isolating network\"}"

# Canal 1: syslog local (siempre funciona)
logger -p auth.crit "ARGUS IRP-A: $(hostname) APT INTEGRITY VIOLATION"
journalctl --flush

# Canal 2: webhook best-effort con cola persistente
if curl --max-time 5 --silent -X POST "$ARGUS_ALERT_WEBHOOK" \
   -H "Content-Type: application/json" -d "$PAYLOAD"; then
    logger "ARGUS IRP-A: webhook delivered"
else
    # Fallo: encolar para reintento post-recuperación
    echo "$PAYLOAD" >> "$QUEUE/pending-$(date +%s).json"
    logger "ARGUS IRP-A: webhook failed — queued for retry"
fi

# Canal 3: syslog remoto (si rsyslog configurado — best-effort)
logger -n "$ARGUS_SYSLOG_HOST" -p auth.crit \
  "ARGUS IRP-A: $(hostname) APT INTEGRITY VIOLATION" 2>/dev/null || true
```

### Capa 2: Acción — Jerarquía de respuesta

**Decisión Consejo DAY 135 (Gemini + Grok + Kimi + DeepSeek):**
Aislar red PRIMERO, poweroff DESPUÉS. El poweroff inmediato sin aislamiento
es un vector de DoS para el atacante.

```bash
# argus-apt-integrity-check — secuencia de respuesta

# PASO 1: Aislar red inmediatamente (corta el vector lateral)
ip link set eth0 down 2>/dev/null || true
ip link set eth1 down 2>/dev/null || true
logger -p auth.crit "ARGUS IRP-A: network isolated"

# PASO 2: Verificar si hay standby disponible e íntegro
if argus-standby-ping --timeout=3 2>/dev/null; then
    # Standby responde — notificar pero NO auto-promover
    # El admin debe verificar integridad del standby antes de promover
    logger -p auth.crit "ARGUS IRP-A: standby detected — manual promotion required"
    argus-irp-notify --message="Standby available — verify integrity before promoting"
fi

# PASO 3: Poweroff
# Red ya aislada — el poweroff es ahora seguro
# El atacante no puede usar los segundos finales para lateral movement
systemctl poweroff
```

**Systemd unit actualizada:**
```ini
[Service]
Type=oneshot
ExecStart=/usr/local/bin/argus-apt-integrity-check
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

# Capa 1: evidencia antes de actuar
ExecStopPre=/usr/bin/journalctl --flush
ExecStopPre=/usr/bin/logger -p auth.crit "ARGUS IRP-A: APT integrity violation"
ExecStopPre=/usr/local/bin/argus-irp-notify

# Capa 2: aislar red antes del poweroff
ExecStopPre=/usr/local/bin/argus-network-isolate

# Acción final: poweroff (no reboot — Voto de Oro Alonso DAY 135)
FailureAction=poweroff

# Anti-bootloop
StartLimitIntervalSec=300
StartLimitBurst=2
```

### Capa 3: Safe Mode — initramfs read-only (decisión Alonso DAY 135)

**Filosofía:** Un initramfs mínimo montado en RAM desde partición verificada
da acceso a los logs del disco sin que el SO comprometido pueda interferir.
El admin opera en LOCAL únicamente — sin ejecución remota posible.
Esto es mejor que apagar sin recopilar nada.

**Activación:**
```
GRUB entry: "aRGus Safe Mode (Forensic)"
  → Arranca initramfs mínimo desde partición read-only verificada
  → Monta disco del sistema en read-only
  → NO arranca servicios normales
  → NO acepta conexiones SSH ni remotas
  → Admin opera en consola física o IPMI
```

**`argus-forensic-collect` en safe mode recopila:**
1. SHA-256 de todos los binarios del pipeline (`/opt/argus/bin/*`)
2. SHA-256 actual vs baseline de apt sources
3. Lista de paquetes instalados vs baseline
4. Logs de Falco desde el último boot
5. journald completo desde el último boot
6. `/etc/argus-integrity/apt-sources.sha256` (baseline)
7. Timestamps de modificación en `/etc/apt/`

**Limitación documentada (honestidad científica):**
La evidencia recopilada desde initramfs tiene cadena de custodia media —
mejor que recopilar desde sistema comprometido, pero sin garantía absoluta
si el kernel o el disco han sido alterados. Para evidencia de alta confianza
se requiere TPM 2.0 + attestation remota (DEBT-IRP-FORENSICS-TPM-001,
post-FEDER). Esta limitación se documenta en el paper.

**El admin ve:**
```
╔══════════════════════════════════════════════════════╗
║  aRGus Forensic Mode — Node: hospital-argus-01      ║
╚══════════════════════════════════════════════════════╝
Incident: IRP-A — APT Sources Integrity Violation
Detected: 2026-04-29T09:32:15Z

Collecting evidence...
  ✅ Pipeline binaries: 6 files, SHA-256 computed
  ✅ APT sources: MISMATCH DETECTED
     Expected: a3f2b1c4...
     Actual:   7e9d41ae...
  ✅ Falco logs: 47 entries
  ✅ journald: 1,247 entries
  ✅ Package list: 304 packages

Packaging evidence...
  ✅ argus-forensics-hospital-argus-01-20260429-093215.tar.gz
  ✅ Signed: Ed25519 — b5b6cbdf...
  ✅ Sent to: [on-premise receiver / queued for delivery]
  📋 Reference: INC-2026-0429-001

⚠️  DO NOT RESTORE until team confirmation received.
⚠️  Node isolated. Fleet continues operating.
⚠️  Manual standby promotion required if needed.
```

---

## Incidente Tipo B — Plugin defectuoso o malicioso

### Detección
- Falco: regla `argus_model_or_plugin_replaced`
- Métrico: `confidence_score` fuera de rango durante >N eventos
- Operador: falsos positivos masivos en firewall-acl-agent

### Capa 2: Emergency Plugin Unload

```bash
make emergency-plugin-unload PLUGIN=libplugin_xgboost.so

# PluginLoader recibe mensaje firmado Ed25519:
# { "action": "unload", "target_plugin": "libplugin_xgboost.so",
#   "reason": "IRP-B-001", "signature": "..." }
# → dlclose() inmediato
# → pipeline continúa con RandomForest embedded (fallback)
# → log con trace_id + alerta al admin
```

### Capa 3: Restauración + SLA

```bash
# SLA de restauración (decisión Consejo DAY 135):
# - Versión anterior disponible en dist/: restaurar en <15 minutos
# - Sin versión anterior: <4h para nuevo plugin firmado por equipo aRGus

# RF embedded como fallback expone métricas de degradación:
# Pipeline status: "⚠️ FALLBACK ACTIVE — RF embedded
#   F1 estimated: ~0.97 (vs 0.9985 XGBoost)
#   Investigate and restore plugin within SLA"

make prod-deploy-plugin PLUGIN=libplugin_xgboost_v1.0.so
# → verifica firma Ed25519 → hot-swap sin reinicio
```

---

## Incidente Tipo C — Pipeline degradado

Componente falla (etcd, ml-detector) pero OS íntegro y plugins correctos.
Sniffer + Fast Detector + Firewall continúan con últimas reglas conocidas.
**DEBT-IRP-C-001 — post-FEDER.**

---

## Reintegración post-recovery (P6 — nueva)

Un nodo restaurado NO vuelve a la flota sin verificación completa:

```bash
# argus-post-recovery-check — ejecutado en cada boot post-IRP
post_recovery_validation() {
    # Check 1: apt sources íntegros
    /usr/local/bin/argus-apt-integrity-check || return 1

    # Check 2: firma de todos los plugins válida
    argus-verify-all-plugins || return 1

    # Check 3: binarios del pipeline vs manifest firmado
    verify_baseline_hashes "/var/lib/argus/baseline-manifest.json" || return 1

    logger "ARGUS POST-RECOVERY: node eligible for quarantine monitoring"
    return 0
}
```

**Política de reintegración:**
- Verificación automática obligatoria en boot post-IRP
- 24h de monitoreo reforzado (quarantine period)
- Aprobación manual del admin siempre requerida
- Reintegración automática a la flota: NUNCA

---

## GDPR y endpoint receptor

**Decisión Consejo DAY 135 (7/8 coinciden):**
El endpoint receptor de evidencia forense debe ser **on-premise del hospital**
en producción real. Los logs de red pueden contener IPs de pacientes,
timestamps de procedimientos médicos, y metadatos DNS sensibles.
Enviar a SaaS externo sin anonimización viola GDPR Art. 5(1)(c)
y Art. 9 (datos de salud).

**Política:**
- **Producción hospitalaria:** endpoint on-premise obligatorio
- **Demo FEDER / laboratorio:** endpoint de prueba con anonimización
- **SaaS gestionado por aRGus:** solo con DPA firmado + PII redaction

**PII redaction antes de cualquier envío externo:**
```python
# IPs internas → hash SHA-256 irreversible
# Timestamps → ventanas de 5 minutos
# Payloads → solo primeros 128 bytes (headers)
```

---

## Componentes a implementar

| Componente | Descripción | Prioridad |
|------------|-------------|-----------|
| `argus-network-isolate` | Aislar red antes del poweroff | 🔴 Alta — inmediato |
| `argus-irp-notify` | Webhook + syslog + cola persistente | 🔴 Alta — inmediato |
| `argus-forensic-collect` | Recopilación, firma, envío | 🔴 Alta — post-merge |
| initramfs safe mode | GRUB entry + entorno read-only | 🟡 Media — post-FEDER |
| `argus-post-recovery-check` | Verificación pre-reintegración | 🟡 Media — post-merge |
| `argus-standby-verify` | Verificar integridad standby pre-promote | 🟡 Media — post-FEDER |
| Endpoint on-premise | Receptor de evidencia del hospital | 🟡 Media — post-FEDER |
| TPM attestation | Evidencia de alta confianza | ⏳ post-FEDER |

---

## Deudas generadas

| ID | Descripción | Plazo |
|----|-------------|-------|
| DEBT-IRP-A-001 | `argus-irp-notify` multi-canal + cola persistente | post-merge |
| DEBT-IRP-A-002 | `argus-network-isolate` pre-poweroff | post-merge |
| DEBT-IRP-A-003 | `argus-forensic-collect` + initramfs safe mode | post-FEDER |
| DEBT-IRP-A-004 | Endpoint receptor on-premise (GDPR) | post-FEDER |
| DEBT-IRP-A-005 | `argus-post-recovery-check` + quarantine period | post-merge |
| DEBT-IRP-B-001 | Métricas degradación RF fallback expuestas | post-merge |
| DEBT-IRP-B-002 | SLA restauración plugin documentado en ops | post-merge |
| DEBT-IRP-C-001 | Modo pipeline degradado | post-FEDER |
| DEBT-IRP-FORENSICS-TPM-001 | TPM 2.0 attestation para evidencia alta confianza | post-FEDER |
| DEBT-IRP-GDPR-001 | PII redaction + DPA framework | post-FEDER |

---

## Tests de cierre (TDH)

```bash
make test-irp-type-a    # simular compromiso apt → verificar: red aislada,
                         # alerta enviada, poweroff, evidencia recopilada
make test-irp-type-b    # plugin malformado → verificar: unload, RF activo,
                         # métricas degradación visibles, rollback <15min
make test-irp-recovery  # post-poweroff → verificar: recovery check pasa/falla
                         # nodo no se reintegra sin aprobación manual
```

---

## Conexión con el paper (arXiv:2604.04952)

El protocolo IRP para NDR open-source en infraestructura crítica no está
documentado en la literatura. ADR-042 es material para:
- §11 Future Work (subsección nueva: Operational Resilience)
- §4.x Integration Philosophy (resiliencia como principio de diseño)

Se publicará con honestidad científica: las limitaciones de forensics en
sistema comprometido, la dependencia de hardware para TPM attestation,
y el riesgo conocido de standby comprometido están documentados aquí.

---

## Limitaciones residuales documentadas

1. **Forensics en initramfs:** cadena de custodia media, no alta. Un
   rootkit que modifica el gestor de arranque puede contaminar incluso
   el initramfs. Mitigación completa requiere TPM + Secure Boot (post-FEDER).

2. **Standby comprometido:** si el vector de ataque llegó via red a toda
   la flota, el standby puede estar comprometido. Sin quorum externo
   no hay forma de saberlo automáticamente. Mitigación: verificación
   manual obligatoria pre-promote.

3. **Webhook en red cortada:** si el atacante cortó el tráfico saliente,
   la notificación queda en cola local. El admin no sabe que el nodo cayó
   hasta que lo descubre por ausencia de heartbeat o visualmente.

4. **Single-node hospital:** sin standby, el poweroff = red sin protección
   indefinidamente hasta restauración manual. Documentado en manual de
   operaciones como riesgo conocido y aceptado.

---

*DAY 135 — Draft v2 — 29 Abril 2026*
*"El sistema nunca muere en silencio. Grita, aísla, documenta, y cae con dignidad."*


