Tienes razón — me pediste mis respuestas y me quedé en el rol de moderador. Si formo parte del Consejo (soy uno de los 8), me toca responder las preguntas, no solo formularlas. Aquí va mi voto razonado a las tres, como CLAUDE.

---

# DAY 170 — Respuesta del Consejo · CLAUDE

## P1 — Wazuh y la clave de correlación host↔red

**Mi voto: (A) + (C) combinados. (B) solo como optimización oportunista posterior, nunca como mecanismo primario.**

El error conceptual a evitar es tratar a Wazuh como "un sensor de red al que le falta el community_id". No le falta — opera en otra dimensión. Forzar un `community_id` en Wazuh (opción B como base) es ingeniería inversa de una clave que su telemetría no posee de forma natural, y produciría cobertura parcial y frágil. La 5-tupla no es el dominio de Wazuh; el **host y el tiempo** lo son.

Por eso el grafo debe tener **dos tipos de arista de correlación** (C), no una forzada:
- **Arista flujo↔flujo** por `community_id`: une aRGus/Suricata/Zeek sobre el mismo flujo de red. Es exacta (hash de 5-tupla).
- **Arista host↔flujo** por `(host, ventana_temporal)`: une eventos Wazuh al subgrafo de red del nodo donde ocurren. Es probabilística (correlación temporal + identidad de host), no determinista.

Esta asimetría no es un defecto, es **la estructura del problema**. Y es exactamente donde Neo4j + GDS aporta valor diferencial que un join SQL plano no daría: el grafo modela nativamente "este proceso malicioso (Wazuh) ocurrió en el host que originó este flujo C2 (aRGus/Zeek) dentro de esta CrisisWindow". Esa es la señal conjunta de calidad superior que persigues — y nace precisamente de **no** homogeneizar la clave.

**Sobre las sub-preguntas, que son donde está la dificultad real:**

- **NAT/proxy** — es el problema serio, y descarta cualquier ilusión de join determinista host↔red. Si el host observa su tráfico con IP interna y el sensor de red lo ve tras NAT con IP externa, la arista host↔flujo por IP **se rompe**. Mi propuesta: la arista host↔flujo no debe depender solo de IP, sino de `(IP_candidata ∪ correlación_temporal ∪ identidad_de_proceso↔puerto)`. Wazuh *sabe* qué proceso abrió qué socket local (puerto efímero) — ese `(proceso, puerto_local, timestamp)` es un puente más robusto que la IP cuando hay NAT, porque el puerto efímero sobrevive a la traducción de dirección aunque no de puerto. No es perfecto, pero es señal. **Esto merece ser su propia investigación** — lo marco abajo.

- **Ventana temporal asimétrica** — sí, rotundamente. La ventana red↔red puede ser estrecha (flujos del mismo incidente convergen en segundos). La ventana host↔red debe ser **más laxa y causal-asimétrica**: un proceso malicioso puede ejecutarse *antes* de generar tráfico (descarga→ejecución→C2) o *después* (tráfico de reconocimiento→explotación→proceso). La CrisisWindow de ADR-046 ya tiene el `late_arrival: true` para Wazuh, pero sugiero ir más allá: la ventana host debe ser **bidireccional alrededor del pico de la CrisisWindow**, no solo hacia adelante. Un `host_correlation_window` separado del `source_wait_timeout`.

## P2 — Coste de mantener seed=0 como invariante

**Mi voto: SÍ a un gate de arranque, y además un health-check continuo. Los dos, no uno u otro.**

El modo de fallo silencioso es inaceptable para infraestructura hospitalaria. Un join que devuelve cero matches no es distinguible, sin instrumentación, de "no hubo correlación" vs. "los seeds no casan y todo está roto". Eso es precisamente el tipo de fallo que mata un despliegue en producción sin que nadie se entere hasta el post-mortem.

Dos capas:
1. **Gate de arranque (P0, análogo al NTP):** el correlation-engine, al bootear, consulta el seed declarado de cada sensor registrado (vía su config o un endpoint de health) y **rechaza arrancar** si detecta divergencia. Igual que NTP rechaza arrancar con offset >1s. La paridad de seed es tan fundamental para el join como la sincronía temporal.
2. **Health-check continuo (runtime):** monitorizar la tasa de `community_id` huérfanos (flujos que un sensor reporta y que *ningún otro* sensor corrobora cuando deberían). Una tasa de orfandad sistemáticamente alta entre dos sensores que ven el mismo segmento es la firma de un seed mismatch que se coló post-arranque (reconfiguración, parche). Alerta CRITICAL.

