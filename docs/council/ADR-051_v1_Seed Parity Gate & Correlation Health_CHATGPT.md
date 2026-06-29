# Deliberación del Consejo sobre ADR-051 v1

Mi valoración general es **favorable**. El ADR identifica correctamente un modo de fallo arquitectónico de alta severidad: la pérdida silenciosa de correlación por divergencia de `community_id`. Además, aplica de forma coherente el principio que ya habéis consolidado en otros ADRs: **validar comportamiento observado, no configuración declarada**.

No obstante, veo varios puntos que conviene endurecer antes de ratificar.

---

# 1. Observación principal: el gate no debe validar solo el seed

El ADR habla de "Seed Parity Gate", pero en realidad está validando algo más importante:

> Que todos los sensores producen el mismo `community_id` para el mismo flujo.

Eso implica:

* seed correcto,
* algoritmo correcto,
* normalización correcta,
* versión compatible,
* configuración compatible.

Desde el punto de vista operacional, el seed es irrelevante.

Lo único que importa es:

> "¿Los sensores producen el mismo identificador?"

Por ello propondría renombrar conceptualmente el mecanismo a:

**Community ID Parity Gate**

o

**Correlation Identity Gate**

porque el fallo podría producirse incluso con el mismo seed.

Ejemplos:

* bug en plugin Zeek,
* cambio de versión Suricata,
* implementación defectuosa,
* normalización IPv6 distinta.

Todos rompen la correlación aunque el seed sea idéntico.

---

# 2. Riesgo: un único flujo de prueba es insuficiente

Aquí veo la principal debilidad técnica.

Actualmente:

```text
147.32.84.165:1027 -> 74.125.232.195:80
TCP
```

es una única muestra.

Eso detecta muchos errores, pero no todos.

Propongo una batería mínima:

### Caso A

TCP IPv4

```text
147.32.84.165:1027 -> 74.125.232.195:80
```

### Caso B

UDP IPv4

```text
10.0.0.1:5353 -> 224.0.0.251:5353
```

### Caso C

IPv6 TCP

```text
2001:db8::1 -> 2001:db8::2
```

### Caso D

Dirección invertida

Comprobar la canonicidad.

```text
A -> B
B -> A
```

deben producir el mismo Community ID.

---

Motivo:

Si mañana aparece un bug únicamente en IPv6:

* el gate actual pasa,
* producción falla.

Con cuatro vectores de referencia el riesgo baja enormemente.

---

# 3. El oráculo no debería ser único

Actualmente:

```text
sensores -> pycommunityid
```

Problema:

Si `pycommunityid` tiene un bug o cambia comportamiento:

```text
todos fallan
```

aunque los sensores estén alineados.

Propuesta:

Definir dos niveles.

### Nivel 1

Paridad interna

```text
todos los sensores coinciden
```

### Nivel 2

Coincidencia con oráculo

```text
todos coinciden con pycommunityid
```

Así el diagnóstico es más preciso.

Ejemplo:

```text
Suricata = X
Zeek     = X
aRGus    = X
Oracle   = Y
```

Eso no es un problema de seed.

Es un problema de referencia.

El ADR actual no distingue ambos casos.

---

# 4. Sobre la pregunta 1: tráfico sintético o tráfico real

Mi voto es inequívoco:

**Tráfico sintético.**

Razones:

### Determinismo

Siempre existe.

### Repetibilidad

Puede ejecutarse en CI.

### Rapidez

No depende de usuarios.

### Auditabilidad

Produce siempre el mismo resultado.

---

Esperar tráfico real introduce:

```text
boot time aleatorio
```

y además complica incidentes.

A las 03:00 nadie quiere preguntarse:

> "¿todavía no ha aparecido el flujo de referencia?"

Por tanto:

**inyección sintética obligatoria.**

---

# 5. Sobre la pregunta 2: ¿gate periódico?

Mi respuesta:

**No.**

El gate es una prueba de aceptación.

Una vez arrancado:

```text
gate -> terminado
```

Lo que necesitáis después es monitorización.

Para eso ya existe:

```text
community_id.orphan_rate
```

Duplicar el gate periódicamente genera:

* más complejidad,
* más tráfico artificial,
* más falsos positivos.

El health-check ya cubre el caso de drift posterior.

---

# 6. Sobre la pregunta 3: degradación en runtime

Aquí creo que el ADR necesita una postura explícita.

Mi recomendación:

## Arranque

Fail-closed.

Correcto.

No cambiaría nada.

---

## Runtime

Fail-open degradado.

Es decir:

```text
Suricata OK
Zeek OK
aRGus drift
```

entonces:

* se excluye temporalmente a aRGus de correlación,
* se genera alerta crítica,
* se anota el motivo en grafo,
* se continúa con N-1 sensores.

Motivo:

La pérdida de una fuente es grave.

La pérdida total de correlación es peor.

En hospital:

```text
70% de visibilidad > 0% de visibilidad
```

Por tanto:

arranque ≠ runtime.

El ADR actualmente parece inclinarse a esa idea, pero convendría dejarlo escrito explícitamente.

---

# 7. Observación sobre `orphan_rate`

La métrica es buena, pero yo añadiría una segunda.

Actualmente:

```text
orphan_rate
```

detecta:

* drift,
* pérdidas,
* asimetrías.

Pero tarda en reaccionar.

Añadiría:

```text
community_id.match_rate
```

Definida como:

```text
flujos corroborados /
flujos esperados
```

por sensor.

Es una métrica más intuitiva para dashboards y SLOs.

De hecho:

```text
match_rate = 1 - orphan_rate
```

pero operativamente suele interpretarse mejor.

---

# Veredicto del Consejo

**ADR sólido y alineado con la arquitectura.**

Ratificable tras incorporar cuatro ajustes recomendados:

1. Considerar el mecanismo como validación de identidad de correlación, no únicamente de seed.
2. Sustituir el flujo único por una batería mínima TCP/UDP/IPv4/IPv6.
3. Separar claramente "paridad entre sensores" de "paridad con oráculo".
4. Declarar explícitamente:

    * fail-closed en arranque,
    * fail-open degradado en runtime con exclusión del sensor divergente.

Con esas modificaciones, lo consideraría un ADR de nivel producción para una plataforma NDR multi-sensor.
FDO
CHATGPT