# 🏛️ Consejo de Sabios — DAY 159

**Revisión técnica de DAY 158/159 — aRGus NDR**

El hallazgo importante no es solo el bug de endianness. El hallazgo importante es sistémico: durante 61 días el sistema validaba “componentes correctos” pero no “comportamiento correcto”. Eso cambia la prioridad arquitectónica de las pruebas.

El pipeline acaba de demostrar algo fundamental:

> Los contratos reales entre componentes son ahora más críticos que la lógica interna individual.

Eso es típico en sistemas distribuidos maduros.

---

# 1. ¿Añadir test de integración del wire protocol o basta con E2E?

## Respuesta corta:

Sí. Recomendamos añadir un test explícito de contrato/binario del wire protocol. El E2E no sustituye eso.

## Por qué

El E2E detecta:

* “algo está roto”.

Pero NO detecta:

* quién rompió el contrato,
* en qué byte exacto,
* si el fallo es serialización,
* compresión,
* cifrado,
* framing,
* endianess,
* compatibilidad retroactiva,
* o corrupción parcial.

Lo que os ocurrió es exactamente el caso clásico donde:

* unit tests → verdes,
* E2E → insuficientemente observables,
* contrato binario → nunca validado.

## Recomendación concreta

Añadid una capa intermedia:

```text
UNIT TESTS
    ↓
WIRE CONTRACT TESTS   ← FALTA ESTO
    ↓
INTEGRATION TESTS
    ↓
E2E TESTS
```

## Qué debería validar ese test

El test debería:

* generar un payload real desde ml-detector,
* serializarlo,
* comprimirlo,
* cifrarlo,
* transmitirlo,
* deserializarlo en firewall,
* y verificar byte a byte:

```text
magic
version
endianness
payload_length
compression_type
encryption_type
checksum/hash
payload integrity
```

## Muy importante

Definid formalmente el protocolo.

Ahora mismo probablemente existe “implícitamente” en el código.

Necesitáis algo tipo:

```text
ADR-0XX — Binary Wire Protocol Specification
```

Con:

* offsets,
* tamaños,
* endianess,
* flags,
* compatibilidad,
* versionado.

Eso evita futuros “DAY 98 → DAY 159”.

## Conclusión

El gate E2E es necesario.
El contract-test binario es obligatorio.

Los dos cubren fallos distintos.

---

# 2. ¿`check-abs` es aceptable o debe pasar a snapshot/delta?

## Recomendación:

Para FEDER/CI real:
→ snapshot/delta obligatorio.

Para VM dev local:
→ `check-abs` aceptable como modo rápido.

## Problema actual

Ahora mismo vuestro test puede responder:

```text
“sí hubo tráfico”
```

cuando en realidad solo hubo:

* tráfico antiguo,
* contadores históricos,
* o residuos previos.

Eso convierte el test en:

* parcialmente ciego,
* no determinista,
* dependiente del estado previo.

En CI/CD eso acaba generando:

* falsos positivos,
* confianza artificial,
* degradación silenciosa.

Y precisamente acabáis de sufrir un caso de degradación silenciosa.

## Recomendación ideal

### Modo desarrollo rápido

```bash
make test-e2e-live-fast
```

→ usa `check-abs`

### Modo CI/FEDER

```bash
make test-e2e-live-strict
```

→ snapshot/delta obligatorio.

## Recomendación adicional

Añadid:

* monotonic counters,
* trace_id temporal,
* correlation_id de test,
* timestamp window verification.

Ejemplo:

```text
TEST_RUN_ID=day159-ci-0042
```

Y verificáis que:

* aparecen eventos nuevos,
* dentro de ventana temporal,
* asociados al test actual.

Eso convierte el E2E en determinista.

---

# 3. ¿`DEBT-ALERTING-LIBCRYPTO-PROVIDER-001` es P0 antes de FEDER?

## Evaluación honesta:

No es P0 operacional.
Sí es P1 arquitectónico.

## El sistema ya protege

La función primaria del pipeline es:

* detectar,
* clasificar,
* reaccionar,
* bloquear.

No “enviar Discord”.

