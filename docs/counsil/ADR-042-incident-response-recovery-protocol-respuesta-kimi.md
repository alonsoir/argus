## Kimi — Revisión Adversarial — ADR-042

*Evaluación crítica bajo criterios de operabilidad 24/7 en hospitales, GDPR sanitario, y resistencia a adversarios sofisticados. Se identifican 7 fallos graves, 3 tensiones no resueltas, y 4 alternativas industriales.*

---

## Fallos Críticos Identificados

### F1 — `FailureAction=poweroff` sin confirmación de standby: disponibilidad cero

**Problema:** El ADR asume que existe un nodo standby para promover. En un hospital con un único sensor aRGus (presupuesto 150€), el poweroff deja la red sin protección **indefinidamente**. El principio P4 ("El hospital no queda indefenso") es violado por la Capa 2.

**Impacto:** Un falso positivo en `argus-apt-integrity-check` (por ejemplo, una actualización legítima de Debian que modifica `sources.list` durante el apt daily) convierte un evento de mantenimiento en una caída de seguridad.

**Alternativa industrial:** **Modo degrado controlado** en lugar de poweroff inmediato. Ejemplo: Wazuh (OSSEC) en modo "active response" desactiva la interfaz de red (`ip link set down`) pero mantiene el sistema encendido para forense local. Suricata en modo "fail-open" deja pasar el tráfico sin inspección pero sin caída.

**Recomendación:** Reemplazar `FailureAction=poweroff` por una jerarquía:

```bash
# Nivel 1: Aislamiento de red (siempre reversible)
ip link set eth0 down
ip link set eth1 down

# Nivel 2: Si hay standby confirmado vía heartbeat (3s timeout)
if argus-standby-ping --timeout=3; then
    systemctl poweroff
else
    # Nivel 3: Modo degrado — sniffer continúa, ZeroMQ detenido
    systemctl stop argus-etcd-server
    systemctl stop argus-rag-ingester
    # El sniffer y firewall continúan con últimas reglas conocidas
    logger -p auth.crit "ARGUS IRP-A: STANDALONE MODE — network isolated, local protection active"
fi
```

---

### F2 — Webhook best-effort: evidencia no garantizada

**Problema:** El webhook con `curl --max-time 5` y `|| true` es "best-effort" que en la práctica significa "probablemente falla silenciosamente". En un ataque real, el adversario:
1. Compromete apt sources
2. Bloquea tráfico saliente a `irp.argus-ndr.org`
3. El webhook falla
4. El nodo se apaga
5. **Nadie sabe que el nodo se apagó ni por qué**

El principio P1 ("El sistema nunca muere en silencio") es violado por la implementación.

**Alternativa industrial:** **Store-and-forward con ACK criptográfico.** Ejemplo: systemd-journal-remote con buffer persistente en disco. Si el webhook falla, los logs se encolan en `/var/lib/argus/irp-queue/` y se reintentan en el próximo arranque (si el nodo se restaura limpio).

**Recomendación:**

```bash
# argus-irp-notify — store-and-forward con ACK
NOTIFY_DIR="/var/lib/argus/irp-queue"
mkdir -p "$NOTIFY_DIR"
chmod 0700 "$NOTIFY_DIR"

# Generar payload
PAYLOAD=$(cat <<EOF
{"incident":"IRP-A","node":"$(hostname)","timestamp":"$(date -u -Iseconds)",
 "severity":"CRITICAL","evidence_hash":"${EVIDENCE_HASH}"}
EOF
)

# Firmar payload
echo "$PAYLOAD" | openssl pkeyutl -sign -inkey /etc/ml-defender/node_key.sk > "$NOTIFY_DIR/$(date +%s).sig"

# Intentar envío
if curl --max-time 5 --silent --fail -X POST "$ARGUS_ALERT_WEBHOOK" \
   -H "Content-Type: application/json" -d "$PAYLOAD"; then
    # ACK recibido: marcar como enviado
    touch "$NOTIFY_DIR/$(date +%s).ack"
else
    # Fallo: payload firmado queda en cola para reintento post-recuperación
    logger -p auth.crit "ARGUS IRP-A: webhook failed, evidence queued for retry"
fi
```

