Claro.

---

**Q1 — Perfiles AppArmor**

Los `deny` explícitos son en su mayoría redundantes si AppArmor es default-deny, pero los mantendría en los perfiles por dos razones: documentación de intención (quien lee el perfil sabe qué se consideró) y protección ante cambios futuros en `#include <abstractions/base>` que pudieran añadir permisos implícitos. La excepción: los `deny` cruzados entre componentes (`deny /opt/argus/bin/sniffer x` en ml-detector) son valiosos y no redundantes — documentan explícitamente que la separación entre componentes es intencional, no accidental.

**Q2 — Linux Capabilities**

`cap_bpf` existe desde Linux 5.8 y separa el permiso de cargar programas eBPF de `cap_sys_admin`. En la hardened VM con Debian bookworm (kernel 6.1) esto es viable. Mi recomendación: sustituir `cap_sys_admin` en el sniffer por `cap_bpf` + `cap_perfmon` (para acceso a mapas de rendimiento). Es una reducción real de superficie. Sobre `cap_ipc_lock`: es suficiente para `mlock()` básico, pero el límite del sistema (`RLIMIT_MEMLOCK`) puede ser un problema — en la práctica, en Debian el límite por defecto para usuarios del sistema es muy bajo. Solución: añadir `LimitMEMLOCK=infinity` en el unit de systemd del componente, no elevar el cap.

**Q3 — Falco**

`modern_ebpf` es la elección correcta para 2026 — el módulo de kernel está en proceso de deprecación en el roadmap de Falco. Para los falsos positivos durante el ajuste: la estrategia que funciona es arrancar Falco en modo `--dry-run` (solo loga, no alerta) mientras los perfiles AppArmor están en `complain`, ajustar ambos en paralelo, y solo pasar a `enforce` + alertas reales cuando el pipeline lleva 30 minutos sin falsos positivos. No intentar ajustar AA y Falco por separado — se retroalimentan.

**Q4 — Keypairs separados**

Sí, deberían ser keypairs separados. La clave de ADR-025 fue diseñada con semántica de "plugin signing" — su compromiso invalida la cadena de confianza de los plugins. Reutilizarla para binarios de pipeline mezcla dos dominios de confianza distintos. Mi recomendación: crear `binary_signing.sk/pk` junto a `plugin_signing.sk/pk` en el provisioning. El coste es mínimo (dos líneas en `provision.sh`), la separación de responsabilidades es clara, y si un keypair se compromete el otro sigue siendo válido. Deuda: DEBT-PROD-BINARY-SIGNING-KEYPAIR-001.

**Q5 — "Fuzzing misses nothing within CPU time"**

Esta frase es **incorrecta** y debería eliminarse. El problema es doble: primero, el fuzzing *sí* puede fallar en encontrar bugs aunque tenga tiempo de CPU infinito, porque la cobertura guiada por ramas no garantiza explorar todo el espacio de estados relevante (especialmente en código con estado implícito o dependencias de orden). Segundo, la frase contradice la oración siguiente ("cannot prove absence of defects") — si no puede probar ausencia, tampoco puede "no perderse nada".

Mi reformulación propuesta:

> *"Coverage-guided fuzzing explores the input space beyond what structured generation can anticipate, discovering crashes and undefined behavior at parser and protocol boundaries. Unlike unit and property tests, it does not require the developer to enumerate failure hypotheses in advance. It provides no completeness guarantee — bugs undiscovered after N executions may still exist — but each corpus-expanding input permanently extends the regression suite."*

Esto es honesto, citable, y un revisor de cs.CR no lo objetará.

---

Esas son mis posiciones. La de Q5 es la que más claramente veo — la frase actual no debería sobrevivir la revisión por pares.