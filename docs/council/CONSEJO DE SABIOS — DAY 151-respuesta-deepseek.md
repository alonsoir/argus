Bajo la atenta mirada del Consejo, abordamos estas tres cuestiones entrelazadas. La decisión no es meramente táctica (qué hacer mañana), sino que define la trayectoria de la arquitectura de autonomía del sistema.

---

## 1. Prioridad para DAY 152: ¿Máquina de estados (A) o compilación dual (B)?

**Veredicto: Opción A — Máquina de estados primero.**

La razón es de principios: la compilación dual (`DEBT-EMECAS-DUAL-COMPILATION-001`) es un escudo, pero la máquina de estados (`DEBT-CRYPTO-AUTONOMY-001`) es la espada. Si el hospital se queda sin conectividad y `VaultClient` no tiene una máquina de estados, el NDR simplemente se apaga al expirar el TTL de la caché. Ya hemos descartado esa opción (Opción A del debate anterior) por inaceptable.

La máquina de estados es el núcleo de la resiliencia edge. Sin ella, todas las demás deudas de autonomía (`DEBT-FIREWALL-AUTONOMY-MODE-001`, `DEBT-ALERTING-EDGE-SOS-001`) son parches sobre una base que no está preparada. El `firewall-acl-agent` no puede entrar en modo `default-deny` si no hay una señal de `EXTENDED_AUTONOMY` que consumir; el webhook SOS no tiene sentido si el componente ni siquiera sabe que está en autonomía extendida.

La compilación dual es necesaria para garantizar que el código `community` no se contamina con símbolos de Vault, pero **es una deuda de calidad, no de funcionalidad**. Si el hospital es atacado mañana, la ausencia de CI dual no lo deja vulnerable; la ausencia de máquina de estados, sí. Por tanto, la Opción A precede a la B.

**Tercera vía:** El Consejo sugiere una **Opción C híbrida**: implementar la máquina de estados mínima (transiciones `NORMAL ↔ EXTENDED_AUTONOMY`) en DAY 152, y reservar `RECONCILIATION → REVOKED` para DAY 153, intercalando la compilación dual en paralelo si hay ancho de banda. Pero si hay que elegir una sola, la A.

---

## 2. ¿Máquina de estados dentro de `VaultClient` o en clase separada?

**Veredicto: Extraer a `CryptoAutonomyStateMachine` separada.**

`VaultClient` ya tiene demasiadas responsabilidades: jitter anti-stampede, caché en tmpfs, keepalive de etcd, derivación HKDF, parseo de JSON de Vault, y ahora la máquina de estados. Añadir la lógica de transiciones, timers de gracia y reconciliación convertiría esta clase en un monolito inmantenible.

La recomendación del Consejo:

```cpp
// Nueva clase ligera, sin dependencia de VaultClient
class CryptoAutonomyStateMachine {
public:
    enum class State { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };
    
    State current() const;
    void on_vault_unreachable();   // NORMAL → EXTENDED_AUTONOMY
    void on_vault_reachable();     // EXTENDED_AUTONOMY → RECONCILIATION
    void on_reconciliation_ok();   // RECONCILIATION → NORMAL
    void on_revocation();          // cualquier estado → REVOKED
    
    // TTL de autonomía extendida (circuit breaker, default 30 días)
    bool is_autonomy_expired() const;
};
```

`VaultClient` compone una instancia de `CryptoAutonomyStateMachine` y delega las transiciones. Esto permite testear la máquina de estados de forma aislada (sin Vault, sin red, sin etcd) y reutilizarla en `VaultProvider` y potencialmente en `SeedFileProvider` (aunque en community el concepto de autonomía es más simple).

---

## 3. ¿Exponer `get_autonomy_state()` en `ICryptoProvider`?

**Veredicto: Sí, exponer en la interfaz abstracta.**

El argumento a favor de encapsularlo en `VaultProvider` es que `SeedFileProvider` (community) no tiene estados de autonomía complejos. Pero esa es una visión cortoplacista. La interfaz `ICryptoProvider` ya expone `is_healthy()`, que es una consulta binaria. `get_autonomy_state()` es la consulta enriquecida que permite a los componentes tomar decisiones contextuales.

Propuesta concreta:

```cpp
class ICryptoProvider {
public:
    // ... métodos existentes ...
    
    enum class AutonomyState { NORMAL, EXTENDED_AUTONOMY, RECONCILIATION, REVOKED };
    
    // Estado actual de autonomía del proveedor.
    // SeedFileProvider devuelve siempre NORMAL (no hay Vault del que aislarse).
    // VaultProvider delega en CryptoAutonomyStateMachine.
    virtual AutonomyState get_autonomy_state() const = 0;
    
    // TTL restante de autonomía extendida en segundos.
    // 0 si no está en EXTENDED_AUTONOMY.
    // Útil para que el firewall-acl-agent planifique ventanas de gracia.
    virtual uint32_t autonomy_ttl_remaining() const = 0;
};
```

**Beneficio directo:** `firewall-acl-agent` puede consultar `provider->get_autonomy_state()` y activar `default-deny` sin necesidad de un canal lateral. `etcd-server` puede registrar el estado en el bootstrap status. El webhook SOS puede dispararse en la transición `NORMAL → EXTENDED_AUTONOMY`.

**Riesgo mitigado:** La `AutonomyState` es un `enum class` con 4 valores, no una abstracción con fugas. `SeedFileProvider` devuelve `NORMAL` sin lógica adicional. No se rompe el principio de segregación de interfaces porque el concepto de autonomía es inherente a la obtención de material criptográfico en un edge node.

---

### Resumen para el acta del Consejo

| Pregunta | Decisión | Fundamento |
|---|---|---|
| DAY 152: ¿A o B? | **Opción A** | La autonomía edge es funcionalidad crítica; la CI dual es calidad. |
| ¿Clase separada? | **Sí**, `CryptoAutonomyStateMachine` | SRP: `VaultClient` ya está sobrecargado. |
| ¿Exponer en `ICryptoProvider`? | **Sí**, `get_autonomy_state()` + `autonomy_ttl_remaining()` | Permite que `firewall-acl-agent` y `etcd-server` reaccionen sin acoplamiento. |

El Consejo permanece atento a la implementación de DAY 152.