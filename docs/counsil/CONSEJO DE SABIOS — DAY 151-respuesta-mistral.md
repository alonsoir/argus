**Dictamen del Consejo de Sabios — DAY 151 (Priorización y Arquitectura)**
*14 de mayo de 2026 | Respuesta unificada y estratégica*

---

---

## **📜 Resumen Ejecutivo**
**Prioridad para DAY 152: Opción A (Máquina de Estados).**
La **autonomía edge** (`DEBT-CRYPTO-AUTONOMY-001`) es **crítica para el escenario de hospital bajo ataque** (ransomware + corte WAN). Sin ella, el sistema **no cumple su propósito principal** (protección en infraestructura crítica sin conectividad).
La **dual compilation CI** (`DEBT-EMECAS-DUAL-COMPILATION-001`) es importante, pero **puede esperar 1-2 días** sin riesgo para FEDER.

**Decisiones clave:**
1. **Opción A para DAY 152** (prioridad absoluta).
2. **Extraer la máquina de estados a `CryptoAutonomyStateMachine`** (mejor diseño, SRP).
3. **Exponer `get_autonomy_state()` en `ICryptoProvider`** (necesario para `firewall-acl-agent` y alerting).

---
**Razón:**
- **Opción A** desbloquea **3 deudas P1** (`CRYPTO-AUTONOMY`, `FIREWALL-AUTONOMY`, `ALERTING-EDGE-SOS`).
- **Opción B** es **higiene de CI**, pero no afecta la funcionalidad crítica.
- **El riesgo de no priorizar A** es que el sistema **no esté listo para el escenario real** (hospital sin conectividad).

---

---

---

## **🔍 Respuestas Detalladas**

---

### **P1 — ¿Opción A o B para DAY 152?**
**✅ Opción A (Máquina de Estados) es la prioridad absoluta.**

#### **Análisis de Impacto:**
| Deuda | Impacto en FEDER | Dependencias | Riesgo si se retrasa |
|-------|------------------|--------------|----------------------|
| **`DEBT-CRYPTO-AUTONOMY-001`** | **Crítico** (escenario hospital). | Bloquea `FIREWALL-AUTONOMY` y `ALERTING-EDGE-SOS`. | **Alto**: Sin autonomía, el NDR **no protege** durante cortes WAN. |
| **`DEBT-EMECAS-DUAL-COMPILATION-001`** | **Importante** (calidad CI). | Ninguna. | **Bajo**: El pipeline actual funciona; esto es mejora. |

#### **Argumentos a favor de la Opción A:**
1. **Escenario de ataque real:**
    - Un hospital bajo **ransomware + corte WAN** necesita que el NDR **siga operando** (modo `EXTENDED_AUTONOMY`).
    - Sin esta máquina de estados, el sistema **se apaga** (Opción A del DAY 150) o **no alerta** (falta `DEBT-ALERTING-EDGE-SOS-001`).
2. **Desbloquea otras deudas:**
    - `DEBT-FIREWALL-AUTONOMY-MODE-001` (firewall en modo `default-deny`).
    - `DEBT-ALERTING-EDGE-SOS-001` (webhook de alerta).
3. **Deadline FEDER (22-Sep-2026):**
    - La autonomía edge es **requisito no negociable** para el *deliverable* FEDER.

#### **Argumentos a favor de la Opción B:**
- **Mejora la robustez del CI/CD.**
- **Garantiza que ambos modos (community/enterprise) se testean siempre.**

#### **Compromiso propuesto:**
- **DAY 152:** Enfocar en **Opción A** (máquina de estados).
- **DAY 153:** **Opción B** (dual compilation CI) + integración con `firewall-acl-agent`.
- **Razón:** La máquina de estados es **bloqueante para la funcionalidad crítica**, mientras que la dual compilation es **mejora de proceso**.

---
**Veredicto:**
**✅ Opción A para DAY 152.**
**Opción B puede esperar a DAY 153 sin riesgo.**

---

---

