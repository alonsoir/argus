# Consejo de Sabios — Revisión DAY 184 → DAY 185

Voy a responder exclusivamente desde ingeniería de sistemas distribuidos, arquitectura de datos y metodología experimental.

---

# Veredicto general

La decisión más importante del DAY 184 no es Kuzu.

Es haber empezado a convertir supuestos en invariantes medidos.

El patrón que aparece repetidamente es:

1. Se identifica una hipótesis.
2. Se construye un mecanismo que impide violarla silenciosamente.
3. Se mide.
4. Solo después se construye encima.

Ese patrón es científicamente correcto.

Lo contrario sería construir capas enteras de arquitectura sobre supuestos no validados.

---

# 1. ¿Es correcto medir primero?

## Respuesta corta

Sí.

La decisión es correcta.

---

## Razón

La primera pregunta que intenta responder el proyecto es:

> ¿El pipeline pierde o corrompe información?

No:

> ¿Tenemos la arquitectura final perfecta?

Son preguntas distintas.

Si todavía no sabes si el camino actual preserva datos, introducir:

* Avro
* Arrow
* Parquet
* Iceberg
* Medallones

añade miles de líneas de código y decenas de nuevos puntos de fallo.

En experimentación eso es una mala práctica.

Porque si aparece pérdida de datos no sabrás dónde.

---

## Principio científico

Cuando se valida una cadena:

```text
A -> B -> C -> D
```

primero se mide:

```text
A -> D
```

con la menor cantidad posible de variables intermedias.

Solo después se introducen:

```text
A -> B -> C -> D
```

y se mide otra vez.

---

## Riesgo del falso verde

Existe.

Pero no donde parece.

El riesgo no es:

> "CSV no se parece a producción"

El riesgo es:

> "CSV oculta un problema que aparecerá al añadir Avro."

Eso es cierto.

Pero ese problema pertenece a una capa futura.

No invalida la medición actual.

Simplemente significa que más adelante habrá que repetir la medición.

---

## Recomendación

Definir explícitamente:

```text
FASE 1:
CSV -> Correlation Engine -> Kuzu

Objetivo:
demostrar integridad

FASE 2:
CSV -> Avro -> Correlation Engine -> Kuzu

Objetivo:
demostrar que Avro no altera integridad

FASE 3:
CSV -> Avro -> Parquet -> Iceberg -> ...

Objetivo:
demostrar que la arquitectura completa conserva integridad
```

Cada fase hereda la anterior.

---

# 2. Opción B vs Opción A

## Veredicto

B es superior.

---

## Razón arquitectónica

Actualmente:

```text
ml-detector
 ├─ clasificación
 └─ serialización
```

Eso mezcla dos responsabilidades.

La serialización no pertenece al detector.

Pertenece al contrato.

---

## Modelo correcto

```text
NetworkSecurityEvent
          |
          v
CorrelationV1Row
          |
          v
CorrelationWriter
```

El contrato se convierte en el centro.

No protobuf.

---

## Error común

Muchos equipos convierten:

```text
protobuf
```

en

```text
modelo de dominio
```

y terminan acoplando todo el sistema a protobuf.

Eso suele convertirse en deuda técnica.

---

## Sobre la divergencia

La preocupación es legítima.

Pero ya habéis identificado el mecanismo correcto.

Si existe:

```cpp
old_path(event)
```

y

```cpp
new_path(event)
```

y ambos producen salida byte-idéntica en CI:

```text
old == new
```

entonces la divergencia deja de ser una opinión.

Se vuelve una propiedad comprobada.

---

## Recomendación adicional

Añadir fuzzing.

No solo casos manuales.

Generar eventos aleatorios.

```text
10000
50000
100000
```

comparaciones old/new.

Eso suele descubrir conversiones raras:

* UTF-8
* NaN
* campos vacíos
* timestamps extremos

---

# 3. ¿Qué le falta al injector adversarial?

Aquí es donde veo más trabajo pendiente.

