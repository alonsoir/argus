**Opinión del Consejo — DAY 170**

---

### 1. Valoración del cierre de hoy

El cierre de DAY 170 es **sólido y verificable**. Tres observaciones:

- **La tríada de red está sellada.** Tener `community_id` con seed 0 explícito en aRGus, Zeek y Suricata —verificado byte a byte contra `pycommunityid` y validado en VM— eleva la correlación de red de "intención" a "invariante". El test unitario da correctitud; la Diana E2E da confianza operacional. Esto es exactamente el nivel de rigor que se espera antes de declarar un join "viable".
- **La higiene del BACKLOG.** La deduplicación no fue solo limpieza: fue **arqueología forense**. Identificar que el daño vino de un `cat >>` manual y no del script de DAY 158 es crítico. Significa que la causa raíz está en los procedimientos humanos, no en la automatización. La lección de verificar con `grep secciones | sort | uniq -d` sobre el fichero completo, no solo cabeceras, debe pasar a la `runbook` de operación documental.
- **Idempotencia por línea.** La corrección en el Vagrantfile de Zeek (guardas por línea, no por bloque) es un patrón que debe replicarse en cualquier provisión futura. Anotarlo como regla de estilo en `docs/OPS-PROVISIONING.md` si existe, o crearlo.

**Veredicto:** DAY 170 está **cerrado con mérito**. Las deudas documentadas se pagan; no se dejan pendientes.

---

### 2. Valoración del plan para DAY 171

La propuesta del **cross-check E2E de tres ventanas** (cliente `.50` replayando Neris en LAN interna, captura paralela de los tres sensores) es **correcta y necesaria**.

El unit test prueba que cada sensor *implementa correctamente el algoritmo*. El E2E prueba que los tres sensores, en condiciones reales de red (timing del kernel, buffers de libpcap, reordenamiento de paquetes en la interfaz), **convergen al mismo valor semántico**. Son ortogonales: uno sin el otro deja un agujero.

**Sugerencia menor:** Documentar no solo el `community_id` esperado, sino también el **timestamp de captura relativo** y el **número de paquete** (o offset de flujo) en el que cada sensor lo emite. Si hay desfase temporal en la emisión (p. ej., Suricata agrupa por `flow.timeout` mientras Zeek emite al cierre del flujo TCP), eso es información valiosa para el correlation-engine, aunque el `community_id` sea idéntico.

**Veredicto:** Aprobado sin objeciones. Es el prerequisito lógico antes de tocar Wazuh.

---

### 3. Respuestas a las preguntas

#### **P1 — Wazuh y la correlación host↔red**

La intuición del equipo es **correcta: (A) + (C) combinados.**

**Arquitectura recomendada:**

- **Dimensión temporal + host (A):** Esta es la correlación *principal*. La mayoría de los eventos Wazuh (FIM, process monitoring, rootcheck) no tienen 5-tupla. Su punto de anclaje al grafo de red es el **nodo `Host`** (identificado por `host_id` estable, no por IP dinámica) y la **CrisisWindow**. El correlation-engine debe evaluar: "¿Qué eventos de red (community_id) ocurrieron en el mismo host, dentro de la ventana de crisis, que coinciden temporalmente con este evento Wazuh?" Esto es coherente con `late_arrival: true` de ADR-046 v3.

- **Doble arista en Neo4j (C):** El modelo de grafo debe tener dos tipos de arista de correlación:
    - `CORRELATES_BY_FLOW` (o similar): entre nodos de flujo de red, clave `community_id`.
    - `CORRELATES_BY_HOST` (o `OBSERVED_ON`): entre evento Wazuh y nodo `Host`, y entre nodo `Host` y flujo de red (por IP observada en ese momento).

  Esto permite que GDS opere sobre una **red multiplex**: una capa de topología de red (comunidades de flujos) y otra de topología de hosts (comunidades de comportamiento). El valor diferencial del grafo está precisamente en cruzar estas dos capas.

- **Enriquecimiento puntual (B):** Sí, pero como **optimización**, no como arquitectura principal. Para los eventos Wazuh que sí portan datos de red (módulo de conexiones activas, logs de firewall parseados), calcular `community_id` derivado en el ingester es barato y permite joins directos. Pero la cobertura es parcial; no se debe diseñar el sistema asumiendo que todos los eventos Wazuh tendrán esto.

**Sobre NAT/proxy:**

Este es el **agujero más peligroso** de la correlación host↔red. Si Wazuh ve la IP interna (`192.168.x.x`) y el sensor de red ve la IP NATada o la del proxy, un join por IP explícita falla silenciosamente.

**Solución:** El nodo `Host` en Neo4j debe ser **canónico** (por `host_id`, UUID estable de Wazuh). Las aristas `Host↔Flow` no deben ser por "IP igual", sino por **"IP observada en ese momento por ese sensor"**. Es decir:

```
(Host {host_id: "wazuh-uuid-123"})-[:HAS_IP_AT {ip: "192.168.1.50", timestamp: t1}]->()
```

Y el correlation-engine, al hacer el join, debe resolver: "¿Qué `host_id` tenía asignada la IP `X` en el momento del flujo?" Si hay NAT, se necesita una tabla de mapeo (o al menos, el registro histórico de IPs por host). En ausencia de mapeo NAT explícito, el engine debe caer graciosamente a la correlación temporal+host más laxa, en lugar de fallar por IP no coincidente.

