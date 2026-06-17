# Dictamen del Consejo — DAY 184 → DAY 185

He leído el brief. A continuación, mi escrutinio siguiendo el método científico: cada afirmación se sostiene sobre pruebas demostrables, no sobre preferencia. Donde no hay prueba, lo declaro.

---

## 1. ¿Es correcto el orden medir-primero?

**Sí, con una condición de validez que debes explicitar.**

Tu argumento es sólido: construir el medallón completo antes de medir es *asumir* que el cuello de botella está en la consolidación, no en la ingestión. La evidencia que presentas (0.86s baseline del componente con BD, crecimiento contabilizado desde 0.48s) demuestra que ya tienes una métrica de coste del sink. Eso es *suelo medido*, no conjetura.

**Pero hay un riesgo de sesgo de selección que no has cuantificado:** si el camino CSV-directo no pierde filas a caudal, ¿qué conclusión extraes? "El pipeline no pierde" o "El pipeline no pierde *en este path*"? Son distintas. El primero es falso verde; el segundo es un teorema de caja cerrada correcto.

**Recomendación medible:** define *a priori* el criterio de "suelo suficiente". Ejemplo: "Si CSV-directo soporta 10× el caudal esperado de producción sin pérdida, el suelo es válido y se construye encima". Eso convierte la decisión en una regla de decisión estadística, no en juicio post-hoc.

---

## 2. Opción B vs A

**B es correcto, pero el test de equivalencia byte-idéntica es condición necesaria, no suficiente.**

Tu evidencia es el patrón DAY 183 (`build_cypher` rebasado con salida idéntica). Eso demuestra que el método funciona *para ese caso*. La pregunta abierta es: ¿el espacio de `NetworkSecurityEvent` que genera ml-detector es cerrado bajo la transformación `event → row → build_row`? Si ml-detector genera campos que `CorrelationV1Row` no puede representar (ej. extensiones de protobuf añadidas post-DAY 184), el test de equivalencia pasa hoy y falla mañana sin que el test lo detecte.

**Mitigación adicional:** el test de equivalencia debe incluir *fuzzer* de `NetworkSecurityEvent` que ejercite todos los campos `optional` y `repeated` del protobuf. Si el fuzzer no genera divergencia en 1M iteraciones, tienes evidencia estadística, no solo un caso.

**Sobre el peso de protobuf:** tu argumento de "los otros stress-testers no arrastran protobuf" es correcto si y solo si el injector de `correlation_v1` no necesita *validar* contra el protobuf real. Si el consumidor espera protobuf wire-format, el injector debe producirlo. Tu brief dice que el consumidor acepta `correlation_v1` (no especifica formato), pero si el path real es `protobuf → row → build_row`, el injector debe saber qué partes del protobuf son relevantes. Eso es conocimiento que B centraliza en el adaptador, pero que el injector no ejercita.

---

## 3. ¿Qué le falta al injector adversarial?

**Faltan tres clases de adversidad que no están en tu lista:**

1. **Adversidad de orden:** `flow_uid` con timestamps desordenados (no solo `temporal_anomaly`, sino *causalidad invertida*: evento de cierre de flujo antes de su apertura). Esto rompe inferencias temporales en el grafo que asumen orden parcial.

2. **Adversidad de cardinalidad:** `node_id` que colisionan *hash* pero no valor (colisión de 64-bit, no de string). Si Kuzu usa hash interno para índices, esto es un caso distinto al H-1 de strings.

3. **Adversidad de concurrencia:** múltiples injectores escribiendo al mismo fichero bronce sin lock. El brief no menciona si el injector es single-writer o multi-writer. Si es multi-writer, la condición de carrera en `write()` + `flush()` es un vector de corrupción que el tcpreplay no ejercita (porque los paquetes son independientes), pero el fichero bronce sí.

**Pregunta de medición:** ¿el injector tiene modo multi-writer? Si no, lo declaras explícitamente como limitación del banco.

---

## 4. Injector-a-fichero vs tcpreplay

**Es legítimo, pero con una advertencia de validez externa.**

