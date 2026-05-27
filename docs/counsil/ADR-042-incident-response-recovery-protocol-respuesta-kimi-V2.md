## Kimi — Revisión Adversarial — ADR-042 v2

*Evaluación crítica bajo criterios de resistencia a adversarios sofisticados, operabilidad 24/7 en hospitales sin personal de seguridad dedicado, y trazabilidad forense judicial.*

---

## Veredicto Global

**ADR-042 v2 es una mejora sustancial sobre v1.** Los 7 fallos graves identificados en la revisión anterior han sido corregidos o mitigados. Sin embargo, persisten **3 fallos de diseño arquitectónico** que hacen el protocolo inoperable en producción hospitalaria real sin modificaciones mayores. El ADR es **aprobable como visión estratégica**, pero **no implementable tal cual** para FEDER.

---

## Fallos Persistentes (v2 no resuelve)

### F1 — `ip link set down` no aísla: el atacante ya está dentro

**Problema:** La Capa 2 propone `ip link set eth0 down` como aislamiento de red. Esto es **ilusorio** si el compromiso del OS es real. Un atacante con root en el sistema puede:

1. **Reactivar la interfaz** inmediatamente: `ip link set eth0 up` (el atacante corre como root, puede revertir la acción)
2. **Usar interfaces no monitoreadas**: `lo`, `docker0`, `virbr0`, interfaces de túnel creadas dinámicamente
3. **Exfiltrar datos por side-channels**: timing de LEDs, ultrasonido de ventiladores, o simplemente escribir a disco y esperar a que el admin monte el disco en otro sistema

**Alternativa industrial:** **Hardware-level network kill switch** o **BMC/IPMI power control** con credenciales separadas. Ejemplo: Dell iDRAC permite cortar alimentación de NIC independientemente del OS. En commodity hardware, **unmanaged switch con port security** que el admin desconecte físicamente.

**Recomendación:** Documentar explícitamente que `ip link set down` es **best-effort** y no constituye aislamiento efectivo contra un atacante con root. El aislamiento real requiere:

```bash
# Opción A: hardware-level (requiere switch administrado o BMC)
# Opción B: eBPF/XDP drop-all en la NIC (el atacante necesitaría recompilar el programa eBPF)
# Opción C: iptables drop-all en mangle/PREROUTING y mangle/POSTROUTING con reglas numeradas 1
#           (el atacante necesitaría flush de iptables, detectable por Falco)

# Implementación C (mejor que ip link down):
iptables -t mangle -I PREROUTING 1 -j DROP
iptables -t mangle -I POSTROUTING 1 -j DROP
ip6tables -t mangle -I PREROUTING 1 -j DROP
ip6tables -t mangle -I POSTROUTING 1 -j DROP
# Esto dropa paquetes en kernel space, antes de que lleguen a userspace
# El atacante necesitaría modificar iptables (detectado por Falco)
# o modificar el kernel (requiere módulo, detectado por module load rules)
```

**Nota:** Incluso iptables es reversible por root. La única defensa efectiva es **hardware externo** o **hypersvisor-level isolation** (si la VM corre en KVM, el host puede pausar la VM).

---

### F2 — `argus-standby-ping` sin autenticación: amplificación del compromiso

**Problema:** El script `argus-standby-ping --timeout=3` verifica disponibilidad pero **no verifica integridad**. Si el atacante ha comprometido el nodo principal, puede haber comprometido el standby previamente (por ejemplo, via etcd, ZeroMQ, o una vulnerabilidad compartida). El ping solo dice "el standby responde", no "el standby es íntegro".

**Alternativa industrial:** **Quorum criptográfico** antes de failover. Ejemplo: Consul raft requiere mayoría de nodos para elegir líder. Cada nodo debe demostrar integridad via hash de binarios firmado.

**Recomendación:** `argus-standby-ping` debe ser `argus-standby-attest` y requerir:

