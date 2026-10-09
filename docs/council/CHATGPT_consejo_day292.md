# Consejo de Sabios — DAY292: cabeza de clasificación DDoS de aRGus NDR

Mi dictamen inicial es que todavía no tenemos evidencia suficiente para desplegar un clasificador DDoS con capacidad de bloqueo autónomo en un hospital. Sí tenemos evidencia suficiente para construir la siguiente iteración experimental e integrarla en el pipeline de evaluación de aRGus.

La distinción importa: habéis identificado dos problemas diferentes que no deben confundirse.

- Problema de detección: reconocer un ataque frente a tráfico legítimo, incluida una víctima sin historial.
- Problema de generalización: reconocer el comportamiento de un ataque que no se parece a los generadores usados durante el entrenamiento.

El segundo es el más preocupante. Los resultados de exclusión de familias que describes sugieren que el bosque aprende características accidentales de los generadores, en lugar de una representación suficientemente general del comportamiento DDoS. Un recall del 100 % en una partición de test no resuelve esa cuestión si las familias, los tamaños de paquete y las condiciones de generación siguen estando correlacionados con las etiquetas.

Hay además una tercera cuestión: un buen clasificador no es, por sí solo, una política de bloqueo segura. La decisión del modelo, la confianza estadística en esa decisión y la autorización para bloquear deben ser capas distintas.

Voy a tratar los resultados que has aportado como observaciones del laboratorio, no como resultados verificados independientemente: sin los datos, el código de generación, las particiones y los artefactos del modelo no podemos reproducirlos ni comprobar sus métricas.

## 1. ¿B sin `victim_pps`, B o un híbrido?

Mi candidato para la siguiente iteración sería B sin `victim_pps`, acompañado de un estado explícito de confianza de la víctima y una política de mitigación independiente del clasificador. No lo declararía ganador todavía.

| Alternativa        | Ventaja                                                     | Riesgo principal                                                                  |
| ------------------ | ----------------------------------------------------------- | --------------------------------------------------------------------------------- |
| B con `victim_pps` | Aprovecha una señal directa de volumen                      | Aprende un umbral absoluto dependiente del laboratorio                            |
| B sin `victim_pps` | Favorece cambios relativos respecto al historial            | Una víctima fría puede no presentar una anomalía relativa detectable              |
| Híbrido            | Puede responder durante el arranque y usar contexto después | La regla de arranque puede generar falsos positivos y necesita calibración propia |

Hay un detalle fundamental: si una víctima fría recibe 30 pps de un ataque y esos mismos rasgos son compatibles con tráfico legítimo, ningún clasificador puede distinguir ambos casos de forma fiable solo con esos datos. No es una limitación específica de los bosques aleatorios, sino de la información disponible.

### Qué haría con el estado frío

Separaría tres estados operativos:

- `COLD`: historial insuficiente; no se confía en la anomalía relativa.
- `WARM`: historial utilizable; se puede evaluar el cambio relativo.
- `UNDER_PRESSURE`: existe evidencia suficiente de presión; se aplican las reglas de adaptación de la EWMA que hayáis definido.

En `COLD`, mantendría la clasificación, pero limitaría la autoridad de bloqueo. Una política de rate limiting o mitigación reversible puede ser más apropiada que un bloqueo permanente, siempre que su efecto esté validado y no afecte al servicio legítimo.

No usaría un umbral absoluto de 30–40 pps como regla general: el hueco observado entre los benignos y los ataques de este laboratorio no demuestra que exista ese hueco en producción.

### Experimento que decidiría la cuestión

Mantendría tres candidatos idénticos en datos, particiones y evaluación:

1. B con `victim_pps`.
2. B sin `victim_pps`.
3. Híbrido con una regla de arranque explícita, cuyos parámetros se fijan exclusivamente en validación.

Los probaría en víctimas con historial y sin historial, bases de 10, 50 y 200 pps, ataques de 30, 60 y 100 pps, y escalas adicionales no vistas durante el entrenamiento.

Mediría:

