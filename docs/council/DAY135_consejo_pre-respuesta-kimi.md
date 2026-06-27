## Kimi — Respuesta al Consejo de Sabios — DAY 135

*Evaluación bajo criterios de fail-closed operacional, criptografía de transferencia y priorización de entregables críticos.*

---

### Q1 — `FailureAction=reboot` en `argus-apt-integrity.service`

**Hipótesis:** Un nodo cuya cadena de suministro de paquetes está comprometida no puede ser confiable para ninguna operación posterior, incluida la notificación de su propio compromiso.

**Veredicto: APROBADA la filosofía fail-closed. MODIFICADA la implementación: 30 segundos son insuficientes para envío remoto; NO configurable vía etcd/JSON.**

**Justificación técnica:**

La decisión de `FailureAction=reboot` es arquitectónicamente correcta para un sistema de seguridad de red en entornos hospitalarios. Si `/etc/apt/sources.list` o sus hashes SHA-256 han sido modificados, el atacante ya tiene capacidad de persistencia a nivel de sistema operativo. Permitir que el nodo arranque y se una a la red aRGus (ZeroMQ, etcd) convierte un compromiso local en un compromiso de flota.

**Análisis de los 30 segundos:**

| Evento | Tiempo estimado | ¿Ocurre en 30s? |
|--------|----------------|-----------------|
| `systemd` detecta fallo del servicio | < 1s | Sí |
| `journald` escribe entrada persistente | < 2s | Sí |
| Envío de log vía rsyslog/syslog-ng a central | 5–30s (depende de red) | **A veces no** |
| Falco detecta la modificación y genera alerta | 1–5s | Sí |
| ZeroMQ pub del nodo a la red | Variable | No garantizado |

Los 30 segundos son suficientes para que `journald` persista el evento en disco (si `Storage=persistent` está configurado), pero **no son suficientes** para garantizar la entrega remota. La evidencia forense debe residir en el disco local, no depender de la red.

**Configurabilidad vía etcd/JSON: RECHAZADA.**

Si los apt sources están comprometidos, no se puede confiar en:
- El daemon etcd (podría estar apuntando a un endpoint malicioso)
- El parser JSON (podría haber sido modificado por el atacante)
- El propio fichero de configuración (podría haber sido alterado)

Hacer configurable el `FailureAction` vía etcd introduce una dependencia circular de confianza. La decisión de reboot debe ser **hardcoded** en la unit systemd o en un binario firmado en `/usr/local/bin/` protegido por AppArmor.

**Modificación recomendada:**

```ini
# /etc/systemd/system/argus-apt-integrity.service
[Unit]
Description=Argus APT Sources Integrity Check
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/argus-apt-integrity-check
TimeoutStartSec=30
# Hardcoded: no configurable externamente
FailureAction=reboot

# Protección contra loop de reboot infinito
StartLimitIntervalSec=300
StartLimitBurst=2

[Install]
WantedBy=multi-user.target
```

**Con `StartLimitIntervalSec=300` y `Burst=2`:** Si el check falla dos veces en 5 minutos, systemd marca la unidad como failed y **no reintenta más**. Esto evita que un bug en el script de verificación convierta el nodo en un brick de reboot cíclico.

**Riesgo identificado:** Un falso positivo en el checksum (por ejemplo, una actualización legítima de seguridad de Debian que modifica `sources.list` durante el boot) provocaría un reboot inesperado. Mitigación: el script debe verificar contra un **checksum conocido y versionado** en el repo, no contra un checksum capturado dinámicamente. Si Debian actualiza sus sources, el admin debe actualizar el checksum versionado y redeploy.

**Test reproducible:**

```bash
# Test de comportamiento ante compromiso simulado
vagrant ssh hardened-x86 -c 'sudo bash -c "
    echo \"deb http://evil.example.com/debian bookworm main\" > /etc/apt/sources.list
    systemctl start argus-apt-integrity.service
    sleep 5
    # Verificar que el nodo ha iniciado reboot
    # (en Vagrant esto se observa como desconexión de SSH)
"'

# En el host, verificar que journald persistió el evento antes del reboot
vagrant ssh hardened-x86 -c 'sudo journalctl -u argus-apt-integrity.service --no-pager'
# Esperado: "FAIL: APT sources hash mismatch" seguido de "Rebooting..."
```

