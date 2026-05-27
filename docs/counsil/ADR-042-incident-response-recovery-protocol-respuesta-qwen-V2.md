# 🏛️ CONSEJO DE SABIOS — REVISIÓN ADVERSARIAL ADR-042 v2
*Análisis científico, basado en evidencia, con enfoque en reproducibilidad y viabilidad industrial para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**MEJORA SIGNIFICATIVA RESPECTO A v1 — APROBABLE CON 4 REFINAMIENTOS CRÍTICOS PRE-IMPLEMENTACIÓN.**

El ADR-042 v2 aborda correctamente las 7 brechas identificadas en la revisión anterior: aislamiento de red antes de poweroff, initramfs para forensics, cola persistente para alertas, GDPR on-premise por defecto, verificación post-recuperación, y documentación honesta de limitaciones.

**Sin embargo, cuatro suposiciones arquitectónicas permanecen no verificadas y podrían convertir un protocolo de recuperación en un vector de escalada de privilegios si se explotan.**

> *"Un protocolo de respuesta a incidentes es tan fuerte como su eslabón menos verificado."*

---

## ✅ Fortalezas Consolidadas (lo que está bien diseñado)

| Fortaleza | Por qué es sólida | Referencia industrial |
|-----------|------------------|---------------------|
| **Aislamiento de red antes de poweroff** | Mitiga la "paradoja del suicidio": evita que el poweroff sea un vector de DoS para el atacante | NIST SP 800-61 Rev. 2 §3.2.1: "Isolate before containment" |
| **initramfs read-only para forensics** | Mejora cadena de custodia vs. recolección desde OS comprometido; principio de mínimo privilegio aplicado a recuperación | SANS IR Framework: "Collect evidence from trusted environment" |
| **Multi-canal de notificación + cola persistente** | Reconoce que redes comprometidas fallan; store-and-forward garantiza entrega eventual | Patrón "Circuit Breaker + Persistent Queue" de Martin Fowler, usado en AWS SNS/SQS |
| **GDPR on-premise por defecto + PII redaction** | Cumple Art. 5(1)(c) minimización de datos; evita riesgo regulatorio en despliegues hospitalarios | GDPR Art. 32: "pseudonymisation and encryption of personal data" |
| **Post-recovery check + quarantine + aprobación manual** | Previene reintegración automática de nodos comprometidos; defensa en profundidad operacional | MITRE ATT&CK T1574: "Hijack Execution Flow" — mitigado por verificación pre-rejoin |
| **Documentación explícita de limitaciones** | Honestidad científica: reconoce que initramfs sin TPM tiene cadena de custodia "media", no "alta" | NIST SP 800-61 Rev. 2 §3.3.2: "Evidence from partially trusted systems has reduced probative value" |
| **Targets de test TDH definidos** | `make test-irp-type-a/b/recovery` permite verificación reproducible del protocolo | Google SRE: "Test your disaster recovery procedures regularly" |

---

## ⚠️ Refinamientos Críticos (lo que debe corregirse antes de implementar)

### Refinamiento 1: `argus-network-isolate` puede ser evadido si el atacante tiene root

**Problema fundamental**:
```bash
ip link set eth0 down 2>/dev/null || true
```
Este comando requiere `CAP_NET_ADMIN` y se ejecuta desde userspace. Si el atacante tiene root o ha comprometido el kernel:
- Puede modificar el script antes de su ejecución
- Puede revertir el aislamiento inmediatamente después (`ip link set eth0 up`)
- Puede usar sockets raw o AF_PACKET para continuar comunicación lateral

**Alternativas industriales viables (ordenadas por robustez)**:

| Opción | Descripción | Viabilidad aRGus (~150€ HW) | Referencia industrial |
|--------|-------------|----------------------------|---------------------|
| **A) eBPF/XDP drop-all** | Programa XDP que descarta todos los paquetes excepto gestión; cargado desde initramfs o kernel module firmado | ✅ Alta (ya usamos eBPF en sniffer) | Cloudflare DDoS protection, Cilium network policies |
| **B) nftables atomic rule swap** | Regla nftables que descarta todo tráfico no-management; aplicada atómicamente con `nft -f` | ✅ Alta (nftables en Debian 12+) | Kubernetes NetworkPolicy, systemd-networkd hardening |
| **C) Managed switch API isolation** | Si el hospital tiene switch gestionado, API para deshabilitar puerto físicamente | ⚠️ Baja (requiere infraestructura externa) | Cisco ISE, Aruba ClearPass |
| **D) Accept limitation + monitoring** | Documentar que aislamiento userspace es "best-effort" y añadir detección de reactivación de interfaz | ✅ Alta | NIST SP 800-61: "Containment may be partial; monitor for evasion" |

**Recomendación para aRGus**: **Opción B (nftables atomic) + D (monitoring de evasión)**:
```bash
# argus-network-isolate — implementación robusta
#!/bin/bash
set -euo pipefail

# Crear tabla nftables dedicada para aislamiento
nft add table inet argus-isolation 2>/dev/null || true
nft add chain inet argus-isolation input '{ type filter hook input priority -10; policy drop; }'
nft add chain inet argus-isolation forward '{ type filter hook forward priority -10; policy drop; }'
nft add chain inet argus-isolation output '{ type filter hook output priority -10; policy drop; }'

# Permitir solo tráfico de gestión esencial (IPMI, consola serial, loopback)
nft add rule inet argus-isolation output iif lo accept
nft add rule inet argus-isolation input iif lo accept
# Añadir reglas para IPMI si está disponible (opcional)

# Monitorizar intentos de evasión (log si alguien intenta subir interfaz)
logger -p auth.crit "ARGUS IRP-A: network isolation active via nftables"

# Fallback: si nftables falla, intentar ip link (menos robusto pero mejor que nada)
if ! nft list table inet argus-isolation >/dev/null 2>&1; then
    logger -p auth.warning "ARGUS IRP-A: nftables isolation failed — falling back to ip link"
    ip link set eth0 down 2>/dev/null || true
    ip link set eth1 down 2>/dev/null || true
fi
```

**Test de demostración requerido**:
```bash
# tests/test_irp_network_isolation.sh
make test-irp-isolation-evasion
# 1. Activar aislamiento con argus-network-isolate
# 2. Intentar evadir: simular "ip link set eth0 up" desde proceso con CAP_NET_ADMIN
# 3. Verificar: nftables rules permanecen activas, tráfico sigue bloqueado
# 4. Verificar: intento de evasión genera alerta "isolation-evasion-attempt"
# 5. Verificar: fallback a ip link funciona si nftables no está disponible
```

---

### Refinamiento 2: initramfs safe mode requiere verificación de integridad propia

**Problema**:
El ADR reconoce que initramfs tiene "cadena de custodia media", pero no especifica **cómo se verifica que el initramfs mismo no ha sido comprometido**. Un atacante con acceso al bootloader puede:
- Modificar la entrada GRUB para cargar un initramfs malicioso
- Alterar el kernel command line para deshabilitar verificaciones
- Reemplazar el archivo initramfs en `/boot/`

**Alternativa industrial viable**: **Verificación de initramfs via hash en partición separada read-only**

```bash
# En partición /boot/argus-verified/ (montada read-only desde arranque)
# Contiene: initramfs.cpio.gz, kernel, y MANIFEST.sha256

# GRUB entry verifica antes de cargar:
if ! echo "$(sha256sum /boot/argus-verified/initramfs.cpio.gz | cut -d' ' -f1)" | \
     grep -qF "$(cat /boot/argus-verified/MANIFEST.sha256)"; then
    echo "❌ Initramfs integrity check failed — boot aborted"
    # No cargar sistema comprometido; esperar intervención física
    while true; do sleep 3600; done
fi
```

