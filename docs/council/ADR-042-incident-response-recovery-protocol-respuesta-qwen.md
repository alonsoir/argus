# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADVERSARIAL ADR-042
*Análisis científico, basado en evidencia, con enfoque en reproducibilidad y viabilidad industrial para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**CONCEPTO ARQUITECTÓNICO SÓLIDO, PERO CON 7 BRECHAS CRÍTICAS QUE IMPIDEN IMPLEMENTACIÓN DIRECTA EN PRODUCCIÓN.**

El ADR-042 identifica correctamente el patrón común entre incidentes de integridad y disponibilidad, y sus principios (P1-P5) son fundamentales para cualquier sistema de seguridad crítica. Sin embargo, **la arquitectura propuesta contiene suposiciones no verificadas que, en producción, podrían convertir un incidente manejable en una catástrofe operacional**.

> *"Un protocolo de respuesta a incidentes no probado es un plan de evacuación dibujado en servilleta."*

---

## 🔍 Análisis de Fortalezas (lo que está bien diseñado)

| Fortaleza | Por qué es sólida | Evidencia/Referencia |
|-----------|------------------|---------------------|
| **Principios P1-P5** | Alineados con NIST SP 800-61 (IR lifecycle) y SANS IR framework | Estándar industria para IR en infraestructura crítica |
| **Three-layer architecture** (Detect → Act → Recover) | Patrón probado en SIEM/SOAR comerciales (Splunk ES, IBM QRadar) | Separación de preocupaciones reduce acoplamiento y facilita testing |
| **Best-effort webhook + no bloquear poweroff** | Reconoce realidad de redes comprometidas sin sacrificar acción defensiva | Patrón "fire-and-forget with local persistence" usado en AWS GuardDuty, Azure Sentinel |
| **Ed25519 signing de evidencia forense** | Mantiene cadena de custodia para auditoría legal/regulatoria | Requisito GDPR Art. 32, HIPAA §164.312(b) para integridad de logs |
| **Fallback a RandomForest embedded** | Defensa en profundidad: degradación controlada vs fallo total | Patrón "circuit breaker + fallback" de Martin Fowler, aplicado a seguridad |
| **Debt tracking explícito con prioridades** | Permite iteración incremental sin perder visión arquitectónica | Práctica estándar en proyectos de seguridad (OpenSSF, CNCF) |

---

## ⚠️ Brechas Críticas (lo que debe corregirse antes de implementar)

### Brecha 1: Recolección forense desde sistema potencialmente comprometido (OQ-2)

**Problema fundamental**:
> *"Collecting evidence from a compromised OS is like asking a suspect to write their own alibi."*

Si el atacante tiene control del kernel o del filesystem, puede:
- Modificar `argus-forensic-collect` para omitir evidencia incriminatoria
- Alterar hashes pre-firma
- Intercepter la firma Ed25519 si la clave está en el mismo sistema

**Alternativas industriales viables (ordenadas por viabilidad para aRGus)**:

| Opción | Descripción | Viabilidad aRGus (~150€ HW) | Referencia industrial |
|--------|-------------|----------------------------|---------------------|
| **A) TPM 2.0 + Measured Boot** | Attestación remota: el nodo prueba su estado de boot antes de recolectar | ✅ Alta (TPM en RPi 4/5 + x86 commodity) | Microsoft Defender for IoT, Google Titan M |
| **B) Out-of-band collection** | Recolección vía IPMI/iDRAC o red de gestión aislada | ⚠️ Media (requiere hardware con OOB) | Cisco Secure Network Analytics, Palo Alto Cortex XDR |
| **C) Integrity-checked collection** | Hash cada archivo pre-colección + verificación en receptor + logging de discrepancias | ✅ Alta (software-only) | OSSEC, Wazuh forensics module |
| **D) Accept & document limitation** | Reconocer limitación pero añadir salvaguardas: firma de manifiesto, verificación cruzada con logs externos | ✅ Alta | NIST SP 800-61 Rev. 2 §3.3.2: "Evidence from compromised systems has reduced trust" |

