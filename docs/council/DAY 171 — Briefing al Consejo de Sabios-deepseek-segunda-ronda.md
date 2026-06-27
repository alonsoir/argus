**Intervención del Consejo de Sabios — DAY 171, Segunda Ronda**

Apreciado equipo,

Hemos leído con detenimiento vuestra segunda exposición. La grieta en P2 es real, y celebráis el debate porque es el tipo de fricción técnica que previene decisiones que esconden defectos. Procedemos a dirimirla con argumentos contrastables, sin dejar espacio para interpretaciones.

---

### **1. Sobre la posibilidad de discrepancia legítima de VALOR en TCP/UDP (P2)**

**La respuesta del Consejo es unánime y firme: NO existe mecanismo legítimo que produzca un `community_id` de VALOR distinto para el mismo flujo TCP/UDP cuando los tres sensores ven exactamente los mismos paquetes, sin pérdida y a tasa baja.**

Aportamos la evidencia:

- El `community_id` se computa exclusivamente sobre la **5‑tupla** (direcciones IP origen/destino, puertos origen/destino, número de protocolo). Estas cabeceras están en los paquetes IP/TCP/UDP que los sensores capturan **bit a bit idénticos** si el pcap se reproduce sin pérdida en un intnet común.
- Reensamblado TCP, seguimiento de estado, análisis de aplicaciones, orden de llegada de paquetes, retransmisiones… todo ello ocurre en capas superiores a la extracción de la 5‑tupla. Ninguno de esos mecanismos modifica las cabeceras IP/TCP/UDP ya fijadas en el cable.
- Si un sensor viera paquetes fuera de orden, la 5‑tupla sigue siendo la misma, porque el `community_id` no depende de números de secuencia ni de la dirección del flujo; se usa la regla de orden canónico: `(ip_menor, puerto_menor, ip_mayor, puerto_mayor, protocolo)`. Esa ordenación es determinista y no varía entre sensores.
- La única vía para obtener valores distintos es que un sensor extraiga una tupla diferente, lo cual puede ocurrir por:
  1. **Bug en la canonicalización** (ej. no aplicar correctamente la ordenación, mal manejo de VLAN/QinQ que afecte a la 5‑tupla, error en el parseo de cabeceras).
  2. **Evasion o manipulación activa** por parte del tráfico (p. ej. fragmentación que oculte cabeceras, inyección de paquetes con tuplas diferentes que pretendan confundir a los sensores).

Ambos casos son **defectos o ataques**, no diferencias legítimas de capa. Por tanto, **la propuesta de umbral porcentual (1 %, <2 %, etc.) es técnicamente incorrecta** porque no existe un “porcentaje tolerable” de discrepancia de valor; cualquier discrepancia de valor es un indicador de fallo o amenaza.

**Conclusión:** El criterio correcto para el replay #1 es **cero discrepancias de valor en flujos TCP/UDP**. Esto no es “cero ciego”, sino el resultado natural de la construcción del `community_id`. Lo que los defensores del umbral interpretan como “1 % legítimo” es en realidad **discrepancia de presencia** (un sensor no emitió el mismo flujo que los otros), y en condiciones ideales de replay (tasa baja, sin pérdida) esa presencia tampoco puede ser tolerada, porque debe ser cero.

---

### **2. Clasificación obligatoria y el criterio VERDE del replay #1**

Coincidimos plenamente con la síntesis que proponéis: **clasificación obligatoria de anomalías, no un número mágico**. Lo refinamos y lo convertimos en el criterio de aceptación definitivo para el hito #1:

- Tras el replay, el verificador separa `expected_diff` (flujos ICMP/IPv6‑ICMP que aRGus deliberadamente no computa) del resto.
- Las anomalías (todo aquello que no sea `agree`) se dividen en tres categorías:
  - **(a) Bug de valor**: discrepancia de `community_id` sobre la misma 5‑tupla.
  - **(b) Discrepancia de presencia**: un sensor emite un `community_id` que otro no emitió, **sin discrepancia de valor** (podemos comprobarlo usando la 5‑tupla como etiqueta forense, como ya hacéis).
  - **(c) Inexplicable**: cualquier otra situación que no encaje en (a) ni (b), con prioridad para ser tratada como posible evasión.
- **El replay #1 se considera VERDE si y solo si**:
  - Cero anomalías de tipo (a).
  - Cero anomalías de tipo (b) después de verificar que **los tres sensores capturaron exactamente los mismos paquetes** (sin pérdidas; ver punto 3).
  - Cero anomalías de tipo (c).

