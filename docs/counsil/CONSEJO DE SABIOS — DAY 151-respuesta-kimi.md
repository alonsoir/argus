**Consejo de Sabios — Dictamen DAY 151**

Compañero, la abstracción `ICryptoProvider` es un hito arquitectónico. Has separado correctamente la identidad criptográfica del transporte, y la factoría centraliza el `#ifdef` donde debe estar. El log con fingerprint Ed25519 en etcd-server confirma que la integración funciona. Vamos a tus tres preguntas.

---

## P1 — Opción A vs. B para DAY 152

**Opción A: máquina de estados de autonomía.** Es la única opción que bloquea el valor diferencial del paper.

El dual compilation CI (Opción B) es una inversión de 2-3 horas que ahorra días de debug, pero no añade una línea al argumento científico de FEDER. La máquina de estados, en cambio, es la materialización del escenario hospital-corte-WAN-ransomware que describe tu contribución. Sin ella, el firewall no puede entrar en default-deny, el SOS no puede alertar, y el demo del 22 de septiembre no tiene qué mostrar ante el evaluador.

**Veredicto: A primero, B después.**

| Día | Tarea | Justificación |
|-----|-------|---------------|
| **DAY 152** | `DEBT-CRYPTO-AUTONOMY-001` | Bloquea firewall y SOS. Es el corazón del valor de aRGus. |
| **DAY 153** | `DEBT-EMECAS-DUAL-COMPILATION-001` | Una vez que la state machine está estable, protegerla con CI dual es trivial (añadir un stage paralelo en Jenkinsfile). |

**No hay Opción C mejor.** La tercera opción sería "hacer ambas a medias", lo cual, siendo un solo desarrollador, garantiza que ninguna termine.

---

## P2 — ¿Clase separada para la máquina de estados?

**Sí. Extrae `CryptoAutonomyStateMachine` inmediatamente.**

`VaultClient` ya tiene cinco responsabilidades: HTTP a Vault, KDF, jitter, cache tmpfs, keepalive etcd. Añadirle una sexta (gestión de estados con transiciones temporales y callbacks de sistema) la convierte en una clase imposible de testear unitariamente sin mock de red, mock de filesystem, y mock de reloj.

**Estructura propuesta:**

```cpp
// autonomy_state_machine.h
enum class AutonomyState { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };

struct AutonomyEvent {
    bool vault_reachable;
    bool cache_valid;
    std::chrono::seconds cache_age;
    std::optional<KeyVersion> vault_key_version;
};

class CryptoAutonomyStateMachine {
public:
    explicit CryptoAutonomyStateMachine(Config cfg);
    AutonomyState process_event(const AutonomyEvent& ev);
    AutonomyState current_state() const noexcept;
    
    // Callbacks registrables para reacciones externas
    std::function<void()> on_enter_autonomy;
    std::function<void()> on_reconciliation;
    std::function<void()> on_revoked;
};
```

**Ventajas:**
- **Testeabilidad:** Puedes alimentarle eventos sintéticos y verificar transiciones sin levantar Vault ni etcd.
- **SRP:** `VaultClient` se encarga de "obtener material de Vault". La state machine se encarga de "decidir si ese material sigue siendo operativamente válido".
- **Reutilización:** Si en el futuro `SeedFileProvider` necesita un modo "offline extendido" (ej. lectura de seed.bin en USB de respaldo), la misma state machine sirve.

**Dónde vive la instancia:** Dentro de `VaultProvider`, no expuesta directamente. `VaultProvider` la instancia y la consulta en cada `refresh()`.

---

## P3 — ¿Exponer autonomía vía `ICryptoProvider`?

**Sí. El firewall y el SOS lo necesitan. Pero no expongas el estado interno de Vault; expón un modo operativo genérico.**

Si encapsulas el estado dentro de `VaultProvider`, el `firewall-acl-agent` tendría que hacer `dynamic_cast<VaultProvider*>` para consultarlo. Eso rompe la abstracción y fuerza a community a conocer detalles de enterprise.