**Recomendación para aRGus**: **Opción C + D híbrida** (software-only, viable hoy):
```bash
# argus-forensic-collect — pseudocode con integridad verificable
collect_evidence() {
    local manifest="forensic-manifest.json"
    echo "{" > $manifest
    
    for file in /etc/apt/sources.list /usr/bin/argus-* /var/log/falco/*; do
        if [ -f "$file" ]; then
            local hash=$(sha256sum "$file" | cut -d' ' -f1)
            local size=$(stat -c%s "$file")
            echo "  \"$file\": {\"sha256\": \"$hash\", \"size\": $size}," >> $manifest
            # Copiar archivo para envío (opcional, puede omitirse si solo hash)
        fi
    done
    
    # Firmar manifiesto con clave del nodo (en memoria protegida si es posible)
    sign_manifest "$manifest" "/etc/ml-defender/forensic-signing.sk"
    
    # Enviar manifiesto firmado (no requiere enviar todos los archivos)
    curl -X POST "$FORENSIC_ENDPOINT" -d "@${manifest}.sig" || \
        echo "⚠️  Forensic manifest pending local delivery" >> /var/log/argus/pending-forensics.log
}
```

**Test de demostración requerido**:
```bash
# tests/test_irp_forensic_integrity.sh
# Escenario: sistema comprometido intenta falsificar evidencia
make test-irp-forensic-tamper
# 1. Modificar un archivo de log post-compromiso simulado
# 2. Ejecutar argus-forensic-collect
# 3. Verificar: hash en manifiesto NO coincide con archivo modificado
# 4. Verificar: receptor rechaza evidencia con hash mismatch
# 5. Verificar: alerta de "forensic integrity violation" generada
```

---

### Brecha 2: Webhook best-effort puede silenciar alertas críticas (OQ-1)

**Problema**: `|| true` significa que fallos de red = alertas perdidas. En seguridad, "silencio" es indistinguible de "todo bien".

**Alternativa industrial**: **Persistent local queue + retry + explicit delivery status**
```bash
# argus-irp-notify — diseño con garantía de entrega eventual
notify_incident() {
    local alert=$(build_alert_json "$@")
    local queue="/var/log/argus/pending-alerts.jsonl"
    
    # Intento síncrono con timeout corto (no bloquear poweroff)
    if curl --max-time 5 --silent -X POST "$WEBHOOK" -d "$alert" 2>/dev/null; then
        logger "✅ Alert delivered"
        return 0
    fi
    
    # Fallback: enqueue localmente con timestamp y retry count
    echo "{\"alert\":$alert,\"queued_at\":\"$(date -u +%s)\",\"retry\":0}" >> "$queue"
    logger "⚠️  Alert queued locally for retry"
    
    # Disparar background retry (no bloquear)
    (retry_pending_alerts "$queue" "$WEBHOOK") &
    return 0  # No bloquear poweroff
}

retry_pending_alerts() {
    local queue="$1" webhook="$2"
    while [ -s "$queue" ]; do
        # Procesar primer elemento
        local entry=$(head -1 "$queue")
        local retry=$(echo "$entry" | jq -r .retry)
        
        if [ "$retry" -ge 5 ]; then
            # Máximo intentos: mover a dead-letter
            echo "$entry" >> "${queue}.dlq"
            sed -i '1d' "$queue"
            continue
        fi
        
        # Intentar envío
        if curl --max-time 10 -X POST "$webhook" -d "$(echo "$entry" | jq -r .alert)"; then
            sed -i '1d' "$queue"  # Éxito: remover de cola
        else
            # Reintentar con backoff exponencial
            local new_retry=$((retry + 1))
            local new_entry=$(echo "$entry" | jq ".retry = $new_retry")
            sed -i "1s|.*|$new_entry|" "$queue"
            sleep $((2 ** new_retry))
        fi
    done
}
```

**Test de demostración**:
```bash
# tests/test_irp_alert_delivery.sh
make test-irp-alert-reliability
# 1. Simular webhook caído (nc -l 9999 que no responde)
# 2. Disparar argus-irp-notify
# 3. Verificar: alerta en pending-alerts.jsonl
# 4. Restaurar webhook, esperar retry
# 5. Verificar: alerta entregada, cola vacía
# 6. Verificar: forensic report incluye "alerts_delivered=1, alerts_pending=0"
```

---

### Brecha 3: GDPR/Protección de datos en evidencia forense (OQ-3)

**Problema**: Logs de red pueden contener IPs de pacientes, timestamps de procedimientos médicos, patrones de tráfico que revelan diagnósticos. Enviar esto a `irp.argus-ndr.org` sin salvaguardas viola GDPR Art. 5(1)(c) (minimización de datos).

**Alternativa industrial**: **On-premise by default + PII redaction + configurable retention**
```yaml
# /etc/argus/irp-config.yaml (ejemplo)
forensic:
  receiver:
    default: "on-premise"  # o "saas" con DPA firmado
    saas_endpoint: "https://irp.argus-ndr.org/incidents"  # solo si DPA activo
  pii_redaction:
    enabled: true
    rules:
      - field: "src_ip"
        action: "hash_sha256"  # irreversible
      - field: "payload"
        action: "truncate_128b"  # solo headers
      - field: "timestamp"
        action: "round_to_5min"  # reducir precisión temporal
  retention:
    local_days: 90
    remote_days: 30  # si se envía a SaaS
```