Por tanto:

* el núcleo defensivo no depende de ello.

## Pero…

Hay un riesgo importante:

Actualmente el alerting está:

* fragmentado,
* parcialmente centralizado,
* acoplado.

Eso provoca:

* inconsistencias,
* dependencias ocultas,
* fallos de ownership.

## Recomendación

Antes de FEDER:

* no hace falta completar toda la migración,
* PERO sí dejar definida la arquitectura final.

Es decir:

* interfaz estable,
* ownership claro,
* API congelada.

Algo tipo:

```cpp
IAlertProvider
```

con:

* Discord,
* Telegram,
* syslog,
* webhook,
* etc.

## Prioridad real

| Elemento                | Prioridad |
| ----------------------- | --------- |
| Pipeline funcional      | P0        |
| Wire protocol estable   | P0        |
| E2E determinista        | P0        |
| Alerting desacoplado    | P1        |
| Multi-provider elegante | P2        |

## Conclusión

Puede esperar post-merge si:

* etcd-server alerta,
* logging funciona,
* evidencias quedan persistidas.

No debería bloquear FEDER.

---

# 4. ¿El synthetic_ml_output_injector debe auto-adaptarse también?

## Respuesta:

Sí, especialmente compression/encryption.

Porque ya habéis descubierto que:

* la configuración distribuida puede divergir,
* y cuando diverge el fallo puede ser silencioso.

## Ahora mismo existe riesgo de:

```text
injector → compresión X
pipeline → espera compresión Y
```

Y volvéis a:

* payload inválido,
* falsos positivos,
* crashes,
* o drops invisibles.

## Recomendación

El injector sintético debe comportarse como:

> “cliente real del protocolo”.

No como:

> “generador artificial simplificado”.

## Muy importante

Los injectors sintéticos son valiosos precisamente porque:

* emulan comportamiento real,
* detectan incompatibilidades,
* validan contratos.

Si simplificáis demasiado:

* dejan de protegeros.

## Recomendación concreta

Auto-adaptar:

* endpoint,
* compression,
* encryption,
* protocol_version,
* framing mode,
* feature flags.

Idealmente:

* leyendo config dinámica,
* o negociando capacidades.

---

# 5. ¿Paralelizar E2E en Jenkins o es peligroso?

## Respuesta corta:

Ahora mismo: peligroso.

## Razón

Vuestro pipeline aún parece:

* stateful,
* compartiendo logs,
* compartiendo sockets,
* compartiendo métricas,
* compartiendo runtime.

Paralelizar E2E sobre infraestructura compartida genera:

* flaky tests,
* carreras,
* contaminación cruzada,
* falsos fallos,
* falsos éxitos.

## Recomendación

### Fase actual

Ejecutar serialmente:

```text
synthetic-full
→ synthetic-firewall
→ live
```

Priorizad:

* reproducibilidad,
* determinismo,
* aislamiento.

## Cuándo paralelizar

Cuando tengáis:

* namespaces aislados,
* logs aislados,
* puertos efímeros,
* runtime por test,
* test IDs,
* storage temporal independiente.

Es decir:

* infra “test sandboxed”.

## Alternativa muy buena

Paralelizad:

* unit,
* contract,
* serialization,
* fuzzing,
* parsers.

Pero mantened:

* E2E serial.

Eso suele ser el equilibrio correcto en NDR/EDR distribuidos.

---

# Evaluación global del DAY 159

El hallazgo es serio, pero el modo en que lo habéis encontrado es extremadamente positivo.

Muchos sistemas distribuidos mueren exactamente aquí:

* tests verdes,
* dashboards verdes,
* pipeline roto internamente durante meses.

Vosotros habéis reaccionado correctamente:

* identificando deuda sistémica,
* creando gates reales,
* introduciendo validación E2E,
* migrando injectors,
* validando desde VM limpia.

Eso es ingeniería defensiva madura.

La prioridad ahora ya no es “añadir features”.

La prioridad es:

* formalizar contratos,
* aislar estados,
* hacer deterministas los tests,
* y convertir el pipeline en verificable extremo a extremo.