---

## A. Campos gigantes

Actualmente habláis de:

* comillas
* backslashes

Pero no de tamaño.

Probad:

```text
1 KB
10 KB
100 KB
1 MB
```

en campos textuales.

---

## B. UTF-8 hostil

Probad:

```text
emoji
árabe
chino
combinaciones Unicode
caracteres inválidos
```

Muchos pipelines fallan aquí.

---

## C. Valores nulos

No solo vacíos.

Verdaderos nulos semánticos.

```text
src_ip=""
dst_ip=""
timestamp=""
```

---

## D. Desorden temporal

No solo anomalías.

Eventos válidos pero fuera de orden.

```text
t=100
t=50
t=90
t=120
```

---

## E. Duplicados exactos

Muchos sistemas soportan:

```text
A
B
C
```

Pero fallan con:

```text
A
A
A
A
A
```

---

## F. Reinicio durante flush

Para mí este es el caso más importante.

Inyectar:

```text
write()
write()
write()
flush()
SIGKILL
```

y medir:

```text
filas esperadas
vs
filas persistidas
```

Ese escenario reproduce fallos reales.

---

## G. Corrupción parcial

Simular:

```text
fila truncada
HMAC correcto
payload roto
```

o

```text
payload correcto
HMAC roto
```

---

# 4. Injector a fichero vs tcpreplay

## Veredicto

Injector a fichero primero.

Sin duda.

---

## Razón

Queréis medir:

```text
pipeline
```

no

```text
VirtualBox
```

Actualmente ya existe evidencia previa de que VirtualBox introduce ruido experimental.

Por tanto:

```text
NIC virtual
```

es una variable de confusión.

---

## Orden correcto

### Etapa 1

```text
Injector -> Bronze
```

Validación funcional.

---

### Etapa 2

```text
tcpreplay
```

Validación sistémica.

---

### Etapa 3

```text
sensores reales
```

Validación operacional.

---

La secuencia es correcta.

---

# 5. ¿Es correcto extraer CorrelationWriter?

## Sí.

Y además es exactamente el tipo de refactor que suele sobrevivir a cambios arquitectónicos.

---

La operación fundamental que aparece en todos los escenarios es:

```text
producir correlation_v1
```

No:

```text
leer logs
```

No:

```text
usar ZMQ
```

No:

```text
usar protobuf
```

---

Si mañana cambiáis:

```text
CSV -> Kafka
```

o

```text
ZMQ -> NATS
```

seguiréis necesitando:

```text
CorrelationV1Row -> correlation_v1
```

Por tanto el corte parece estable.

---

# 6. HMAC en el banco de tortura

## Estoy de acuerdo con vuestra conclusión.

Aquí el HMAC no es una medida de seguridad.

Es una condición de validez experimental.

---

Sin HMAC correcto mediríais:

```text
rechazo esperado
```

y lo interpretaríais como:

```text
pérdida de datos
```

Eso contaminaría el experimento.

---

## Sobre el acoplamiento a claves

Hay una solución sencilla.

Definir:

```text
TestKeyProvider
```

para el injector.

Por ejemplo:

```cpp
TEST_HMAC_KEY
```

inyectada desde entorno.

El banco de tortura no necesita conocer:

* etcd
* rotación
* provisión real

Solo necesita generar firmas válidas.

---

# Conclusión

Las dos decisiones que considero más sólidas del DAY 184 son:

1. **No construir todavía Avro/Parquet/Iceberg y medir primero el camino mínimo.**
2. **Elegir Opción B y convertir `CorrelationV1Row` en el contrato central.**

La principal debilidad que todavía veo no está en la arquitectura, sino en el plan de tortura: aún faltan pruebas de reinicio abrupto, duplicados masivos, desorden temporal, tamaños extremos y corrupción parcial. Históricamente, esos escenarios descubren más defectos de integridad que los casos clásicos de comillas, escapes e inyección.

FDO

CHATGPT