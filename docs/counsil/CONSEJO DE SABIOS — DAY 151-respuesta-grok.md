**Consejo de Sabios — Respuesta DAY 152**

Miembros presentes: Arquitecto de Sistemas Distribuidos (ex-Linux Foundation/eBPF), Ingeniero de Seguridad en C++ (ex-Cloudflare), Lead de Infra Crítica (sector salud), Experto en ZeroMQ + Modelos de Autonomía Edge.

---

### 1. Prioridad para DAY 152: **Opción A (con matices)**

**Elegimos Opción A como principal**, pero con un alcance mínimo viable y acotado.

**Razones:**
- El escenario de **autonomía edge** (hospital/municipio sin conectividad a Vault durante días/semanas) es el **diferenciador de producto** y el que justifica el open-core. Sin esto, el sistema no cumple el requisito de "infraestructura crítica que no puede permitirse downtime".
- Las deudas `DEBT-FIREWALL-AUTONOMY-MODE-001` y `DEBT-ALERTING-EDGE-SOS-001` dependen directamente de la máquina de estados. Bloquearlas es riesgo real.
- La dual compilation (**Opción B**) es deuda de calidad importante, pero **no bloqueante funcionalmente**. Se puede fusionar en el mismo día o en DAY 153 sin drama (es "infra").

**Tercera vía recomendada (la que proponemos):**
- **A-mínima** hoy: implementar la máquina de estados + transiciones básicas + persistencia mínima (etcd o archivo local 0600).
- Mañana (o en paralelo si tenéis capacidad): etapa de dual-compilation + tests de smoke en ambas configuraciones.
- **Regla de oro**: nunca merges a main sin que compile y pasen tests en **ambas** variantes (VAULT_ENABLED=ON/OFF). Esto debe ser sagrado antes de FEDER.

---

### 2. ¿Extraer `CryptoAutonomyStateMachine` o mantener en `VaultClient`?

**Extraer obligatoriamente a clase separada: `CryptoAutonomyStateMachine`**.

**Justificación (SRP + experiencia real en sistemas críticos):**
- `VaultClient` ya tiene jitter, cache de materiales, keepalive, reconexión, etcd bootstrap, etc. Añadirle una máquina de estados finita con temporizadores y acciones laterales (firewall, alerting) es **receta para spaghetti manteniblemente caro**.
- La máquina de estados tiene su propio ciclo de vida, persistencia, observabilidad y testing needs (time travel para tests es muy útil aquí).
- Beneficios de extracción:
    - Fácil de testear en aislamiento (GoogleTest + tiempo simulado o inyección de clock).
    - Reutilizable si en el futuro tenéis otros proveedores que necesiten autonomía (ej. future KMS local).
    - Claridad: `VaultClient` se queda como "cliente de Vault + cache", la máquina como "gestor de política de autonomía".
    - Facilita el futuro `ICryptoProvider` sin exponer `VaultClient` completo.

**Estructura recomendada (C++20):**
```cpp
class CryptoAutonomyStateMachine {
public:
    enum class State { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };
    
    struct Config { std::chrono::seconds extended_ttl; /* ... */ };
    
    explicit CryptoAutonomyStateMachine(std::shared_ptr<ICryptoProvider> crypto, Config cfg);
    
    void on_vault_unreachable();
    void on_vault_recovered();
    void tick();                    // llamado periódicamente
    State current_state() const;
    std::chrono::seconds time_in_current_state() const;
    
    // callbacks o observers para acciones laterales (firewall, alerts)
    using ActionHandler = std::function<void(State, State)>;
    void set_transition_handler(ActionHandler h);
};
```

Usad `std::atomic<State>` + `std::chrono` + un timer simple (o integration con el event loop existente).

---

### 3. Exposición del estado y TTL

**Exponer vía interfaz: `ICryptoProvider::get_autonomy_state()`**.

**Diseño recomendado:**
```cpp
struct AutonomyState {
    CryptoAutonomyStateMachine::State state;
    std::chrono::seconds time_remaining;   // 0 si no aplica
    std::chrono::system_clock::time_point last_transition;
    std::string reason;                    // debug
};

class ICryptoProvider {
public:
    virtual AutonomyState get_autonomy_state() const = 0;
    // ...
};
```

**Razones:**
- Los consumidores (`firewall-acl-agent`, `etcd-server`, alerting scripts, RAG, etc.) necesitan consultar el estado **sin conocer** si estamos en modo community o enterprise.
- `SeedFileProvider` puede devolver siempre `NORMAL` (o `EXTENDED_AUTONOMY` con TTL infinito si queréis consistencia).
- Encapsular completamente en `VaultProvider` viola el principio de que `ICryptoProvider` es la fuente de verdad de todo lo criptográfico + identidad.
- Es información de **control**, no secreto. El estado debe ser observable (logs, métricas, `/health` endpoint).

Mantened el TTL configurable en el `CryptoAutonomyStateMachine::Config` y exponedlo solo de forma derivada (tiempo restante), no el valor crudo de configuración.

---

### Recomendaciones adicionales (DAY 152)

1. **Persistencia del estado**: Al entrar en `EXTENDED_AUTONOMY` escribir un archivo `/run/argus/crypto-autonomy-state.json` (0600) con timestamp + firma Ed25519 del propio nodo. Al recuperar, validar que no ha sido manipulado.
2. **Circuit breaker**: Usar exponential backoff + jitter ya existente. Transición a `RECONCILIATION` solo cuando se recupere Vault **y** se complete handshake de key_version.
3. **Observabilidad**: Cada transición debe emitir evento ZeroMQ interno (topic `crypto.autonomy.transition`) para que el resto de componentes reaccionen.
4. **Testing**: Fixture que simule pérdida de Vault durante N días. Verificar que firewall pasa a default-deny y se dispara SOS.

---

**Veredicto final del Consejo:**
- **DAY 152 → Opción A-mínima + extracción de StateMachine + `get_autonomy_state()` en interfaz**.
- DAY 153 → Dual compilation + tests cruzados.
- Este orden maximiza la resiliencia del producto sin sacrificar calidad del pipeline.

Que la fuerza de la **autonomía edge** os acompañe. El sector salud y crítico lo agradecerá.

Si necesitáis revisión de código de la state machine o el ADR correspondiente, subid el diff y lo revisamos.

**Firmado:**  
Consejo de Sabios — aRGus NDR