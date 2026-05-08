### **Respuestas del Consejo de Sabios — DAY 143**
*(Unánime 8/8, basado en **principios de seguridad operacional**, **diseño de sistemas críticos** y **pragmatismo para entornos hospitalarios**)*

---

---

## **🔍 Respuesta a P1: Zombies por `fork() + execv()` sin `wait()`**
**Veredicto:** **Sí, hay riesgo de acumulación de zombies. Solución: `waitpid(-1, WNOHANG)` periódico.**

### **Análisis:**
1. **Problema:**
    - **`fork() + execv()` sin `wait()`** → El proceso padre no recoge al hijo.
    - **Consecuencia:** Si el hijo termina (ej: `argus-network-isolate` falla), el proceso se convierte en **zombie** hasta que `init`/`systemd` lo recoge.
    - **Riesgo en producción:**
        - **Acumulación de zombies:** En un pipeline que dispara aislamientos repetidamente (ej: ransomware persistente), el número de zombies **crece indefinidamente**.
        - **Límite del sistema:** `kernel.pid_max` (por defecto: 32768 en Linux). Si se alcanza, **no se pueden crear nuevos procesos**.

2. **Solución recomendada:**
    - **Llamar a `waitpid(-1, WNOHANG)` periódicamente** en el hilo worker del `BatchProcessor`.
    - **Implementación:**
      ```cpp
      // En el loop principal del BatchProcessor (ej: cada 1000 eventos)
      while (true) {
          // Procesar eventos...
          process_batch();
 
          // Limpiar zombies cada 1000 eventos
          static int event_count = 0;
          if (++event_count % 1000 == 0) {
              while (waitpid(-1, nullptr, WNOHANG) > 0) {
                  // Limpiar todos los zombies pendientes
              }
          }
      }
      ```
    - **Alternativa (más robusta):**
        - Usar **`SIGCHLD`** para recibir notificaciones asíncronas:
          ```cpp
          // En el constructor del BatchProcessor
          signal(SIGCHLD, [](int) {
              while (waitpid(-1, nullptr, WNOHANG) > 0) {}
          });
          ```

3. **¿Por qué no `wait()` bloqueante?**
    - **Bloquearía el hilo worker** (el pipeline dejaría de procesar eventos mientras espera al hijo).

**Conclusión:**
✅ **Añadir `waitpid(-1, WNOHANG)` periódico (cada 1000 eventos) o manejar `SIGCHLD`.**

---
---

## **🔢 Respuesta a P2: Tolerancia IEEE 754 (`1e-6`) vs. Tipos Consistentes**
**Veredicto:** **Mantener `double` para el threshold y la tolerancia `1e-6`.**

### **Análisis:**
1. **Problema de precisión:**
    - **`float` vs `double`:**
        - `float`: ~7 dígitos de precisión.
        - `double`: ~15 dígitos de precisión.
    - **Ejemplo:**
      ```cpp
      float threshold = 0.95f;  // 0.94999988...
      double confidence = 0.95; // 0.95000000...
      // Comparación directa: confidence > threshold → false (incorrecto)
      ```

2. **Soluciones evaluadas:**
   | **Opción** | **Ventajas** | **Desventajas** | **Decisión** |
   |------------|--------------|----------------|--------------|
   | **Tolerancia `1e-6`** | Simple, funciona con tipos mixtos. | Requiere mantener tolerancia. | ✅ **Aprobado.** |
   | **Usar `float` para threshold** | Elimina el problema de raíz. | Pérdida de precisión en umbrales. | ❌ Rechazado. |
   | **Cast a `double` en comparación** | Precisión máxima. | Requiere cambios en todos los call sites. | ⚠️ Alternativa válida. |

3. **¿Por qué mantener `double` para el threshold?**
    - **Precisión:** `double` permite umbrales como `0.999999` (6 nueves) sin pérdida de información.
    - **Consistencia:** El modelo ML ya usa `double` para `confidence_score`.
    - **Flexibilidad:** Permite ajustar umbrales con mayor granularidad en el futuro.

4. **Recomendación adicional:**
    - **Documentar la tolerancia en el código:**
      ```cpp
      // Comparación con tolerancia para evitar problemas de precisión float/double
      // IEEE 754: float tiene ~7 dígitos de precisión; 1e-6 es seguro.
      bool should_auto_isolate(double confidence, double threshold) {
          return confidence >= threshold - 1e-6;
      }
      ```

