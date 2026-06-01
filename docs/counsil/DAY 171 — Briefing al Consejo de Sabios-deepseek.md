**Intervención del Consejo de Sabios — DAY 171**

Apreciado equipo,

Leemos el briefing con atención y reconocemos la solidez del trabajo de hoy. El cierre de la mitad sniffer con emisión observable, el verificador de paridad y el dry-run exitoso son pasos fundamentales. Vuestro rigor al distinguir validación empírica (data‑plane) frente a especificación, y al no descartar anomalías, es exactamente la madurez que esperábamos. Pasamos a las preguntas.

---

### **P1 — Lenguaje del verificador vs. adaptadores de ingesta**

*El verificador de paridad (`community_id_crosscheck.py`)*  
Vuestro instinto es correcto: **mantenedlo en Python**.  
Es una herramienta de host, de uso esporádico (replays, laboratorio), que orquesta `vagrant ssh` y que convive con `parse_results.py` y el resto del *scaffolding* de experimentos. Migrarla a C++ no la acerca al pipeline; solo añade fricción en mantenimiento para una pieza que debe ser ágil de modificar. La coherencia con el ecosistema de análisis de laboratorio pesa más que la uniformidad de lenguaje.

*Los adaptadores de ingesta real (AdapterSpec, en pipeline)*  
**Ahí sí es pertinente la discusión de lenguaje.**  
El adaptador que lee `eve.json` (Suricata) y `conn.log` (Zeek), normaliza a `SecurityEvent` y publica por ZeroMQ al motor de correlación, **corre en las VMs y forma parte del pipeline**. Nuestra recomendación:

- **C++ para el adaptador de Suricata** que lee ficheros JSON en línea. Podéis usar `nlohmann/json` (header-only, bien probada) y la misma infraestructura de ZeroMQ que ya tiene el sniffer. Mantiene la criticidad, rendimiento y `-Werror` del pipeline.
- **Para Zeek** evaluad dos caminos:
    - (A) Un proceso externo en C++ que siga `conn.log` como un `tail -F` con rotación, similar a lo que hará el adaptador de Suricata. Simple, homogéneo, sin dependencias de Zeek internals.
    - (B) Un plugin nativo de Zeek (C++) que publique eventos directamente, evitando el fichero. Ventaja: menor latencia y saneamiento del camino de datos. Inconveniente: acoplamiento a la API de Zeek (v4.x/v5.x), mantenimiento adicional.
    - La decisión depende de si valoráis más la homogeneidad del adaptador (A) o la optimización de latencia y la robustez del canal (B). Para la fase actual, (A) es suficiente y os permite tener un único ejecutable de adaptador configurable por fuente. Ya habrá tiempo de madurar a (B) si el correlation‑engine lo exige.

**Resumen:** Python para andamiaje, C++ para la línea de producción. Separación limpia.

---

### **P2 — Criterio de aceptación de anomalías en el replay #1**

Debéis fijarlo **antes** del replay y sin ambigüedad. Dado que el replay #1 se hace en condiciones ideales (mismo pcap, tasa baja, tres sensores en modo promiscuo viendo todos los paquetes), **el objetivo es cero anomalías en flujos TCP/UDP**.

Razonamiento:
- La especificación de `community_id` (Corelight, seed=0) es determinista y la habéis implementado de forma idéntica en los tres sensores (ADR-046 v4).
- Si los tres ven exactamente los mismos paquetes, la 5‑tupla que extraen es la misma, por lo que el `community_id` **debe coincidir**. No hay margen para diferencias de capa: la tupla se construye a partir de cabeceras IP/TCP/UDP que no dependen de reensamblado, estado de conexión ni heurísticas.
- Las diferencias que observasteis en el dry‑run (14 K anomalías) son un artefacto de datos no homogéneos y diferencias de cobertura; en el replay en vivo con condiciones controladas, ese número debe colapsar.

**Criterio de aceptación para el hito #1:**
> Tras filtrar las `expected_diff` (ICMP, IPv6-ICMP y cualquier protocolo donde aRGus devuelve `nullopt` por diseño), **las categorías `agree` y `anomaly` deben ser mutuamente excluyentes: `anomaly` = ∅**.  
> Es decir, **cero discrepancias en flujos TCP/UDP observados por los tres sensores**.

Si aparecieran anomalías reales, no se racionalizan como “diferencias legítimas de capa”. Se tratan como defecto a corregir *antes* de continuar (bug de canonicalización, pérdida de paquetes silenciosa, error de despliegue). Este umbral estricto es el que da sentido al cimiento sobre el que se apoya AdapterSpec §10.

Cuando más adelante enfrentéis tráfico hostil (fragmentación, evasión, RSS bajo carga), las discrepancias que sobrevivan alimentarán el grafo de desacuerdo, y ese es su valor. Pero hoy, el cimiento debe ser monolítico.

---

### **P3 — Promiscuidad del intnet y riesgo de falso verde**

El riesgo que identificáis es real y el `guard N>0` lo mitiga, pero no basta: **un falso “tres vacíos coinciden” es una pérdida de tiempo y de confianza**.  
**Confirmamos: `PromiscModePolicy=allow-all` debe ser invariante documentado en el Vagrantfile para las interfaces `eth1` de las VMs Suricata, Zeek y Defender.**  
Además, sugerimos incluir en la orquestación del replay un **pre-flight check** de 15 segundos que:
1. Ponga `eth1` en modo promiscuo explícitamente (`ip link set eth1 promisc on`).
2. Lance un `tcpdump` rápido en cada VM para verificar que se ven los paquetes ARP/tráfico del intnet.
3. Aborte el replay con un mensaje claro si algún sensor muestra recuento cero tras el pre‑tráfico.

Así evitáis que un olvido de configuración en el Vagrantfile os haga perseguir fantasmas.

---

### **Nota adicional del Consejo: próxima jugada**

Vemos tres acciones inmediatas para mañana (DAY 172) antes del replay:
- **Instrumentar el pre‑flight check** y fijar `allow-all` en el Vagrantfile.
- **Redactar una sola orquestación** (script bash desde el host) que: levante sensores, active `ARGUS_CID_CROSSCHECK=1`, lance `tcpreplay` a tasa ≤1 Mbps, detenga Zeek con `kill -TERM`, y ejecute el verificador con el criterio estricto de §P2.
- **Aislar el caso bidireccional** con un pcap mínimo (SYN+SYN-ACK) para confirmar que la canonicalización por tupla ordenada funciona; eso os dará una segunda verificación de escritorio antes del replay completo.

El delta de timestamps de emisión (punto 3 del briefing) puede esperar al post‑replay: primero demostrad que los tres sensores derivan exactamente los mismos *valores*; luego mediréis *cuándo* los emiten.

---

El Consejo os felicita por la calidad de la ejecución y por elevar el estándar de validación empírica. Continuad con esta disciplina.

— El Consejo de Sabios

DEEPSEEK