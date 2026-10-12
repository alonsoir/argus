# Consejo de Sabios — DAY294

Consejero: ChatGPT (GPT-6)

Criterio de revisión: medir, no votar. Distingo entre lo que demuestran los resultados aportados, lo que todavía es una hipótesis y las pruebas que permitirían decidir. No considero validada una mitigación real por haber superado pruebas en sombra.

Una limitación documental: en el contexto disponible tengo el contenido de DAY294 que has incluido en el mensaje, pero no he podido recuperar los cuatro adjuntos por sus nombres exactos. Por tanto, esta revisión se apoya en los datos reproducidos aquí y no atribuye a esos archivos detalles que no he podido comprobar.

## 1. Auditoría adversaria de las medidas

### A1. Cero falsos positivos no demuestra generalización

Problema. Los cero DROP del inocente .51 son un resultado positivo, pero solo para ese origen, ese tráfico y esa combinación de carga. No demuestran que la etapa 2 discrimine comportamiento malicioso frente a tráfico legítimo que se parezca a los generadores de entrenamiento.

Además, los dos positivos de DNS legítimo no producen un inicio de mitigación porque la política temporal exige 3 positivos de 5. Hay que separar el rendimiento del clasificador del rendimiento de la política de decisión.

- Medida: ejecutar al menos 30 repeticiones independientes por escenario, con semillas distintas, alternando el orden de ataque y tráfico benigno. Registrar por separado las matrices de confusión de las etapas 1 y 2, los positivos por ventana y los inicios de sombra.
- Predicción: si la política funciona igual en esas condiciones, los escenarios benignos deberían producir cero inicios de sombra en las 30 repeticiones.
- Refutación: un inicio de sombra benigno refuta el resultado de cero inicios en ese conjunto de pruebas. No demuestra por sí solo que el sistema sea inservible, pero obliga a cuantificar el falso positivo.
- Confusor adicional: si las 30 repeticiones reutilizan el mismo PCAP, la misma semilla o una distribución prácticamente idéntica, no constituyen 30 evidencias independientes de generalización.

### A2. La tasa de DROP necesita un denominador verificable

Problema. Los 5.357 eventos DROP son compatibles con un ataque de 60 pps durante 90 segundos, pero no demuestran por sí solos que el sistema haya procesado correctamente todo el tráfico. El ataque nominal generaría unos 5.400 paquetes; hay que comprobar cuántos llegaron realmente al punto de observación, cuántos se perdieron antes del detector y cuántos fueron descartados por cada componente.

- Medida: correlacionar paquetes transmitidos, recibidos en XDP, contabilizados en los mapas, entregados por el anillo, evaluados por el modelo y registrados como DROP. Usar contadores acumulativos independientes de los eventos de log.
- Predicción: con un generador determinista de 5.400 paquetes, sin pérdidas, se esperan 5.400 paquetes recibidos y clasificados en el punto de observación elegido.
- Refutación: cualquier diferencia sin explicación entre contadores impide interpretar los 5.357 DROP como cobertura de ataque.

### A3. El inicio y el fin de la sombra no están suficientemente validados

Problema. NTP sincroniza relojes de pared; no hace que los relojes monotónicos de máquinas diferentes sean directamente comparables. Por ello, los 2 segundos de reloj de eventos y los 29,3 segundos de hold no son todavía medidas fiables de tiempo real transcurrido entre componentes.

- Medida: registrar, en cada transición, el instante monotónico local y un instante de referencia de pared, junto con identificador de máquina y de arranque. Medir el tiempo de extremo a extremo con un observador externo.
- Predicción: con una política `m=5, k=3, hold=30 s`, una vez definidos los puntos exactos de inicio y fin del hold, el intervalo medido por el observador debería ser de 30 segundos más el error de planificación y ejecución previamente cuantificado.
- Refutación: desviaciones superiores a ese margen o intervalos que cambien con la carga demuestran que la semántica temporal o la planificación de eventos no está bajo control.

