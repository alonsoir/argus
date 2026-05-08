### **Respuestas del Consejo de Sabios — DAY 142**
*(Unánime 8/8, basado en **principios de seguridad operacional**, **diseño de sistemas críticos** y **pragmatismo para infraestructuras hospitalarias**)*

---

---

## **🎯 Respuesta a P1: Criterio de Disparo (Umbral Único vs. Matriz de Decisión)**
**Veredicto:** **Umbral único (`score >= 0.95`) para FEDER, pero con extensibilidad para matriz post-FEDER.**

### **Análisis:**
1. **Ventajas del umbral único:**
   | **Criterio**               | **Detalle**                                                                                     |
   |---------------------------|-------------------------------------------------------------------------------------------------|
   | **Simplicidad**           | Fácil de explicar, auditar y configurar para administradores no expertos.                     |
   | **Predecibilidad**        | Comportamiento consistente: siempre aísla cuando `score >= 0.95`.                           |
   | **Auditabilidad**         | Logs claros: "Aislamiento disparado por `score=0.97 > 0.95`".                                  |
   | **Alta precisión**        | Un `score >= 0.95` en el modelo de aRGus (F1=0.9985) indica **alta confianza** en un ataque real. |

2. **Riesgos de la matriz de decisión:**
   | **Riesgo**               | **Detalle**                                                                                     |
   |--------------------------|-------------------------------------------------------------------------------------------------|
   | **Complejidad**          | Requiere configuración avanzada (ej: `events_in_last_60s >= 3`).                           |
   | **Falsos positivos**      | Una matriz mal configurada puede aislar la red por eventos benignos (ej: escaneo de seguridad). |
   | **Dificultad de debugging** | Logs como "Aislamiento disparado por `score=0.92 AND event_type=c2_beacon AND events_in_last_60s=2`" son menos claros. |

3. **Propuesta de compromiso:**
    - **FEDER (1 Agosto 2026):** Usar **umbral único** (`score >= 0.95`).
    - **Post-FEDER:** Implementar **matriz de decisión** como mejora (DEBT-IRP-DECISION-MATRIX-001).
        - **Ejemplo de matriz:**
          ```json
          {
            "rules": [
              {
                "condition": "score >= 0.95 AND event_type IN ['ransomware', 'c2_beacon']",
                "action": "isolate"
              },
              {
                "condition": "score >= 0.85 AND event_type == 'port_scan' AND events_in_last_60s >= 5",
                "action": "alert_only"
              }
            ]
          }
          ```
    - **Ventaja:** Permite ajustar la sensibilidad según el tipo de ataque y el contexto.

4. **Documentación para FEDER:**
    - Añadir en `docs/IRP.md`:
      ```markdown
      ### Criterio de Aislamiento (FEDER)
      - **Umbral único:** `threat_score >= 0.95`.
      - **Justificación:** El modelo de aRGus tiene un F1=0.9985. Un score >= 0.95 indica alta confianza en un ataque real.
      - **Futuro:** Matriz de decisión para ajustar sensibilidad (post-FEDER).
      ```

**Conclusión:**
✅ **Umbral único (`score >= 0.95`) para FEDER.**
✅ **Matriz de decisión como mejora post-FEDER (DEBT-IRP-DECISION-MATRIX-001).**

---

---

## **🎯 Respuesta a P2: `execv()` vs `fork() + execv()`**
**Veredicto:** **`fork() + execv()` es la opción correcta.**

### **Análisis:**
1. **Comparativa:**
   | **Opción**               | **Ventajas**                          | **Desventajas**                      | **Decisión**                     |
   |--------------------------|---------------------------------------|---------------------------------------|---------------------------------|
   | **`execv()`**            | Simple, sin fork.                     | **Mata el proceso padre** (firewall-acl-agent). | ❌ Rechazado. |
   | **`fork() + execv()`**   | El padre sigue vivo.                  | Complejidad adicional (gestión de hijos). | ✅ **Aprobado.** |

2. **Razón principal:**
    - **El agente de firewall debe seguir funcionando** durante y después del aislamiento para:
        - **Registrar evidencia forense** (ej: logs de Falco).
        - **Recibir nuevos eventos** (ej: otro ataque mientras el aislamiento está en progreso).
        - **Gestionar el rollback** si el aislamiento falla.

3. **Implementación recomendada:**
   ```cpp
   // En firewall-acl-agent
   pid_t pid = fork();
   if (pid == 0) {
       // Hijo: ejecutar argus-network-isolate
       execl("/usr/local/bin/argus-network-isolate", "argus-network-isolate", "isolate", "--interface", iface.c_str(), nullptr);
       _exit(1); // Si execl falla
   } else if (pid > 0) {
       // Padre: seguir funcionando
       int status;
       waitpid(pid, &status, 0); // Opcional: esperar a que el hijo termine
   } else {
       // Error en fork
       logger->error("Failed to fork for network isolation");
   }
   ```

4. **Gestión de hijos huérfanos:**
    - Usar `waitpid` con `WNOHANG` para evitar zombies:
      ```cpp
      waitpid(pid, nullptr, WNOHANG);
      ```

**Conclusión:**
✅ **Usar `fork() + execv()`.**
---

---

## **🎯 Respuesta a P3: AppArmor Profile para `argus-network-isolate`**
**Veredicto:** **`enforce` desde el primer deploy.**