- Recall por familia y por intensidad del ataque.
- Falsos positivos por víctima-hora y por escenario benigno.
- Tiempo desde el inicio real del ataque hasta la primera detección y hasta la primera acción autorizada.
- Resultados con tráfico legítimo concurrente.
- Sensibilidad al reinicio del sniffer y a la pérdida de estado.

La selección debe hacerse por una restricción de seguridad: primero cumplir el límite de falsos bloqueos establecido; después, optimizar detección y latencia.

## 2. ¿Basta con diversificar los generadores?

No. Diversificar los generadores es necesario, pero no suficiente. El problema puede estar tanto en el dataset como en la representación de los datos.

Los resultados leave-one-family-out son una señal de alarma importante. Sin NTP, el recall cae prácticamente a cero; sin SYN, el modelo marca casi todo el TCP inocente. Eso indica que la cobertura del comportamiento aprendido es insuficiente, aunque no identifica por sí solo la causa exacta.

### A. El contrato de rasgos debe ser causal

Antes de añadir más tráfico, auditaría cada rasgo con una pregunta:

¿Podría calcularse exactamente con la información disponible en el instante en que el firewall tendría que actuar?

Por ejemplo:

- `mean_packet_size`: media acumulada hasta el paquete actual, no media final del flujo.
- `packet_size_entropy`: entropía de los paquetes observados hasta ese instante, con tratamiento explícito de muestras pequeñas.
- `flow_packet_count`: contador acumulado, no tamaño final del flujo.
- `flow_completion_rate`: definición operacional estricta. Si depende de que el flujo termine o de observar su futuro, introduce fuga de información para una decisión por paquete.
- `syn_ack_ratio`: solo con paquetes observados hasta ese momento.
- `reflection_signature`: señal contextual, no prueba de ataque por sí sola.
- `victim_rate_ratio`: calcularlo con estado previo al paquete o a la ventana evaluada, con una convención temporal idéntica en entrenamiento y servicio.

Si alguno de los rasgos usa información futura, el modelo puede parecer excelente offline y ser imposible de reproducir online. Esta auditoría tiene prioridad sobre la elección del algoritmo.

### B. Rediseñaría el dataset por escenarios, no por filas

El dataset debería cruzar, como mínimo, estas dimensiones:

| Dimensión              | Cobertura necesaria                                                   |
| ---------------------- | --------------------------------------------------------------------- |
| Familia de ataque      | NTP, DNS, SYN, UDP, fragmentación y variantes no vistas               |
| Tráfico legítimo       | TCP, UDP, DNS, respuestas grandes, ráfagas y conexiones cortas/largas |
| Intensidad de fondo    | Varias escalas, incluidas mezclas de tráfico                          |
| Intensidad del ataque  | Inferior, similar y superior a la línea base                          |
| Historia de la víctima | Fría, en calentamiento, estable y bajo presión                        |
| Generador              | Implementaciones diferentes para una misma familia                    |
| Temporalidad           | Inicio, régimen sostenido, fluctuación, final y recuperación          |
| Interacción            | Varios orígenes, tráfico legítimo concurrente y varias víctimas       |

Los tamaños aleatorios son útiles, pero no deberían limitarse a añadir ruido a los mismos paquetes. Necesitáis solapamiento real entre las distribuciones benignas y maliciosas de tamaño, protocolo, ritmo y composición del tráfico.

También introduciría ataques a tasas variables, ráfagas, pausas, cambios de intensidad y combinaciones de familias. Los generadores propios deben producir variabilidad de comportamiento, no solo variabilidad superficial.

### C. La partición es tan importante como la generación

No dividiría filas aleatoriamente. Las filas de una misma corrida, flujo o ventana comparten contexto y no son observaciones independientes.

Reservaría conjuntos completos por:

- Corrida y sesión de captura.
- Generador o implementación.
- Familia de ataque.
- Escala de tráfico.
- Escenario de coexistencia benigno/malicioso.

Usaría validación agrupada durante el desarrollo y un test final bloqueado que no se consulte para ajustar parámetros. El test final debería incluir escenarios y generadores que no hayan intervenido en la selección del modelo.