**Interfaz recomendada para `ICryptoProvider`:**

```cpp
enum class OperationalMode {
    NORMAL,        // Autoridad criptográfica contactable y válida
    AUTONOMOUS,    // Operando con material local/cache, autoridad no contactable
    RECONCILING,   // Reconectando, validando material pendiente
    DEGRADED       // Material revocado o inválido, capacidad reducida
};

class ICryptoProvider {
public:
    virtual ~ICryptoProvider() = default;
    virtual CryptoMaterial get_material() = 0;
    virtual bool refresh() = 0;
    virtual bool is_healthy() const = 0;
    virtual std::string component_name() const = 0;
    
    // NUEVO: modo operativo visible para todos los componentes
    virtual OperationalMode get_operational_mode() const noexcept = 0;
};
```

**Implementaciones:**
- `SeedFileProvider::get_operational_mode()` → siempre `NORMAL` (o `AUTONOMOUS` si quieres ser filosófico: community siempre es autónomo por diseño).
- `VaultProvider::get_operational_mode()` → delega a `state_machine.current_state()` con un mapping:
    - `NORMAL` → `NORMAL`
    - `EXTENDED_AUTONOMY` → `AUTONOMOUS`
    - `RECONCILIATION` → `RECONCILING`
    - `REVOKED` → `DEGRADED`

**Uso en firewall:**
```cpp
if (crypto_provider->get_operational_mode() == OperationalMode::AUTONOMOUS) {
    firewall.set_policy(Policy::DEFAULT_DENY_NEW_FLOWS);
    log(LOG_CRIT, "AUTONOMY MODE: blocking lateral movement");
}
```

**Uso en SOS:**
```cpp
if (crypto_provider->get_operational_mode() == OperationalMode::AUTONOMOUS) {
    sos_alert("Vault unreachable > TTL. NDR operating in island mode.");
}
```

---

## Recomendaciones de implementación para DAY 152

### 1. No uses `std::chrono::steady_clock` directamente
Inyecta un `Clock` template o interfaz. En tests, usas un `ManualClock` que avanzas a voluntad. En producción, `SteadyClock`.

```cpp
template<typename Clock = std::chrono::steady_clock>
class CryptoAutonomyStateMachine { ... };
```

### 2. La transición a `EXTENDED_AUTONOMY` debe ser inmediata
No esperes a que expire el TTL. El evento es: *"Vault no responde tras N intentos consecutivos"*. El TTL es el tiempo máximo que puedes permanecer en autonomía antes de que la reconciliación sea obligatoria al recuperar conectividad.

### 3. `REVOKED` no significa `exit(1)`
Según el dictamen del Consejo anterior, `REVOKED` significa "operación local-only sin cifrado de canal". El nodo sigue detectando y bloqueando, pero no puede autenticar con central. Nunca se apaga solo.

### 4. Thread-safety
La state machine probablemente recibe eventos desde el hilo de keepalive. Usa un `std::mutex` interno o, mejor en C++20, haz que `process_event()` sea el único método público que modifica estado, y documenta que debe llamarse desde un hilo serializado (el de keepalive).

---

## Resumen de acciones DAY 152

| Orden | Tarea | Tiempo estimado |
|-------|-------|-----------------|
| 1 | Crear `CryptoAutonomyStateMachine.h/.cpp` con estados, eventos, y tests unitarios | 3h |
| 2 | Integrar en `VaultProvider`, exponer `get_operational_mode()` en `ICryptoProvider` | 1.5h |
| 3 | Verificar que `SeedFileProvider` compila y testea con la interfaz ampliada | 0.5h |
| 4 | `make test-all` verde en ambas configuraciones (manualmente, ON y OFF) | 0.5h |

**Total: ~5.5 horas.** Deja el dual compilation CI para DAY 153; es un Jenkinsfile de 20 líneas una vez que la interfaz es estable.

*El Consejo ha hablado. Que la state machine sea testeable, que el firewall reaccione, y que el hospital nunca se quede ciego.* 🛡️