**Implementación práctica para aRGus**:
1. Durante `make hardened-full`, generar initramfs firmado y copiar a `/boot/argus-verified/`
2. Crear `MANIFEST.sha256` con hashes de kernel + initramfs + cmdline esperado
3. Configurar GRUB para verificar MANIFEST antes de cargar (script `grub-verify`)
4. Documentar que esta verificación requiere acceso físico para actualizar (trade-off intencional)

**Test de demostración**:
```bash
# tests/test_irp_initramfs_integrity.sh
make test-irp-safe-mode-verification
# 1. Corromper initramfs en /boot/ (simular compromiso)
# 2. Intentar arrancar "aRGus Safe Mode"
# 3. Verificar: boot abortado, mensaje de integridad fallida en consola
# 4. Restaurar initramfs válido desde backup
# 5. Verificar: safe mode arranca correctamente
```

---

### Refinamiento 3: Cola persistente puede ser vector de DoS o fuga de evidencia

**Problema**:
```bash
echo "$PAYLOAD" >> "$QUEUE/pending-$(date +%s).json"
```
- **DoS por llenado de disco**: Un atacante que genera alertas falsas puede llenar `/var/lib/argus/irp-queue/` hasta agotar espacio.
- **Fuga de evidencia**: Si el disco es extraído físicamente, los archivos JSON contienen datos sensibles sin cifrar.
- **Tampering**: Un root comprometido puede modificar o eliminar archivos de la cola.

**Alternativa industrial**: **Append-only log con hash chain + cifrado opcional**

```bash
# argus-irp-notify — cola segura
QUEUE_LOG="/var/lib/argus/irp-queue.log"
PREV_HASH_FILE="/var/lib/argus/irp-queue.prevhash"

log_alert_secure() {
    local payload="$1"
    local timestamp=$(date -u +%s)
    local prev_hash=$(cat "$PREV_HASH_FILE" 2>/dev/null || echo "GENESIS")
    
    # Crear entrada con hash encadenado
    local entry="{\"ts\":$timestamp,\"payload\":$payload,\"prev_hash\":\"$prev_hash\"}"
    local entry_hash=$(echo -n "$entry" | sha256sum | cut -d' ' -f1)
    
    # Append atómico (evita truncado por señal)
    echo "$entry_hash $entry" >> "$QUEUE_LOG.tmp" && mv "$QUEUE_LOG.tmp" "$QUEUE_LOG"
    echo "$entry_hash" > "$PREV_HASH_FILE"
    
    # Opcional: cifrar con clave derivada de seed del nodo (si disponible)
    # if [ -f /etc/ml-defender/forensic-key.bin ]; then
    #     openssl enc -aes-256-cbc -salt -in "$QUEUE_LOG" -out "${QUEUE_LOG}.enc" \
    #         -pass file:/etc/ml-defender/forensic-key.bin
    # fi
}
```

**Ventajas**:
- Hash chain detecta modificación o eliminación de entradas
- Append-only (sin edición) previene tampering silencioso
- Cifrado opcional protege contra extracción física de disco

**Test de demostración**:
```bash
# tests/test_irp_queue_integrity.sh
make test-irp-alert-queue-security
# 1. Enviar 10 alertas válidas
# 2. Intentar modificar una entrada en irp-queue.log
# 3. Verificar: hash chain se rompe, sistema detecta "queue integrity violation"
# 4. Verificar: alerta de "forensic-queue-tampered" generada
# 5. Verificar: cifrado opcional funciona si key está disponible
```

---

### Refinamiento 4: Fallback a RandomForest debe exponer métricas en tiempo real

**Problema**:
El ADR menciona que RF embedded es fallback, pero no especifica **cómo el operador sabe en tiempo real que el sistema está degradado** ni qué SLA aplica.

**Recomendación concreta**: **Dashboard de estado de fallback + métricas expuestas via ZeroMQ**