**Implementación en collector**:
```python
# argus-forensic-collect — redacción PII
def redact_pii(log_entry: dict, config: dict) -> dict:
    if not config['pii_redaction']['enabled']:
        return log_entry
    
    for rule in config['pii_redaction']['rules']:
        if rule['field'] in log_entry:
            if rule['action'] == 'hash_sha256':
                log_entry[rule['field']] = hashlib.sha256(
                    log_entry[rule['field']].encode()
                ).hexdigest()[:16]  # truncar hash para legibilidad
            elif rule['action'] == 'truncate_128b':
                log_entry[rule['field']] = log_entry[rule['field']][:128] + "..."
            elif rule['action'] == 'round_to_5min':
                ts = datetime.fromisoformat(log_entry[rule['field']])
                log_entry[rule['field']] = ts.replace(
                    minute=(ts.minute // 5) * 5, second=0, microsecond=0
                ).isoformat()
    return log_entry
```

**Test de demostración**:
```bash
# tests/test_irp_gdpr_compliance.sh
make test-irp-pii-redaction
# 1. Generar log con IP de paciente (ej: 192.168.1.100)
# 2. Ejecutar argus-forensic-collect con redacción activada
# 3. Verificar: IP original NO aparece en evidencia enviada
# 4. Verificar: hash de IP SÍ aparece (para correlación interna)
# 5. Verificar: config permite desactivar redacción solo con flag explícito + warning
```

---

### Brecha 4: Fallback a RandomForest puede degradar protección por debajo de SLA (OQ-4)

**Problema**: Si XGBoost se eligió por F1=0.9985 vs RF=0.9968, el fallback podría dejar al hospital con detección insuficiente para amenazas modernas.

**Alternativa industrial**: **Metric-gated fallback + escalation policy**
```yaml
# /etc/argus/fallback-policy.yaml
fallback:
  target_model: "randomforest_embedded"
  minimum_metrics:
    f1: 0.9950  # umbral mínimo aceptable
    recall: 0.9900  # crítico: falsos negativos
    latency_p99_ms: 10  # no degradar throughput
  escalation:
    if_metrics_below_threshold: "trigger_irp_type_a"  # aislar nodo
    manual_override_available: true
    notification_channels: ["webhook", "email", "sms"]
```

**Implementación en plugin-loader**:
```cpp
// plugin_loader.cpp — verificación de métricas de fallback
bool validate_fallback_metrics(const ModelMetrics& metrics, const FallbackPolicy& policy) {
    if (metrics.f1 < policy.minimum_metrics.f1) {
        log_critical("Fallback F1 %.4f < threshold %.4f", metrics.f1, policy.minimum_metrics.f1);
        return false;
    }
    if (metrics.recall < policy.minimum_metrics.recall) {
        log_critical("Fallback Recall %.4f < threshold %.4f", metrics.recall, policy.minimum_metrics.recall);
        return false;
    }
    if (metrics.latency_p99_ms > policy.minimum_metrics.latency_p99_ms) {
        log_warning("Fallback latency %.2fms > threshold %.2fms", 
                   metrics.latency_p99_ms, policy.minimum_metrics.latency_p99_ms);
        // Warning pero no fallo: latencia es degradación, no fallo de seguridad
    }
    return true;
}

// Si fallback no cumple métricas → escalar a IRP Tipo A
if (!validate_fallback_metrics(rf_metrics, policy)) {
    log_critical("Fallback inadequate — triggering IRP-Type-A isolation");
    trigger_isolation_protocol();  // eBPF/XDP: drop all non-management traffic
    // No unload plugin defectuoso aún: mantenerlo para forensics
}
```

**Test de demostración**:
```bash
# tests/test_irp_fallback_metrics.sh
make test-irp-fallback-gate
# 1. Configurar fallback con métricas artificiales por debajo de umbral
# 2. Simular fallo de plugin XGBoost
# 3. Verificar: fallback NO se activa, se dispara IRP-Type-A
# 4. Verificar: nodo aislado (tráfico bloqueado excepto gestión)
# 5. Verificar: alerta de "fallback inadequate" enviada
```

---

### Brecha 5: Promoción automática de standby puede propagar compromiso (OQ-5)