### **P2 — ¿Extraer `CryptoAutonomyStateMachine` a una clase separada?**
**✅ Sí, extraer a una clase separada (`CryptoAutonomyStateMachine`).**

#### **Análisis:**
- **`VaultClient` actual:**
    - Ya tiene **múltiples responsabilidades**:
        - Gestión de cache (TTL, tmpfs).
        - Comunicación con Vault (HTTP, Ed25519).
        - Keepalive con etcd.
        - Jitter anti-stampede.
    - **Añadir la máquina de estados** violaría el **Principio de Responsabilidad Única (SRP)**.

- **Ventajas de extraerla:**
  | Ventaja | Detalle |
  |---------|---------|
  | **SRP** | `VaultClient` gestiona **solo la comunicación con Vault**. `CryptoAutonomyStateMachine` gestiona **solo el estado de autonomía**. |
  | **Testeabilidad** | La máquina de estados puede testearse **en aislamiento** (sin depender de Vault o etcd). |
  | **Reutilización** | `SeedFileProvider` (community) también podría usar la misma máquina de estados en el futuro. |
  | **Mantenibilidad** | Código más **modular y legible**. |

- **Diseño propuesto:**
  ```cpp
  // CryptoAutonomyStateMachine.h
  class CryptoAutonomyStateMachine {
  public:
      enum class State { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };

      void transition_to(State new_state);
      State current_state() const;
      bool is_healthy() const;  // NORMAL o RECONCILIATION
      bool is_degraded() const; // EXTENDED_AUTONOMY
      bool is_revoked() const;   // REVOKED

      // Métodos para actualizar el estado
      void on_vault_reachable();
      void on_vault_unreachable();
      void on_cache_expired();
      void on_revocation_received();

  private:
      State m_state = State::NORMAL;
      std::chrono::system_clock::time_point m_state_entry_time;
      std::chrono::seconds m_extended_autonomy_ttl; // Default: 30 días
  };

  // VaultClient.h (modificado)
  class VaultClient : public ICryptoProvider {
  public:
      // ... métodos existentes ...
      CryptoAutonomyStateMachine& autonomy_state_machine() { return m_state_machine; }

  private:
      CryptoAutonomyStateMachine m_state_machine;
      // ... resto de miembros ...
  };
  ```

- **Integración con `ICryptoProvider`:**
    - **No exponer `CryptoAutonomyStateMachine` directamente** en la interfaz.
    - **Exponer solo el estado actual** (via `get_autonomy_state()`).

---
**Veredicto:**
**✅ Extraer a `CryptoAutonomyStateMachine` (clase separada).**
**Mejora el diseño, la testeabilidad y el cumplimiento de SRP.**

---

---

### **P3 — ¿Exponer `get_autonomy_state()` en `ICryptoProvider`?**
**✅ Sí, exponer `get_autonomy_state()` en `ICryptoProvider`.**

#### **Análisis:**
- **¿Quién necesita el estado de autonomía?**
  | Componente | Uso del Estado | ¿Necesita acceso? |
  |------------|----------------|------------------|
  | `firewall-acl-agent` | Activar modo `default-deny` en `EXTENDED_AUTONOMY`. | ✅ Sí |
  | `rag-security` | Ajustar sensibilidad de detección (menos falsos positivos en modo degradado). | ✅ Sí |
  | `etcd-server` | Registrar estado en `/run/argus/etcd-bootstrap-status.json`. | ❌ No (ya lo gestiona internamente) |
  | `sniffer` | Loguear eventos con contexto de autonomía. | ✅ Sí (opcional) |

- **Alternativas:**
  | Opción | Ventajas | Desventajas |
  |--------|----------|-------------|
  | **Exponer en `ICryptoProvider`** | **Acceso unificado** para todos los componentes. | **Acoplamiento** (los componentes dependen de `ICryptoProvider` para algo que no es criptografía). |
  | **Exponer solo en `VaultProvider`** | Menos acoplamiento. | **Los componentes deben hacer `dynamic_cast`** para acceder al estado. |
  | **Eventos asíncronos (ZeroMQ)** | **Desacoplamiento total**. | **Complejidad adicional** (nuevo canal de comunicación). |

