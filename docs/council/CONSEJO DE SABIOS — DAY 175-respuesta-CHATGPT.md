Consejo reunido. Mi lectura es que DAY 175 ha sido un día mucho más importante de lo que aparenta.

Muchos equipos consideran "terminado" un writer cuando pasa sus unit tests. Vosotros habéis demostrado algo más valioso: que el dato generado por el productor real puede ser consumido por el consumidor real usando los secretos reales. Históricamente, ahí es donde aparecen la mayoría de los fallos de integración.

---

# Evaluación general de DAY 175

### Lo que considero especialmente acertado

**1. Cablear en el punto único antes de la bifurcación RAG/no-RAG**

Eso evita crear una segunda semántica de generación de bronce.

Si el contrato de correlación depende de una rama concreta del pipeline, tarde o temprano aparecerán divergencias imposibles de depurar.

[SUGERENCIA-ARQUITECTO: Todo evento que aspire a ser correlable debe pasar por exactamente una ruta de emisión de bronce.]

---

**2. Mantener protobuf fuera del correlation-engine**

Me parece una decisión de arquitectura muy sana.

El engine debe consumir un contrato estable (CSV hoy, Avro mañana), no depender de la representación interna de ml-detector.

La dependencia protobuf crea acoplamiento temporal.

Hoy es protobuf.
Mañana puede ser FlatBuffers.
El engine no debería enterarse.

---

**3. Descubrir el problema de provisioning ahora**

El hallazgo más importante del día no son las 3.712 filas.

Es esto:

> el round-trip pasó y la integración real falló.

Eso demuestra que la estrategia de validación está funcionando.

Muchos incidentes de producción nacen exactamente porque se prueba:

```
writer(real)
↓
reader(real)
↓
misma clave hardcodeada
```

y se asume que el sistema está validado.

No lo está.

Vosotros habéis validado una capa más arriba: el provisioning.

Eso tiene mucho valor.

---

# Q1 — ¿Injectors primero o consumidor primero?

Coincido con tu instinto.

**A primero.**

No por comodidad.

Por economía de defectos.

Ahora mismo la situación es:

```
Productor real
↓
Bronce real
↓
Consumidor futuro
```

Si implementáis el consumidor antes:

```
Productor real
↓
Bronce real
↓
Consumidor nuevo
```

cada prueba dependerá de:

* sniffer
* pcap
* eBPF
* timings
* infraestructura

Es decir, pruebas caras.

---

Lo que necesitáis es:

```
Injector
↓
Bronce
↓
Consumidor
```

ejecutable en CI.

---

Mi orden sería:

### Fase 1

Actualizar todos los injectors.

Objetivo:

```
community_id != empty
```

siempre que el flujo sea correlable.

---

### Fase 2

Crear un test de integración:

```
Injector
↓
CorrelationWriter
↓
CSV real
↓
parse_and_verify
```

sin eBPF.

---

### Fase 3

Construir encima:

```
Injector
↓
Bronce
↓
Avro
↓
ZMQ
↓
Consumer
```

---

[SUGERENCIA-SISTEMAS: No construyáis más componentes sobre un generador de datos que no pueda ejecutarse de forma determinista en CI.]

---

# Q2 — int o string para authoritative_source

Mi respuesta es:

**Bronce debe almacenar ambos.**

Porque cada opción resuelve un problema distinto.

---

Si guardas sólo string:

```
ML_PRIORITY
```

ganas legibilidad.

Pierdes:

* espacio
* velocidad
* facilidad de indexación

---

Si guardas sólo int:

```
4
```

ganas eficiencia.

Pierdes:

* auto-descripción
* robustez ante renumeraciones

---

La experiencia de sistemas distribuidos suele acabar en:

```csv
authoritative_source=4
authoritative_source_name=ML_PRIORITY
```

---

Ventajas:

### Compatibilidad

Si un día:

```
ML_PRIORITY = 7
```

el histórico sigue siendo interpretable.

---

### Forense

Dentro de tres años alguien abrirá el CSV con:

```bash
awk
grep
cut
```

y agradecerá no tener que buscar el enum en Git.

---

### Migraciones

El nombre suele ser el contrato estable.

El número suele ser implementación.

---

[SUGERENCIA-DATOS: En sistemas que aspiran a larga vida, el valor numérico y el valor semántico suelen merecer coexistir.]

---

Si obligaras a elegir uno solo:

**preferiría string.**

Porque corregir almacenamiento es barato.

Corregir pérdida de semántica histórica es caro.

---

# Q3 — HMAC simétrico cuando existan miles de nodos

Aquí sí veo una cuestión estratégica importante.

No urgente para DAY 176.

Pero sí digna de ADR.

---

Hoy vuestro modelo es:

```
writer
↓
HMAC(K)
↓
reader
```

donde ambos conocen:

```
K
```

Perfectamente válido dentro de un nodo.

---

Cuando aparezcan miles de sensores:

```
sensor A
sensor B
sensor C
...
sensor N
```

el servidor central necesitará conocer:

```
KA
KB
KC
...
KN
```

para verificar.

Eso escala.

Pero introduce gestión masiva de secretos.

---

La pregunta clave es:

> ¿Queréis autenticidad o queréis no repudio?

Son cosas distintas.

---

### HMAC

Garantiza:

* integridad
* autenticidad compartida

No garantiza:

* no repudio

Porque cualquiera con la clave pudo generar el mensaje.

---

### Ed25519

Garantiza:

* integridad
* autenticidad
* no repudio

Porque:

```
sensor firma
servidor verifica
```

y el servidor nunca posee la clave privada.

---

Mi recomendación arquitectónica:

### Corto plazo

Mantener HMAC.

Es simple.
Es rápido.
Ya funciona.

---

### Medio plazo

Introducir una abstracción:

```cpp
ISignatureVerifier
```

o

```cpp
IIntegrityProvider
```

para que el consumidor no sepa si valida:

* HMAC
* Ed25519
* futuro mecanismo

---

### Largo plazo

Cuando exista agregación multi-tenant real:

```
Hospital A
Ayuntamiento B
Empresa C
```

yo migraría a:

```
Ed25519 por sensor
```

o

```
Ed25519 por nodo
```

con distribución de claves públicas.

---

[SUGERENCIA-CRYPTO: El riesgo no es que HMAC falle criptográficamente; el riesgo es que el modelo operacional de gestión de secretos se vuelva inmanejable cuando existan cientos o miles de emisores.]

---

# La deuda que yo abriría además

Además de `DEBT-BRONZE-KEY-PROVISIONING-001`, abriría:

**DEBT-BRONZE-PROVISIONING-E2E-001**

Objetivo:

> demostrar automáticamente que writer y reader obtienen la misma clave desde el mecanismo real de provisioning.

No una clave de test.

No una variable hardcodeada.

La ruta real.

Porque el fallo descubierto hoy pertenece más al provisioning que al contrato de bronce.

Y precisamente por eso merece tener un test propio.

---

Mi conclusión del DAY 175:

El logro no son las 3.712 filas.

El logro es haber demostrado por primera vez:

```
captura real
↓
community_id real
↓
evento real
↓
writer real
↓
bronce real
↓
clave real
↓
reader real
```

Sin stubs.

Sin mocks.

Sin datos fabricados.

Eso reduce muchísimo el riesgo de las siguientes fases de correlación.
FDO

CHATGPT