**Problema**: Si el ataque es supply-chain (ej: paquete apt comprometido), el standby probablemente tiene la misma vulnerabilidad. Promoverlo automáticamente amplifica el incidente.

**Alternativa industrial**: **Attestation-required promotion + manual override**
```yaml
# /etc/argus/ha-policy.yaml
standby_promotion:
  auto_promote: true  # default para disponibilidad
  pre_promotion_checks:
    - argus_apt_integrity_check  # debe pasar
    - argus_plugin_signature_verify  # todos los plugins firmados válidos
    - falco_no_critical_alerts_24h  # sin alertas críticas recientes
  manual_override:
    enabled: true
    require_2_of_3_admins: true  # cuórum para forzar promoción
  fallback_if_checks_fail: "alert_admin_no_promotion"
```

**Implementación en orchestrator**:
```bash
# argus-standby-promote — verificación pre-promoción
pre_promotion_checks() {
    local node="$1"
    
    # Check 1: apt integrity
    if ! ssh "$node" argus-apt-integrity-check --quiet; then
        log_error "Standby $node failed apt integrity check"
        return 1
    fi
    
    # Check 2: plugin signatures
    if ! ssh "$node" argus-verify-all-plugins --quiet; then
        log_error "Standby $node has invalid plugin signatures"
        return 1
    fi
    
    # Check 3: recent alerts
    local recent_alerts=$(ssh "$node" journalctl -u falco --since "24h ago" \
        | grep -c "CRITICAL\|ARGUS_")
    if [ "$recent_alerts" -gt 0 ]; then
        log_warning "Standby $node has $recent_alerts critical alerts in 24h"
        # No fallar, pero requerir confirmación manual
        return 2  # código especial: "needs manual approval"
    fi
    
    return 0
}

promote_standby() {
    local node="$1"
    local check_result=$(pre_promotion_checks "$node")
    
    case "$check_result" in
        0) 
            log_info "Standby $node passed all checks — promoting"
            execute_promotion "$node"
            ;;
        1)
            log_error "Standby $node failed critical checks — promotion aborted"
            alert_admins "Standby promotion aborted: integrity failure on $node"
            ;;
        2)
            log_warning "Standby $node requires manual approval for promotion"
            request_manual_approval "$node"  # notifica a admins, espera confirmación
            ;;
    esac
}
```

**Test de demostración**:
```bash
# tests/test_irp_standby_promotion.sh
make test-irp-standby-safety
# 1. Configurar standby con apt sources comprometidos
# 2. Simular fallo en primario
# 3. Verificar: promoción automática ABORTADA
# 4. Verificar: alerta de "standby integrity failure" enviada
# 5. Verificar: sistema entra en modo degradado (no promoción, no fallo total)
```

---

### Brecha 6: Falta estrategia de testing del protocolo IRP

**Problema**: Un protocolo de respuesta a incidentes no probado es una promesa sin firma. ¿Cómo sabemos que `argus-irp-notify` funciona cuando más se necesita?

**Alternativa industrial**: **Chaos engineering + automated IRP drills**
```makefile
# Makefile — targets de testing IRP
.PHONY: test-irp-type-a test-irp-type-b test-irp-drill

test-irp-type-a:
	@echo "🔥 Simulating IRP-Type-A: apt source compromise"
	@./scripts/chaos/tamper-apt-sources.sh
	@./scripts/chaos/trigger-apt-check.sh
	@./scripts/verify/irp-type-a-outcome.sh  # verifica: alert sent, poweroff, forensic collected
	@echo "✅ IRP-Type-A test passed"

test-irp-type-b:
	@echo "🔥 Simulating IRP-Type-B: malicious plugin"
	@./scripts/chaos/deploy-malformed-plugin.sh
	@./scripts/chaos/trigger-falco-alert.sh
	@./scripts/verify/irp-type-b-outcome.sh  # verifica: plugin unloaded, fallback active, metrics OK
	@echo "✅ IRP-Type-B test passed"

test-irp-drill: test-irp-type-a test-irp-type-b
	@echo "✅ Full IRP drill completed"
```

**Referencia industrial**:
- Netflix Chaos Monkey para resiliencia
- AWS Fault Injection Simulator para incident response testing
- NIST SP 800-61 Rev. 2 §4.2: "Organizations should test IR plans at least annually"

**Test de demostración mínimo**:
```bash
# tests/test_irp_end_to_end.sh
make test-irp-full-drill
# 1. Desplegar entorno de test aislado
# 2. Ejecutar escenario Tipo A + Tipo B en secuencia
# 3. Verificar: cada capa (detect→act→recover) funciona como esperado
# 4. Verificar: evidencia forense es recuperable y verificable
# 5. Verificar: métricas de fallback cumplen SLA o escalan correctamente
```

