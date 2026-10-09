**Respuesta del Consejo de Sabios — DAY292**

He leído el documento con atención. La honestidad metodológica del equipo es encomiable: medir antes de construir, documentar resultados negativos y no votar. A continuación, respondo a cada pregunta con argumentos medibles, basados en lo que habéis observado y en la literatura sobre detección de DDoS con ML en entornos críticos.

---

### 1. ¿B sin victim_pps es el candidato correcto? ¿Híbrido con regla absoluta en frío?

**B sin victim_pps es el candidato correcto como núcleo**, pero no como solución completa. La razón es que su fallo (víctima fría) es *explicable y acotado*: sin historia, el ratio no tiene suelo y el modelo no puede decidir. Un umbral absoluto de `victim_pps` (como el que aprendió B) es una **firma de laboratorio**: depende de las tasas que elegisteis (30/60/100 pps). En un hospital con tráfico legítimo de 5 pps o de 200 pps, ese umbral fallará en silencio o generará falsos positivos.

**Un híbrido tiene sentido solo si la regla absoluta es de *emergencia* y está calibrada con margen.** Propuesta concreta y medible:

- Regla: `victim_pps > 500` **y** `victim_rate_ratio > 10` **y** `reflection_signature == 1` (o firma de SYN flood). Es decir, solo cuando la víctima está fría **y** la evidencia de ataque es abrumadora por tasa absoluta.
- Este umbral de 500 pps no sale de vuestro lab; sale de un requisito de negocio: “¿cuál es el pps máximo que un servidor crítico legítimo puede recibir sin que sea anómalo?”. Eso se mide en el hospital, no en el laboratorio.
- **Medible**: comparad en frío la tasa de detección del híbrido vs. B sin victim_pps en los primeros 2 s de ataque. Si el híbrido detecta ≥ 80 % de los ataques a 60 pps en < 1 s **y** no marca ningún benigno en el corpus de contraste, es aceptable como *modo de arranque*. Si no, mejor no cablearlo: el coste de un falso bloqueo en un hospital es mayor que el de una detección tardía de 1–2 s.

**Conclusión**: B sin victim_pps como modelo principal; el híbrido solo como **modo de emergencia explícito**, con umbrales derivados de requisitos operativos, no de tasas de lab.

---

### 2. Dependencia de la firma: ¿basta con diversificar generadores?

**No basta.** Vuestros propios resultados lo demuestran: al dejar fuera NTP, el recall cae a ~0 %; al dejar fuera SYN, marca el 99 % del TCP benigno. Eso no es detección de comportamiento, es **aprendizaje de firmas de vuestros generadores** (tamaño fijo por familia).

**Diseño de dataset que propondría** (medible paso a paso):

1. **Benigno diverso y que solape**: no solo DNS pequeño/grande. Incluid HTTP, HTTPS, SSH, NTP legítimo, backups, video streaming, tráfico de historia clínica electrónica (HL7/FHIR), con **tamaños de paquete variables** y **tasas variables** (1, 5, 10, 50, 100, 200 pps). El benigno debe contener picos de 100 pps legítimos para que el modelo no aprenda “100 pps = ataque”.
2. **Ataques con parámetros aleatorizados**: en cada corrida, el generador debe variar el tamaño del paquete (p. ej., 64–1500 B), el puerto de servicio, el TTL, y la tasa (no solo 30/60/100, sino también 20, 45, 75, 120 pps). Si el tamaño es fijo, el modelo aprende el tamaño, no el patrón.
3. **Ataques que imitan comportamiento benigno**: SYN flood con handshake parcial pero con tamaños de paquete que coincidan con el benigno; reflexión DNS con respuestas de 200 B (no solo 1442 B); UDP flood con paquetes de 512 B (tamaño típico de VoIP).
4. **Base mixta UDP+TCP**: ataques que usen ambos protocolos en la misma corrida para forzar al modelo a depender de la dinámica temporal (ratio EWMA) y no del protocolo.
5. **Validación por permutación de familias**: además de dejar una familia fuera, haced **validación cruzada por generador**. Entrenad con generadores A, B, C y evaluad con generador D (no visto). Si el recall se mantiene > 90 % fuera del arranque, habéis roto la dependencia de firma.