Además, etiquetaría cada ejemplo con su procedencia: corrida, generador, familia, escala, víctima, ventana temporal y estado de la EWMA. No son rasgos para el clasificador; son metadatos de auditoría.

Mi criterio de aceptación: que el rendimiento no dependa de reconocer el generador y que las métricas se mantengan al retirar una familia o cambiar la escala de tráfico.

## 3. ¿Cablear ya o mejorar primero el dataset?

Haría ambas cosas en paralelo, pero con una separación estricta de responsabilidades.

Cablearía ahora el candidato como implementación experimental, no como política de bloqueo en producción. Esperar a tener el dataset perfecto para integrar el modelo retrasaría la detección de errores del contrato Python/C++, de latencia y de semántica temporal. Pero tampoco permitiría que una integración temprana convirtiera un modelo inmaduro en candidato de producción por inercia.

Propongo tres puertas independientes.

Puerta 1 — Corrección de la implementación

Ahora

- Paridad Python/C++ con vectores de entrada fijos, incluidos valores límite.
- Igualdad exacta de rasgos, orden, tipos, valores ausentes y estado temporal.
- Pruebas de reinicio, desbordamiento, saturación y pérdida de estado.
- Latencia p50, p95, p99 y máxima observada bajo carga.
- Recuento de nodos, memoria y coste de inferencia.

Puerta 2 — Validez estadística

Antes de aceptar el modelo

- Test por corridas y escenarios independientes.
- Exclusión de familias y generadores.
- Pruebas con bases mixtas y víctimas frías.
- Medición de falsos positivos por víctima-hora.
- Auditoría de fuga temporal y de etiquetas.

Puerta 3 — Seguridad de la acción

Antes de habilitar bloqueos

- Modo sombra con tráfico representativo.
- Política de agregación y mitigación independiente.
- Pruebas end-to-end de falsos bloqueos.
- Límites de actuación, caducidad y recuperación.
- Evidencia estadística suficiente para el objetivo de seguridad.

La tercera puerta no queda superada porque la segunda produzca un recall elevado. Tampoco basta con obtener cero bloqueos erróneos en una prueba corta.

Un matiz adicional: si el contrato de rasgos está cambiando, versionaría el contrato y los artefactos del modelo de forma inseparable. No permitiría cargar un bosque entrenado con una semántica de rasgos diferente de la que ejecuta el sniffer.

## 4. ¿Qué política de agregación usar antes de bloquear?

Mi recomendación es separar cuatro operaciones:

1. Clasificación por paquete.
2. Acumulación de evidencia.
3. Decisión de mitigación.
4. Ejecución y verificación del bloqueo.

El clasificador puede operar por paquete, pero no implica que el firewall deba actuar por paquete.

### Política experimental inicial

Agregaría evidencia en dos escalas:

- Por víctima y ventana: para detectar presión global, cambios de volumen y ataques distribuidos entre muchos orígenes.
- Por origen y víctima: para determinar qué contribución concreta puede atribuirse a un origen antes de considerar un bloqueo selectivo.

Un ejemplo de política inicial que se puede evaluar sería el siguiente:

| Capa                       | Decisión experimental                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------- |
| Paquete                    | Inferencia inmediata, sin bloquear directamente                                               |
| Ventana de 1 s por víctima | Acumular evidencia y medir el cambio respecto a la línea base                                 |
| Origen-víctima             | Acumular decisiones y verificar persistencia                                                  |
| Mitigación                 | Aplicar una acción reversible y limitada si la evidencia satisface los criterios de seguridad |
| Bloqueo duro               | Exigir una autorización más estricta que la necesaria para limitar temporalmente la tasa      |

No fijaría todavía un valor de \\(k\\) en una política de \\(k\\) de \\(n\\) paquetes. Debe salir de un barrido de parámetros sobre validación independiente, midiendo simultáneamente la latencia y el error de cada política. Además, la persistencia de los paquetes hace que \\(k\\) de \\(n\\) no equivalga a \\(n\\) observaciones independientes.

