# BACKLOG-RESILIENCE-ZMQ-LIMITS-001

**Estado:** Diferido — post-backlog primario
**Tipo:** BACKLOG (no DEBT: no es deuda contraída, es endurecimiento planificado)
**ADR paraguas:** ADR-047 (resiliencia en capas)
**Fecha registro:** DAY 163
**Prioridad:** Media — activable solo tras cierre del backlog primario y de la precondición de HA

---

## Contexto

ZMQ es el *fast path* de aRGus: latencia baja, throughput alto, auto-reconnect TCP.
Pero PUB/SUB es **at-most-once** por diseño: sin persistencia para suscriptores
offline, y con descarte silencioso al llenarse el HWM (`ZMQ_SNDHWM`/`ZMQ_RCVHWM`)
en red saturada.

En redes degradadas (escenario realista en infraestructura crítica de Extremadura
con conectividad no garantizada), esto es crítico para los mensajes que **no se
pueden perder**: señales de autonomía y cambios de ACL en firewall.

La arquitectura actual ya tiene el patrón correcto: **etcd como fuente de verdad
(durable path) + ZMQ como canal rápido de notificación (fast path)**. Falta el
watchdog explícito que cierre el lazo: detectar el silencio de ZMQ y caer a polling
de etcd.

Decisión de Alonso: **llevar ZMQ al límite** antes de evaluar cualquier sustituto.
No se reemplaza tecnología que funciona por especulación — solo con evidencia
empírica de su límite.

---

## PRECONDICIÓN BLOQUEANTE: etcd en HA (ADR-048)

**Este backlog NO se inicia hasta que etcd HA (ADR-048, Raft nativo) esté
implementado en producción.**

Razón: el Nivel 1 hace de etcd el oracle de estado vía fallback-to-etcd. Un oracle
single-point-of-failure invalida toda la resiliencia — el escenario que dispara el
fallback (partición, nodo caído) coincide con el escenario en que un etcd mononodo
podría no responder. La disponibilidad compuesta quedaría acotada por el eslabón
más débil.

Implicación de diseño: el fallback-to-etcd del Nivel 1 debe apuntar a la lista de
endpoints del clúster con failover en cambio de líder, no a un nodo fijo. El HA
moldea la implementación del Nivel 1, no solo lo habilita.

```
Cadena de dependencias:
  ADR-048 (etcd HA, Raft)  ──►  Nivel 1  ──►  Nivel 2  ──►  [trigger]  ──►  Nivel 3
  [implementación]              [ZMQ]         [ADR]          (contador)     (eval JetStream)
```

---

## Nivel 1 — Heartbeat + fallback-to-etcd instrumentado (coste mínimo)

- `ZMQ_HEARTBEAT_IVL` + `ZMQ_HEARTBEAT_TIMEOUT` en todos los sockets TCP entre
  componentes.
- Al fallar el heartbeat: el componente marca el canal como muerto y activa polling
  a etcd (clúster HA) como fallback.
- **Métrica obligatoria:** el evento "ZMQ silenciado → polling a etcd" incrementa un
  **contador observable**. Este contador ES el criterio de límite.
- Instrumentar también los **drops por HWM** (log contado), para convertir
  "ZMQ descarta mensajes" de teoría a observación.

**Alcance:** solo paths TCP entre componentes. El path IPC (Unix socket local,
etcd-server → firewall) queda fuera — es esencialmente lossless mientras el proceso
viva.

### Criterio de cierre del Nivel 1
El contador de fallback y el contador de drops por HWM están expuestos y observables.
A partir de aquí, la decisión sobre el Nivel 3 es un número, no una intuición.

---

## Nivel 2 — Formalización en ADR (FEDER scope)

ADR nuevo (número pendiente, asignar el siguiente libre) que documente:

- ZMQ es **at-most-once deliberado**.
- etcd (HA) es el **oracle de estado**.
- Cada componente tiene lógica **explícita** de fallback-to-etcd si ZMQ se silencia
  más de N segundos.

Un ADR documenta una decisión **ya tomada**. Por eso el Nivel 2 sí es ADR, mientras
que el Nivel 3 (JetStream) NO lo es todavía: esa decisión está deliberadamente
diferida a la evidencia.

---

## Nivel 3 — Evaluación de JetStream (post-FEDER, CONDICIONAL)

**No se inicia salvo trigger empírico.** El trigger lo da el contador del Nivel 1:

| Lectura del contador | Conclusión |
|---|---|
| ≈ 0 en producción real | ZMQ aguanta. JetStream nunca hace falta. **Decisión cerrada con datos.** |
| Alto y correlacionado con degradación de red | Trigger empírico para evaluar NATS JetStream (persistencia nativa, at-least-once, API comparable). |

Solo si el trigger se dispara: se redacta un ADR de decisión sobre JetStream. El ADR
llega cuando el contador habla.

---

## Resumen del razonamiento

El Nivel 1+2 no es solo mitigación: es **también el experimento** que decide si el
Nivel 3 llega a existir. Instrumentación primero, sustitución de tecnología solo con
evidencia. etcd HA es la precondición que hace que todo lo demás sea coherente.