**Claude — Voto Consejo DAY 151→152**

---

**1. Prioridad DAY 152: Opción A — Máquina de estados primero.**

La razón es de dependencias. `DEBT-EMECAS-DUAL-COMPILATION-001` es importante pero no bloquea funcionalidad real — el CI compila community hoy y funciona. La máquina de estados en cambio es la columna vertebral del argumento FEDER: "el sistema opera autónomamente en un hospital sin conectividad". Sin ella, `ICryptoProvider` es una abstracción elegante pero sin comportamiento de resiliencia real. El Jenkinsfile puede hacerse en paralelo o al final del día si hay tiempo.

---

**2. Extraer a `CryptoAutonomyStateMachine` — sí, pero con matiz.**

`VaultClient` ya tiene demasiadas responsabilidades: HTTP, jitter, cache tmpfs, etcd keepalive, derivación de claves. Añadir una máquina de estados con transiciones, timers, webhooks y reconciliación la convierte en una clase inmanejable.

Mi propuesta: clase `CryptoAutonomyStateMachine` en `common/crypto_autonomy.h`, owned por `VaultProvider` (no por `VaultClient`). `VaultClient` solo expone el estado raw de Vault (`OK`, `KO`, `cache_valid`). `VaultProvider` alimenta esos datos a la máquina de estados y toma las decisiones. Esto respeta SRP y mantiene `VaultClient` testeable en aislamiento.

---

**3. Exposición del estado: `ICryptoProvider::get_autonomy_state()` — no todavía.**

Añadirlo a la interfaz ahora fuerza a `SeedFileProvider` a implementarlo con un stub `NORMAL` permanente — ruido semántico. Mi recomendación: método opcional en `VaultProvider` directamente, accesible via `dynamic_cast` solo donde sea necesario (firewall-acl-agent). Si el Consejo converge en que otros componentes también lo necesitan, lo promovemos a la interfaz en DAY 153 con base empírica, no especulativa.

---

**Riesgo que veo y no está en las preguntas:**

El bootstrap status file (`/run/argus/etcd-bootstrap-status.json`) que escribimos hoy no tiene firma Ed25519. En el escenario hospital, un atacante con acceso local podría escribir un fingerprint falso antes del arranque. Para DAY 152 o 153, ese fichero debería estar firmado con la clave del componente. Lo registro como `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` (P1 pre-FEDER).