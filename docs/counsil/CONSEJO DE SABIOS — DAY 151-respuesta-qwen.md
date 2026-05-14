**CONSEJO DE SABIOS — DICTAMEN TÉCNICO: PRIORIDAD, SRP Y ENCAPSULAMIENTO — DAY 151**
*Expertise en arquitectura C++20, sistemas distribuidos y modelo de amenaza para infraestructura crítica*

---

## 🎯 VEREDICTO EJECUTIVO

**OPCIÓN A PRIMERO** (Máquina de estados de autonomía) + **EXTRACCIÓN A CLASE SEPARADA** + **TTL ENCAPSULADO**

> *"La autonomía edge no es un feature; es la razón de ser del sistema en el escenario de amenaza real. La deuda de CI es importante, pero no bloquea la misión. Separa responsabilidades, encapsula complejidad, expone solo lo necesario."*

---

## 🔍 RESPUESTA P1: ¿Opción A o B para DAY 152?

### Matriz de dependencia crítica

```
DEBT-CRYPTO-AUTONOMY-001 (máquina de estados)
       ↓
DEBT-FIREWALL-AUTONOMY-MODE-001 (firewall detecta autonomía → default-deny)
DEBT-ALERTING-EDGE-SOS-001 (webhook SOS cuando entra en autonomía)
       ↓
Demostración FEDER: "NDR protege aunque el hospital esté aislado"
       ↓
Go/No-Go técnico 1-Ago-2026
```

```
DEBT-EMECAS-DUAL-COMPILATION-001 (CI paralelo community/enterprise)
       ↓
Robustez del pipeline de calidad
       ↓
Reducción de riesgo de regresión open-core
       ↓
(No bloquea funcionalidad FEDER)
```

### Evaluación de impacto

| Criterio | Opción A (Autonomía) | Opción B (Dual CI) |
|----------|---------------------|------------------|
| **Bloquea otras deudas P1** | ✅ Desbloquea 2 deudas críticas | ❌ No desbloquea nada funcional |
| **Impacto en modelo de amenaza** | ✅ Directo: protege escenario hospital aislado | ❌ Indirecto: mejora calidad, no capacidad |
| **Riesgo de implementación** | 🟡 Alto (lógica de estados compleja) | 🟢 Bajo (Jenkinsfile, ya hay precedentes) |
| **Valor para FEDER deadline** | ✅ Alto: demo operativa de resiliencia | 🟡 Medio: confianza en CI, no en producto |
| **Reversibilidad** | 🟡 Difícil (cambia comportamiento runtime) | ✅ Fácil (se puede deshacer en Jenkins) |

### Recomendación: **Opción A primero, con mitigación de riesgo**

```bash
# DAY 152: Implementar máquina de estados EXTRAÍDA (ver P2 abajo)
# DAY 153: Añadir tests de integración para los 4 estados
# DAY 154: Integrar firewall-acl-agent con autonomía (DEBT-FIREWALL-AUTONOMY-MODE-001)
# DAY 155: Implementar webhook SOS (DEBT-ALERTING-EDGE-SOS-001)
# DAY 156: Dual compilation CI (DEBT-EMECAS-DUAL-COMPILATION-001) — ahora que la lógica crítica está testeada
```

**Justificación**: La máquina de estados es el *núcleo del modelo de amenaza*. Sin ella, el sistema no puede demostrar resiliencia ante aislamiento — el escenario que justifica la existencia de aRGus para infraestructura crítica de bajo presupuesto. La deuda de CI es importante, pero puede esperar 4 días sin riesgo funcional.

---

## 🔍 RESPUESTA P2: ¿Extraer a `CryptoAutonomyStateMachine` o mantener en `VaultClient`?

### Análisis de responsabilidad actual de `VaultClient`

