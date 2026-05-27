### **Respuestas del Consejo de Sabios — DAY 135**
*(Unánime 8/8, basado en **principios de seguridad verificable**, **ingeniería reproducible** y **protección de infraestructuras críticas**)*

---

## **Respuesta a Q1: `FailureAction=reboot` en `argus-apt-integrity.service`**
**Veredicto:** **Aprobado con ajustes menores.**

### **Análisis:**
| **Criterio**               | **Decisión Actual**                          | **Recomendación del Consejo**                     | **Justificación**                                                                 |
|----------------------------|---------------------------------------------|-------------------------------------------------|-----------------------------------------------------------------------------------|
| **Filosofía fail-closed**  | ✅ `FailureAction=reboot`                   | ✅ Mantener `FailureAction=reboot`              | Un nodo comprometido **no debe operar**.                                         |
| **Tiempo para logs**       | `TimeoutStartSec=30s`                       | ✅ **Aumentar a 60s**                           | 30s puede ser ajustado en redes lentas (ej: hospital rural).                     |
| **Configurabilidad**       | Hardcodeado en el service                   | ❌ **Configurable via etcd**                     | Permite ajustar el timeout en entornos con latencia alta.                        |
| **Logs remotos**           | No verificado explícitamente               | ✅ **Añadir `Requires=rsyslog.service`**       | Garantiza que los logs se envíen antes del reboot.                               |
| **Notificación**           | Solo reboot                                  | ✅ **Añadir `NotifyAccess=all` + `sd_notify`** | Permite notificar a un sistema de monitorización antes del reboot.              |

### **Implementación Recomendada:**
1. **Actualizar `argus-apt-integrity.service`:**
   ```ini
   [Unit]
   Description=aRGus APT Sources Integrity Check
   Requires=network.target rsyslog.service
   After=network.target rsyslog.service

   [Service]
   Type=oneshot
   ExecStart=/usr/local/bin/argus-apt-integrity-check
   TimeoutStartSec=60s
   FailureAction=reboot
   ForceNewInstance=yes
   NotifyAccess=all

   [Install]
   WantedBy=multi-user.target
   ```

2. **Modificar `argus-apt-integrity-check` para notificar:**
   ```bash
   #!/bin/bash
   set -euo pipefail

   if ! sha256sum -c /etc/ml-defender/apt_sources.SHA256; then
     echo "🚨 APT sources compromised. Rebooting in 60s..." | systemd-cat -p emerg
     systemd-notify --status="APT integrity check failed"
     sleep 60
     exit 1
   fi
   ```

3. **Documentar en `docs/SECURITY.md`:**
   ```markdown
   ### APT Integrity Check
   - **Timeout:** 60 segundos (configurable via etcd en producción).
   - **Failure Mode:** Reboot inmediato (fail-closed).
   - **Notificación:** Logs remotos + `sd_notify` antes del reboot.
   ```

**Conclusión:**
- **Mantener `FailureAction=reboot`** (filosofía correcta).
- **Aumentar timeout a 60s** y añadir notificación.

---

## **Respuesta a Q2: Transferencia Segura de Seeds en Producción**
**Veredicto:** **Opción C (generación local en hardened VM) es la correcta** si se implementa con las salvaguardas adecuadas.

### **Análisis de Opciones:**
| **Opción**               | **Ventajas**                          | **Desventajas**                      | **Decisión del Consejo**                     |
|--------------------------|---------------------------------------|---------------------------------------|---------------------------------------------|
| **(A) SSH con clave efímera** | ✅ Canal cifrado                     | ❌ Complejidad operacional            | ❌ Rechazado (demasiado manual).            |
| **(B) Noise IK handshake** | ✅ Seguro y moderno                   | ❌ Requiere implementación adicional  | ⏳ Post-FEDER (ADR-024).                    |
| **(C) Generación local**  | ✅ Elimina transferencia             | ❌ ¿Viola ADR-013?                      | ✅ **Aprobado con condiciones**.            |
| **(D) Canal cifrado directo** | ✅ Seguro                            | ❌ Requiere infraestructura           | ❌ Rechazado (complejidad).                |