---

### F3 — `argus-forensic-collect` en sistema comprometido: evidencia contaminada

**Problema:** La Capa 3 propone ejecutar `argus-forensic-collect` en el sistema comprometido. Si el atacante ha modificado `/etc/apt/sources.list`, también podría haber modificado:
- `/usr/local/bin/argus-forensic-collect` (binario reemplazado)
- `sha256sum` (binario troyanizado que miente sobre hashes)
- `journalctl` (filtra logs del atacante)
- El kernel mismo (rootkit)

**Alternativa industrial:** **Trusted Platform Module (TPM) + Remote Attestation.** Ejemplo: Microsoft Azure Attestation, AWS Nitro Enclaves. El hardware certifica el estado del sistema antes de que el software pueda mentir.

**Recomendación:** Dividir la recolección de evidencia en dos niveles:

| Nivel | Fuente | Confianza | Método |
|-------|--------|-----------|--------|
| **Nivel 1 (hardware)** | TPM PCR registers, UEFI logs | Alta (si TPM no comprometido) | `tpm2_quote` antes del boot del OS |
| **Nivel 2 (offline)** | Disco montado desde live USB / PXE boot | Media (si el disco no está cifrado) | `argus-forensic-collect` desde entorno limpio |
| **Nivel 3 (runtime)** | Logs en memoria antes de que el atacante los borre | Baja | `dmesg`, `/proc/*/fd/`, capturas de red en RAM |

El ADR actual solo menciona Nivel 3. Debe documentar explícitamente que la evidencia recopilada desde sistema comprometido tiene **cadena de custodia débil** y requiere correlación con fuentes externas (Falco en otro nodo, logs de switch).

---

### F4 — RandomForest embedded como fallback: degradación no cuantificada

**Problema:** El ADR asume que descargar un plugin XGBoost y volver a RandomForest embedded es "restauración sin downtime". No se cuantifica:
- ¿Cuál es el F1 de RF embedded vs XGBoost en el golden set?
- ¿Cuánto aumenta la latencia de inferencia?
- ¿El firewall-acl-agent sigue recibiendo decisiones en tiempo real?

Si RF embedded tiene F1=0.85 (vs 0.9985 de XGBoost), el "fallback" es en realidad una **degradación masiva** que el hospital no notaría hasta que ocurra un ataque.

**Alternativa industrial:** **Graceful degradation con métricas expuestas.** Ejemplo: Kubernetes HPA (Horizontal Pod Autoscaler) expone métricas de capacidad. Si un pod falla, el tráfico se redirige pero el admin ve inmediatamente que la capacidad está degradada.

**Recomendación:** Exponer métricas de calidad del fallback:

```protobuf
// En el mensaje de status del pipeline
message PipelineStatus {
    bool healthy = 1;
    string active_detector = 2;  // "xgboost_v2.1" o "randomforest_embedded_fallback"
    float active_f1_estimate = 3;  // F1 del detector activo (del golden set)
    uint64 inference_latency_p99_us = 4;
    bool fallback_active = 5;
}
```

El admin debe ver: `⚠️ FALLBACK ACTIVE — F1 degraded from 0.9985 to 0.9200 — investigate immediately`

---

### F5 — GDPR: logs con IPs de pacientes en endpoint externo

**Problema:** OQ-3 identifica la tensión pero no la resuelve. Los logs de red de un hospital contienen:
- IPs de estaciones de trabajo médicas (mapeables a departamentos)
- Timestamps de acceso a sistemas de historiales (inferencia de actividad clínica)
- Metadatos DNS (qué servidores externos consulta el hospital)