### El peligro de bloquear por origen

En ataques de reflexión DNS o NTP, la dirección de origen puede corresponder a un servidor legítimo que ha enviado una respuesta a una petición falsificada. Bloquear ese servidor puede cortar tráfico legítimo sin eliminar la causa del ataque.

Por tanto, distinguiría:

- La víctima está bajo presión.
- Un origen contribuye a la presión.
- Ese origen puede bloquearse con seguridad.

Son tres afirmaciones distintas y requieren evidencia distinta.

Para un hospital, empezaría por una mitigación reversible con límites conservadores, cuando la arquitectura de red lo permita, y mantendría el bloqueo duro sujeto a condiciones más estrictas. El criterio no es conseguir que el firewall reaccione rápidamente, sino impedir que una clasificación errónea interrumpa un servicio legítimo.

### Cómo demostrar que el error es suficientemente bajo

Si se observan cero falsos bloqueos en \\(N\\) observaciones independientes, la regla aproximada de tres proporciona un límite superior del 95 % para la tasa de error de alrededor de \\(3/N\\).

Pero en este proyecto las observaciones por paquete no son independientes. Un millón de paquetes de una sola corrida no equivale a un millón de escenarios independientes.

Usaría intervalos de confianza calculados por unidades de agrupación apropiadas —corridas, sesiones o periodos de víctima— y reportaría también el peor resultado observado por escenario.

La puerta de cero falsos bloqueos debe entenderse como una condición operacional que se verifica en pruebas y se vigila después del despliegue, no como algo que un número finito de ensayos pueda garantizar universalmente.

## 5. ¿Bosque aleatorio, árbol pequeño o regla explícita?

Compararía los tres. No descartaría el bosque por sus resultados actuales, pero tampoco lo conservaría solo porque obtiene mejores métricas dentro del laboratorio.

Modelo A — Regla explícita

Ejemplo conceptual: anomalía relativa persistente, evidencia de volumen y una señal de protocolo compatible. Los parámetros deben aprenderse o calibrarse con validación, no escogerse para separar las tasas concretas del laboratorio.

Ventaja: comportamiento auditable, coste bajo y facilidad para establecer límites de actuación.

Riesgo: las combinaciones rígidas de condiciones pueden omitir ataques nuevos.

Modelo B — Árbol poco profundo

Un árbol pequeño permitiría descubrir interacciones sencillas y convertirlas en reglas comprensibles.

Ventaja: inspección directa de los umbrales y menor complejidad.

Riesgo: inestabilidad ante pequeños cambios del dataset y capacidad limitada para representar comportamientos heterogéneos.

Modelo C — Bosque aleatorio

Conserva capacidad para representar interacciones no lineales entre señales.

Ventaja: puede modelar combinaciones de rasgos que no se expresan bien con una sola regla.

Riesgo: complejidad mayor, explicabilidad limitada y posibilidad de memorizar artefactos de los generadores.

### El experimento comparativo

Entrenaría los tres modelos sobre exactamente las mismas particiones. Ajustaría sus parámetros exclusivamente en validación y los congelaría antes de ejecutar el test final.

Evaluaría:

- Recall por familia y por escenario no visto.
- Falsos positivos por víctima-hora.
- Latencia de detección y de decisión.
- Tamaño del modelo, memoria y coste por paquete.
- Robustez ante cambios en la escala de tráfico.
- Estabilidad de las decisiones ante pequeñas variaciones de los rasgos.
- Complejidad de implementación y reproducibilidad Python/C++.

La regla explícita no debería incluir una firma concreta del generador como condición obligatoria. Si se usa una señal de protocolo, debe demostrarse que aporta información útil en escenarios diversos y que no confunde tráfico legítimo con ataque.

Mi preferencia para aRGus es el modelo más sencillo que supere las mismas puertas de seguridad y generalización, no necesariamente el que alcance el mayor F1. Si una regla obtiene resultados equivalentes con menos errores y un comportamiento más fácil de auditar, tendrá una ventaja operativa clara.