El gate atrapa el error en deploy; el health-check atrapa la deriva en operación. Hospital: defensa en profundidad.

## P3 — ¿Es `community_id` global la clave correcta en multi-nodo?

**Mi voto: clave compuesta `(node_id, community_id)` en el esquema de Neo4j DESDE EL DISEÑO. Esta es la decisión más importante de las tres y la que más cuesta revertir.**

El `community_id` con seed compartido tiene una propiedad que es virtud en un nodo y trampa en varios: **es determinista sobre la 5-tupla, deliberadamente independiente del observador.** En un nodo eso es lo que quieres (tres sensores, mismo flujo, mismo ID → join). En multi-nodo es una **colisión semántica**: dos flujos `10.0.0.5:443→10.0.0.9:1234` en dos hospitales distintos producen idéntico `community_id`, y un join naïve los fusionaría como si fueran el mismo flujo. Catastrófico — mezclarías incidentes de dos centros.

La tentación de "ya lo arreglaremos con node_id en la ingestión" es deuda de esquema disfrazada. Si el grafo se construye con `community_id` como identidad de nodo-flujo, migrar después a clave compuesta es reescribir el modelo de datos con datos en producción. **Mucho más barato decidirlo hoy, con el grafo vacío.**

Propuesta concreta: el nodo-flujo en Neo4j se identifica por `(node_id, community_id)`. El `community_id` sigue siendo la clave de join **intra-nodo** (los tres sensores de un mismo nodo); el `node_id` es el namespace que evita colisión **inter-nodo**. La arista flujo↔flujo de P1 solo se forma dentro del mismo `node_id`. (Y ojo: esto interactúa con P1 — la correlación host↔red de Wazuh también es intra-nodo, porque el host vive en un nodo concreto.)

**Caveat para el Consejo:** esto asume que NO queremos correlacionar el "mismo" flujo entre nodos (p.ej. tráfico lateral hospital A→hospital B atravesando ambos). Si ese caso de uso existe (movimiento lateral inter-sede), entonces necesitamos *además* una noción de "flujo global" que una `(nodeA, cid)` con `(nodeB, cid)` cuando representan el mismo tráfico cruzando el límite — y eso es un tercer tipo de arista. Pero yo lo dejaría fuera del FEDER y lo marcaría como investigación futura; sobre-diseñar el multi-sede ahora es prematuro.

---

**Deudas/ADRs que mis respuestas sugieren abrir** (para que decidas si entran al BACKLOG tras el consenso):

- **ADR nuevo — modelo de correlación de dos aristas en Neo4j** (flujo↔flujo por community_id; host↔flujo por host+ventana). Recoge P1.
- **DEBT-CORRELATION-SEED-GATE-001** — gate de arranque de paridad de seed + health-check de orfandad. Recoge P2.
- **DEBT-NEO4J-FLOW-KEY-COMPOSITE-001 (P0 de esquema)** — clave `(node_id, community_id)` antes de poblar el grafo. Recoge P3. La marco P0 porque bloquea el diseño del correlation-engine.
- **RESEARCH — puente host↔red bajo NAT vía (proceso, puerto_local)** — la sub-pregunta dura de P1. Futuro.

---

Esas son mis respuestas como CLAUDE, con voto y razonamiento. Mi convicción más fuerte es **P3**: la clave compuesta es barata hoy e infernal de retrofitear. Si solo pudieras llevarte una cosa de mi voto al resto del Consejo, sería esa.

Ahora dime: ¿quieres que (a) integre estas respuestas como la sección CLAUDE dentro del documento del Consejo y lo escriba en `docs/council/`, (b) las deje como fichero `-respuesta-claude.md` aparte siguiendo tu patrón, o (c) ajuste algo de fondo antes? Y sigue en pie la pregunta del nombre del fichero del prompt principal.
FIRMADO
CLAUDE
