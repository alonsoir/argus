# Consejo de Sabios — Respuesta al DAY 170

La sensación general del Consejo es que el trabajo de DAY 170 es de los que cambian la naturaleza del sistema más que añadir una feature nueva. Habéis convertido el `community_id` en una **clave de identidad operacional verificable** y no simplemente en un campo más del protobuf.

La validación contra oráculo externo, la fijación explícita de `seed=0` en los tres sensores y la comprobación con tráfico real son exactamente las medidas que evitan años de "joins fantasma" imposibles de depurar.

Veredicto general:

**DAY 170 = aprobado con nota alta.**

Lo realizado hoy reduce deuda arquitectónica futura de forma significativa.

---

# Evaluación de lo realizado hoy

## Sobre community_id

El Consejo coincide en que habéis seguido el orden correcto:

1. Correctitud matemática (oráculo).
2. Correctitud de implementación (tests).
3. Correctitud de provisión (Zeek/Suricata).
4. Correctitud operacional (captura real).

Muchos proyectos intentan empezar por el paso 4 y acaban persiguiendo fantasmas.

La observación más importante es esta:

> El verdadero activo no es el hash.
>
> El activo es que todos los sensores producen exactamente el mismo hash.

Eso es lo que convierte a `community_id` en una clave de correlación utilizable.

---

## Sobre la limpieza del BACKLOG

La reparación era necesaria.

El Consejo considera especialmente importante la lección aprendida:

> Las comprobaciones de integridad deben buscar duplicación semántica, no únicamente textual.

La conclusión de usar validaciones por secciones y no por cabeceras es correcta.

No parece existir riesgo inmediato de regresión si efectivamente el origen fue un append manual sobre el mismo fichero.

---

# Sobre el plan de DAY 171

El Consejo respalda completamente el E2E propuesto.

De hecho considera que es el siguiente paso lógico obligatorio.

El objetivo real del ensayo no es verificar el hash.

Ya se ha demostrado.

El objetivo es verificar:

```
Paquete real
        ↓
aRGus
Zeek
Suricata
        ↓
community_id idéntico
        ↓
Ingesta
        ↓
Join real
```

Es decir:

**validar la cadena completa de confianza.**

---

# P1 — Correlación Wazuh ↔ Red

Esta es probablemente la decisión arquitectónica más importante de las planteadas.

La opinión mayoritaria del Consejo es:

## Opción B sola: NO

Calcular `community_id` desde eventos Wazuh sólo sirve para una fracción de los eventos.

Muchos eventos relevantes jamás tendrán 5-tupla:

* creación de proceso
* modificación de binario
* persistencia
* elevación de privilegios
* cambios de registro
* integridad de ficheros

Construir la arquitectura alrededor de algo que sólo existe a veces es un error.

---

## Opción A sola: insuficiente

Correlación únicamente por host + ventana temporal funciona.

Pero pierde mucha expresividad.

Terminas teniendo:

```
host X
hizo algo raro
cerca de un flujo raro
```

Eso es útil.

Pero no es una relación fuerte.

---

## Opción C: correcta

El Consejo considera que el grafo debe modelar explícitamente dos realidades distintas.

### Dimensión red

```
Flow
  ↔
Flow
```

unidos por:

```
community_id
```

---

### Dimensión host

```
Host
  ↔
Flow
```

unidos por:

* IP
* MAC (si existe)
* hostname
* agent_id
* identidad del activo

según disponibilidad.

---

## Recomendación final

La solución más robusta es:

### (A) + (C)

Es decir:

```
Wazuh Event
       ↓
Host
       ↓
Flow
       ↓
Community_ID
       ↓
Otros Flows
```

No intentar forzar a Wazuh a hablar el lenguaje de red.

Modelar explícitamente que es otra fuente de evidencia.

---

## Sobre NAT y proxies

Aquí el Consejo es unánime:

**el nodo Host debe ser una entidad de primer nivel del grafo.**

No confiar únicamente en IP.

Porque:

```
Host real
      ↓
NAT
      ↓
IP observada
```

rompe la correlación.

El Host debe disponer de atributos múltiples:

* agent_id
* hostname
* fqdn
* MAC
* IP histórica
* etiquetas de inventario

para resolver identidad.

---

## Ventana temporal

Sí.

Debe ser distinta.

Recomendación:

### Red ↔ Red

Ventana corta.

Segundos.

Incluso subsegundos si el pipeline lo permite.

---

### Host ↔ Red

Ventana más amplia.

Minutos.

Porque:

```
proceso arranca
      ↓
espera
      ↓
abre conexión
```

es un patrón completamente normal.

La correlación host suele tener más latencia natural.

---

# P2 — Gate para seed

La respuesta es sí.

Sin ninguna duda.

El Consejo considera el `seed` equivalente a:

* versión de esquema
* sincronización NTP
* compatibilidad protobuf

Si difiere:

```
todo parece funcionar
pero nada correlaciona
```

Lo peor posible.

---

## Recomendación

Dos mecanismos.

### 1. Startup Gate

Al arrancar:

```
sensor A
sensor B
sensor C
```

publican:

```
community_id_seed
community_id_version
```

El correlation-engine verifica paridad.

Si no existe:

```
estado DEGRADED
```

o incluso

```
FAIL_START
```

según política.

---

### 2. Health Check Continuo

Métrica:

```
community_id_orphan_ratio
```

Por ejemplo:

```
flows_sin_match / flows_totales
```

Si aumenta de forma anómala:

alerta.

Porque un cambio accidental de seed suele verse primero como explosión de huérfanos.

---

# P3 — ¿community_id global o compuesto?

Esta es la pregunta más estratégica.

La opinión del Consejo:

## No usar community_id como clave primaria global

Porque semánticamente identifica:

```
5-tupla + protocolo
```

No identifica:

```
sensor
sitio
nodo
tenant
```

---

## Diseño recomendado

Desde hoy mismo:

```
(node_id, community_id)
```

como identidad operacional.

Y mantener:

```
community_id
```

como propiedad indexada.

---

### Motivo

Dentro de tres años será mucho más fácil ignorar `node_id` cuando no haga falta que migrar millones de nodos del grafo.

El coste actual es casi cero.

El coste futuro puede ser enorme.

---

# Conclusión del Consejo

Las tres decisiones recomendadas son:

### 1

Correlación host↔red mediante:

**Host + Ventana Temporal + Grafo de relaciones**

(A + C)

---

### 2

Introducir un gate de compatibilidad de `seed` y un health-check de huérfanos.

---

### 3

Adoptar desde ahora:

```text
(node_id, community_id)
```

como identidad operacional del flujo en Neo4j.

---

Respecto a DAY 171, el Consejo no ve prerrequisitos bloqueantes antes del E2E. El ensayo propuesto es exactamente el siguiente paso que corresponde tras haber cerrado la validación contra especificación y la provisión de los tres sensores. Si el E2E sale verde, podréis afirmar con bastante confianza que el join basado en `community_id` es viable en producción y no sólo en laboratorio.

FIRMADO
CHATGPT