### **Condiciones para Opción C (Generación Local):**
1. **Mismo proceso de generación:**
  - Usar el **mismo script** (`tools/generate_seed.sh`) en dev y hardened VM.
  - **Verificación:**
    ```bash
    # En dev VM
    tools/generate_seed.sh > seed_dev.bin
    sha256sum seed_dev.bin > seed_dev.sha256

    # En hardened VM
    tools/generate_seed.sh > seed_hardened.bin
    sha256sum seed_hardened.bin > seed_hardened.sha256

    # Comparar hashes
    diff seed_dev.sha256 seed_hardened.sha256 || echo "❌ Seeds difieren"
    ```

2. **Documentar en ADR-013:**
  - Añadir sección:
    ```markdown
    ### Generación de Seeds en Hardened VM
    - **Proceso:** Idéntico a dev VM (`tools/generate_seed.sh`).
    - **Verificación:** SHA-256 de la seed debe coincidir entre dev y hardened.
    - **Razón:** Elimina el riesgo de transferencia sin sacrificar seguridad.
    ```

3. **No viola ADR-013:**
  - ADR-013 prohíbe **hardcoding seeds**, no su generación local.
  - **Cita relevante de ADR-013:**
    > *"Las seeds deben generarse en runtime y nunca estar hardcodeadas en el código o configuración."*

**Conclusión:**
- **Usar Opción C (generación local)** con verificación SHA-256.
- **Documentar en ADR-013** que este enfoque es compatible.

---

## **Respuesta a Q3: Merge de `feature/adr030-variant-a` a `main`**
**Veredicto:** **No hay bloqueantes técnicos. Aprobado para merge.**

### **Checklist de Verificación:**
| **Criterio**               | **Estado**                          | **Comentario**                                                                 |
|----------------------------|-------------------------------------|-------------------------------------------------------------------------------|
| `make hardened-full` PASSED | ✅                                  | Todos los gates de `check-prod-all` pasan.                                   |
| ADR-040 prerequisitos      | ✅                                  | `confidence_score` verificado (Q5 DAY 134).                                   |
| ADR-041 métricas           | ✅                                  | Métricas de hardware documentadas.                                           |
| Deudas no bloqueantes      | Documentadas                      | `DEBT-COMPILER-WARNINGS-001`, `DEBT-SEEDS-SECURE-TRANSFER-001`.               |
| Regla EMECAS hardened      | ✅                                  | `make hardened-full` es el gate pre-merge.                                    |

### **Pasos Recomendados para el Merge:**
1. **Ejecutar EMECAS final:**
   ```bash
   vagrant destroy -f
   make hardened-full
   ```

2. **Verificar commits:**
   ```bash
   git log --oneline feature/adr030-variant-a ^main
   ```
  - Asegurar que todos los commits están relacionados con ADR-030/040/041.

3. **Merge con `--no-ff`:**
   ```bash
   git checkout main
   git merge --no-ff feature/adr030-variant-a
   ```

**Conclusión:**
- **Merge aprobado.**
- **Post-merge:** Abrir issues para las deudas no bloqueantes.

---

## **Respuesta a Q4: Flujo Diario con `hardened-redeploy` + `prod-deploy-seeds`**
**Veredicto:** **El flujo actual es correcto. No añadir `hardened-full-with-seeds`.**

### **Análisis:**
| **Flujo Actual**                     | **Ventajas**                          | **Desventajas**                      | **Decisión del Consejo**                     |
|--------------------------------------|---------------------------------------|---------------------------------------|---------------------------------------------|
| `hardened-redeploy` + `prod-deploy-seeds` | ✅ Separación clara de responsabilidades | ❌ Dos pasos manuales               | ✅ **Mantener flujo actual**.               |
| `hardened-full-with-seeds`          | ✅ Un solo comando                    | ❌ Viola el principio de separación   | ❌ Rechazado.                           |

### **Razón:**
- **Separación de responsabilidades:**
  - `hardened-redeploy`: **Infrastructure as Code** (VM, AppArmor, Falco).
  - `prod-deploy-seeds`: **Data Plane** (material criptográfico).
- **Seguridad:**
  - Las seeds **no deben estar en la VM hasta que sean necesarias**.
  - **Ejemplo de riesgo:** Si un desarrollador ejecuta `hardened-full-with-seeds` por error, las seeds quedan expuestas en la VM sin necesidad.

