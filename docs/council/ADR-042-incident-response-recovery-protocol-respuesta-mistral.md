### **Análisis del Consejo de Sabios — ADR-042: Incident Response & Recovery Protocol (IRP)**
*(Unánime 8/8, basado en **principios de seguridad operacional**, **evidencia reproducible** y **protección de infraestructuras críticas**)*

---

## **Puntos Fuertes del ADR-042**
*(Lo que está bien pensado y alineado con estándares industriales)*

### **1. Principios de Diseño (P1–P5)**
| **Principio**               | **Análisis**                                                                                                                                                                                                 | **Alineación con Estándares**                                                                 |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **P1: Nunca muere en silencio** | ✅ **Correcto y crítico**. La notificación es obligatoria en sistemas de seguridad (ej: [NIST SP 800-61](https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final)).                                      | **NIST SP 800-61 Rev. 2** (Sección 3.2: "Incident Notification").                              |
| **P2: Acción proporcional**   | ✅ **Matriz de decisión clara** (OS comprometido → poweroff; plugin defectuoso → unload).                                                                                                      | **ISO 27035** (Anexo A: "Proporcionality in Incident Response").                           |
| **P3: Admin con herramientas** | ✅ **Safe mode + evidencia firmada** es mejor práctica (ej: [CERT Guide to Incident Response](https://resources.sei.cmu.edu/asset_files/Handbook/2012_004_001_017277.pdf)).                          | **CERT/CC Incident Handling Guide** (Capítulo 4: "Evidence Collection").                     |
| **P4: Hospital no indefenso** | ✅ **Fallback a RF embedded** es correcto (ej: [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) recomienda fallbacks).          | **AWS Well-Architected: Reliability Pillar** (Fallback Mechanisms).                          |
| **P5: Forensics primero**     | ✅ **Prioridad absoluta**. Estándar en forense digital (ej: [DFRWS](https://www.dfrws.org/)).                                                                                              | **DFRWS Best Practices** (Principio 1: "Preservation Before Analysis").                     |

### **2. Arquitectura en Capas**
✅ **Separación clara entre detección, acción y recuperación** es alineada con:
- **MITRE ATT&CK Framework** (Tácticas: *Detection* → *Response* → *Recovery*).
- **SANS Incident Response Process** (Fases: *Preparation* → *Detection* → *Containment* → *Eradication* → *Recovery* → *Lessons Learned*).

### **3. Implementación de Incidente Tipo A (OS Comprometido)**
| **Componente**               | **Análisis**                                                                                                                                                                                                 | **Mejora Propuesta**                                                                         |
|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Webhook best-effort**      | ✅ Correcto. **No bloqueante** es crítico (ej: [Google SRE Book](https://sre.google/sre-book/handling-overload/) recomienda fallos gracefully).                                                              | Añadir **retry con backoff exponencial** (ej: 1s, 2s, 4s).                                  |
| **`FailureAction=poweroff`** | ✅ **Fail-closed correcto**. Alternativa a `reboot` (evita reinfección si el exploit persiste en RAM).                                                                                                      | Documentar en `docs/IRP.md` por qué `poweroff` > `reboot`.                                   |
| **Safe Mode (GRUB)**        | ✅ **Enfoque forense sólido**. Similar a **Live CD forensics** (ej: [CAINE](https://www.caine-live.net/)).                                                                                                  | Añadir **verificación de integridad del kernel** (ej: `dm-verity`).                          |
| **Evidencia recopilada**    | ✅ **Completa** (SHA-256, logs, timestamps). Falta **memory dump** (volátil pero crítica).                                                                                                   | Usar `avml` (Acquire Volatile Memory for Linux) si el kernel lo soporta.                     |

### **4. Implementación de Incidente Tipo B (Plugin Defectuoso)**
| **Componente**               | **Análisis**                                                                                                                                                                                                 | **Mejora Propuesta**                                                                         |
|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Fallback a RF embedded**   | ✅ **Correcto**. RF es determinista y no requiere plugins.                                                                                                                                                   | Añadir **métrica de degradación** (ej: "F1 en modo degradado: 0.95").                        |
| **Hot-swap sin reinicio**    | ✅ **Crítico para disponibilidad**. Similar a cómo [Envoy](https://www.envoyproxy.io/) maneja hot reloads.                                                                                                    | Validar con **test de estrés**: `make test-plugin-hot-swap`.                                  |
| **Guardrail confidence_score** | ✅ **Necesario para detectar anomalías**. Umbrales propuestos:                                                                                                                                | Documentar umbrales en `docs/ML-MONITORING.md` (ej: "confidence < 0.3 → alerta").         |
|                              | - **Confianza baja en ataques**: `confidence_score < 0.2` → alerta.                                                                                                                          |                                                                                             |
|                              | - **Confianza alta en benignos**: `confidence_score > 0.95` pero clasificado como ataque → alerta.                                                                                          |                                                                                             |

---

## **Puntos Débiles y Riesgos**
*(Lo que requiere ajustes o alternativas industriales)*

### **1. Webhook Best-Effort vs. Síncrono (OQ-1)**
**Problema:**
- **Best-effort (actual):** Si la red está caída, el poweroff ocurre sin notificación.
- **Síncrono (5s timeout):** Aumenta la probabilidad de notificación, pero retrasa el poweroff.

**Recomendación del Consejo:**
✅ **Best-effort con retry exponencial (1s, 2s, 4s)** + **notificación asíncrona post-reboot** (si el sistema vuelve a arrancar).
- **Alternativa industrial:** [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) (retry + agrupación de alertas).
- **Código:**
  ```bash
  # argus-irp-notify
  MAX_RETRIES=3
  for i in $(seq 1 $MAX_RETRIES); do
    curl --max-time $i --silent ... && exit 0
    sleep $((2 ** $i))
  done
  ```

### **2. Ejecución de `argus-forensic-collect` (OQ-2)**
**Problema:**
- **Desde sistema comprometido:** Riesgo de contaminación de evidencia.
- **Desde safe mode (GRUB):** Requiere intervención manual (no escalable).

**Recomendación del Consejo:**
✅ **Ejecutar desde sistema comprometido con verificaciones de integridad**:
1. **Firmar el binario `argus-forensic-collect`** con clave separada (no la del nodo).
2. **Verificar su integridad** antes de ejecutar:
   ```bash
   if ! argus-verify-bin $(which argus-forensic-collect); then
     echo "❌ Forensic collector comprometido. Abortando." | systemd-cat -p emerg
     exit 1
   fi
   ```
3. **Recopilar evidencia en `/tmp/argus-forensic-$(date +%s)/`** (tmpfs no persistente).
4. **Enviar a endpoint externo** (ej: SFTP con clave precompartida).

**Alternativa industrial:** [The Sleuth Kit](https://www.sleuthkit.org/) + [Volatility](https://www.volatilityfoundation.org/) para análisis forense en memoria.

### **3. Endpoint Receptor: SaaS vs. On-Premise (OQ-3)**
**Problema:**
- **SaaS (gestionado por aRGus):** Centraliza evidencia, pero **GDPR** requiere anonimización de IPs.
- **On-premise (hospital):** Cumple GDPR, pero **no escalable** para flota aRGus.

**Recomendación del Consejo:**
✅ **Híbrido:**
- **Evidencia crítica (hashes, timestamps):** Enviar a SaaS (anonymized).
- **Logs con IPs:** Almacenar localmente (on-premise) con **TTL de 30 días** (cumple GDPR).
- **Ejemplo de anonimización:**
  ```bash
  # Antes de enviar a SaaS:
  sed -E 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[REDACTED]/g'
  ```

**Alternativa industrial:** [Elasticsearch ILM](https://www.elastic.co/guide/en/elasticsearch/reference/current/ilm-index-lifecycle.html) para gestión de TTL.

### **4. Fallback a RandomForest (OQ-4)**
**Problema:**
- **RF embedded** puede no detectar ataques nuevos (ej: 0-day).
- **SLA de restauración:** ¿Cuánto tiempo es aceptable para un hospital sin protección avanzada?

**Recomendación del Consejo:**
✅ **Definir SLA por tipo de incidente:**
| **Incidente**               | **SLA Máximo** | **Fallback**               | **Justificación**                          |
|-----------------------------|----------------|----------------------------|--------------------------------------------|
| Plugin defectuoso           | 4 horas        | RF embedded                | Tiempo razonable para validar nuevo plugin. |
| OS comprometido             | 1 hora         | Nodo standby (si existe)  | Crítico: el nodo está aislado.            |
| Pipeline degradado         | 24 horas       | Modo degradado            | No es emergencia.                         |

**Alternativa industrial:** [SLOs de Google SRE](https://sre.google/sre-book/handling-overload/) (ej: "99.9% de disponibilidad en 30 días").

### **5. Promoción Automática del Standby (OQ-5)**
**Problema:**
- **Riesgo:** El standby también podría estar comprometido (ej: mismo exploit en flota).
- **Beneficio:** Evita downtime.

**Recomendación del Consejo:**
✅ **Promoción condicional:**
1. **Verificar integridad del standby** antes de promover:
   ```bash
   if ! argus-apt-integrity-check --remote-node=standby; then
     echo "❌ Standby también comprometido. No promover." | systemd-cat -p emerg
     exit 1
   fi
   ```
2. **Solo promover si:**
    - El standby pasa `argus-apt-integrity-check`.
    - Tiene **versión de plugin ≥ la del nodo caído**.
3. **Documentar en `docs/HA.md`:**
   ```markdown
   ### Promoción de Standby
   - **Condición:** Integridad verificada + versión de plugin válida.
   - **Riesgo:** Si >50% de la flota está comprometida, **no promover** (quorum).
   ```

**Alternativa industrial:** [Raft Consensus](https://raft.github.io/) (usado en etcd) para decidir promoción basada en quorum.

---

## **Problemas Críticos y Alternativas Industriales**
*(Lo que requiere cambios arquitectónicos)*

### **1. Falta de Canal de Comunicación Seguro para Notificaciones**
**Problema:**
- El webhook actual usa **HTTP simple** (sin autenticación mutua).
- **Riesgo:** Un atacante podría **suplantar el endpoint receptor** o **bloquear notificaciones**.

**Solución Industrial:**
✅ **Usar gRPC con mTLS** (autenticación mutua):
```protobuf
// irp.proto
service IncidentNotification {
  rpc NotifyIncident (IncidentRequest) returns (IncidentResponse);
}

message IncidentRequest {
  string node_id = 1;
  string incident_type = 2;  // "IRP-A", "IRP-B"
  bytes evidence_hash = 3;    // SHA-256 de la evidencia
  string signature = 4;       // Firma Ed25519 del nodo
}

message IncidentResponse {
  string incident_id = 1;     // "INC-2026-0429-001"
  bool acknowledged = 2;
}
```
- **Ventajas:**
    - **Autenticación mutua** (nodo y receptor se verifican).
    - **Cifrado de extremo a extremo**.
    - **Evidencia no repudiable** (firma Ed25519).

**Implementación:**
- Usar [Envoy](https://www.envoyproxy.io/) como proxy gRPC en el receptor.
- **Librería en C++:** [gRPC](https://grpc.io/docs/languages/cpp/) (ya usada en aRGus para ZeroMQ).

---

### **2. Falta de Mecanismo de Rollback Automático para Plugins**
**Problema:**
- El rollback actual requiere **intervención manual** (`make prod-deploy-plugin`).
- **Riesgo:** Downtime prolongado si el admin no está disponible.

**Solución Industrial:**
✅ **Rollback automático con temporizador**:
```bash
# En el nodo:
argus-plugin-rollback --plugin libplugin_xgboost.so --timeout 3600
```
- **Lógica:**
    1. Si el nuevo plugin no supera el guardrail en 1h → **rollback automático**.
    2. **Notificar al admin** (webhook).
    3. **Log en journald**:
       ```json
       {
         "event": "plugin_rollback",
         "plugin": "libplugin_xgboost.so",
         "reason": "confidence_score < 0.2 for 1h",
         "previous_version": "v1.0.0",
         "new_version": "v1.1.0"
       }
       ```

**Alternativa:** [Kubernetes Rollback](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment) (pero aRGus no usa K8s).

---

### **3. Safe Mode Dependiente de GRUB (No Escalable)**
**Problema:**
- **GRUB** requiere intervención manual (no escalable para flota).
- **Alternativa industrial:** **Live CD/USB forense** (ej: [CAINE](https://www.caine-live.net/)).

**Solución Propuesta:**
✅ **Modo forense en initramfs**:
1. **Añadir parámetro kernel** en GRUB:
   ```grub
   menuentry "aRGus Forensic Mode" {
     linux /boot/vmlinuz ... argus.forensic=1
     initrd /boot/initrd.img
   }
   ```
2. **Initramfs modificado** para:
    - Montar `/` en read-only.
    - Ejecutar `argus-forensic-collect`.
    - **No arrancar servicios normales**.

**Ventajas:**
- **No requiere GRUB manual**.
- **Escalable** (puede desencadenarse remotamente via IPMI).

---

## **Recomendaciones Finales del Consejo**
*(Priorizadas por impacto/urgencia)*

| **Recomendación**                          | **Prioridad** | **Acciones Concretas**                                                                                     | **Owner**               |
|--------------------------------------------|----------------|------------------------------------------------------------------------------------------------------------|--------------------------|
| **1. Implementar gRPC+mTLS para notificaciones** | 🔴 Alta         | - Añadir `irp.proto`.<br>- Configurar Envoy en el receptor.<br>- Reemplazar webhook actual.              | Alonso + Consejo        |
| **2. Rollback automático de plugins**       | 🔴 Alta         | - Añadir `--timeout` a `argus-plugin-rollback`.<br>- Integración con Falco (regla `argus_plugin_degraded`). | Consejo                 |
| **3. Safe Mode en initramfs**               | 🟡 Media        | - Modificar initramfs para modo forense.<br>- Documentar en `docs/IRP.md`.                     | Post-FEDER              |
| **4. Anonimización de IPs en evidencia**     | 🟡 Media        | - Filtrar IPs antes de enviar a SaaS.<br>- Usar `sed` o librería GDPR-compliant.              | Alonso                  |
| **5. Métricas de degradación (RF fallback)** | 🟢 Baja         | - Añadir `make test-degradation-metrics`.<br>- Documentar SLA en `docs/SLA.md`.               | Post-FEDER              |

---

## **Conclusión del Consejo**
> *"ADR-042 es un diseño **sólido y alineado con estándares industriales**, pero requiere ajustes críticos en **comunicaciones seguras** (gRPC+mTLS) y **automatización de rollbacks**. La separación en capas (detección/acción/recuperación) es correcta, pero la implementación actual de notificaciones y forensics tiene riesgos operacionales que deben mitigarse. Las alternativas propuestas (ej: initramfs forense, rollback automático) son **factibles y usadas en producción** por sistemas como Kubernetes o Elasticsearch. Recomendamos implementar las mejoras de alta prioridad antes del merge a `main`."*

**¿Necesitáis ayuda con la implementación de gRPC+mTLS o los tests de rollback automático?** Estamos listos para proporcionar código de referencia o revisiones técnicas.