**Sobre ventanas temporales:**

Sí, **distintas y más laxas para host↔red**.

- **Red↔red:** Ventana estricta. Dos flujos con el mismo `community_id` son el mismo flujo visto desde dos sensores; el tiempo de emisión puede desfasarse segundos (buffers), pero el evento de red es el mismo.
- **Host↔red:** Ventana asimétrica y más ancha. Un proceso malicioso puede ejecutarse, dormir 30 segundos, y luego abrir la conexión. O la conexión puede establecerse primero y el payload escribirse en disco después. Sugerencia: ventana de **±5 minutos** para host↔red, con posibilidad de extensión si hay indicios de "beaconing" o comportamiento lento. La CrisisWindow de ADR-046 v3 puede anidarse: una ventana global de crisis (p. ej., 1 hora) y dentro de ella, ventanas de correlación más estrechas.

#### **P2 — Coste del seed=0 como invariante**

**Sí, merece ambos: gate de arranque + health-check de huérfanos.**

El fallo es **silencioso y catastrófico**: community_ids distintos implican cero joins, lo que a su vez implica que el correlation-engine produce un grafo disconexo. Peor aún: el sistema no falla; simplemente emite señales de baja calidad que nadie detecta hasta una auditoría manual.

**Gate de arranque (preventivo):**
Análogo al gate NTP P0 de ADR-046. Antes de que el correlation-engine acepte su primera tupla, debe verificar que todos los sensores activos reportan seed consistente. Implementación ligera: el ingester, al recibir el primer evento de cada sensor, extrae el seed (del campo protobuf en aRGus, del log de Zeek, del EVE de Suricata) y lo compara. Si hay discrepancia, **aborta el pipeline** con error explícito: `SEED_MISMATCH`.

**Health-check de huérfanos (detectivo):**
Periódicamente (cada 5 minutos o por ventana de crisis), el engine calcula: "¿Qué porcentaje de community_ids aparece en solo un sensor?" En un sistema sano, la gran mayoría de los community_ids de red debería aparecer en al menos dos sensores (aRGus + Zeek, o aRGus + Suricata). Si el porcentaje de "huérfanos" (aparición única) supera un umbral (p. ej., 15%), dispara alerta `CORRELATION_DEGRADATION`. Esto captura no solo seed drift, sino también pérdida de sensores o particiones de red.

**Coste/beneficio:** Tres ficheros de config es un coste bajo de mantenimiento. Un gate + health-check es un coste bajo de implementación. El riesgo de fallo silencioso es alto. **El Consejo vota a favor.**

#### **P3 — `community_id` a largo plazo en multi-nodo**

**Decididlo ahora: la clave compuesta es `(node_id, community_id)`.**

El `community_id` con seed global es semánticamente correcto **solo dentro del dominio de un nodo** (misma 5-tupla, mismo seed, mismo punto de observación). En multi-nodo:

- Dos nodos en segmentos distintos pueden ver la **misma 5-tupla** (p. ej., tráfico replicado, o tráfico interno con IPs privadas superpuestas en dos sedes).
- NAT entre nodos hace que la misma 5-tupla represente **flujos semánticamente distintos**.
- El `community_id` colisiona intencionalmente para el *mismo* flujo visto por dos sensores del *mismo* nodo, pero **no debe colisionar** para flujos distintos en nodos distintos.

**Diseño recomendado:**

En Neo4j, el nodo `Flow` debe tener:
- `community_id`: el hash original (string).
- `node_id`: el identificador del sensor/nodo de captura.
- **Constraint/índice compuesto** sobre `(node_id, community_id)`.

No "namespaciéis" el `community_id` en el ingester (p. ej., `node_id:hash`) porque rompe la legibilidad y la capacidad de verificar contra oráculos externos. Mantenedlos como campos separados. Las queries de correlación *intra-nodo* usan solo `community_id`; las queries *inter-nodo* o de deduplicación usan el compuesto.

**¿Está `node_id` ya en el pipeline?**
Si cada evento que llega al ingester ya lleva `node_id` (por ejemplo, por la topología P2P de ADR-026/027), entonces el cambio es de esquema, no de pipeline. Si no lleva `node_id`, añadidlo **ahora**, antes de que el volumen de datos en producción haga la migración dolorosa.

**Veredicto:** Aprobado. Esquema compuesto desde el diseño. No aplacéis esto.

---

### 4. Cierre

El equipo ha tenido un día de **ingeniería disciplinada**: invariante verificada, deuda documental pagada, lecciones extraídas con diagnóstico causal correcto. El plan de DAY 171 es el paso lógico siguiente.

Las tres preguntas al Consejo tienen respuestas convergentes:

1. **Wazuh se une por host + tiempo, no por flujo; el grafo es dual; NAT se resuelve por `host_id` canónico, no por IP cruda.**
2. **Seed=0 merece gate de arranque + health-check de huérfanos.**
3. **La clave de grafo para flujos en multi-nodo es `(node_id, community_id)` desde hoy.**

No hay prerequisitos bloqueantes para DAY 171. Adelante con el E2E de tres ventanas. Que Diana registre no solo el `community_id`, sino también el **tiempo relativo de emisión** por sensor.

*— Opinión emitida por el Consejo, DAY 170*
FIRMADO
KIMI