Enviar esto a `irp.argus-ndr.org` sin anonimización es una **violación de GDPR art. 9** (datos de salud) y puede incurrir en sanciones de hasta 4% del volumen de negocio.

**Alternativa industrial:** **Anonimización diferencial + on-premise SIEM.** Ejemplo: Splunk Phantom en hospital local, no en cloud. Datos anonimizados (hash de IP, rangos de tiempo agregados) para análisis externo.

**Recomendación:** El endpoint receptor debe ser **on-premise del hospital**, no SaaS de aRGus. El protocolo IRP debe incluir un paso de sanitización:

```python
# argus-irp-sanitize — ejecutado antes de cualquier envío externo
def sanitize_log(line: str) -> str:
    # Reemplazar IPs internas por hashes irreversibles
    line = re.sub(r'\b10\.\d+\.\d+\.\d+\b', lambda m: f"IP-{hashlib.sha256(m.group().encode()).hexdigest()[:8]}", line)
    # Agregar timestamps a ventanas de 5 minutos
    line = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', lambda m: f"{m.group()[:15]}00:00", line)
    return line
```

**Regla:** Ningún dato que salga del perímetro del hospital debe ser reversible a identidad de paciente o patrón clínico.

---

### F6 — `make safe-mode` como target de Makefile: dependencia circular

**Problema:** `make safe-mode` requiere un sistema operativo funcional con `make` instalado. Si el OS está comprometido, `make` podría estar troyanizado. Si el nodo está apagado, `make` no ejecuta.

El ADR no especifica **dónde** se ejecuta `make safe-mode`:
- ¿En el nodo comprometido? (F3: evidencia contaminada)
- ¿En un live USB? (No mencionado)
- ¿En el host de desarrollo conectando el disco del nodo? (No mencionado)

**Alternativa industrial:** **PXE boot + initramfs forense.** Ejemplo: GRML (Debian-based live system) en PXE. El nodo arranca por red en un entorno limpio, recolecta evidencia del disco local, y la envía.

**Recomendación:** Documentar tres modos de safe-mode con prerequisitos claros:

| Modo | Prerequisito | Comando | Confianza evidencia |
|------|-------------|---------|---------------------|
| **Modo A (runtime)** | OS parcialmente funcional, `argus-forensic-collect` no modificado | `systemctl start argus-safe-mode` | Baja |
| **Modo B (live USB)** | USB con GRML/Debian Live preparado previamente | Boot desde USB, `argus-forensic-collect /dev/sda1` | Media |
| **Modo C (PXE)** | Servidor PXE en red hospitalaria | Boot por red, recolecta y envía | Alta |

---

### F7 — Nodo standby auto-promote: problema del "standby comprometido"

**Problema:** OQ-5 identifica la tensión pero no la resuelve. Si el atacante compromete la flota a través de etcd (vector de ataque común en sistemas distribuidos), el standby también puede estar comprometido. Promoverlo antes de investigar amplifica el compromiso.

**Alternativa industrial:** **Quorum de decisión antes de failover.** Ejemplo: Consul serf + raft. El failover solo ocurre si N/2+1 nodos sanos lo confirman.

**Recomendación:** Para la versión actual (federación post-FEDER), el standby NO debe auto-promoverse. El protocolo debe ser:

```bash
# argus-standby-check — ejecutado antes de cualquier poweroff
if argus-standby-ping --timeout=3; then
    # Standby responde: enviar alerta pero NO auto-promover
    # El admin debe verificar manualmente que el standby no está comprometido
    logger -p auth.crit "ARGUS IRP-A: STANDBY DETECTED — manual promotion required"
    # El nodo se aísla pero NO se apaga, dando tiempo al admin
    ip link set eth0 down
    ip link set eth1 down
    # Loop infinito de alerta hasta intervención manual
    while true; do
        argus-irp-notify --priority=CRITICAL
        sleep 60
    done
else
    # No hay standby: modo degrado (F1)
    logger -p auth.crit "ARGUS IRP-A: NO STANDBY — entering standalone protection mode"
fi
```

