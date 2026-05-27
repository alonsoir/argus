# ADR-042 — Incident Response & Recovery Protocol (IRP)
**Estado:** PRE-DISEÑO — DAY 135
**Autor:** Alonso Isidoro Román
**Revisión:** Consejo de Sabios (pendiente DAY 136)
**Relacionado:** ADR-025 (Plugin Integrity), ADR-025-EXT-001 (Emergency Patch), ADR-030 (Hardened Variant A), ADR-039 (BSR)

---

## Motivación

Dos incidentes distintos, un mismo patrón arquitectónico sin resolver:

**Incidente tipo A — OS comprometido (DAY 135):**
`argus-apt-integrity.service` detecta que `/etc/apt/sources.list` ha sido
modificado. `FailureAction=poweroff` se ejecuta inmediatamente. El nodo cae.
El hospital queda sin protección hasta que un humano interviene.
Sin notificación. Sin forensics automatizados. Sin recuperación asistida.

**Incidente tipo B — Plugin defectuoso o malicioso (Hugo Vázquez Caramés):**
Un plugin Ed25519-firmado se despliega en producción y produce falsos positivos
masivos, bloquea tráfico legítimo, o exhibe comportamiento anómalo.
Hay que sacarlo ASAP sin parar el pipeline ni dejar la red sin protección.
El mecanismo de unload existe (ADR-025-EXT-001) pero el protocolo completo
detección → decisión → acción → recuperación no está definido.

**El patrón común:**
Ambos son emergencias de integridad que generan emergencias de disponibilidad
si no existe un protocolo de respuesta. aRGus no puede ser un sistema que
elige entre seguridad y disponibilidad — debe gestionar ambas.

---

## Principios de diseño

**P1 — El sistema nunca muere en silencio.**
Toda acción defensiva va precedida de notificación al exterior.
Si no hay red, la evidencia queda en disco local.
Si hay red, el admin es alertado en segundos.

**P2 — La acción defensiva es proporcional al incidente.**
OS comprometido → poweroff inmediato (riesgo de flota).
Plugin defectuoso → unload + rollback (riesgo localizado).
Pipeline degradado → modo safe + alerta (riesgo parcial).

**P3 — El admin tiene herramientas, no un sistema negro.**
Safe mode recopila evidencia completa, la firma, la envía,
y confirma visualmente al admin con referencia de incidencia trazable.

**P4 — El hospital no queda indefenso.**
Si existe nodo standby → promover antes del poweroff.
Si no existe → SLA de restauración es el tiempo crítico a minimizar.

**P5 — Forensics primero, diagnóstico después.**
La evidencia se recopila antes de cualquier intento de recuperación.
Limpiar el nodo antes de recopilar evidencia destruye la capacidad
de entender qué ocurrió y cómo prevenir la siguiente vez.

---

## Arquitectura

### Tres capas por incidente

┌─────────────────────────────────────────────────────┐
│  CAPA 1 — DETECCIÓN + GRITO                         │
│  El sistema detecta, documenta y notifica           │
│  antes de actuar. Nunca en silencio.                │
├─────────────────────────────────────────────────────┤
│  CAPA 2 — ACCIÓN DEFENSIVA PROPORCIONAL             │
│  Poweroff / Plugin unload / Pipeline degradado      │
├─────────────────────────────────────────────────────┤
│  CAPA 3 — RECUPERACIÓN ASISTIDA (SAFE MODE)         │
│  Forensics → Firma → Envío → Confirmación           │
│  El admin ve qué pasó y que la evidencia fue        │
│  enviada antes de intentar restaurar.               │
└─────────────────────────────────────────────────────┘

---

## Incidente Tipo A — OS comprometido (apt sources)

### Capa 1: Detección + Grito

```bash
# argus-apt-integrity-check — secuencia antes del poweroff
journalctl --flush
logger -p auth.crit "ARGUS IRP-A: APT INTEGRITY VIOLATION node=$(hostname)"

# Webhook best-effort — si falla no bloquea el poweroff
curl --max-time 5 --silent \
  -X POST "${ARGUS_ALERT_WEBHOOK}" \
  -H "Content-Type: application/json" \
  -d "{\"incident\":\"IRP-A\",\"node\":\"$(hostname)\",
       \"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
       \"message\":\"APT sources integrity violation — powering off\",
       \"hash_expected\":\"${EXPECTED}\",
       \"hash_actual\":\"${ACTUAL}\"}" || true
```

### Capa 2: Acción

```ini
[Service]
FailureAction=poweroff           # Voto de Oro Alonso DAY 135
ExecStartPre=/usr/bin/journalctl --flush
ExecStartPre=/usr/bin/logger -p auth.crit "ARGUS IRP-A: powering off"
ExecStartPre=/usr/local/bin/argus-irp-notify   # webhook best-effort
StartLimitIntervalSec=300
StartLimitBurst=2
```

### Capa 3: Safe Mode (boot externo / entrada GRUB especial)

```bash
make safe-mode
# o directamente:
/usr/local/bin/argus-forensic-collect
```