---

### Q2 — DEBT-SEEDS-SECURE-TRANSFER-001

**Hipótesis:** La transferencia de seeds entre entornos de confianza es el momento de máximo riesgo criptográfico. Eliminar la transferencia es preferible a asegurarla.

**Veredicto: Opción C (generación local en hardened VM) es la arquitectónicamente correcta para el modelo P2P/federado. NO viola ADR-013.**

**Análisis de opciones:**

| Opción | Seguridad | Complejidad | Alineación con ADR-026/027 | Veredicto |
|--------|-----------|-------------|---------------------------|-----------|
| **A) SSH efímero** | Media | Baja | Neutro | Aceptable como fallback |
| **B) Noise IK** | Alta | Alta | Muy alta | Correcta para transferencia obligatoria |
| **C) Generación local** | **Máxima** | **Mínima** | **Muy alta** | **Recomendada** |
| **D) TPM/SGX** | Máxima | Media | Alta | Ideal post-FEDER |

**Justificación de Opción C:**

En una arquitectura P2P (ADR-026/027), cada nodo es una identidad criptográfica independiente. No hay razón técnica para que el nodo A y el nodo B compartan el mismo seed. Cada nodo debe generar su propio seed a partir de entropía del kernel (`getrandom(2)`, `/dev/urandom`) durante el provisioning inicial.

**¿Violación de ADR-013? No.** ADR-013 establece:
- Seeds a `0400 root:root`
- Seeds solo en runtime, nunca en CMake ni logs
- `mlock()` + `explicit_bzero()`
- `resolve_seed()` verifica permisos estrictos

Ninguna de estas reglas prohíbe la generación local. De hecho, la generación local **satisface** ADR-013 de forma más pura que la transferencia, porque elimina un vector de exposición (el canal de transferencia).

**Secuencia de generación local propuesta:**

```bash
# /usr/local/bin/argus-seed-init — ejecutado una vez en provisioning
# Firmado con Ed25519 del sistema (ADR-025)

#!/bin/bash
set -euo pipefail

COMPONENT=$1
SEED_DIR="/etc/ml-defender/${COMPONENT}"
SEED_FILE="${SEED_DIR}/seed.bin"

mkdir -p "$SEED_DIR"
chmod 0750 "$SEED_DIR"

# 32 bytes de entropía criptográfica del kernel
head -c 32 /dev/urandom > "$SEED_FILE"
chmod 0400 "$SEED_FILE"
chown root:root "$SEED_FILE"

# Verificación inmediata
if [ "$(stat -c %a "$SEED_FILE")" != "400" ]; then
    echo "FAIL: Seed permissions incorrect" >&2
    rm -f "$SEED_FILE"
    exit 1
fi

echo "OK: Seed generated locally for ${COMPONENT}"
```

**Cuándo usar Opción B (Noise IK):** Si el modelo pre-P2P (etcd centralizado) requiere que todos los nodos compartan un seed común (por ejemplo, para derivar claves de cifrado de flota), entonces la transferencia es inevitable. En ese caso, Noise IK es la opción correcta. Pero ADR-026/027 apuntan a P2P, donde cada nodo tiene su propia identidad.

**Riesgo identificado:** Si la generación local ocurre en una VM clonada (misma entropía inicial por snapshot), los seeds podrían no ser únicos. Mitigación: asegurar que la VM hardened se provisiona desde cero (`vagrant destroy && vagrant up`), no desde snapshot. En bare-metal, el TPM proporciona entropía única por dispositivo.

**Recomendación para post-FEDER:** Implementar Opción C como default. Documentar Opción B como fallback para escenarios pre-P2P o de recuperación de desastre donde un nodo debe restaurar su identidad previa desde backup cifrado.

---

### Q3 — Merge de `feature/adr030-variant-a` a `main`

**Hipótesis:** Un branch que pasa el gate pre-merge (`hardened-full` + `check-prod-all`) y no introduce regresiones en el EMECAS de desarrollo es candidato válido para merge.