- **Recomendación:**
    - **Exponer en `ICryptoProvider`** (opción más simple y práctica).
    - **Método propuesto:**
      ```cpp
      // ICryptoProvider.h
      class ICryptoProvider {
      public:
          virtual ~ICryptoProvider() = default;
          virtual CryptoMaterial get_material() = 0;
          virtual void refresh() = 0;
          virtual bool is_healthy() const = 0;
          virtual std::string component_name() const = 0;
          virtual CryptoAutonomyStateMachine::State get_autonomy_state() const = 0; // ✅ Nuevo
      };
      ```
    - **Implementación en `VaultProvider`:**
      ```cpp
      CryptoAutonomyStateMachine::State VaultProvider::get_autonomy_state() const {
          return m_state_machine.current_state();
      }
      ```
    - **Implementación en `SeedFileProvider` (community):**
      ```cpp
      CryptoAutonomyStateMachine::State SeedFileProvider::get_autonomy_state() const {
          // En community, siempre NORMAL (no hay autonomía)
          return CryptoAutonomyStateMachine::State::NORMAL;
      }
      ```

- **Ventajas:**
    - **Acceso unificado** para todos los componentes.
    - **Fácil de mockear** en tests (solo necesitan implementar `get_autonomy_state()`).
    - **Extensible** (futuras implementaciones de `ICryptoProvider` pueden definir su propio estado).

---
**Veredicto:**
**✅ Exponer `get_autonomy_state()` en `ICryptoProvider`.**
**Es la opción más práctica y alinea con el diseño actual.**

---

---
---
## **📌 Plan de Acción para DAY 152**

### **1. Implementar `CryptoAutonomyStateMachine` (P0)**
- **Tareas:**
    - Crear clase `CryptoAutonomyStateMachine` (header + implementación).
    - Definir estados: `NORMAL`, `EXTENDED_AUTONOMY`, `RECONCILIATION`, `REVOKED`.
    - Implementar transiciones:
        - `NORMAL → EXTENDED_AUTONOMY` (si Vault es inaccesible y cache válida).
        - `EXTENDED_AUTONOMY → RECONCILIATION` (si Vault vuelve a estar accesible).
        - `RECONCILIATION → NORMAL` (si la cache se renueva con éxito).
        - `* → REVOKED` (si Vault envía revocación explícita).
    - Añadir TTL configurable para `EXTENDED_AUTONOMY` (default: 30 días).
- **Tests:**
    - Probar todas las transiciones.
    - Probar TTL de `EXTENDED_AUTONOMY`.

### **2. Integrar en `VaultClient` (P0)**
- **Tareas:**
    - Añadir `CryptoAutonomyStateMachine` como miembro de `VaultClient`.
    - Actualizar `is_healthy()` para que devuelva `true` solo en `NORMAL` o `RECONCILIATION`.
    - Llamar a `on_vault_reachable()`/`on_vault_unreachable()` en los métodos correspondientes.
    - Implementar `get_autonomy_state()` en `ICryptoProvider`.

### **3. Actualizar `firewall-acl-agent` (P1, si hay tiempo)**
- **Tareas:**
    - Usar `get_autonomy_state()` para activar modo `default-deny` en `EXTENDED_AUTONOMY`.
    - Loguear el cambio de modo.

---
**Orden de prioridad:**
1. **`CryptoAutonomyStateMachine`** (clase separada).
2. **Integración en `VaultClient`**.
3. **Exponer en `ICryptoProvider`**.
4. **Actualizar `firewall-acl-agent`** (si queda tiempo).

---

---
---
## **🛡 Mitigaciones para la Máquina de Estados**