### A4. Los 37 eventos/s ajenos a flujos son una deuda abierta

Problema. Un aumento desde aproximadamente un evento cada 30 segundos hasta 37 por segundo puede saturar consumidores, alterar el orden efectivo de procesamiento o inflar métricas. No sabemos aún si es un cambio real de emisión, acumulación en cola, reintentos o una clase de evento nueva.

- Medida: contabilizar por tipo de evento en el productor, la cola y el consumidor; medir profundidad de cola, antigüedad del evento al consumirlo y descartes. Mantener contadores independientes del reloj de evento.
- Predicción: si el fenómeno es acumulación en cola, aparecerá una diferencia creciente entre el ritmo de producción y el consumo, acompañada de mayor antigüedad de los eventos.
- Refutación: si producción, consumo y antigüedad permanecen alineados, la hipótesis de cola no explica el fenómeno; habrá que investigar la semántica del reloj y la fuente concreta de esos eventos.

## 2. P1 — Etapa 2 por comportamiento

Recomendación: incorporar primero una medida de dispersión de orígenes por víctima y una medida de asimetría petición/respuesta; no sustituir todavía los seis rasgos actuales sin una comparación experimental.

Medida propuesta

Definir ventanas de un segundo, agregadas por `{victim_ip, protocol}`. Para cada ventana:

1. `source_ip_dispersion`: número de orígenes distintos que envían tráfico a la víctima. Si el número de orígenes es grande, usar un estimador de cardinalidad acotado en memoria, validado frente al conteo exacto.
2. `source_rate_share`: tasa del origen dividida por la tasa total observada para esa víctima. Es una medida por origen, no una propiedad global de la víctima.
3. `request_response_asymmetry`: relación entre bytes o paquetes entrantes y salientes, cuando ambos sentidos puedan observarse de forma fiable.

Calcular las estadísticas en el sniffer, actualizar acumuladores por ventana y entregar los rasgos agregados al detector. No se deben recalcular recorridos de todos los orígenes por cada paquete. La dispersión debe tener un límite de memoria explícito y una política documentada para tablas llenas.

Hay una precaución importante: la asimetría no es fiable si el sensor solo ve una dirección del tráfico, si el retorno sigue una ruta distinta o si el tráfico legítimo es unidireccional. Y el número de IP de origen tampoco es una medida fiable del número de atacantes: puede estar afectado por NAT, spoofing o distribución artificial de direcciones.

Predicción numérica

En una primera batería con familias completamente separadas del entrenamiento, propongo exigir:

- Recall de al menos el 90 % para cada familia de ataque evaluada.
- Tasa de falsos positivos por ventana benigna inferior al 0,1 %.
- Reducción de al menos el 50 % en falsos negativos frente al modelo actual en las familias desconocidas.

Son objetivos experimentales propuestos, no resultados que podamos dar por alcanzados.

Qué lo refutaría

Si añadir los rasgos no reduce los falsos negativos al menos un 50 %, o si supera el límite de falsos positivos, la hipótesis de que esos rasgos aportan generalización no queda respaldada.

La comparación debe ser por familia y por captura independiente. Un resultado agregado podría ocultar que se detecta bien una familia y se falla completamente en otra.

## 3. P2 — ¿Basta la batería v3?

Recomendación: usar la batería v3 como base, pero añadir un eje de validación cruzada por familia de ataque y por procedencia de captura.

Medida propuesta

Mantener los tamaños aleatorios, las bases UDP+TCP mixtas y las tasas de 45, 75 y 150 pps. Añadir:

- Una familia de ataque completamente ausente del entrenamiento, no simplemente una tasa distinta.
- Una captura legítima con características similares a la familia de ataque reservada.
- Un escenario de ataque con pocos orígenes y otro con muchos orígenes, manteniendo la tasa total de la víctima.
- Pruebas con y sin asimetría visible entre petición y respuesta.
- Separación estricta entre entrenamiento, selección de umbrales y evaluación final.