**`argus-forensic-collect` recopila:**
1. SHA-256 de todos los binarios del pipeline
2. SHA-256 actual vs baseline de apt sources
3. Lista completa de paquetes instalados
4. Logs de Falco desde el último boot
5. journald completo desde el último boot
6. `/etc/argus-integrity/apt-sources.sha256` (baseline original)
7. Timestamps de modificación en `/etc/apt/`

**Empaqueta, firma con Ed25519 del nodo, y envía.**

**El admin ve:**

✅ Evidencia recopilada: 47 ficheros, 2.3 MB
✅ Firmada: SHA-256 = abc123...
✅ Enviada a: irp.argus-ndr.org/incidents/INC-2026-0429-001
📋 Referencia: INC-2026-0429-001
📧 Equipo notificado. Tiempo de respuesta: <4h
⚠️  NO RESTAURAR hasta recibir confirmación del equipo aRGus.
⚠️  El nodo está aislado. La flota continúa operativa.

---

## Incidente Tipo B — Plugin defectuoso o malicioso

### Detección

- **Automático:** Falco — regla `argus_model_or_plugin_replaced`
- **Métrico:** `confidence_score` fuera de rango durante >N eventos
- **Operador:** falsos positivos masivos en firewall-acl-agent

### Capa 2: Emergency Plugin Unload

```bash
make emergency-plugin-unload PLUGIN=libplugin_xgboost.so

# PluginLoader recibe mensaje firmado:
# { "action": "unload", "target": "libplugin_xgboost.so",
#   "reason": "IRP-B-001", "signature": "Ed25519..." }
# → dlclose() inmediato
# → pipeline continúa con RandomForest embedded (fallback)
# → log con trace_id
```

### Capa 3: Restauración sin downtime

```bash
# Pipeline continúa — RF embedded es el fallback
# Admin restaura versión anterior firmada:
make prod-deploy-plugin PLUGIN=libplugin_xgboost_v1.0.so
# → verifica firma Ed25519 → hot-swap sin reinicio
```

---

## Incidente Tipo C — Pipeline degradado

Un componente falla (etcd, ml-detector) pero OS íntegro y plugins correctos.
Pipeline en modo degradado: Sniffer + Fast Detector + Firewall continúan.
**No implementado — DEBT-IRP-C-001 — post-FEDER.**

---

## Componentes a implementar

| Componente | Descripción | Prioridad |
|------------|-------------|-----------|
| `argus-irp-notify` | Webhook best-effort pre-poweroff | 🔴 Alta |
| `argus-forensic-collect` | Recopilación + firma + envío | 🔴 Alta |
| `make safe-mode` | Makefile target modo forense | 🔴 Alta |
| `ARGUS_ALERT_WEBHOOK` | Discord / email / SIEM | 🟡 Media |
| `irp.argus-ndr.org/incidents/` | Endpoint receptor | 🟡 Media |
| Guardrail runtime confidence_score | Detección automática Tipo B | 🟡 Media |
| Nodo standby auto-promote | HA antes del poweroff | 🔴 Alta (hospitales) |
| DEBT-IRP-C-001 | Pipeline degradado | ⏳ post-FEDER |

---

## Deudas generadas

| ID | Descripción | Plazo |
|----|-------------|-------|
| DEBT-IRP-A-001 | `argus-irp-notify` — webhook best-effort pre-poweroff | post-merge |
| DEBT-IRP-A-002 | `argus-forensic-collect` + `make safe-mode` | post-FEDER |
| DEBT-IRP-A-003 | Endpoint receptor de evidencia forense | post-FEDER |
| DEBT-IRP-B-001 | Guardrail runtime confidence_score | post-FEDER |
| DEBT-IRP-C-001 | Modo pipeline degradado | post-FEDER |

---

## Preguntas abiertas para el Consejo DAY 136

**OQ-1:** ¿El webhook es best-effort (nunca bloquea) o síncrono con
timeout máximo de 5s? Tensión: si el atacante cortó la red, falla
de todas formas. Pero 5s de bloqueo antes del poweroff puede ser
aceptable si aumenta significativamente la probabilidad de notificación.

**OQ-2:** ¿`argus-forensic-collect` en safe mode (boot externo) o
puede ejecutarse en el sistema comprometido? Tensión: evidencia
recopilada desde sistema comprometido puede estar contaminada.

**OQ-3:** ¿El endpoint receptor es SaaS gestionado por el equipo aRGus
o on-premise del hospital? Implicaciones GDPR: los logs pueden contener
IPs de pacientes.

**OQ-4:** ¿RandomForest embedded como fallback de Tipo B es suficiente
para un hospital, o debe existir SLA máximo de restauración de plugin?

**OQ-5:** ¿La promoción automática del standby antes del poweroff es
siempre deseable? ¿Puede el standby también estar comprometido?

---

## Estado

**PRE-DISEÑO — pendiente revisión Consejo DAY 136.**
No hay código implementado. Solo arquitectura y deudas documentadas.
`DEBT-IRP-A-001` (`argus-irp-notify`) es la más urgente — puede añadirse
a `argus-apt-integrity.service` en pocas horas sin riesgo arquitectónico.

---

*DAY 135 — 29 Abril 2026*
*"El sistema nunca muere en silencio. Grita, documenta, y cae con dignidad."*