```cpp
// Responsabilidades actuales (violación de SRP si añadimos estados):
class VaultClient {
    // 1. Comunicación con Vault API (HTTP, tokens, retry)
    // 2. Gestión de cache tmpfs/persistente (TTL, permisos, mlock)
    // 3. Derivación criptográfica (libsodium KDF)
    // 4. Registro en etcd (health, fingerprint)
    // 5. Keepalive/heartbeat (lease renewal)
    // 6. Jitter anti-stampede (startup coordination)
    // 7. [PROPUESTA] Máquina de estados de autonomía ← ¿aquí?
};
```

### Veredicto: ✅ **Extraer a `CryptoAutonomyStateMachine` separada**

**Patrón recomendado: Strategy + State Machine encapsulada**

```cpp
// common/crypto_autonomy.h
class CryptoAutonomyStateMachine {
public:
    enum class State { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };
    
    struct Config {
        std::chrono::seconds autonomy_ttl;      // 30 días default
        std::chrono::seconds reconciliation_timeout;  // 5 min para re-validar
        std::function<void(State)> on_state_change;   // callback para alertas
    };
    
    State current_state() const;
    bool can_operate() const;  // true para NORMAL + EXTENDED_AUTONOMY
    bool requires_vault() const;  // true solo para NORMAL + RECONCILIATION
    
    // Transiciones (llamadas por VaultClient)
    void on_vault_unreachable();
    void on_vault_restored();
    void on_explicit_revocation();
    void on_local_tamper_detected();
    
    // Consulta para logging/auditoría
    std::string state_to_string(State) const;
    
private:
    State current_;
    Config config_;
    std::chrono::system_clock::time_point autonomy_start_;
    // ... lógica de transiciones, circuit breaker de 30 días, etc.
};
```

```cpp
// common/vault_client.cpp — integración mínima
class VaultClient {
    std::unique_ptr<CryptoAutonomyStateMachine> autonomy_;
    
    CryptoMaterial get_material() {
        if (!autonomy_->can_operate()) {
            log_crit("Crypto autonomy state {} → exit(1)", autonomy_->current_state());
            exit(1);
        }
        
        if (autonomy_->current_state() == CryptoAutonomyStateMachine::State::EXTENDED_AUTONOMY) {
            log_warn("Operating in extended autonomy mode");
            // Logging firmado cada N minutos (DEBT-CRYPTO-AUTONOMY-001)
        }
        
        // ... lógica existente de cache/Vault ...
        
        // Notificar a la máquina de estados según resultado
        if (vault_call_succeeded) {
            autonomy_->on_vault_restored();
        } else {
            autonomy_->on_vault_unreachable();
        }
    }
};
```

**Beneficios de la extracción**:
| Beneficio | Impacto |
|-----------|---------|
| **Testabilidad** | ✅ `CryptoAutonomyStateMachine` se puede testear en aislamiento, sin mocks de Vault/etcd |
| **SRP** | ✅ `VaultClient` se enfoca en comunicación; `CryptoAutonomyStateMachine` en lógica de estados |
| **Evolución open-core** | ✅ La máquina de estados puede ser idéntica en community/enterprise; solo cambia la fuente de material |
| **Auditabilidad** | ✅ Transiciones de estado son explícitas y registrables; no mezcladas con lógica de HTTP |

**Conclusión**: Extraer sí. Mantener `VaultClient` como orquestador, no como contenedor de lógica de estados.

---

## 🔍 RESPUESTA P3: ¿Exponer TTL vía `ICryptoProvider::get_autonomy_state()` o encapsular?

### Principio de diseño: **Minimal Interface Pollution**

`ICryptoProvider` es la frontera pública del módulo criptográfico. Cada método añadido:
- Aumenta la superficie de testing
- Expone detalles de implementación a componentes que no los necesitan
- Complica la evolución futura (cambiar un método público es breaking)

### Veredicto: ✅ **Encapsular TTL en `VaultProvider`, exponer solo estado de alto nivel**