**Conclusión:**
✅ **Mantener `double` para el threshold y tolerancia `1e-6`.**
---
---

## **🏥 Respuesta a P3: `auto_isolate: true` por defecto en hospitales**
**Veredicto:** **Cambiar a `auto_isolate: false` por defecto + gate de confirmación en el onboarding.**

### **Análisis:**
1. **Riesgo de `auto_isolate: true` por defecto:**
    - **Falso positivo en equipo médico crítico** → **Aislamiento automático** → **Pérdida de conectividad** → **Riesgo para vidas humanas**.
    - **Ejemplo:** Un monitor de quirófano podría ser aislado por un falso positivo en su tráfico de telemetría.

2. **Ventajas de `auto_isolate: false` por defecto:**
    - **Seguridad por defecto:** El admin **debe habilitar explícitamente** el aislamiento automático.
    - **Conciencia del riesgo:** El admin **lee la documentación** (o al menos el mensaje de confirmación).
    - **Alta disponibilidad:** Evita aislamientos accidentales en equipos críticos.

3. **Propuesta de compromiso:**
    - **Default:** `auto_isolate: false`.
    - **Onboarding:**
        - Mostrar un mensaje claro al primer arranque:
          ```
          ⚠️  aRGus IRP está deshabilitado.
          Para habilitar el aislamiento automático de red (recomendado para seguridad),
          edite /etc/ml-defender/firewall-acl-agent/isolate.json y establezca:
              "auto_isolate": true
          ADVERTENCIA: Esto puede aislar equipos médicos críticos en caso de falso positivo.
          ```
        - **Requerir confirmación explícita** (ej: `argus-enable-auto-isolate`).

4. **Documentación:**
    - Añadir en `docs/IRP.md`:
      ```markdown
      ### Configuración de Aislamiento Automático
      - **Por defecto:** `auto_isolate: false` (seguridad por defecto).
      - **Habilitar:**
        ```json
        {
          "auto_isolate": true,
          "threat_score_threshold": 0.95
        }
        ```
        - **Advertencia:** Solo habilitar en entornos donde los falsos positivos no pongan en riesgo vidas humanas.
      ```

**Conclusión:**
✅ **Cambiar a `auto_isolate: false` por defecto + gate de confirmación en el onboarding.**
---
---

## **🔒 Respuesta a P4: AppArmor y `/tmp/argus-*.nft`**
**Veredicto:** **Restringir a `/var/lib/argus/irp/` con permisos estrictos.**

### **Análisis:**
1. **Riesgo actual:**
    - **`/tmp/argus-*.nft`** es **escribible por cualquier proceso** que coincida con el glob.
    - **Ataque:** Un atacante que comprometa otro proceso (ej: `rag-ingester`) podría **escribir archivos maliciosos** en `/tmp` con nombres como `argus-backup-123.nft`.

2. **Solución recomendada:**
    - **Crear directorio dedicado:**
      ```bash
      mkdir -p /var/lib/argus/irp
      chown argus:argus /var/lib/argus/irp
      chmod 700 /var/lib/argus/irp
      ```
    - **Actualizar el perfil AppArmor:**
      ```apparmor
      /var/lib/argus/irp/argus-{backup,isolate}-*.nft rw,
      deny /tmp/** rw,  # Bloquear acceso a /tmp
      ```
    - **Actualizar `argus-network-isolate`:**
        - Usar `/var/lib/argus/irp/` en lugar de `/tmp/`.

3. **Ventajas:**
    - **Aislamiento:** Solo `argus-network-isolate` puede escribir en `/var/lib/argus/irp/`.
    - **Seguridad:** `/tmp` es un directorio compartido y peligroso.
    - **Consistencia:** Alineado con el principio **BSR** (Build/Security/Runtime).

**Conclusión:**
✅ **Restringir a `/var/lib/argus/irp/` con permisos `700`.**
---
---

## **🎯 Respuesta a P5: Criterio de Disparo Multi-Señal**
**Veredicto:** **Para FEDER, dos señales son suficientes. Registrar `DEBT-IRP-MULTI-SIGNAL-001` para post-FEDER con arquitectura de 3 señales.**