## 6. ¿Es correcto sacar el arranque del entrenamiento y publicar la latencia?

Es correcto tratar el arranque como un régimen operativo diferente. No es correcto excluirlo de la evaluación y presentar el resultado como si describiera el sistema completo.

Las primeras filas de un ataque pueden ser indistinguibles del tráfico benigno porque los rasgos de víctima todavía reflejan la ventana anterior. Pero esa explicación debe comprobarse con una reconstrucción temporal exacta del estado del kernel y del servicio.

Separaría tres métricas:

1. Rendimiento condicionado al estado: cómo clasifica el modelo una vez que dispone de señales informativas.
2. Latencia desde el inicio del ataque: cuánto tarda el sistema completo en acumular evidencia suficiente.
3. Rendimiento desde estado frío: qué decisiones puede tomar antes de disponer de una línea base fiable.

El test debe conservar los periodos de arranque. Se pueden excluir del entrenamiento para evitar enseñar al modelo ejemplos que no contienen información discriminante, pero hay que seguir evaluándolos como parte del comportamiento real.

Publicaría los resultados con nombres inequívocos:

- `recall_after_warmup`
- `cold_start_detection_rate`
- `detection_latency_p50/p95/p99`
- `time_to_mitigation`
- `false_block_rate_during_warmup`

Los nombres son propuestas de métricas, no una afirmación de que esos valores ya se hayan medido.

También mediría el tiempo hasta que la EWMA entra en presión y el tiempo hasta que sale de ella. Una latencia de clasificación baja puede coexistir con una latencia operacional elevada si el sistema necesita esperar a la siguiente ventana, acumular evidencia o satisfacer la política de agregación.

Y haría una prueba de reinicio en mitad de un ataque: el estado de la víctima puede perderse, y el sistema debe volver a comportarse como un sistema frío, no asumir que conserva una historia que ya no existe.

## 7. ¿Qué más puede haberse pasado por alto?

Hay varios puntos que considero prioritarios antes de cerrar DAY292.

### 7.1. El número de corridas no equivale al número de ejemplos independientes

Diecinueve corridas constituyen una base experimental inicial, no una validación suficiente para afirmar generalización amplia en infraestructura crítica.

Necesitamos saber cuántas corridas independientes corresponden a cada combinación de familia, tasa, generador y estado de víctima. Un gran número de paquetes dentro de pocas corridas puede dar métricas aparentemente muy precisas sin proporcionar evidencia equivalente sobre nuevos escenarios.

### 7.2. Las etiquetas por origen pueden no representar toda la verdad operacional

Etiquetar el tráfico del atacante como malicioso y el del origen inocente como benigno es razonable para el experimento descrito. Sin embargo, en un escenario de reflexión, un paquete de respuesta puede proceder de un servidor legítimo y formar parte del volumen que recibe la víctima.

Conviene distinguir entre:

- Etiqueta de origen.
- Etiqueta del paquete o flujo en su contexto.
- Etiqueta de escenario de ataque.
- Acción segura sobre ese origen.

Si esas categorías se mezclan, el clasificador puede aprender una definición de «malicioso» que no coincide con lo que el firewall debe bloquear.

### 7.3. La señal de víctima introduce dependencia entre orígenes

`victim_pps` y `victim_rate_ratio` son señales compartidas por los flujos que se dirigen a la misma víctima y protocolo.

Eso es intencionado, pero tiene una consecuencia: el clasificador no está evaluando únicamente el paquete actual. Está utilizando un estado agregado que puede cambiar por la actividad de otros orígenes.

Por ello probaría ataques distribuidos entre muchos orígenes, un solo origen dominante y tráfico benigno que aumente simultáneamente. También probaría que un atacante no pueda alterar fácilmente la línea base o forzar transiciones de estado.

### 7.4. La EWMA necesita pruebas adversariales propias

La histéresis y la adaptación lenta bajo presión pueden solucionar la absorción de ataques sostenidos, pero no demuestran robustez ante ataques de baja intensidad, pausas estratégicas o cambios graduales.