**Medible**: la importancia por permutación de `mean_packet_size` y `reflection_signature` debe caer drásticamente tras este rediseño; el peso debe desplazarse hacia `victim_rate_ratio` y `flow_completion_rate`.

---

### 3. ¿Cablear ya el candidato o iterar el dataset antes?

**Cablear ya, pero en modo *shadow* (sin bloqueo automático) y con el dataset actual como referencia.** La puerta de “cero bloqueos E2E” es innegociable, así que no podéis poner B sin victim_pps a bloquear directamente. Pero sí podéis:

1. **Cablear el pipeline completo** (paridad Python/C++, umbrales crudos, tamaño/latencia) con el candidato actual.
2. **Ejecutarlo en paralelo al detector actual** en el hospital (o en un entorno de réplica) durante 2–4 semanas, registrando cada decisión con su vector de rasgos.
3. **Medir en producción**: FP por hora, latencia de detección, casos de víctima fría. Eso os dará el *número real* que CICDDoS2019 no puede dar (su clase benigna es ~0.1 %, single-capture, homogénea).
4. **Iterar el dataset en paralelo**, usando los falsos positivos y las detecciones tardías de producción como casos de entrenamiento.

**No iteréis el dataset antes de cablear** porque el laboratorio ya os ha dado toda la información que puede dar: sabéis que el modelo aprende firmas, sabéis que el arranque es el punto débil. Lo que falta es **tráfico real de hospital**, no más generadores sintéticos.

---

### 4. Política de agregación antes de bloquear

La decisión por paquete es demasiado ruidosa para un firewall. La literatura sobre agregación escalable ya advierte del **behavioral aliasing**: agregar comportamientos buenos puede parecer malo, y agregar malos puede parecer bueno. En un hospital, necesitáis una política **conservadora y explicable**.

**Propuesta medible**:

- **Por víctima y ventana de 1 s**: no por origen. Bloquear un origen benigno porque un paquete suyo coincidió con una firma es inaceptable.
- **K de N paquetes**: por ejemplo, **5 de 10 paquetes** en la misma ventana de 1 s deben ser clasificados como ataque por el modelo. Esto reduce la varianza del clasificador base.
- **Umbral de ratio**: además de K de N, la ventana debe tener `victim_rate_ratio > 5` (consistente con la histéresis de la EWMA).
- **Confirmación temporal**: la ventana debe repetirse en **2 ventanas consecutivas** antes de emitir un bloqueo. Esto añade 1 s de latencia pero elimina ráfagas benignas.

**Medible**: comparad la tasa de FP por hora con y sin agregación en el corpus de contraste (19 corridas). Si con agregación el FP es 0 y el recall fuera del arranque se mantiene ≥ 99 %, la política es válida. Si el FP sigue siendo > 0, subid K.

---

### 5. ¿Árbol poco profundo o regla explícita frente al bosque?

**Regla explícita, si su rendimiento es comparable.** En un hospital, la auditabilidad es un requisito de seguridad. Un bosque de 3714 nodos es una caja negra; una regla como:

```
if victim_rate_ratio > 5 and reflection_signature == 1 and flow_completion_rate < 0.3:
    attack
```

es **explicable, testeable y depurable**.

**Cómo medirlo**:

1. Entrenad un árbol de decisión de profundidad máxima 3 sobre los mismos datos (con `victim_rate_ratio`, `reflection_signature`, `flow_completion_rate`, `syn_ack_ratio`).
2. Comparad su recall y FP con B sin victim_pps en el test de 60 pps + DNS grande.
3. Si el árbol de profundidad 3 tiene un recall fuera del arranque ≥ 95 % y FP = 0, **usad el árbol o la regla explícita**. Si no, usad el bosque, pero publicad la regla aproximada derivada con SHAP o xAI para que los operadores del hospital sepan por qué se bloquea.