**Veredicto: APROBADO para merge. Sin bloqueantes técnicos ni arquitectónicos identificados.**

**Justificación:**

| Criterio | Estado | Evaluación |
|----------|--------|------------|
| EMECAS dev (destroy + up + bootstrap + test-all) | ✅ PASSED (04:00 DAY 135) | Línea base limpia confirmada |
| EMECAS hardened (`hardened-full`) | ✅ PASSED | Reproducibilidad total desde cero |
| `check-prod-all` (5/5 gates) | ✅ PASSED | BSR, AppArmor, capabilities, permissions, Falco |
| Deudas pendientes | No bloqueantes | Compiler warnings (pre-existentes), secure transfer (post-FEDER), seeds deploy explícito (intencional) |
| Conflicto con `main` | No reportado | Asumido limpio |

**Bloqueantes potenciales que NO existen:**
- No hay cambios en la interfaz pública del pipeline (API ZeroMQ, protobuf)
- No hay cambios en el modelo ML (F1 invariante)
- No hay introducción de nuevas dependencias de runtime en la dev VM
- No hay modificación de `resolve_seed()` ni de las primitivas `safe_path`

**Condición de merge:** Ejecutar EMECAS dev una vez más en `main` **post-merge** para confirmar que la integración no introduce efectos de borde. Esto no es un bloqueante previo, es una verificación posterior.

**Riesgo identificado:** El merge introduce ~15 commits nuevos en `main`. Si otro desarrollador tiene un branch paralelo basado en `main` antiguo, podría haber conflictos en el `Makefile` (nuevos targets de producción). Mitigación: comunicar el merge inmediatamente al equipo y recomendar `git rebase main` en branches activos.

---

### Q4 — `hardened-redeploy` + `prod-deploy-seeds` en el flujo diario

**Hipótesis:** La separación entre deploy de infraestructura y deploy de material criptográfico es una barrera de seguridad intencional que no debe eliminarse por conveniencia.

**Veredicto: El flujo actual es CORRECTO. NO crear `hardened-full-with-seeds`.**

**Justificación:**

El deploy de seeds es una operación de **alto privilegio** que debe ser:
1. **Consciente:** El operador debe saber que está desplegando material criptográfico
2. **Auditada:** Debe quedar constancia de cuándo y qué seeds se desplegaron
3. **Reversible:** Debe poder eliminarse sin afectar la infraestructura subyacente

Si `hardened-full-with-seeds` existiera, un desarrollador podría ejecutarlo accidentalmente en un entorno de demostración, dejando seeds de producción (o de test) en una VM que luego se comparte. Esto viola el principio de **separación de concerns** y el BSR axiom (la VM de runtime no debe contener material de build, y viceversa).

**Flujo correcto documentado:**

```bash
# Iteración rápida (desarrollo, múltiples veces al día)
make hardened-redeploy        # Infraestructura + binarios
make check-prod-all           # Verificación

# Deploy de seeds (operación consciente, una vez por entorno)
make prod-deploy-seeds        # Material criptográfico
make check-prod-permissions   # Verificación de seeds

# Validación total (release, gate pre-merge)
make hardened-full            # Desde cero, sin seeds
# + manual: make prod-deploy-seeds (si el entorno requiere operación)
```

**Riesgo identificado:** La ausencia de `hardened-full-with-seeds` podría hacer que un operador olvide ejecutar `prod-deploy-seeds` después de `hardened-full`, dejando el sistema sin seeds y con componentes criptográficos fallando. Mitigación: `check-prod-all` debe incluir una verificación de que **si** el componente requiere criptografía (ej. `encryption_enabled=true`), **entonces** el seed existe. Durante EMECAS, los componentes no están habilitados, así que el check pasa. En operación, el check fallaría explícitamente.

---

### Q5 — Próximos pasos post-merge (DAY 136)

**Hipótesis:** La priorización post-merge debe maximizar el valor acumulado para FEDER mientras minimiza el riesgo de no entregar entregables tangibles.

**Evaluación de opciones:**

