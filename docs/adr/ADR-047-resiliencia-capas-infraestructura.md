# ADR-047 — Resiliencia en capas ante fallo de infraestructura crítica

- **Estado:** En preparación
- **Fecha:** 2026-05-23
- **Autor:** Alonso Isidoro Román
- **Revisores:** Consejo de Sabios (pendiente votación formal)
- **Referencias:** ADR-046 (ventana de correlación), ADR-048 (etcd HA), ADR-049 (Vault HA)

---

## Contexto

aRGus NDR protege infraestructura crítica hospitalaria en Extremadura. Vault y etcd-server son componentes de infraestructura críticos para el funcionamiento del pipeline criptográfico y la máquina de estados. Su caída no puede traducirse en pérdida de protección del hospital ni en interrupción de operaciones internas.

Dos hechos fundamentales guían esta decisión:

1. Vault y etcd-server no correrán en modo single-node en producción — correrán en HA con quórum Raft (ver ADR-048 y ADR-049). Un fallo de nodo minoritario es absorbido transparentemente por el quórum sin que el pipeline lo perciba.
2. Discord se asume siempre disponible como canal de notificación al administrador.

**Parar el sistema no es una opción. Dejar al hospital sin protección no es una opción.**

---

## Decisión

El sistema implementa resiliencia en tres capas ordenadas. Cada capa actúa solo si la anterior no ha absorbido el fallo.

### Capa 1 — HA con quórum Raft (línea de defensa primaria)

etcd-server y Vault corren en cluster con Raft. Un fallo de nodo minoritario es transparente para el pipeline. La reelección de líder en Raft ocurre en ~200ms, imperceptible operacionalmente.

> **Estado transitorio:** etcd-server corre actualmente en single-node (DAY 159). Vault HA pendiente. Falco + cron actúan como resiliencia transitoria hasta que el quórum esté implementado (ver ADR-048 y ADR-049).

### Capa 2 — Falco + cron (recuperación automática)

Falco monitoriza los procesos críticos (etcd-server, Vault). Si detecta caída de un proceso, cron intenta recuperación automática antes de escalar al administrador humano.

**Requisito explícito:** los scripts cron de recuperación deben ser idempotentes. Si Falco dispara múltiples eventos por la misma caída, el script debe verificar el estado actual antes de actuar. Un doble intento de arranque no debe producir estado inconsistente.

### Capa 3 — Discord + administrador (último recurso humano)

Si las capas anteriores no han resuelto el fallo, Discord notifica al administrador. La notificación es continua y repetida hasta resolución confirmada. Cuando el administrador resuelve el fallo, el sistema debe recuperarse automáticamente sin intervención en el runtime.

---

## Máquina de estados — nuevos estados

### CRYPTO_DEGRADED

**Condición de entrada:** Vault inaccesible, intento de renovación del token criptográfico fallido.

**Comportamiento:**
- La criptografía anterior permanece activa. No ha sido comprometida — simplemente no se ha podido renovar por un fallo de infraestructura. Destruirla sería eliminar un mecanismo de defensa funcional por razones administrativas, no de seguridad.
- El firewall pasa a modo defensivo exterior: bloquea conexiones entrantes desde internet, mantiene intacto el tráfico interno entre máquinas del hospital.
- Discord notifica al administrador con alerta continua hasta resolución.
- Los logs muestran claramente la transición de estado y el motivo.

**Justificación del modo defensivo:**
Un atacante sofisticado puede tumbar Vault deliberadamente como paso previo para cargar payload desde exterior aprovechando una ventana de degradación criptográfica. El modo defensivo cierra esa ventana sin romper la operativa interna del hospital.

### CRYPTO_RECOVERED

**Condición de entrada:** Vault accesible de nuevo, renovación del token criptográfica exitosa.

**Comportamiento:**
- La renovación se reanuda automáticamente sin reiniciar ningún componente ni intervención en el runtime.
- El firewall vuelve a modo normal.
- Discord notifica al administrador con alerta de resolución.
- Los logs muestran la transición de vuelta al estado operacional.

**Requisito crítico:** La transición `CRYPTO_DEGRADED → CRYPTO_RECOVERED` debe ser completamente automática.

---

## Escenarios validados (DAY 161)

Los siguientes escenarios deben ejecutarse y documentarse como parte del plan de validación:

| Escenario | Condición | Comportamiento esperado |
|-----------|-----------|------------------------|
| A | Vault caído (parcial, con HA) | Quórum absorbe el fallo. Pipeline no lo percibe. |
| A' | Vault caído (total, transitorio single-node) | CRYPTO_DEGRADED. Falco+cron intentan recuperación. Discord alerta. |
| B | Jenkins caído | Ningún cambio en etcd ni en máquina de estados. **Sin alerta Discord.** |
| C | etcd caído (parcial, con HA) | Quórum absorbe el fallo. Pipeline no lo percibe. |
| C' | etcd caído (total, transitorio single-node) | Firewall modo defensivo exterior. Tráfico interno intacto. Discord alerta. |
| D | Token expirado durante caída Vault | CRYPTO_DEGRADED con crypto anterior activa. Firewall defensivo. |
| E | Vault + etcd caídos simultáneamente | Comportamiento aditivo. Firewall defensivo. Dos notificaciones Discord. Sin deadlock. |
| F | Arranque con Vault no disponible | Arranque en modo degradado, no bloqueo. Comportamiento análogo al boot gate NTP (ADR-046). |

**Escenario B — assertion explícito:** el silencio correcto es tan importante como la alerta correcta. La parada de Jenkins no debe generar ninguna notificación Discord. Jenkins solo produce binarios. No modifica la máquina de estados en etcd-server.

---

## Escenarios fuera de scope (backlog post-FEDER)

**Vault sealed vs Vault stopped:** Son estados diferentes. Un Vault sellado requiere unseal manual con las claves Shamir — no se recupera solo al arrancarlo. Si Vault se sella (por ejemplo, tras detectar un intruso), el comportamiento debe diferenciarse del Vault simplemente caído, con una notificación diferenciada al administrador. Ver ADR-049 y DEBT-VAULT-AUTOUNSEAL-001.

---

## Deudas técnicas relacionadas

| Deuda | Prioridad | Descripción |
|-------|-----------|-------------|
| DEBT-ALERTING-VAULT-001 | P2 | Migrar credenciales Discord/Telegram a Vault |
| DEBT-FALCO-LIBCURL-WHITELIST-001 | P2 | Reglas Falco para whitelist de destinos libcurl por componente |
| DEBT-VAULT-AUTOUNSEAL-001 | Post-FEDER | Auto-unseal Vault con YubiHSM2 (ver ADR-049) |

---

## Consecuencias

- Falco requiere reglas explícitas para monitorizar etcd-server y Vault como procesos críticos.
- Los scripts cron de recuperación deben implementarse y probarse en DAY 161 antes de considerarse parte de la Capa 2.
- El tiempo en `CRYPTO_DEGRADED` es operacionalmente irrelevante con HA activo. En single-node transitorio, Falco+cron minimizan esa ventana.
- Esta decisión no es un workaround. Es una decisión de diseño deliberada que refleja el valor que aRGus aporta a infraestructura crítica que no puede permitirse interrupción de servicio.