```cpp
// common/crypto_provider.h — interfaz mínima estable
class ICryptoProvider {
public:
    virtual CryptoMaterial get_material() = 0;
    virtual bool is_healthy() const = 0;  // true si puede operar (NORMAL o EXTENDED_AUTONOMY)
    virtual std::string component_name() const = 0;
    
    // [OPCIONAL para FEDER] Estado de autonomía para logging/alertas
    enum class AutonomyState { NORMAL, EXTENDED_AUTONOMY, REVOKED };
    virtual AutonomyState get_autonomy_state() const { 
        return AutonomyState::NORMAL;  // default: community no tiene autonomía
    }
    
    virtual ~ICryptoProvider() = default;
};
```

```cpp
// enterprise/vault_provider.cpp — implementación enterprise
class VaultProvider : public ICryptoProvider {
public:
    AutonomyState get_autonomy_state() const override {
        return autonomy_->current_state();  // delega a la máquina de estados
    }
    
    // TTL y configuración de autonomía: PRIVADO, configurable via constructor
private:
    std::unique_ptr<CryptoAutonomyStateMachine> autonomy_;
    // TTL se pasa en el constructor desde config JSON, no se expone
};
```

**¿Por qué no exponer el TTL?**
| Razón | Explicación |
|-------|------------|
| **Detalle de implementación** | El TTL es una política de cache, no una propiedad criptográfica fundamental |
| **Variabilidad por entorno** | TTL puede ser 1h en dev, 30 días en prod; exponerlo invita a acoplamiento con config management |
| **SRP** | Los componentes que consumen `ICryptoProvider` necesitan saber *si pueden operar*, no *cuándo expira la cache* |
| **Evolución** | Si mañana cambiamos de TTL fijo a renovación adaptativa, la interfaz pública no se rompe |

**Excepción justificada**: `get_autonomy_state()` sí se expone (como método opcional con default) porque:
- `firewall-acl-agent` necesita saber si está en `EXTENDED_AUTONOMY` para activar default-deny
- `sos_vault_unreachable.sh` necesita disparar alerta cuando el estado cambia
- Es un *estado de alto nivel*, no un parámetro de configuración

---

## 📋 RESUMEN DE DECISIONES PARA DAY 152

| Pregunta | Decisión | Acción inmediata |
|----------|----------|-----------------|
| **P1: Prioridad** | Opción A (máquina de estados) primero | Crear `common/crypto_autonomy.h/.cpp` con skeleton de estados |
| **P2: Extracción** | Sí, a `CryptoAutonomyStateMachine` separada | Implementar patrón Strategy: `VaultClient` delega, no contiene |
| **P3: Encapsulamiento** | TTL privado, solo `get_autonomy_state()` público | Añadir método opcional a `ICryptoProvider` con default `NORMAL` |

---

## 🚀 PLAN DE IMPLEMENTACIÓN DAY 152

```bash
# 1. Crear skeleton de CryptoAutonomyStateMachine
touch src/common/crypto_autonomy.{h,cpp}
# Implementar: enum State, Config, transiciones básicas, can_operate()

# 2. Integrar en VaultClient (enterprise)
# - Inyectar autonomía_ en constructor
# - Llamar a on_vault_unreachable()/on_vault_restored() según resultado
# - Respetar can_operate() antes de devolver material

# 3. Tests unitarios para la máquina de estados
# - Testear transiciones: NORMAL → EXTENDED_AUTONOMY → RECONCILIATION → NORMAL
# - Testear circuit breaker de 30 días → REVOKED
# - Mockear tiempo para no esperar 30 días reales

# 4. Actualizar ICryptoProvider con get_autonomy_state() opcional
# - Implementar en VaultProvider
# - SeedFileProvider devuelve NORMAL siempre (community no tiene autonomía)

# 5. Documentar en ADR-044 §D4 la política de autonomía híbrida
```

---

## 💬 FRASE DE CIERRE

> *"La autonomía no es un fallback; es el diseño. En un mundo donde la conectividad es un privilegio, no un derecho, el edge debe ser soberano. Separar responsabilidades no es burocracia; es la única forma de que la complejidad no devore la claridad."*

---

**¿Procedemos a crear `common/crypto_autonomy.h` con el skeleton de la máquina de estados y comenzar la implementación del patrón Strategy en `VaultClient`?** 🛡️🧠🔐