---

### Brecha 7: Recuperación sin verificación de limpieza

**Problema**: Después de un poweroff por compromiso, ¿cómo sabemos que el nodo está limpio antes de reintegrarlo a la flota?

**Alternativa industrial**: **Post-recovery attestation + quarantine period**
```yaml
# /etc/argus/recovery-policy.yaml
recovery:
  post_poweroff:
    require_clean_integrity_scan: true
    quarantine_hours: 24  # monitoreo reforzado antes de reintegración
    rejoin_conditions:
      - apt_integrity_check_passed: true
      - plugin_signatures_valid: true
      - falco_zero_critical_alerts_24h: true
      - manual_approval: true  # siempre requerido post-IRP-Type-A
  automatic_rejoin: false  # nunca automático post-compromiso
```

**Implementación en boot sequence**:
```bash
# /usr/local/bin/argus-post-recovery-check
post_recovery_validation() {
    echo "🔍 Validating node integrity post-recovery..."
    
    # Check 1: apt sources
    if ! /usr/local/bin/argus-apt-integrity-check --quiet; then
        log_error "Post-recovery: apt integrity still compromised"
        return 1
    fi
    
    # Check 2: plugin signatures
    if ! argus-verify-all-plugins --quiet; then
        log_error "Post-recovery: invalid plugin signatures detected"
        return 1
    fi
    
    # Check 3: baseline file hashes
    if ! verify_baseline_hashes "/var/lib/argus/baseline-manifest.json"; then
        log_error "Post-recovery: file hash mismatch vs baseline"
        return 1
    fi
    
    echo "✅ Post-recovery validation passed — node eligible for quarantine monitoring"
    return 0
}

# En systemd unit de arranque normal (no safe-mode)
[Service]
ExecStartPre=/usr/local/bin/argus-post-recovery-check
# Si falla, el servicio no arranca → nodo permanece en "quarantine mode"
```

**Test de demostración**:
```bash
# tests/test_irp_recovery_verification.sh
make test-irp-post-recovery
# 1. Simular poweroff por compromiso
# 2. "Reparar" sistema (simular limpieza)
# 3. Reiniciar nodo
# 4. Verificar: post-recovery check se ejecuta y pasa/falla según estado
# 5. Verificar: nodo no se reintegra a flota hasta validación + aprobación manual
```

---

## 📋 Checklist de Refinamientos Obligatorios (pre-implementación)

```markdown
- [ ] Implementar integrity-checked forensic collection (Opción C+D) + test de tampering
- [ ] Añadir persistent queue para alertas + retry logic + delivery status en forensics
- [ ] Implementar PII redaction configurable + on-premise receiver default
- [ ] Definir metric-gated fallback policy + escalation a IRP-Type-A si umbrales no se cumplen
- [ ] Implementar attestation-required standby promotion + manual override
- [ ] Crear suite de testing IRP: chaos engineering + automated drills
- [ ] Implementar post-recovery validation + quarantine period antes de reintegración
- [ ] Documentar limitaciones residuales en `docs/IRP-LIMITATIONS.md`
```

---

## 🏁 Palabras Finales

Alonso:

El ADR-042 tiene el mérito de abordar uno de los problemas más difíciles en ciberseguridad: **cómo responder a incidentes sin empeorarlos**. Sus principios son sólidos, su arquitectura es coherente, y su enfoque en forensics-first es exactamente lo que requiere un sistema para infraestructura crítica.

Pero la seguridad no se construye con buenas intenciones. Se construye con **verificación explícita, salvaguardas contra fallos de suposiciones, y testing riguroso de los mecanismos de defensa**.

Las siete brechas identificadas no son fallos de diseño; son **oportunidades para elevar el protocolo de "bien pensado" a "probado y confiable"**. Cada una tiene alternativas industriales viables, adaptadas al contexto de presupuesto y complejidad de aRGus.

> *"Un escudo que no se prueba contra el ataque real es un escudo de teatro. Un protocolo de respuesta que no se prueba contra el fallo real es un plan de evacuación en servilleta."*

Recomendamos: **aprobar el concepto arquitectónico, pero condicionar cualquier implementación de código a la resolución de las siete brechas críticas**. Empezar por `DEBT-IRP-A-001` (webhook con queue persistente) es un primer paso de bajo riesgo y alto valor.

Proceded con los refinamientos. El Consejo revisará los primeros tests de demostración IRP con el mismo rigor adversarial con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 136** 🏛️