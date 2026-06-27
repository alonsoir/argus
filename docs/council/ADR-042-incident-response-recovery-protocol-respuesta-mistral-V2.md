### **Análisis del Consejo de Sabios — ADR-042 v2**
*(Unánime 8/8, basado en **principios de seguridad operacional**, **evidencia reproducible** y **protección de infraestructuras críticas**)*

---

## **Puntos Fuertes (Mejoras respecto a v1)**
*(Lo que ahora está alineado con estándares industriales y es implementable)*

### **1. Arquitectura en Capas Claras**
✅ **Separación explícita entre detección, acción y recuperación** (Capa 1/2/3) sigue el **NIST SP 800-61 Rev. 2** (Incident Handling Lifecycle).
- **Capa 1 (Detección + Grito):**
    - **Múltiples canales** (syslog + webhook + cola persistente) mitiga el riesgo de silencio.
    - **Store-and-forward** (cola en `/var/lib/argus/irp-queue/`) es mejor práctica (ej: [RSYSLOG](https://www.rsyslog.com/)).
- **Capa 2 (Acción Proporcional):**
    - **Aislamiento de red antes del poweroff** (nuevo en v2) resuelve la "Paradoja del suicidio" (Gemini DAY 135).
    - **Jerarquía clara**: OS comprometido → aislar → forensics → poweroff.
- **Capa 3 (Recuperación):**
    - **initramfs read-only** es el enfoque correcto para forensics (similar a [CAINE](https://www.caine-live.net/)).
    - **Reintegración verificada (P6)** añade una capa crítica de seguridad post-recuperación.

### **2. Aislamiento de Red antes del Poweroff**
✅ **Decisión correcta** (Consenso DAY 135: Gemini/Grok/Kimi/DeepSeek).
- **Código implementado:**
  ```bash
  ip link set eth0 down 2>/dev/null || true
  ip link set eth1 down 2>/dev/null || true
  ```
    - **Mitiga:** Vector de DoS (atacante que modifica `sources.list` para apagar el nodo).
    - **Alternativa industrial:** [Cisco IOS "shutdown"](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/sec_data_zbf/configuration/xe-16-10/sec-data-zbf-xe-16-10-book/sec-zbf-interface.html) (similar en propósito).

### **3. Múltiples Canales de Notificación**
✅ **Best-effort + persistente + syslog remoto** cubre todos los casos:
| **Canal**          | **Ventaja**                          | **Alternativa Industrial**               |
|--------------------|---------------------------------------|------------------------------------------|
| Webhook            | Notificación inmediata               | [PagerDuty](https://www.pagerduty.com/)   |
| Syslog local       | Siempre funciona                     | [Rsyslog](https://www.rsyslog.com/)      |
| Cola persistente  | Sobrevive al poweroff                 | [RabbitMQ](https://www.rabbitmq.com/)    |
| Syslog remoto      | Centralización                       | [ELK Stack](https://www.elastic.co/elk-stack) |

### **4. Safe Mode en initramfs**
✅ **Enfoque correcto** para forensics (Consenso DAY 135: 8/8).
- **Ventajas:**
    - **Read-only:** Evita modificación de evidencia.
    - **Local-only:** Sin ejecución remota (mitiga riesgo de contaminación).
- **Limitación documentada:**
  > *"Cadena de custodia media — mejor que recopilar desde sistema comprometido, pero sin garantía absoluta si el kernel o el disco han sido alterados."*
    - **Mitigación futura:** TPM 2.0 + Secure Boot (DEBT-IRP-FORENSICS-TPM-001).

### **5. Reintegración Verificada (P6)**
✅ **Nuevo en v2 y crítico** (identificado por Qwen/Kimi DAY 135).
- **Proceso:**
    1. `argus-post-recovery-check` (automático en boot).
    2. 24h de monitoreo en quarantine.
    3. Aprobación manual del admin.
- **Alternativa industrial:** [AWS Health Checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks.html) (pero adaptado a NDR).

### **6. GDPR y Endpoint On-Premise**
✅ **Decisión correcta** (Consenso DAY 135: 7/8).
- **Política:**
    - **Producción:** Endpoint on-premise obligatorio.
    - **Demo/Lab:** Endpoint externo con anonimización (PII redaction).
- **Implementación propuesta:**
  ```python
  # Anonimización de IPs antes de enviar a SaaS
  def anonymize_logs(log_data):
      log_data = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED]', log_data)
      return log_data
  ```
- **Alternativa industrial:** [Elasticsearch ILM + GDPR](https://www.elastic.co/guide/en/elasticsearch/reference/current/ilm-index-lifecycle.html).

---

## **Puntos Débiles y Riesgos Residuales**
*(Lo que requiere ajustes o mitigaciones adicionales)*

### **1. Falta de Mecanismo de Consenso para Promoción de Standby**
**Problema:**
- **Código actual:**
  ```bash
  if argus-standby-ping --timeout=3 2>/dev/null; then
      logger "ARGUS IRP-A: standby detected — manual promotion required"
  fi
  ```
    - **Riesgo:** Si el standby también está comprometido, promoverlo **amplifica el ataque**.
- **Solución industrial:** **Quorum de nodos sanos** (ej: [Raft Consensus](https://raft.github.io/)).
    - **Implementación propuesta:**
      ```bash
      # Verificar que al menos 2/3 de la flota están sanos antes de promover
      if argus-quorum-check --min-healthy=2; then
          argus-promote-standby --manual-approval-required
      else
          logger "ARGUS IRP-A: quorum failed — no standby promotion"
      fi
      ```

### **2. Webhook sin Autenticación Mutua (mTLS)**
**Problema:**
- **Código actual:**
  ```bash
  curl --max-time 5 --silent -X POST "$ARGUS_ALERT_WEBHOOK" ...
  ```
    - **Riesgo:** MITM o suplantación del endpoint receptor.
- **Solución industrial:** **gRPC con mTLS** (recomendado en v1, aún pendiente).
    - **Implementación:**
      ```protobuf
      service IncidentNotification {
        rpc NotifyIncident (IncidentRequest) returns (IncidentResponse);
      }
      message IncidentRequest {
        string node_id = 1;
        string incident_type = 2;
        bytes evidence_hash = 3;
        string signature = 4;  // Firma Ed25519 del nodo
      }
      ```
    - **Ventajas:**
        - Autenticación mutua (nodo ↔ receptor).
        - Cifrado de extremo a extremo.
        - **Librería:** [gRPC C++](https://grpc.io/docs/languages/cpp/) (ya usada en ZeroMQ).

### **3. Safe Mode Dependiente de GRUB (No Escalable)**
**Problema:**
- **Dependencia de intervención manual** (GRUB) no escala para flotas.
- **Solución industrial:** **Initramfs con trigger automático** (ej: kernel panic).
    - **Implementación:**
      ```bash
      # En /etc/default/grub:
      GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT argus.forensic=1"
      ```
    - **Trigger automático:**
        - Si `argus.forensic=1` está en la línea de kernel → arranca en modo forense.
        - **Ventaja:** No requiere selección manual en GRUB.

### **4. Falta de Métricas de Degradación en Modo Fallback**
**Problema:**
- **Código actual (Incidente Tipo B):**
  ```bash
  # RF embedded como fallback expone métricas de degradación:
  # Pipeline status: "⚠️ FALLBACK ACTIVE — RF embedded
  #   F1 estimated: ~0.97 (vs 0.9985 XGBoost)"
  ```
    - **Riesgo:** El admin no sabe si la degradación es aceptable.
- **Solución:**
    - **Añadir umbrales claros:**
      ```bash
      if [ "$(get_fallback_f1)" -lt 0.95 ]; then
        logger -p auth.crit "ARGUS FALLBACK: F1=$fallback_f1 < 0.95 — CRITICAL"
      else
        logger -p auth.notice "ARGUS FALLBACK: F1=$fallback_f1 — acceptable"
      fi
      ```
    - **Documentar en `docs/SLA.md`:**
      | **Métrica**       | **Umbral Crítico** | **Acción**                          |
      |-------------------|--------------------|-------------------------------------|
      | F1 (fallback)     | < 0.95             | Alertar al equipo (PagerDuty)       |
      | Recall (fallback) | < 0.90             | Escalar a nivel 1                   |
      | Latencia          | > 100ms            | Investigar causa raíz               |

### **5. Falta de Verificación de Integridad del Kernel**
**Problema:**
- **initramfs read-only asume que el kernel es íntegro**.
- **Riesgo:** Un rootkit que modifica el kernel puede contaminar incluso el initramfs.
- **Solución industrial:** **TPM 2.0 + Secure Boot** (DEBT-IRP-FORENSICS-TPM-001).
    - **Implementación futura:**
      ```bash
      # Verificar que el kernel arrancado coincide con el baseline
      if ! dmesg | grep -q "Secure boot enabled"; then
        echo "❌ Secure Boot not enabled — forensic evidence may be tainted"
        exit 1
      fi
      ```

---

## **Recomendaciones de Implementación Priorizadas**
*(Acciones concretas para mejorar el ADR antes del merge)*

| **Recomendación**                          | **Prioridad** | **Acciones Concretas**                                                                                     | **Owner**               |
|--------------------------------------------|----------------|------------------------------------------------------------------------------------------------------------|--------------------------|
| **1. Añadir quorum para standby**          | 🔴 Alta         | Implementar `argus-quorum-check` (2/3 nodos sanos).                                                       | Consejo + Alonso        |
| **2. Reemplazar webhook por gRPC+mTLS**    | 🔴 Alta         | - Definir `irp.proto`.<br>- Configurar Envoy en el receptor.<br>- Reemplazar `curl` en `argus-irp-notify`. | Consejo                 |
| **3. Trigger automático para safe mode**   | 🟡 Media        | Modificar initramfs para detectar `argus.forensic=1` en kernel cmdline.                                   | Post-FEDER              |
| **4. Métricas de degradación claras**     | 🟡 Media        | Añadir umbrales en `docs/SLA.md` y logs.                                                                   | Alonso                  |
| **5. Verificación de Secure Boot**         | 🟢 Baja         | Añadir check en `argus-forensic-collect`.                                                                | Post-FEDER              |

---

## **Alternativas Industriales para Problemas Críticos**
*(Soluciones probadas en producción que podrían adaptarse)*

### **1. Consenso de Quorum (Standby Promotion)**
**Problema:** Promover un standby comprometido amplifica el ataque.
**Solución industrial:** [Raft Consensus](https://raft.github.io/) (usado en etcd, Kubernetes).
- **Implementación:**
  ```bash
  # argus-quorum-check
  HEALTHY_NODES=$(argus-fleet-ping | jq '.healthy | length')
  TOTAL_NODES=$(argus-fleet-ping | jq '.total')
  if [ $HEALTHY_NODES -ge $((TOTAL_NODES * 2 / 3)) ]; then
    echo "✅ Quorum reached: $HEALTHY_NODES/$TOTAL_NODES"
    exit 0
  else
    echo "❌ Quorum failed: $HEALTHY_NODES/$TOTAL_NODES"
    exit 1
  fi
  ```

### **2. Comunicaciones Seguras (gRPC + mTLS)**
**Problema:** Webhook actual es vulnerable a MITM.
**Solución industrial:** [gRPC con mTLS](https://grpc.io/docs/guides/auth/) (usado en Google, Netflix).
- **Ventajas:**
    - Autenticación mutua (nodo ↔ receptor).
    - Cifrado de extremo a extremo.
    - **Ejemplo de certificado mTLS:**
      ```bash
      # Generar certs para el nodo
      openssl req -x509 -newkey rsa:4096 -keyout node-key.pem -out node-cert.pem -days 365 -nodes -subj "/CN=argus-node-01"
      # Certificado del receptor (CA)
      openssl req -x509 -newkey rsa:4096 -keyout receiver-key.pem -out receiver-cert.pem -days 365 -nodes -subj "/CN=argus-irp-receiver"
      ```

### **3. Forensics con TPM 2.0**
**Problema:** initramfs no garantiza integridad si el kernel está comprometido.
**Solución industrial:** [TPM 2.0 + IMA](https://docs.kernel.org/security/ima.html) (usado en RHEL, Debian).
- **Implementación futura:**
  ```bash
  # Verificar que el kernel fue arrancado con IMA + TPM
  if ! dmesg | grep -q "IMA: digital signature verification enabled"; then
    echo "❌ IMA not enabled — forensic evidence may be tainted"
    exit 1
  fi
  ```

---

## **Conclusión del Consejo**
> *"ADR-042 v2 es un diseño **maduro y alineado con estándares industriales**, que aborda los riesgos críticos identificados en la v1 (ej: aislamiento de red pre-poweroff, notificación multi-canal, reintegración verificada). Las mejoras propuestas —**quorum para standby**, **gRPC+mTLS**, y **métricas de degradación claras**— elevan el protocolo a un nivel de producción. Recomendamos implementar estas mejoras antes del merge a `main`, especialmente el **quorum** y **gRPC**, que son críticas para evitar amplificación de ataques y suplantación de notificaciones."*

**Puntos clave para implementar antes del merge:**
1. **Añadir `argus-quorum-check`** para promoción de standby.
2. **Reemplazar webhook por gRPC+mTLS** (seguridad en comunicaciones).
3. **Documentar métricas de degradación** en `docs/SLA.md`.

**¿Necesitáis ayuda con la implementación de gRPC o el quorum?** Estamos listos para proporcionar código de referencia o revisiones técnicas.