```bash
argus-standby-attest() {
    # 1. Solicitar attestación criptográfica del standby
    # 2. Verificar firma Ed25519 del standby sobre su propio hash de binarios
    # 3. Comparar hash contra baseline conocido
    # 4. Solo si coincide, considerar "disponible e íntegro"
    
    # Implementación simplificada (sin TPM):
    STANDBY_HASH=$(ssh standby /usr/local/bin/argus-self-hash)
    EXPECTED_HASH=$(cat /var/lib/argus/standby-baseline.sha256)
    
    if [ "$STANDBY_HASH" = "$EXPECTED_HASH" ]; then
        echo "STANDBY_ATTEST_OK"
        return 0
    else
        echo "STANDBY_ATTEST_FAIL: hash mismatch"
        return 1
    fi
}
```

**Sin esto:** El protocolo promueve un standby potencialmente comprometido, violando P4.

---

### F3 — RF embedded con F1=0.97: degradación inaceptable no cuantificada

**Problema:** El ADR asume que RandomForest embedded tiene F1≈0.97 como fallback. **Este número no está validado.** Si RF embedded tiene F1=0.85 (plausible si fue entrenado con menos datos o features simplificadas), el "fallback" es una **falsa sensación de seguridad**.

**Alternativa industrial:** **Graceful degradation con threshold de aceptación.** Ejemplo: si el fallback no alcanza F1≥0.995, el sistema entra en modo "alert-only" (detecta pero no bloquea automáticamente) en lugar de "auto-remediate".

**Recomendación:** Antes de declarar RF embedded como fallback válido, ejecutar:

```bash
# test_rf_fallback.sh — gate obligatorio antes de merge de ADR-042
./argus-ml-detector --mode=rf-embedded --test-golden-set
# Salida esperada: F1, Recall, FPR, latency_p99

# Criterio de aceptación para fallback:
# F1 ≥ 0.995 (no 0.97)
# Recall ≥ 0.999 (no puede perder ataques)
# FPR ≤ 0.01% (tolerable para alert-only, no para auto-block)
# Latencia p99 ≤ 10 ms (no puede saturar el pipeline)
```

Si RF embedded no alcanza estos umbrales, el fallback debe ser **"alert-only mode"** (sniffer detecta, admin decide) en lugar de **"auto-block with degraded model"**.

---

## Mejoras Confirmadas (v1 → v2)

| Fallo v1 | Corrección v2 | Estado |
|----------|--------------|--------|
| Poweroff sin aislamiento | `ip link set down` + secuencia jerárquica | ✅ Corregido (aunque ver F1) |
| Webhook best-effort silencioso | Store-and-forward + cola persistente | ✅ Corregido |
| Forensics en sistema comprometido | initramfs read-only | ✅ Corregido |
| Fallback sin métricas | F1=0.97 documentado (ver F3) | ⚠️ Parcial |
| GDPR SaaS externo | On-premise obligatorio + PII redaction | ✅ Corregido |
| `make safe-mode` dependencia circular | initramfs + GRUB entry | ✅ Corregido |
| Auto-promote standby | Verificación manual obligatoria | ✅ Corregido |
| Reintegración automática | Post-recovery check + quarantine 24h | ✅ Nuevo en v2 |

---

## Nuevos Problemas Introducidos en v2

### N1 — `RemainAfterExit=yes` en systemd unit: comportamiento no determinista

```ini
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/argus-apt-integrity-check
```

Con `RemainAfterExit=yes`, el servicio se considera "activo" incluso después de que el script termine. Si el script falla (exit code ≠ 0), systemd ejecuta `FailureAction=poweroff`. Pero si el script tiene un bug y nunca termina (por ejemplo, `argus-standby-ping` cuelga), el servicio se queda en estado "activating" indefinidamente y **nunca ejecuta el poweroff**.

**Recomendación:** Añadir `TimeoutStartSec=30` y `TimeoutStopSec=10` para garantizar que el servicio siempre termina.

### N2 — `ExecStopPre` no existe en systemd

El ADR usa `ExecStopPre` que **no es una directiva válida** de systemd. Las directivas correctas son `ExecStartPre` (antes de ExecStart) y `ExecStopPost` (después de ExecStop). No hay `ExecStopPre`.

