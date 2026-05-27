# Consejo de Sabios — Síntesis ADR-042 v2
*DAY 135 — 29 Abril 2026*
*8/8 modelos presentes*

---

## Veredicto global

**ADR-042 v2 APROBADO como documento de arquitectura/requisitos.**
**NO implementable directamente — 5 enmiendas obligatorias pre-implementación.**

Mejora sustancial reconocida por los 8 modelos. v1→v2 resuelve la
"paradoja del suicidio" (Gemini), el silencio del webhook, forensics
en sistema comprometido, GDPR, y reintegración automática.

---

## Enmiendas obligatorias (consenso fuerte)

### E1 — `ip link set down` insuficiente → nftables (7/8)
ChatGPT, Kimi, Qwen, DeepSeek, Grok, Mistral coinciden:
`ip link set down` es reversible por root. Un atacante puede reactivar
la interfaz inmediatamente. Reemplazar por nftables atomic drop-all:

```bash
# argus-network-isolate — implementación robusta
nft add table inet argus-isolation
nft add chain inet argus-isolation input  '{ type filter hook input  priority -10; policy drop; }'
nft add chain inet argus-isolation forward '{ type filter hook forward priority -10; policy drop; }'
nft add chain inet argus-isolation output '{ type filter hook output priority -10; policy drop; }'
nft add rule inet argus-isolation input  iif lo accept
nft add rule inet argus-isolation output oif lo accept
# Fallback si nftables falla:
nft list table inet argus-isolation >/dev/null 2>&1 || {
    ip link set eth0 down 2>/dev/null || true
    ip link set eth1 down 2>/dev/null || true
}
```

Documentar explícitamente: aislamiento es best-effort si el atacante
controla el kernel. Única defensa real: hardware externo (BMC/switch
gestionado) o hypervisor. Documenta en limitations.

### E2 — BUG TÉCNICO: `ExecStopPre` no existe en systemd (Kimi)
`ExecStopPre` NO es una directiva válida de systemd. La directiva
correcta es `ExecStartPre`. El unit actual tiene un bug que haría
que los pasos de notificación/aislamiento NUNCA se ejecuten.

Corrección obligatoria:
```ini
[Service]
Type=oneshot
ExecStartPre=/usr/bin/journalctl --flush
ExecStartPre=/usr/bin/logger -p auth.crit "ARGUS IRP-A"
ExecStartPre=/usr/local/bin/argus-irp-notify
ExecStartPre=/usr/local/bin/argus-network-isolate
ExecStart=/usr/local/bin/argus-apt-integrity-check
RemainAfterExit=yes
FailureAction=poweroff
TimeoutStartSec=30
TimeoutStopSec=10
StartLimitIntervalSec=300
StartLimitBurst=2
```

### E3 — Cola persistente necesita límite y procesador (DeepSeek, Qwen)
Cola sin límite = DoS por disco lleno. Necesita:
- Límite máximo: 100 entradas o 10MB
- Política FIFO: descartar más antiguas si se llena
- Servicio `argus-irp-queue-processor` (systemd, after network-online.target)
  que procesa cola en arranque normal post-recuperación
- Hash chain para detectar tampering (Qwen)

### E4 — Post-recovery check debe bloquear boot si falla (DeepSeek)
Actualmente no está especificado. Si `argus-post-recovery-check` falla,
el sistema debe detenerse en consola de emergencia, no continuar
arrancando con el pipeline comprometido.

```ini
# argus-post-recovery.service
[Service]
ExecStart=/usr/local/bin/argus-post-recovery-check
FailureAction=emergency  # No poweroff — admin necesita consola
```

### E5 — Advertencia Secure Boot para initramfs (DeepSeek, Mistral, Grok)
Sin Secure Boot habilitado, el initramfs en /boot puede ser modificado
por el atacante. Añadir advertencia explícita en el ADR y en la
salida del safe mode:

⚠️  Secure Boot NOT detected. Forensic initramfs integrity cannot
be hardware-verified. For high-assurance environments, enable
UEFI Secure Boot with custom keys (DEBT-IRP-SECUREBOOT-001).

---

## Puntos de divergencia relevantes

### `argus-standby-ping` → `argus-standby-attest` (Kimi, Mistral, DeepSeek)
El ping verifica disponibilidad, no integridad. Un standby que responde
puede estar comprometido. Kimi propone verificación criptográfica:
hash de binarios firmado por el standby vs baseline conocido.
**No bloqueante para la demo FEDER, pero deuda alta.**
→ `DEBT-IRP-STANDBY-ATTEST-001`

### RF fallback F1=0.97 no validado (Kimi)
El número no está medido. Gate requerido antes de declarar RF como
fallback válido: ejecutar golden set con RF embedded y verificar
que cumple mínimos operacionales. Si no los cumple, el fallback
debe ser "alert-only mode" (detecta, no bloquea automáticamente).
→ `DEBT-IRP-RF-FALLBACK-GATE-001`

### Edge case gateway (Claude)
Si el nodo actúa como gateway (§4.2 del paper), bajar las interfaces
corta el tráfico del hospital. `argus-network-isolate` debe ser
consciente del modo de despliegue: sensor pasivo vs gateway.
→ Documentar en el ADR como limitación conocida.

### Tests --dry-run (Claude)
`make test-irp-type-a` no puede ejecutar poweroff real en EMECAS.
Necesita variante `--dry-run` que verifica todos los pasos previos
sin ejecutar el poweroff.

---

## Nuevas deudas identificadas en v2

| ID | Descripción | Severidad | Plazo |
|----|-------------|-----------|-------|
| DEBT-IRP-NFTABLES-001 | Reemplazar ip link por nftables en network-isolate | 🔴 Alta | post-merge |
| DEBT-IRP-SYSTEMD-FIX-001 | Corregir ExecStopPre → ExecStartPre (BUG) | 🔴 Crítico | inmediato |
| DEBT-IRP-QUEUE-PROCESSOR-001 | Servicio procesador de cola + límites | 🔴 Alta | post-merge |
| DEBT-IRP-SECUREBOOT-001 | Advertencia + UEFI Secure Boot para initramfs | 🟡 Media | post-FEDER |
| DEBT-IRP-STANDBY-ATTEST-001 | argus-standby-attest criptográfico vs ping | 🟡 Media | post-FEDER |
| DEBT-IRP-RF-FALLBACK-GATE-001 | Gate validación RF embedded vs golden set | 🟡 Media | post-merge |
| DEBT-IRP-GATEWAY-MODE-001 | network-isolate consciente de modo gateway | 🟡 Media | post-merge |
| DEBT-IRP-TEST-DRYRUN-001 | make test-irp-type-a --dry-run | 🟡 Media | post-merge |

---

## Prioridades de implementación DAY 136+

**Inmediato (sin estas cosas el ADR tiene bugs):**
1. E2 — Corregir ExecStartPre (bug crítico en systemd unit)
2. E1 — nftables en argus-network-isolate

**Post-merge:**
3. E3 — Cola con límites + procesador systemd
4. E4 — post-recovery check bloquea boot
5. RF fallback gate con golden set

**Post-FEDER:**
6. Secure Boot + initramfs firmado
7. argus-standby-attest criptográfico
8. TPM attestation

---

## Conexión con el paper (ratificada 8/8)

ADR-042 es material publicable. Lo más valioso: la documentación honesta
de las limitaciones. Sección de limitations residuales es exactamente
el tipo de contribución que Sommer & Paxson pedían en 2010.

---

*DAY 135 — 8/8 modelos — ADR-042 aprobado como arquitectura*
*"La resiliencia no se declara. Se verifica, se prueba y se mantiene bajo adversidad."*
🏛️