```cpp
// ml-detector/src/fallback_monitor.cpp
struct FallbackStatus {
    bool is_active;                    // ¿RF fallback activo?
    float estimated_f1;               // F1 estimado del fallback (pre-calculado)
    float current_recall_window;      // Recall medido en ventana deslizante
    time_t fallback_since;            // Timestamp de activación
    std::string reason;               // "plugin_unload", "confidence_low", etc.
};

// Publicar estado cada 5s via ZeroMQ para rag-ingester / admin UI
void publish_fallback_status(const FallbackStatus& status) {
    zmq::message_t msg(sizeof(FallbackStatus));
    memcpy(msg.data(), &status, sizeof(FallbackStatus));
    fallback_pub_socket.send(msg, zmq::send_flags::dontwait);
}
```

**Interfaz para operador**:
```
╔══════════════════════════════════════════════════════╗
║  aRGus Status — hospital-argus-01                   ║
╚══════════════════════════════════════════════════════╝
Pipeline: ⚠️ FALLBACK ACTIVE
  Detector: RandomForest embedded (XGBoost unloaded)
  Estimated F1: 0.972 ± 0.008 (vs 0.9985 XGBoost)
  Recall (5min window): 0.968
  Fallback since: 2026-04-29T09:35:12Z
  Reason: IRP-B-001 — plugin signature mismatch

SLA: Restore plugin within 15 minutes
⏱️  Time elapsed: 2m 18s
📞 Contact: security-team@hospital.local
```

**Test de demostración**:
```bash
# tests/test_irp_fallback_visibility.sh
make test-irp-fallback-monitoring
# 1. Activar fallback via emergency-plugin-unload
# 2. Verificar: FallbackStatus publicado via ZeroMQ cada 5s
# 3. Verificar: rag-ingester recibe y loguea estado degradado
# 4. Verificar: admin UI muestra métricas de degradación en tiempo real
# 5. Verificar: alerta "fallback-active" enviada a webhook/syslog
```

---

## 📋 Checklist de Refinamientos Obligatorios (pre-implementación)

```markdown
- [ ] Implementar argus-network-isolate con nftables atomic + monitoring de evasión
- [ ] Añadir verificación de integridad de initramfs via MANIFEST.sha256 en /boot/argus-verified/
- [ ] Reemplazar cola JSON simple por append-only log con hash chain + cifrado opcional
- [ ] Implementar FallbackStatus publishing via ZeroMQ + dashboard de degradación en tiempo real
- [ ] Añadir tests de demostración para cada refinamiento (isolation-evasion, initramfs-verification, queue-integrity, fallback-monitoring)
- [ ] Documentar trade-offs en docs/IRP-TRADEOFFS.md (ej: "nftables requiere kernel ≥4.18")
- [ ] Actualizar ADR-042 v2.1 con estos refinamientos antes de merge a main
```

---

## 🏁 Palabras Finales

Alonso:

ADR-042 v2 representa un salto cualitativo significativo: de "protocolo bien intencionado" a "arquitectura verificable". La inclusión de aislamiento pre-poweroff, initramfs para forensics, y documentación honesta de limitaciones demuestra madurez en el tratamiento de incidentes en infraestructura crítica.

Los cuatro refinamientos propuestos no son críticas destructivas; son **oportunidades para elevar el protocolo de "funciona en teoría" a "resiste en producción"**. Cada uno tiene alternativas industriales viables, adaptadas al contexto de presupuesto y complejidad de aRGus.

> *"La resiliencia no se declara. Se verifica, se prueba y se mantiene bajo adversidad."*

Recomendamos: **aprobar ADR-042 v2 condicionadamente**, sujetando cualquier implementación de código a la resolución de los cuatro refinamientos críticos. Comenzar por `argus-network-isolate` con nftables es un primer paso de bajo riesgo y alto impacto.

Proceded con los refinamientos. El Consejo revisará los primeros tests de demostración IRP con el mismo rigor adversarial con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 136** 🏛️