**Corrección:**

```ini
[Service]
Type=oneshot
ExecStart=/bin/true  # Placeholder para mantener el servicio "activo"
ExecStartPre=/usr/bin/journalctl --flush
ExecStartPre=/usr/bin/logger -p auth.crit "ARGUS IRP-A: APT integrity violation"
ExecStartPre=/usr/local/bin/argus-irp-notify
ExecStartPre=/usr/local/bin/argus-network-isolate
ExecStopPost=/usr/bin/systemctl poweroff  # O mejor: FailureAction=poweroff

# Anti-bootloop
StartLimitIntervalSec=300
StartLimitBurst=2
```

### N3 — `systemctl poweroff` en `ExecStopPost` requiere privilegios

Si el servicio corre como usuario `argus` (no root), `systemctl poweroff` fallará con `Interactive authentication required`. El ADR no especifica el usuario del servicio.

**Recomendación:** El servicio debe correr como root (porque modifica iptables y apaga el sistema), pero con `NoNewPrivileges=true` y `ProtectSystem=strict` para limitar la superficie de ataque.

---

## Tests de Cierre Revisados

Los tests propuestos en el ADR son correctos pero incompletos. Añadir:

```bash
# Test F1: Verificar que el atacante no puede reactivar la red
make test-irp-network-isolate-resilience
# Simular: atacante con root ejecuta `ip link set eth0 up`
# Esperado: Falco detecta el intento, iptables mangle sigue drop-eando

# Test F2: Verificar que standby comprometido no se promueve
make test-irp-standby-compromised
# Simular: standby tiene hash de binarios modificado
# Esperado: argus-standby-attest falla, admin notificado, NO promote

# Test F3: Verificar que RF fallback cumple mínimos
make test-irp-rf-fallback-quality
# Ejecutar golden set con RF embedded
# Esperado: F1 ≥ 0.995, Recall ≥ 0.999, FPR ≤ 0.01%
```

---

## Conexión con el Paper

El material de ADR-042 v2 es publicable en arXiv cs.CR con las siguientes condiciones:

1. **Honestidad sobre limitaciones:** Documentar que `ip link set down` es best-effort y que el aislamiento real requiere hardware externo o hypervisor.
2. **Datos empíricos:** Incluir resultados de `test-irp-rf-fallback-quality` con números reales.
3. **Comparativa:** Contrastar con soluciones enterprise (CrowdStrike Falcon, SentinelOne) que usan kernel-level isolation (no disponible en open source sin firmas de driver).

---

## Resumen de Posiciones — Kimi

| Aspecto | Veredicto v2 | Acción requerida |
|---------|-------------|------------------|
| **Arquitectura general** | Aprobada como visión | No implementable tal cual para FEDER |
| **Aislamiento de red (F1)** | `ip link down` insuficiente | Implementar iptables mangle DROP + documentar limitación |
| **Attestación standby (F2)** | Ping sin autenticación | Reemplazar por `argus-standby-attest` con hash firmado |
| **Calidad fallback (F3)** | F1=0.97 no validado | Ejecutar golden set con RF embedded antes de declarar fallback |
| **systemd unit (N1-N3)** | Errores técnicos | Corregir `ExecStopPre` → `ExecStartPre`, añadir timeouts, especificar usuario root |
| **Tests de cierre** | Incompletos | Añadir tests de resiliencia del aislamiento y calidad del fallback |
| **GDPR** | Correctamente resuelto | Aprobar sin modificaciones |
| **Reintegración (P6)** | Correctamente diseñada | Aprobar sin modificaciones |

**Moción:** Propongo que ADR-042 v2 se apruebe como **documento de requisitos** (no de implementación), y que se creen tres ramas de trabajo paralelas:
1. `feature/irp-network-isolate` — implementar iptables mangle + tests de resiliencia
2. `feature/irp-standby-attest` — implementar attestación criptográfica de standby
3. `feature/irp-rf-fallback` — validar RF embedded contra golden set

Ninguna de estas ramas se mergea a `main` hasta que los tres gates (F1, F2, F3) pasen.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*