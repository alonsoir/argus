Consejo de Sabios — revisión técnica ADR-057

La dirección general me parece sólida. Hay varias decisiones que muestran madurez arquitectónica:

* Separar escritura y consulta.
* Rechazar NL→Cypher libre.
* Tratar Kuzu como vista materializada y no como fuente de verdad histórica.
* Introducir transaction-time explícito (`ingested_at`).
* Priorizar mediciones sobre documentación.

Sin embargo, encuentro algunos puntos débiles que convendría cerrar antes de aprobar el ADR.

# 1. Riesgo principal: `ingested_at` no es realmente transaction-time completo

El ADR afirma que:

> "cuándo lo supimos por primera vez" → `ON CREATE SET` únicamente.

Eso funciona para la creación del nodo.

Pero no responde:

* ¿Qué ocurre cuando cambia un `Alert`?
* ¿Qué ocurre cuando se corrige una clasificación?
* ¿Qué ocurre cuando aumenta el score?

Si un nodo existe y luego se modifica:

```text
flow A
ingested_at = 10:00

10:15 -> score=0.6
10:30 -> score=0.9
```

El nodo seguirá teniendo:

```text
ingested_at = 10:00
```

que refleja el primer conocimiento, pero no el último.

Por tanto:

`ingested_at` = "first_seen"

NO

`transaction_time`

completo.

Recomendación:

Añadir explícitamente:

```text
first_seen_at
last_updated_at
```

o documentar que el transaction-time completo vive exclusivamente en el WAL.

Ahora mismo el ADR mezcla ambas interpretaciones.

---

# 2. Riesgo de crecimiento explosivo en T1

La plantilla:

```cypher
CORRELATES_FLOW*1..N
```

es peligrosa.

En grafos de correlación ocurre algo clásico:

```text
A -> B -> C -> D -> E ...
```

y un único nodo muy conectado puede convertir una consulta aparentemente inocente en miles o millones de nodos visitados.

Acotar N a 4 ayuda, pero no elimina el problema.

La métrica correcta no es:

```text
N <= 4
```

sino:

```text
max_nodes_visited
max_edges_visited
timeout_ms
```

Yo añadiría una cuota dura:

```text
max_graph_expansion = 10.000 nodos
```

o similar.

Es medible y evita ataques de complejidad.

---

# 3. Falta un ADR explícito de costes

T3:

> densidad de amenaza en vecindario.

Es una consulta razonable.

Pero no hay presupuesto de rendimiento.

Preguntas pendientes:

* ¿Tiempo máximo aceptable?
* ¿Latencia p95?
* ¿Tamaño esperado del grafo?
* ¿Número esperado de flujos por día?

Sin estos números es imposible saber si Kuzu sigue siendo adecuado cuando Argus++ lleve meses funcionando.

El ADR debería contener objetivos cuantificados.

Ejemplo:

```text
T1 p95 < 500 ms
T2 p95 < 200 ms
T3 p95 < 1 s
```

---

# 4. Punto ciego: recuperación ante corrupción del WAL

La bitemporalidad descansa completamente sobre:

```text
Kuzu = presente
WAL = pasado
```



Arquitectónicamente es correcto.

Pero ahora el WAL se convierte en:

```text
single point of historical truth
```

No veo respuesta a:

* corrupción parcial
* truncado
* pérdida de segmentos
* reconstrucción tras desastre

Recomendación:

Añadir requisito:

```text
restore_from_wal_smoke_test
```

como criterio de aceptación.

---

# 5. TinyLlama quizá sea innecesario

Esta es probablemente la parte más discutible.

El ADR propone:

```text
NL -> TinyLlama -> plantilla
```



Pero el catálogo inicial tiene sólo 6 consultas.

T1-T6 son tan pocas que podrían clasificarse mediante:

* reglas
* embeddings
* BM25
* intent matching

sin LLM.

Mi sospecha es que:

```text
6 plantillas
```

no justifican un modelo generativo.

La decisión sería más fuerte si el ADR exigiera una medición:

```text
TinyLlama accuracy
vs
Rule Engine accuracy
```

y elegir la solución más simple que alcance el objetivo.

Principio de ingeniería:

```text
No introducir un modelo donde basta una tabla.
```

---

# 6. Falta una plantilla crítica

Añadiría una T7.

Actualmente tienes:

* navegación
* contexto
* retro-hunt
* filtros

Pero falta algo fundamental para tu visión de grafos de ataque.

Propongo:

### T7 — Camino de propagación

```text
Dado un Alert,
mostrar el camino mínimo
hasta cualquier otro Alert crítico
a través de CORRELATES_FLOW.
```

Esto responde preguntas como:

```text
¿cómo llegó este host a comprometerse?
```

Es una consulta genuinamente graph-native.

Mucho más justificable que T5 o T6.

---

# 7. El argumento de Falco es correcto pero no definitivo

El ADR usa Falco como argumento para favorecer in-process.

Eso está bien.

Pero arquitectónicamente Falco no debería decidir el diseño.

La jerarquía correcta es:

```text
1. Modelo de concurrencia Kuzu
2. Rendimiento
3. Seguridad
4. Falco
```

Porque Falco puede reconfigurarse.

El lock de Kuzu no.

Por tanto reformularía el ADR:

```text
Falco refuerza la decisión.
No la fundamenta.
```

---

# Veredicto del Consejo

Estado actual:

```text
APROBABLE CON OBSERVACIONES
```

Ratificaría inmediatamente:

* `ingested_at`
* catálogo cerrado de plantillas
* rechazo de NL→Cypher
* arquitectura in-process por defecto
* WAL como fuente histórica

Antes de cerrar ADR-057 exigiría medir:

1. Concurrencia real Kuzu READ_ONLY + writer.
2. Coste de T1 sobre grafos grandes.
3. Accuracy TinyLlama vs clasificador basado en reglas.
4. Recuperación histórica desde WAL tras corrupción simulada.

Si esos cuatro experimentos salen bien, el ADR pasa de "buen diseño teórico" a "diseño validado empíricamente". Esa transición encaja perfectamente con el principio que ya aparece en el documento: medir, no votar. 
FDO
CHATGPT