### **Análisis:**
1. **Criterio actual (FEDER):**
    - `score >= 0.95 AND event_type IN [ransomware, lateral_movement, c2_beacon]`.
    - **Ventajas:**
        - **Simple y auditable.**
        - **Alta precisión:** El modelo de aRGus tiene F1=0.9985, por lo que `score >= 0.95` es muy confiable.

2. **Riesgo en entornos hospitalarios:**
    - **Falso positivo en equipo crítico** → Aislamiento automático → **Riesgo para vidas humanas**.
    - **Mitigación:** `auto_isolate: false` por defecto (P3).

3. **Arquitectura de 3 señales (post-FEDER):**
    - **Señal 1:** `score >= 0.95` (modelo ML).
    - **Señal 2:** `event_type IN [ransomware, lateral_movement, c2_beacon]` (tipo de evento).
    - **Señal 3:** **Confirmación de segundo sensor** (ej: Falco detecta actividad sospechosa en el mismo host).
        - **Implementación:**
          ```json
          {
            "auto_isolate": true,
            "threat_score_threshold": 0.95,
            "auto_isolate_event_types": ["ransomware", "lateral_movement", "c2_beacon"],
            "require_second_sensor": true,
            "second_sensor_types": ["falco", "suricata"]
          }
          ```
    - **Ventaja:** Reduce falsos positivos en entornos críticos.

4. **Documentación para FEDER:**
    - Añadir en `docs/LIMITATIONS.md`:
      ```markdown
      ### Limitaciones del Criterio de Aislamiento (FEDER)
      - **Criterio actual:** `score >= 0.95 AND event_type IN [ransomware, lateral_movement, c2_beacon]`.
      - **Riesgo:** Falsos positivos en equipos médicos críticos.
      - **Mitigación:** `auto_isolate: false` por defecto + confirmación explícita.
      - **Futuro:** Arquitectura de 3 señales (post-FEDER).
      ```

**Conclusión:**
✅ **Para FEDER, dos señales son suficientes.**
✅ **Registrar `DEBT-IRP-MULTI-SIGNAL-001` para post-FEDER con arquitectura de 3 señales.**
---
---
---
## **📌 Resumen de Decisiones para DAY 144**
*(Priorizadas por impacto en FEDER y seguridad operacional)*

| **Acción** | **Prioridad** | **Detalle** | **Owner** |
|------------|---------------|-------------|-----------|
| **Añadir `waitpid(-1, WNOHANG)` periódico** | 🔴 **P0** | Evitar acumulación de zombies. | Alonso |
| **Mantener `double` + tolerancia `1e-6`** | 🔴 **P0** | Precisión y consistencia. | Alonso |
| **Cambiar `auto_isolate: false` por defecto** | 🔴 **P0** | Seguridad por defecto. | Alonso |
| **Restringir AppArmor a `/var/lib/argus/irp/`** | 🔴 **P0** | Evitar escritura en `/tmp`. | Alonso |
| **Merge `feature/variant-b-libpcap` a `main`** | 🔴 **P0** | EMECAS verde + tests PASSED. | Alonso |
| **Registrar `DEBT-IRP-MULTI-SIGNAL-001`** | 🟡 **P1** | Arquitectura de 3 señales. | Consejo |
| **Documentar limitaciones en `docs/LIMITATIONS.md`** | 🟢 **P2** | Para FEDER. | Alonso |

---
---
## **📢 Observación Final del Consejo**
> *"Las decisiones tomadas en DAY 143 —especialmente el cambio a `auto_isolate: false` por defecto y la restricción de AppArmor a `/var/lib/argus/irp/`— reflejan un **equilibrio perfecto entre seguridad y disponibilidad**, crítico para entornos hospitalarios. Para DAY 144, el foco debe estar en **resolver los riesgos de zombies y el merge a `main`**, ya que son bloqueantes para la estabilidad del pipeline. La arquitectura de 3 señales y el backup de reglas nftables son mejoras valiosas, pero pueden esperar a post-FEDER sin poner en riesgo el deadline del 1 de agosto. Vuestra atención al detalle en temas como la tolerancia IEEE 754 o la gestión de procesos zombies demuestra el nivel de rigor necesario para proteger infraestructuras críticas."*

**¿Necesitáis ayuda con la implementación de `waitpid(-1, WNOHANG)` o el cambio de `auto_isolate` a `false`?**
Estamos listos para proporcionar ejemplos de código o revisiones técnicas.