| Opción | Entregable | Riesgo de no entrega | Bloqueos | Contribución al paper | Veredicto |
|--------|-----------|----------------------|----------|----------------------|-----------|
| **A) FEDER prep** | Presentación | Alto (prereqs no cumplidos) | ADR-026 no merged, ADR-029 B no estable | Media | Prematuro |
| **B) ADR-029 Variant B** | Vagrantfile ARM64 + datos comparativos | Bajo | Ninguno (cross-compile o QEMU) | **Alta** (delta XDP/libpcap publicable) | **Recomendada** |
| **C) Compiler warnings** | Código limpio | Muy bajo | Ninguno | Baja | Paralelizable |

**Veredicto: Opción B — ADR-029 Variant B para DAY 136.**

**Justificación:**

1. **Contribución científica publicable:** El delta de rendimiento entre eBPF/XDP (Variant A) y libpcap (Variant B) es un dato empírico que no existe en la literatura para NDR de código abierto en ARM. Proporciona contenido concreto para §5 del paper y para la narrativa FEDER: *"Protección de grado hospitalario desde x86 hasta ARM64"*.
2. **Prerequisito de FEDER:** La demo FEDER requiere ADR-029 Variants A/B estables. Sin Variant B, la presentación carece de la dimensión de portabilidad hardware, que es un pilar del argumento de coste (150€ vs 15.000€).
3. **Scope acotado:** Un Vagrantfile `hardened-arm64/` con cross-compilation desde la dev VM x86 es un entregable de 1-2 días. No requiere hardware ARM físico (QEMU user-mode o Vagrant con box ARM64).
4. **Paralelismo:** Opción C (compiler warnings) puede ejecutarse en una rama paralela `fix/debt-compiler-warnings-001` sin ocupar el ciclo diario del Consejo. No requiere toma de decisiones arquitectónicas.

**Riesgo de Opción A (FEDER):** Preparar una presentación sin ADR-026 merged y sin Variant B estable es construir sobre cimientos inexistentes. El riesgo de tener que reescribir la presentación es alto.

**Plan DAY 136 propuesto:**

| Horario | Tarea |
|---------|-------|
| 05:00–08:00 | REGLA EMECAS dev + REGLA EMECAS hardened (confirmar main post-merge) |
| 08:30–12:00 | `vagrant/hardened-arm64/Vagrantfile` — Debian ARM64, AppArmor, sin compilador |
| 12:00–14:00 | Cross-compilation: `make build-production-arm64` desde dev VM x86 |
| 14:30–18:00 | Medición comparativa: throughput XDP (x86) vs libpcap (ARM64) con mismo pcap |
| 18:00–20:00 | Documentación: tabla de métricas para paper §5 + ADR-041 actualización |

**Métricas mínimas a obtener:**

| Métrica | x86 XDP | ARM64 libpcap | Delta |
|---------|---------|---------------|-------|
| Throughput máximo (Mbps) | ? | ? | ? |
| Latencia p50 (ms) | ? | ? | ? |
| CPU % a 100 Mbps | ? | ? | ? |
| RAM RSS (MB) | ? | ? | ? |

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | `FailureAction=reboot` aprobado; 30s suficiente para journald local; **NO configurable** vía etcd/JSON | Añadir `StartLimitIntervalSec=300` y `StartLimitBurst=2` a la unit |
| **Q2** | **Opción C** (generación local) recomendada para P2P; no viola ADR-013 | Implementar `argus-seed-init` como binario firmado en provisioning |
| **Q3** | **Merge aprobado** sin bloqueantes | Ejecutar EMECAS dev post-merge como verificación |
| **Q4** | **NO** a `hardened-full-with-seeds`; flujo actual correcto | Documentar flujo de 3 pasos; añadir check condicional de seeds en operación |
| **Q5** | **Opción B** (ADR-029 Variant B) para DAY 136 | Crear `vagrant/hardened-arm64/` + medición comparativa XDP/libpcap |

**Moción:** Propongo que el merge de `feature/adr030-variant-a` a `main` se ejecute inmediatamente tras esta sesión, seguido de un EMECAS dev de verificación. El DAY 136 debe comenzar con la creación de la infraestructura ARM64, no con la preparación de la presentación FEDER. Los datos comparativos de rendimiento son el insumo crítico que falta para que cualquier presentación sea creíble.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*