Las capturas relacionadas no deben repartirse aleatoriamente entre entrenamiento y evaluación: eso puede filtrar firmas del mismo generador a ambos lados.

Predicción numérica

Para el conjunto de familias desconocidas, el criterio inicial sería recall ≥90 %, falsos positivos por ventana benigna inferiores al 0,1 % y cero inicios de sombra en 30 repeticiones independientes del escenario benigno más difícil.

Qué lo refutaría

Una familia no vista con recall inferior al 90 %, o una captura legítima que active repetidamente la política de sombra, refutaría que la batería actual sea suficiente para validar generalización.

Corrida concreta que falta

Entrenar sin la familia NTP y evaluar una familia de reflexión diferente, con distribución de tamaños aleatoria, misma tasa total de víctima y número de orígenes variable. Ejecutar simultáneamente tráfico legítimo DNS y TCP. Repetir con distintas semillas y capturas independientes.

Si el modelo solo reconoce NTP cuando los tamaños y puertos coinciden con los generadores de entrenamiento, el experimento revelará memorización, aunque el tráfico se genere a tasas nuevas.

## 4. P3 — Calibración para un hospital

Recomendación: calibración inicial automática en modo sombra, con propuesta de valores y aprobación humana obligatoria antes de habilitar decisiones de mitigación.

Medida propuesta

No trasladar `K=3`, `m=5`, `k=3/5` y `hold=30 s` directamente del laboratorio al hospital. Recoger tráfico representativo de los ciclos operativos reales, incluidos cambios de turno, copias de seguridad, actualizaciones, consultas DNS y servicios clínicos críticos.

Como protocolo inicial propondría al menos 14 días de observación continua, ampliables a 30 días si no se cubren ciclos operativos relevantes. La duración definitiva debe depender de la cobertura de esos ciclos y de la estabilidad de la muestra, no de un número mágico de días.

Registrar por víctima:

- Distribución de `victim_rate_ratio`, con percentiles 50, 90, 95, 99 y 99,9.
- Frecuencia y duración de las superaciones de umbral.
- Positivos de etapa 2 por ventana y por servicio.
- Número de inicios de sombra por día y por víctima.
- Pérdidas de observación, cambios de ruta y víctimas con historia insuficiente.

No basta con ajustar K al percentil 99,9: los ataques pueden empezar desde una base legítima anormalmente alta, y las ventanas consecutivas no son independientes.

Predicción numérica

Como gate de validación, exigiría cero inicios de sombra en el conjunto benigno de aceptación, con al menos 30 días de tráfico representativo cuando sea viable. Si no se observa ningún falso inicio en \\(N\\) oportunidades independientes, el límite superior aproximado del 95 % para la probabilidad por oportunidad es \\(3/N\\). No observar falsos positivos no significa que su probabilidad real sea cero.

Qué lo refutaría

Un inicio de sombra durante una actividad clínica legítima, o una sensibilidad insuficiente en una batería de ataques aprobada, impide aprobar esa configuración.

Los valores deben versionarse en configuración, acompañados de datos de calibración, rangos permitidos y responsable de aprobación. No haría que el sistema modifique automáticamente los umbrales de producción sin aprobación humana.

## 5. P4 — Mitigación real por víctima

Recomendación: preferir inicialmente la opción (b), descarte selectivo por flujo y origen, pero solo después de validar la clasificación en familias desconocidas y con una política de expiración segura. No activaría aún el bloqueo automático en una red clínica real.

La opción (a), limitar toda la tasa hacia la víctima, puede penalizar tráfico legítimo concurrente. La opción (c), filtrar por puerto y tamaño, reproduce precisamente el problema de memorización que hemos medido.

Medida propuesta

Crear una matriz de tráfico antes y después del punto de mitigación. Ejecutar ataque y tráfico benigno concurrentes hacia la misma víctima, registrando por separado:

- Paquetes y bytes enviados por cada origen.
- Paquetes y bytes recibidos por la víctima.
- Porcentaje de ataque descartado.
- Porcentaje de tráfico benigno perdido.
- Latencia y disponibilidad de los servicios legítimos.

Evaluar además ataques con direcciones de origen falsificadas: bloquear una IP no equivale necesariamente a bloquear al atacante real.

Predicción numérica

Como gate inicial de laboratorio:

- Descartar al menos el 95 % de los paquetes del ataque conocido.
- Entregar al menos el 99 % de los paquetes legítimos del origen .51.
- Mantener una pérdida de tráfico legítimo adicional atribuible al mitigador inferior al 1 %.

Qué lo refutaría

Si el mitigador descarta más del 1 % del tráfico legítimo de .51 o no alcanza el 95 % de descarte del ataque, la configuración propuesta no supera el gate.

Este experimento debe incluir ataques de familias no vistas. Si el clasificador no identifica la familia, el sistema debe reconocer su limitación y no presentar la mitigación selectiva como protección general contra DDoS.

## 6. P5 — Base de tiempo única

Recomendación: elegir la opción (b): reloj monotónico para ordenar eventos y medir duraciones, con un ancla explícita para relacionar relojes de nodos diferentes.

Es la opción que mejor separa dos problemas distintos: medir cuánto tarda algo y determinar cuándo ocurrió en una escala temporal compartida. No usaría `CLOCK_REALTIME` para calcular el hold ni el tiempo hasta el bloqueo. Con `makestep 1 -1`, el reloj de pared puede saltar hacia delante o hacia atrás y alterar esas duraciones.

Medida propuesta

Cada evento debe incluir:

- `node_id` y `boot_id`, para identificar el origen y la instancia temporal.
- `event_mono_ns`, basado en un reloj monotónico.
- `event_wall_ns`, para correlación aproximada con registros externos.
- Un identificador de secuencia por productor, para detectar pérdidas y reordenaciones.
- Una versión del contrato temporal.

Establecer anclas periódicas entre reloj monotónico y reloj de pared. Para correlacionar nodos, medir también la incertidumbre del ancla y de la sincronización. Un reloj monotónico local no puede compararse directamente con el de otra máquina.

Los plazos del firewall deben calcularse con el reloj monotónico del proceso que gestiona la política. Los eventos recibidos tarde deben conservar su instante de origen y no reiniciar artificialmente un plazo por el mero hecho de consumirse tarde.

No elegiría `bpf_ktime_get_tai_ns()` como solución principal sin demostrar antes su disponibilidad y semántica exacta en el kernel objetivo. Además, disponer de TAI no elimina por sí mismo los problemas de sincronización entre nodos.

Predicción numérica

Con un hold de 30 segundos, realizar 100 pruebas inyectando saltos de reloj de pared de +5 y −5 segundos durante el ataque y la expiración de la sombra.

Objetivo propuesto:

- Las 100 pruebas deben conservar el orden monotónico de los eventos de cada productor.
- El hold debe expirar a los 30 segundos, con una tolerancia de ±100 ms en el laboratorio.
- Ningún salto de pared debe provocar un hold negativo, una expiración prematura o una extensión del plazo.

Qué lo refutaría

Una sola expiración incorrecta atribuible al salto de reloj refuta la robustez temporal. Si el error supera ±100 ms sin una causa de planificación identificada, tampoco se supera el criterio de precisión.

La prueba debe ejecutarse bajo carga DNS y con colas deliberadamente saturadas. Así se distingue un defecto de reloj de un retraso de procesamiento.

## 7. P6 — Disyuntor de saturación

Recomendación: aplicar ambas medidas: degradación controlada a una regla barata por víctima y alerta explícita de pérdida de capacidad. La regla degradada no debe convertirse en un bloqueo indiscriminado de todos los flujos de una víctima.