Evaluaría secuencias con:

- Incrementos escalonados.
- Ataques intermitentes.
- Periodos benignos cortos entre ráfagas.
- Aumento gradual del volumen.
- Reinicio del estado y pérdida de eventos.
- Cambios de línea base legítimos.

El suelo de 10 pps, las 30 ventanas para entrar en presión y las constantes de adaptación deben evaluarse como parámetros del sistema, no solo como detalles de implementación.

### 7.5. Cero pérdidas en el laboratorio no demuestra cero pérdidas bajo carga

Mantendría las pruebas de clasificación separadas de las pruebas de integridad del pipeline. Con tráfico creciente, hay que medir pérdidas de eventos, saturación de mapas, retraso de procesamiento y divergencia entre contadores del kernel y del servicio.

Si se pierden selectivamente eventos durante un ataque, tanto las características como las métricas pueden resultar engañosas. La contabilidad de pérdidas debe formar parte de la evidencia que acompaña a cada resultado experimental.

### 7.6. El falso positivo de la respuesta DNS de 1442 bytes es importante

No lo trataría como una excepción irrelevante. Que una respuesta DNS legítima tenga exactamente el tamaño de un ejemplo de ataque indica que el tamaño, aislado o combinado con otras señales, no es suficiente para justificar un bloqueo.

Investigaría si el error desaparece cuando se añaden escenarios legítimos de DNS de tamaño similar y cuando se evalúan respuestas de otros servidores y generadores. Si persiste, hay que identificar qué señal adicional permitiría discriminar sin memorizar el tamaño.

### 7.7. El resultado de exclusión de familias debe descomponerse

La caída del recall sin NTP podría significar que el modelo ha aprendido una firma de NTP, pero también podría reflejar que la familia excluida tiene una distribución de rasgos muy diferente o que el entrenamiento carece de ejemplos representativos de su comportamiento.

Para distinguirlo, realizaría:

- Matrices de confusión por familia.
- Distribuciones de rasgos por etiqueta y familia.
- Importancia por permutación calculada sobre conjuntos agrupados.
- Ablaciones de rasgos manteniendo las mismas particiones.
- Evaluación de la regla y del modelo sobre cada familia excluida.

La importancia por permutación, por sí sola, no prueba causalidad ni identifica una fuga. Es una herramienta diagnóstica que necesita contrastarse con las ablasiones y los resultados fuera de distribución.

## Dictamen final del Consejo

## Decisión propuesta para DAY292

Continuar con B sin `victim_pps` como candidato experimental.

Es la hipótesis más coherente con la intención de detectar anomalías relativas, pero aún no está validada para despliegue.

Cablear el contrato y las pruebas de paridad ahora.

Esto permite descubrir errores de integración mientras se amplía el dataset.

Ampliar el dataset con particiones por escenario y generador.

La generalización, especialmente la exclusión de familias, es la incertidumbre principal que debemos resolver.

No habilitar todavía el bloqueo autónomo.

La clasificación y la autorización para bloquear deben superar puertas de seguridad independientes.

### Orden de trabajo que recomiendo

1. Auditar la causalidad temporal de los ocho rasgos.
2. Congelar y versionar el contrato Python/C++.
3. Reproducir las métricas actuales con artefactos y particiones verificables.
4. Ampliar el dataset con tráfico benigno y malicioso solapado en características.
5. Comparar B, B sin `victim_pps`, el híbrido, un árbol pequeño y una regla explícita.
6. Evaluar víctimas frías, familias excluidas, generadores nuevos y ataques distribuidos.
7. Probar agregación y mitigación en modo sombra antes de autorizar cualquier bloqueo.

La pregunta decisiva no es si el bosque reconoce los ataques que le hemos enseñado. Es si conserva una tasa de falsos bloqueos aceptable cuando cambian el generador, la carga legítima, la historia de la víctima y la composición del tráfico.

Ese es el resultado que debería determinar si la cabeza DDoS de aRGus está lista para avanzar.