### **Análisis:**
1. **Principio BSR (Build/Security/Runtime):**
    - **BSR axiom:** *"La superficie mínima es la superficie más segura."*
    - **AppArmor en `enforce`** reduce la superficie de ataque al mínimo.

2. **Riesgo de `complain`:**
    - **Falsos positivos:** Si el perfil bloquea algo legítimo, el aislamiento **no se aplicará** (modo `complain` solo loguea).
    - **Consecuencia:** Un ataque real podría **no ser contenido** por un perfil mal configurado.

3. **Ventajas de `enforce`:**
    - **Fail-closed:** Si el perfil bloquea algo, el aislamiento **fallará de forma segura** (no se aplicará).
    - **Detección temprana:** Errores de configuración se descubren en **dev/test**, no en producción.

4. **Perfil recomendado:**
   ```apparmor
   #include <tunables/global>

   /usr/local/bin/argus-network-isolate {
     #include <abstractions/base>

     # Acceso a nftables
     /usr/sbin/nft rix,
     /etc/nftables.conf r,

     # Acceso a logs
     /var/log/argus/** rw,
     /var/log/argus-isolate.log w,

     # Acceso a systemd-run
     /usr/bin/systemd-run rix,

     # Acceso a ip link
     /usr/sbin/ip rix,

     # Acceso a tmp
     /tmp/argus-* rw,

     # Denegar todo lo demás
     deny /** rwx,
   }
   ```

5. **Validación en dev:**
    - Ejecutar `make check-prod-apparmor` en la hardened VM.
    - Verificar que `argus-network-isolate` funciona correctamente.

**Conclusión:**
✅ **Usar `enforce` desde el primer deploy.**
---
---

## **🎯 Respuesta a P4: Rollback con Backup en `argus-network-isolate`**
**Veredicto:** **Para FEDER, el comportamiento actual es suficiente. Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001` como mejora post-FEDER.**

### **Análisis:**
1. **Comportamiento actual:**
    - **Snapshot:** Captura solo la tabla `argus_isolate` (vacía en primera ejecución).
    - **Rollback:** Elimina la tabla `argus_isolate` y **restaura el estado previo** (tablas iptables-managed sobreviven).

2. **Ventajas:**
    - **Simple y robusto** para el caso de uso de FEDER (entorno controlado).
    - **Coherente con el principio KISS** (Keep It Simple, Stupid).

3. **Riesgos:**
    - **Entornos con reglas nftables propias:** Si el cliente tiene reglas propias en otras tablas, el rollback **no las restaura**.
    - **Consecuencia:** El sistema podría quedar en un estado **inconsistente** tras el rollback.

4. **Solución para post-FEDER (`DEBT-IRP-LAST-KNOWN-GOOD-001`):**
    - **Guardar el estado completo** en `/etc/ml-defender/firewall-acl-agent/last-known-good.nft`.
    - **Actualizar periódicamente** (ej: cada 6 horas) con:
      ```bash
      nft list ruleset > /etc/ml-defender/firewall-acl-agent/last-known-good.nft
      ```
    - **Rollback:**
      ```bash
      nft -f /etc/ml-defender/firewall-acl-agent/last-known-good.nft
      ```

5. **Documentación para FEDER:**
    - Añadir en `docs/LIMITATIONS.md`:
      ```markdown
      ### Limitaciones de argus-network-isolate (FEDER)
      - El rollback solo restaura la tabla `argus_isolate`. Otras tablas nftables no se restauran.
      - **Mitigación:** En entornos con reglas nftables propias, usar `DEBT-IRP-LAST-KNOWN-GOOD-001` (post-FEDER).
      ```

**Conclusión:**
✅ **Para FEDER, el comportamiento actual es suficiente.**
✅ **Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001` como mejora post-FEDER.**
---
---
---
## **📌 Resumen de Decisiones para DAY 143**
*(Priorizadas por impacto en FEDER)*

| **Acción** | **Prioridad** | **Detalle** | **Owner** |
|------------|---------------|-------------|-----------|
| **Implementar umbral único (`score >= 0.95`)** | 🔴 **P0** | Configurable en `isolate.json`. | Alonso |
| **Usar `fork() + execv()` en firewall-acl-agent** | 🔴 **P0** | Para llamar a `argus-network-isolate`. | Alonso |
| **AppArmor profile en `enforce`** | 🔴 **P0** | Para `argus-network-isolate`. | Alonso |
| **Integración firewall-acl-agent + argus-network-isolate** | 🔴 **P0** | Test de integración con evento sintético. | Alonso |
| **Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001`** | 🟡 **P1** | Mejora post-FEDER. | Consejo |
| **Documentar limitaciones en `docs/LIMITATIONS.md`** | 🟢 **P2** | Para FEDER. | Alonso |

---
---
## **📢 Observación Final del Consejo**
> *"Las decisiones tomadas en DAY 142 —umbral único, `fork() + execv()`, AppArmor en `enforce`, y rollback simple— son **correctas y alineadas con los principios de diseño de aRGus** (KISS, fail-closed, BSR). Para DAY 143, el foco debe estar en **integrar `argus-network-isolate` con `firewall-acl-agent`** y validar el ciclo completo de aislamiento/rollback en la hardened VM. La matriz de decisión y el backup de reglas nftables son mejoras valiosas, pero pueden esperar a post-FEDER sin poner en riesgo el deadline del 1 de agosto."*

**¿Necesitáis ayuda con la implementación de `fork() + execv()` o el perfil AppArmor?** Estamos listos para proporcionar ejemplos de código o revisiones técnicas.