**Medible**: la regla explícita debe tener una **latencia de decisión < 1 µs** (ya la tenéis en el pipeline) y un **tamaño de código generado** mucho menor (cientos de líneas vs. miles de nodos).

---

### 6. ¿Es correcto sacar el arranque del entrenamiento?

**No, es un error metodológico.** Sacar los primeros 2 s de cada ataque del entrenamiento **enmascara el fallo real**: el modelo no puede detectar ataques en frío. Eso no es una “latencia”, es una **incapacidad estructural**.

Lo correcto es:

1. **Incluir el arranque en el entrenamiento**, pero con una etiqueta explícita de “fase de arranque” (o con un rasgo que indique si la clave tiene historia).
2. **Medir la latencia real**: desde el primer paquete del ataque hasta la primera decisión de ataque. Eso incluye los primeros 1,4 s de fallo.
3. **Diseñar una estrategia para el arranque**: el híbrido de la pregunta 1, o un modo de “observación” en el que el sistema no bloquea pero sí registra.

Publicar “recall 100 % fuera del arranque” es una métrica **condicionada**; no es lo mismo que “recall 100 % en producción”. El hospital necesita saber que durante los primeros segundos de un ataque a una víctima fría, el sistema **no protege**. Eso es un riesgo aceptable si se comunica, no si se oculta.

---

### 7. Sesgos y cosas pasadas por alto

1. **Sesgo de etiqueta por origen**: etiquetar por IP de origen asume que un origen es siempre benigno o siempre atacante. En un hospital, una IP comprometida puede empezar siendo benigna y luego atacar. La etiqueta debería ser **por flujo + ventana**, no por origen.
2. **Sesgo de métrica por paquete**: el recall por paquete puede ser 99,45 % con 6 FP, pero en un hospital con 100 000 paquetes/s, 6 FP en 0,5 s pueden ser **miles de bloqueos por hora**. Medid **FP por hora de operación**, no por fila.
3. **Falta de validación temporal**: vuestro test es de 60 pps + DNS grande 10 pps. ¿Qué pasa con un ataque de 120 pps intermitente (ráfagas de 10 s)? ¿O con un ataque que empieza a 5 pps y escala a 50 pps en 30 s? El modelo debe probarse con **perfiles de escalada temporal**.
4. **Concept drift**: los ataques evolucionan. El modelo debe tener un **mecanismo de reentrenamiento** (o al menos de monitorización de la distribución de rasgos) para no quedar obsoleto en 6 meses.
5. **Privacidad**: en un hospital, los rasgos de tráfico son datos sensibles. Aseguraos de que el pipeline no almacena payloads ni IPs más allá de lo necesario para la decisión y la auditoría.
6. **Paridad Python/C++**: la puerta que mencionáis es crítica. Un bosque de 3714 nodos puede generar código C++ con **deriva numérica** (diferencias en el orden de evaluación de umbrales). Haced una prueba de paridad **paquete a paquete** con 1 millón de paquetes aleatorios y verificad que la decisión es idéntica.
7. **Latencia de la EWMA**: la histéresis con τ = 3600 s bajo presión significa que una vez que la EWMA se “acostumbra” a un ataque, tarda **una hora** en volver a la normalidad. Si el ataque dura 90 s, la EWMA estará elevada durante los siguientes 60 minutos, lo que podría **enmascarar** un segundo ataque más pequeño. Medid el impacto de este “efecto de memoria” en un escenario de ataque seguido de tráfico benigno.

---

**Resumen ejecutivo**: B sin victim_pps como núcleo, híbrido de emergencia con umbrales operativos, dataset rediseñado para romper firmas, cableado en modo *shadow* antes de bloquear, agregación por víctima con K de N y confirmación temporal, regla explícita si rinde comparable, arranque incluido en entrenamiento y reportado como latencia real, y auditoría de FP por hora de operación. Medid todo, no votéis.