Este criterio es el “microscopio” que pedís: cada anomalía se nombra y se investiga, no se esconde bajo una tolerancia. Es perfectamente compatible con la decisión ya tomada de no descartar ninguna discrepancia.

---

### **3. El prerequisito del drop: bloqueante pero resuelto (y barato)**

**Los contadores de paquetes capturados y perdidos son un prerequisito inexcusable para el replay #1.** Sin ellos, la clasificación (b) es conjetura: una ausencia de emisión puede deberse a pérdida de paquetes o a un bug de no‑emisión. Como bien señaláis, los tres sensores ya exponen esos contadores:

- **aRGus**: `events_processed`, `events_dropped`, `pkts_sent`, `send_failures` (accesibles internamente o a través de un socket de control).
- **Suricata**: `stats.log` con `capture.kernel_packets`, `capture.kernel_drops`, `decoder.pkts`, etc.
- **Zeek**: `capture_loss.log` y `stats.log` con `capture_loss` y `pkts_dropped`.

**Decisión del Consejo:** Es prerequisito, pero **no requiere instrumentación nueva**; es simplemente recoger esos contadores antes y después del replay para calcular la diferencia. El verificador (`community_id_crosscheck.py`) debe:
1. Antes del replay, consultar los contadores en cada VM (p.ej. mediante `vagrant ssh` y grepping los ficheros de log).
2. Después del replay, repetir la consulta.
3. Comparar: si algún sensor reporta `drop > 0` o diferencia negativa en el total de paquetes capturados, **el replay se invalida** y se repite con corrección. Si no hay drop, podemos afirmar con certeza que cualquier ausencia de `community_id` es un fallo de emisión, no de captura, y se tratará como bug (a) si el valor de la 5‑tupla es distinto, o como bug de no‑emisión si la 5‑tupla está pero no se ha sellado el cid.

Esta instrumentación es trivial y debe incorporarse al pre‑flight check. Así matamos dos pájaros: satisfacemos la necesidad de clasificación y garantizamos la integridad del experimento.

---

### **4. Separación valor/timing (Pregunta de vuelta a Gemini)**

**Confirmamos rotundamente la postura del equipo.**  
El replay #1 debe usar la distribución temporal natural del tráfico Neris. No se deben inyectar ráfagas artificiales para forzar flushes. La razón es quirúrgica:

- El experimento #1 valida **paridad de VALOR** del `community_id`. Cualquier manipulación del ritmo del tráfico que no esté en el pcap original introduce una variable exógena. Si forzamos cierres de flujo, podríamos provocar que Suricata o Zeek emitan un flujo que aRGus aún no ha cerrado, dando lugar a discrepancias de presencia que no existirían con el timing natural. Eso contaminaría los resultados del experimento de valor.
- La calibración de tiempos de emisión (`ts_emision_ns`) y la determinación de los `source_wait_timeout` (aRGus 5s, Suricata 10s, Zeek 20s) es un **experimento posterior** (D+1 o D+2), donde sí tiene sentido usar ráfagas controladas que fuercen flujos cortos y permitan medir la latencia de cada sensor. Separar los experimentos mantiene limpia cada hipótesis bajo prueba.

Así pues, **no mezclar**. El replay #1 se ejecuta con la cadencia original del pcap Neris.

---

### **5. Resumen ejecutivo para mañana (DAY 172)**

- **Criterio de aceptación P2 sellado**: cero anomalías de tipo (a), (b) o (c) tras verificar captura sin pérdidas. El script de verificación clasificará obligatoriamente cualquier anomalía, pero el replay no pasa si alguna existe.
- **Drop counters integrados**: añadir al script de verificación la recolección de contadores pre‑ y post‑replay y la comprobación de `drops == 0` en los tres. Si no se cumple, se aborta la validación y se repite el replay.
- **Separación valor/timing firme**: replay #1 con timing natural del Neris.

P1 y P3, como indicáis, están cerrados y con decisión firme. No hay más debate.

El Consejo os exhorta a proceder con la implementación del verificador ampliado y la recolección de contadores. Mañana, el replay #1 debe ser una verificación limpia del cimiento sobre el que se asienta todo AdapterSpec.

Con el voto unánime del Consejo,  
— Los Sabios

DEEPSEEK