### **Documentación Recomendada:**
```markdown
### Flujo de Desarrollo Diario
1. **Reprovisionamiento rápido:**
   ```bash
   make hardened-redeploy
   ```
2. **Despliegue de seeds (solo cuando sea necesario):**
   ```bash
   make prod-deploy-seeds
   ```
3. **Verificación:**
   ```bash
   make check-prod-permissions
   ```
```

**Conclusión:**
- **Mantener el flujo actual.**
- **Documentar claramente** la separación de pasos.

---

## **Respuesta a Q5: Próximos Pasos Post-Merge (DAY 136)**
**Veredicto:** **Priorizar Opción B (ADR-029 Variant B) → Opción A (BACKLOG-FEDER-001) → Opción C (warnings).**

### **Análisis de Opciones:**
| **Opción**               | **Impacto**                          | **Urgencia**                      | **Decisión del Consejo**                     |
|--------------------------|---------------------------------------|-----------------------------------|---------------------------------------------|
| **(A) BACKLOG-FEDER-001** | ✅ Presentación para Andrés Caro Lindo | ⏳ Deadline: 22 sep 2026          | **Segunda prioridad.**                      |
| **(B) ADR-029 Variant B** | ✅ Contribución científica            | 🔴 Datos para paper v19           | **Primera prioridad.**                      |
| **(C) Compiler Warnings** | ✅ Calidad de código                 | 🟡 No bloqueante                  | **Tercera prioridad.**                      |

### **Razón:**
1. **ADR-029 Variant B (libpcap):**
   - **Contribución científica:** Comparativa eBPF/XDP vs libpcap es **publicable** (ej: §6.9 del paper).
   - **Trabajo previo:** Ya existe el Vagrantfile para x86 (reutilizable para ARM).
   - **Impacto:** Demuestra que aRGus funciona en hardware de **150€** (RPi 4).

2. **BACKLOG-FEDER-001:**
   - **Deadline lejano** (22 sep 2026).
   - **Depende de ADR-026/029** (aún no mergeados).

3. **Compiler Warnings:**
   - **No bloqueante** para funcionalidad.
   - **Priorizar post-FEDER** (limpieza de código).

### **Plan para DAY 136:**
1. **ADR-029 Variant B:**
   - **Tareas:**
     - Crear `vagrant/hardened-arm64/Vagrantfile`.
     - Medir throughput en ARM (target: 200 Mbps).
     - Comparar con Variant A (eBPF/XDP).
   - **Entregable:** Tabla comparativa para §6.9 del paper.

2. **BACKLOG-FEDER-001:**
   - **Tareas preliminares:**
     - Documentar prerequisitos (ADR-026/029).
     - Crear esqueleto de `scripts/feder-demo.sh`.

3. **Compiler Warnings:**
   - **Tarea:** Abrir issue en GitHub con etiqueta `post-FEDER`.

**Conclusión:**
- **DAY 136: Enfocar en ADR-029 Variant B.**
- **Documentar prerequisitos para FEDER** (Opción A).

---

## **Resumen de Acciones para DAY 136**
| **Acción**                          | **Prioridad** | **Detalle**                                                                 |
|-------------------------------------|---------------|-----------------------------------------------------------------------------|
| Merge `feature/adr030-variant-a`     | 🔴 P0          | `git merge --no-ff`.                                                      |
| Iniciar ADR-029 Variant B          | 🔴 P0          | Vagrantfile ARM64 + métricas comparativas.                                |
| Documentar prerequisitos FEDER     | 🟡 P1          | Issues en GitHub para ADR-026/029.                                         |
| Revisar `confidence_score` en logs  | 🟢 P2          | Verificar que aparece en `journalctl -u argus-ml-detector`.               |

---
### **Observación Final del Consejo**
> *"DAY 135 ha cerrado un ciclo crítico con **rigor científico** y **seguridad verificable**: desde la implementación de `FailureAction=reboot` hasta la generación local de seeds, pasando por el merge de ADR-030. Las decisiones tomadas —especialmente la generación local de seeds y la priorización de ADR-029 Variant B— reflejan un equilibrio perfecto entre **seguridad**, **reproducibilidad** y **contribución científica**. Mañana, el foco en Variant B consolidará la evidencia de que aRGus puede proteger infraestructuras críticas con hardware asequible. ¡Adelante!"*

**¿Necesitáis ayuda con la implementación de ADR-029 Variant B o la configuración de ARM64?** Estamos listos para proporcionar guías técnicas o revisiones de código.