Medida propuesta

Los aproximadamente 110 pps son un resultado del laboratorio, no un umbral de producción. La capacidad depende del tamaño de los paquetes, el número de flujos, la distribución de orígenes, el coste del modelo y la presión sobre el anillo.

Medir una curva de carga con escalones crecientes y tráfico mixto. En cada escalón registrar:

- Pérdida de paquetes en XDP y en el anillo.
- Diferencia entre paquetes recibidos y procesados.
- Profundidad y antigüedad de las colas.
- Latencia p50, p95 y p99 de inferencia y decisión.
- CPU y memoria.
- Tiempo hasta activar el disyuntor y recuperar el procesamiento normal.

Predicción numérica

Como criterio experimental inicial, activar la alerta si la pérdida supera el 0,1 % durante una ventana de 5 segundos, o si la cola supera de forma sostenida el 80 % de su capacidad.

Cuando se active el disyuntor, la regla degradada debe conservar la protección de los recursos de la víctima sin bloquear indiscriminadamente al origen benigno concurrente. El sistema debe registrar qué protección ha dejado de ofrecer.

Qué lo refutaría

Si la pérdida supera el 0,1 % sin que se active el disyuntor, la detección de saturación no cumple su objetivo. Si la degradación provoca pérdida de tráfico legítimo por encima del 1 % en el escenario de aceptación, la regla degradada tampoco supera el gate.

Los umbrales del 0,1 %, 5 segundos y 80 % son propuestas de laboratorio que deben contrastarse con la curva real de capacidad, no constantes universales.

## 8. Prioridad recomendada

## 1

P5 — Base temporal única

Es el siguiente PR y debe mantenerse como prioridad. Los errores temporales ya han contaminado el grafo, los logs y los plazos de la sombra. Sin corregirlos, las medidas posteriores pueden ser falsas aunque el clasificador sea correcto.

## 2

P6 — Disyuntor y observabilidad de pérdidas

Antes de añadir más carga de experimentación hay que poder detectar cuándo el propio sensor deja de observar el tráfico correctamente. De lo contrario, el conjunto de evaluación puede estar sesgado por pérdidas invisibles.

## 3

P1 + P2 — Generalización y batería v3

Definir primero los rasgos conductuales y después evaluar las familias que no participaron en el entrenamiento. Evitar invertir tiempo en optimizar una arquitectura cuya limitación principal parece ser la generalización.

## 4

P3 — Calibración del cliente

Preparar el procedimiento y el formato de aprobación ahora, pero no fijar valores universales antes de disponer de una medida de generalización y de falsos positivos más sólida.

## 5

P4 — Mitigación real

Mantenerla fuera de producción hasta demostrar que la detección funciona con familias desconocidas, que el tráfico benigno concurrente se conserva y que los tiempos de expiración son correctos.

## Dictamen final

El resultado más importante de DAY294 no es que la cabeza DDoS funcione con el generador conocido. Es que la arquitectura factorizada evita, en los escenarios medidos, que determinadas cargas legítimas que presionan la etapa 1 se conviertan en una mitigación, gracias en parte a la política temporal de la etapa 2.

Eso es útil, pero hay tres límites que no deben confundirse:

1. La política de decisión puede filtrar positivos aislados sin que el clasificador generalice.
2. Una captura sin pérdidas en el laboratorio no acredita la capacidad de una instalación real.
3. Una mitigación correcta en sombra no acredita que el bloqueo real preserve el tráfico legítimo.

Mi recomendación es cerrar primero la semántica temporal, hacer observable la saturación y ejecutar una batería con separación estricta por familia. Solo entonces evaluaría el paso de sombra a mitigación real.

Criterio de aceptación: no promover el modelo porque haya ganado a otra arquitectura, sino porque supere un conjunto de pruebas independientes, con umbrales de falsos positivos, recall, pérdida de paquetes y tiempo de decisión definidos antes de ejecutar la batería.