Tu evidencia del cuello de NIC de VirtualBox ("Message too long", drops de MTU) es demostrable y documentada. Aislar el pipeline del NIC mide *el código de aRGus*, no *el sistema aRGus*. Eso es correcto si tu hipótesis es "el código no pierde datos", pero incorrecto si tu hipótesis es "el sistema no pierde datos".

**La pregunta científica es:** ¿cuál es la hipótesis del test? Si es "el pipeline de procesamiento es correcto", el aislamiento es válido. Si es "aRGus NDR funciona en el entorno documentado", el aislamiento introduce *error de especificación* (el entorno documentado incluye Raspberries + TCP).

**Recomendación:** documenta el techo de VirtualBox como *limitación conocida del banco*, no del sistema. La primera tortura mide el pipeline; la segunda (tcpreplay CTU-13) mide el sistema con techo conocido; la tercera (red-team real) mide el sistema sin techo artificial. Eso es *secuencia de validación*, no sustitución.

---

## 5. ¿Es el primer ladrillo correcto del `argus-adapter-producer`?

**Es el ladrillo correcto para el injector y el ml-detector. Es un ladrillo *posible* para el producer, no *demostrado*.**

Tu evidencia es que `libcorrelation_v1` sirve a tres consumidores: ml-detector, injector, y "mañana" el producer. Pero el producer, según tu propia descripción, lee-de-log + ZMQ, no serializa-desde-struct. La librería que extraes es *serializadora*, no *productora*. Si el producer necesita leer un log binario y emitir `correlation_v1`, su trabajo es *parse + emit*, no *struct → bytes*.

**Riesgo:** `libcorrelation_v1` queda bien cortada para el injector (que construye structs) y para ml-detector (que adapta), pero mal cortada para el producer (que no construye structs, los consume de otro formato). El refactor es correcto para los dos primeros; el tercero es conjetura.

**Mitigación:** no anticipes el producer en la API de la librería. Extrae `libcorrelation_v1` con la interfaz mínima que necesitan injector + ml-detector. Si el producer la necesita, la extensión será *evidencia*, no *deuda*.

---

## 6. HMAC en el banco de tortura

**Correcto como condición de medición, pero con una deuda técnica que debes contabilizar.**

Tu argumento es demostrable: el consumidor descarta HMAC inválido → sin HMAC correcto, la medición es basura (100% pérdida ficticia). Eso es *correctitud de medición*, no *securización*.

**Pero hay un efecto colateral no medido:** si el injector firma con la misma clave que el consumidor espera, estás asumiendo *sincronización de clave* entre banco y sistema. Eso es una dependencia oculta. Si mañana el consumidor rota clave, el banco falla sin que el código cambie.

**Recomendación:** documenta `DEBT-BRONZE-KEY-PROVISIONING-001` explícitamente como *hipótesis del banco*, no del sistema. El injector debe aceptar clave por variable de entorno (no hardcodeada), y el test debe fallar si la clave no está provisionada. Eso convierte la deuda en *condición de entrada medible*, no en acoplamiento silencioso.

---

## Resumen ejecutivo

| Pregunta | Dictamen | Condición de validez |
|---|---|---|
| 1. Medir primero | Sí | Define criterio a priori de "suelo suficiente" (ej. 10× caudal) |
| 2. Opción B | Sí | Añade fuzzer de protobuf; test de equivalencia es necesario, no suficiente |
| 3. Adversidad | Faltan 3 clases | Orden invertido, colisión hash, concurrencia multi-writer |
| 4. Aislamiento NIC | Legítimo | Documenta como limitación del banco, no del sistema |
| 5. Librería compartida | Correcto para 2/3 | No anticipe API del producer; extraiga mínimo viable |
| 6. HMAC | Correcto como medición | Contabiliza deuda de key-provisioning; clave por env, no hardcode |

**Lo que no está en el brief y necesita evidencia:** ¿cuál es el caudal objetivo de producción? Sin ese número, "10× caudal" es inoperable. ¿Tienes una estimación del caudal de Raspberries en el entorno documentado?

FDO

KIMI