---

## Tensiones No Resueltas

### T1 — Best-effort vs síncrono (OQ-1)

El ADR propone 5s de timeout. Mi posición: **0s de timeout, store-and-forward obligatorio.** Si el webhook es crítico para P1, no puede ser best-effort. Si no es crítico, no debe existir. La solución de cola persistente (F2) resuelve esta tensión.

### T2 — Recolección en sistema comprometido vs offline (OQ-2)

Mi posición: **Ambos, con etiquetas de confianza.** La evidencia de runtime es válida como "indicador temprano", la de offline como "evidencia forense". Deben correlacionarse, no sustituirse.

### T3 — SaaS vs on-premise (OQ-3)

Mi posición: **On-premise obligatorio para hospitales.** El endpoint `irp.argus-ndr.org` debe ser un **software desplegable** (Docker container, .deb) que el hospital instala en su propia infraestructura. aRGus puede ofrecer hosting gestionado como opción, pero no como default.

---

## Alternativas Industriales para Cada Componente

| Componente ADR-042 | Alternativa A (enterprise) | Alternativa B (open source) | Recomendación aRGus |
|-------------------|---------------------------|----------------------------|---------------------|
| Notificación | PagerDuty / Opsgenie | Prometheus Alertmanager + webhook | Alertmanager on-premise |
| Forensics | CrowdStrike Falcon | Velociraptor + OSQuery | Velociraptor agente ligero |
| Safe mode | Dell iDRAC virtual media | GRML PXE boot | GRML + script aRGus |
| Evidence storage | Splunk Cloud | ELK stack local | MinIO S3-compatible local |
| Failover | F5 BIG-IP | Keepalived + VRRP | Keepalived (post-FEDER) |

---

## Deudas Corregidas

| ID ADR-042 original | Problema | Corrección | Nueva ID |
|---------------------|----------|------------|----------|
| DEBT-IRP-A-001 | Webhook best-effort | Store-and-forward con ACK criptográfico | DEBT-IRP-A-001-REV |
| DEBT-IRP-A-002 | Forensic en sistema comprometido | Tres niveles de recolección con confianza etiquetada | DEBT-IRP-A-002-REV |
| DEBT-IRP-A-003 | Endpoint SaaS | Endpoint on-premise obligatorio, SaaS opcional | DEBT-IRP-A-003-REV |
| DEBT-IRP-B-001 | Fallback sin métricas | Exposición de F1 degradado en status | DEBT-IRP-B-001-REV |
| *Nueva* | Poweroff sin standby | Modo degrado controlado + aislamiento de red | DEBT-IRP-A-004 |

---

## Veredicto Global

**ADR-042 es arquitectónicamente necesario pero técnicamente inmaduro para producción hospitalaria.** Los principios P1-P5 son correctos, pero la implementación propuesta tiene 7 fallos graves que la hacen inoperable en un entorno real:

1. **Disponibilidad cero** (F1) — poweroff sin standby es inaceptable
2. **Silencio probable** (F2) — webhook best-effort no garantiza notificación
3. **Evidencia no forense** (F3) — recolección en sistema comprometido es contaminada
4. **Degradación oculta** (F4) — fallback sin métricas expuestas
5. **Violación GDPR** (F5) — envío de datos sanitarios a SaaS externo
6. **Dependencia circular** (F6) — `make safe-mode` requiere OS funcional
7. **Amplificación de compromiso** (F7) — auto-promote sin verificación

**Recomendación:** Aprobar el ADR como **visión estratégica**, pero rechazar la implementación propuesta. Crear una rama `feature/adr042-irp` con los componentes corregidos, comenzando por DEBT-IRP-A-004 (modo degrado) y DEBT-IRP-A-001-REV (store-and-forward). No mergear a `main` hasta que al menos F1, F2 y F5 estén resueltos.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*