| Riesgo | Mitigación |
|--------|------------|
| **TTL de `EXTENDED_AUTONOMY` demasiado largo** | **Default: 30 días** (configurable via `argus.yaml`). |
| **Transiciones no atómicas** | Usar **mutex** para proteger `m_state`. |
| **Falta de logs en cambios de estado** | Loguear **todos los cambios de estado** (con timestamp y razón). |
| **Inconsistencia entre componentes** | **etcd** puede usarse para sincronizar el estado (opcional). |

---
**Ejemplo de logging:**
```cpp
void CryptoAutonomyStateMachine::transition_to(State new_state) {
    std::lock_guard<std::mutex> lock(m_mutex);
    if (m_state == new_state) return;

    log_state_change(m_state, new_state);
    m_state = new_state;
    m_state_entry_time = std::chrono::system_clock::now();
}

void CryptoAutonomyStateMachine::log_state_change(State old_state, State new_state) {
    std::cerr << "[CRYPTO] State transition: "
              << state_to_string(old_state) << " -> "
              << state_to_string(new_state) << " at "
              << std::chrono::system_clock::now().time_since_epoch().count()
              << std::endl;
}
```

---

---
---
## **📅 Plan de Implementación Detallado**

| Tarea | Prioridad | Tiempo Estimado | Responsable | Fecha Límite |
|-------|-----------|------------------|-------------|--------------|
| **Crear `CryptoAutonomyStateMachine`** | P0 | 2h | Alonso | DAY 152 (mañana) |
| **Integrar en `VaultClient`** | P0 | 2h | Alonso | DAY 152 (tarde) |
| **Exponer en `ICryptoProvider`** | P0 | 1h | Alonso | DAY 152 (tarde) |
| **Tests unitarios** | P0 | 1h | Alonso | DAY 152 (tarde) |
| **Actualizar `firewall-acl-agent`** | P1 | 2h | Alonso | DAY 153 |
| **`DEBT-EMECAS-DUAL-COMPILATION-001`** | P1 | 3h | Alonso | DAY 153 |

---
---
## **💡 Recomendaciones Adicionales**

1. **Documentación:**
    - **Añadir diagrama de estados** en `ADR-044` (usar Mermaid):
      ```mermaid
      stateDiagram-v2
          [*] --> NORMAL
          NORMAL --> EXTENDED_AUTONOMY: Vault unreachable
          EXTENDED_AUTONOMY --> RECONCILIATION: Vault reachable
          RECONCILIATION --> NORMAL: Cache renewed
          EXTENDED_AUTONOMY --> REVOKED: Revocation received
          RECONCILIATION --> REVOKED: Revocation received
          REVOKED --> NORMAL: Manual intervention
      ```
    - **Explicar el TTL de `EXTENDED_AUTONOMY`** (por qué 30 días).

2. **Alertas:**
    - **Enviar alerta cuando se entre en `EXTENDED_AUTONOMY`** (via `DEBT-ALERTING-EDGE-SOS-001`).
    - **Enviar alerta cuando se acerque el TTL máximo** (ej: 24h antes de expirar).

3. **Seguridad:**
    - **Asegurar que `REVOKED` es irreversible** (requiere intervención manual).
    - **Loguear todas las transiciones** para auditoría.

4. **Testing:**
    - **Probar escenario de corte WAN** (simular con `iptables`).
    - **Probar revocación explícita** (inyectar mensaje de revocación).

---
---
## **📝 Conclusión Final**
**Prioridad para DAY 152: Implementar la máquina de estados (`DEBT-CRYPTO-AUTONOMY-001`).**
- **Extraer a `CryptoAutonomyStateMachine`** (clase separada, SRP).
- **Exponer `get_autonomy_state()` en `ICryptoProvider`** (para `firewall-acl-agent` y otros).
- **TTL de `EXTENDED_AUTONOMY`: 30 días** (configurable).

**Para el Consejo:**
¿Estáis de acuerdo con este plan? **Sí**, es el camino más robusto para cumplir con los requisitos de FEDER y proteger infraestructuras críticas. **La autonomía edge es no negociable.**