El Consejo se reúne. Antes de las siete preguntas, cinco hallazgos que las atraviesan; después, respuesta por pregunta. Como vosotros: no votamos, dejamos predicciones falsables.

## Hallazgos transversales

**A. Vuestra evidencia "fría" aún no es válida.** Las corridas frías son de otro código (otro contrato de rasgos). Cualquier conclusión sobre víctima fría —incluida la comparación B vs B-sin-victim_pps— está confundida por el cambio de contrato. Re-capturad el escenario frío con código v2 antes de cerrar la pregunta 1. Es barato y es bloqueante.

**B. El fallo frío predecible es auto-absorción, no "el ratio no sirve en frío".** Clave nueva, α = 0,1, suelo 10 pps, ataque de 60 pps: ratio por ventana ≈ 6 → 6 → 5,3 → 3,7 → 2,9. Cruza 3 en ~4 ventanas, pero la clave no es elegible para presión hasta la ventana 30. Techo de recall ≈ 4/90 ≈ **4-5 %**. Observado: 8 % (y con 100 pps: mismo cálculo, ~4 %; observado 13 %). Mismo orden; la discrepancia de 2-3× es justo lo que el plot de ratio(t) debe explicar (sospechamos el código viejo). Predicción falsable: si congeláis la EWMA en el suelo hasta que la clave tenga 30 ventanas, el recall frío a 60/100 pps salta a ~90-100 % sin tocar el modelo.

**C. Falta la métrica que más importa en un hospital: el colateral** (FP sobre el inocente .51 concurrente al ataque). Los rasgos de víctima son compartidos por atacante e inocente; lo único que separa sus paquetes son los rasgos de flujo/paquete — es decir, las firmas que queréis de-empezar a ignorar. La dependencia de firma no es solo un riesgo de generalización: **está cargando el cero-colateral**. ¿Está .51 dentro del cálculo de FP de B, o solo contáis el contraste de .50? Publicadlo como columna en todas las evaluaciones, incluido el leave-family-out.

**D. Ataques desde una sola IP no son DDoS, y el contrato carece del rasgo estructural que generaliza entre familias:** la tasa de fuentes nuevas por víctima y ventana. Reflexión y SYN spoofeado traen muchas fuentes primera-visita; un backup DICOM de 200 pps es UNA fuente. Propuesta de contrato v2.1: `victim_src_newness` (fracción de paquetes de fuentes no vistas en las últimas W ventanas). Coste kernel acotado (LRU/bloom por clave). Es la adición de mayor valor por byte de contrato: resuelve "backup legítimo vs ataque a la misma tasa" sin depender del tamaño de paquete.

**E. La pata benigna es el cuello de botella.** Hoy: DNS 5-20 pps + ambiente. Faltan, por orden de daño: TCP benigno de primera clase (vuestro LOFO sin SYN ya lo demostró: 99 % del TCP inocente marcado), benigno a escala 10/50/200/1000 pps, benigno bulk (pocos flujos, cuentas enormes, minutos — el FP clásico de detectores volumétricos en hospitales) y benigno raro legítimo (tormentas SNMP, burst NTP post-reinicio).

## 1. ¿B sin victim_pps?

Sí como candidato de sombra, pero el dilema absoluto/relativo está mal planteado:

- El umbral 30-40 de B tiene margen benigno_máx/ataque_mín = 20/30 = **1,5×**. Un margen de 1,5× en el único eje decisivo no sobrevive a ningún despliegue con benigno > 30 pps, que es casi todos. Reportad siempre el margen del umbral, no solo el umbral.
- La regla absoluta "solo en frío" que proponéis es matemáticamente el suelo del ratio: ratio ≥ 3 con denominador congelado en 10 pps ≡ pps ≥ 30. No necesitáis un híbrido: necesitáis arreglar el warm-up. Recomendación: **EWMA congelada en el suelo hasta 30 ventanas de edad**, dinámica actual después. Coste medible: una subida legítima en clave joven da ratio alto hasta ~30 s — aceptable si la política exige clave madura para el tier duro (pregunta 4).
- Decisión con números: tras re-capturar frío con v2 y congelar la EWMA, objetivo recall frío 60/100 ≥ 90 % del cálido. Si se cumple, sin regla absoluta. Si no, regla absoluta solo-para-claves-jóvenes con umbral = 3×suelo, el suelo como parámetro de despliegue ("debajo de esto la víctima está silenciosa"), y contador de disparos separado y alarmado. Una regla absoluta silenciosa falla en silencio; una contada, no.

## 2. ¿Basta diversificar generadores?

Necesario, no suficiente:

- **Health-check del dataset (barato y demoledor):** stump de un solo rasgo sobre el dataset. Si algún rasgo alcanza AUC > 0,9 solo, tenéis un atajo, no un modelo. Hoy `mean_packet_size` seguro la viola. Objetivo tras el rediseño: ninguno > 0,9.
- **Cruzar marginales deliberadamente:** benigno con la misma distribución lognormal de tamaños que el ataque, incluyendo el 1442 B (vuestro único FP no transitorio fue exactamente esa colisión); benigno a 200-1000 pps contra ataques a 30; TCP benigno completo (SYN+datos+FIN) y UDP unidireccional (syslog, SNMP).
- **Generalización como métrica de primera clase:** CICDDoS2019 tiene 12 familias. Entrenad con 5-6, dejad 4 held-out (SSDP/MSSQL/LDAP/NetBIOS) y reportad recall Y colateral en held-out en cada iteración. Objetivo declarado, p. ej. ≥ 80 % en reflexión no vista. Hoy es 0 %; ese número en el dashboard gobierna el rediseño.
- **Ejes que cambian rasgos en producción:** fragmentación aleatorizada (ya tenéis udpB), encapsulación (+4 B VLAN, +24-78 B de túnel desplazan `mean_packet_size` y rompen umbrales en bytes — test de invarianza re-evaluando con offsets), y jitter temporal en los generadores: un generador CBR es una firma por sí mismo aunque no midáis inter-llegadas (estabiliza victim_pps y flow_packet_count).

## 3. ¿Cablear antes o iterar dataset antes?

Cablear ya, **en sombra con bloqueo desactivado**, e iterar el dataset en paralelo. Razón medible: las preguntas 1 y 2 dependen de distribuciones que el lab no puede muestrear (pps benigno real por clave, frecuencia real de claves frías, tamaños reales). La sombra las mide; el trabajo de paridad/latencia se reutiliza entero entre versiones del modelo.

Puertas que añadir a vuestra lista: (a) determinismo — mismo pcap replay dos veces → decisiones idénticas; (b) fixtures de frontera — serialización de umbrales float con precisión completa (el codegen que imprime con dígitos de menos es EL bug clásico de paridad; se manifiesta solo en paquetes exactamente en el umbral); (c) fixtures de inicio de flujo — vuestros 6 FP en los primeros 0,5 s de A huelen a rasgos degenerados (entropía de 1 paquete, completion desconocida); el contrato debe definir la política NaN y la paridad debe probarla; (d) criterio de promoción cuantitativo: 30 días de sombra, 0 falsos bloqueos sobre tráfico real, colateral < 1 % de paquetes inocentes en ataques sintéticos inyectados, revisión manual de cada disparo del tier duro.

Dejad victim_pps calculándose y logueándose aunque el modelo no lo use: es el dato con el que calibraréis el suelo por despliegue.

## 4. Política de agregación (cero bloqueos falsos)

Dos tiers; el modelo por paquete no bloquea nada por sí solo:

- **Tier suave (automático, por víctima):** rate-limit/deprioritizar cuando la víctima esté en presión Y la fracción marcada de la ventana supere x %, sostenido ≥ 2 ventanas. Métrica de éxito: supervivencia de paquetes inocentes ≥ 99 % en replay del escenario .51-durante-ataque. El rate-limit no tiene semántica de bloqueo falso: degrada, no corta.
- **Tier duro (por par origen→víctima, nunca por víctima), condiciones en AND:** víctima en presión; ≥ k de los últimos n paquetes de ese origen marcados; origen fuera de allowlist; clave de víctima madura. k se deriva del benigno: medid la racha máxima de marcados consecutivos por origen en todo el corpus benigno (incluido bulk y rarezas) y poned k > 3× esa racha.
- **La aritmética que hace tractable el cero:** un FP por paquete de 10⁻³ (vuestra cota superior con 0 de ~900 filas, regla de tres: 3/n) son decenas de miles de paquetes marcados al día. k-de-n solo no lo arregla porque el FP benigno está correlacionado por flujo (vuestro DNS de 1442 B: se marca el flujo entero). Lo que compra seguridad es el **AND con presión**: un falso bloqueo duro exige (flujo benigno con firma del ataque) Y (víctima bajo ataque real) simultáneos. El residuo es exactamente el colateral — medirlo es la puerta, no asumirlo.
- **Hold-down** con backoff (60 s, ×2, máx 1 h), liberación por silencio, log con snapshot de rasgos por bloqueo.
- **Disyuntor de saturación:** si > 20 % del tráfico total va marcado > 10 s, alarma y caída a solo-tier-suave. Vuestro propio LOFO sin SYN (99 % del TCP inocente) demuestra que el modelo PUEDE entrar en ese modo con un dataset desplazado; el disyuntor convierte esa clase de fallo en incidente ruidoso, no en apagón del hospital.
- Cobertura: contra fuentes spoofeadas aleatorias el tier duro por origen nunca acumula k — el tier suave por víctima es la única respuesta; contra reflexión, bloquear por reflector funciona.

## 5. ¿Regla, árbol poco profundo o bosque?

Es una pregunta empírica y depende de la métrica que hoy no reportáis (colateral). Protocolo: mismos folds, comparad stump de ratio / regla "ratio > K Y firma" / árbol de profundidad 3-4 / el bosque, con columnas: recall cálido, FP contraste, colateral, LOFO held-out, frío, nodos/latencia. Predicción del Consejo: la regla de ratio gana o empata en recall cálido y **pierde el colateral al ~100 %** (marca también al inocente .51, que comparte todos los rasgos de víctima). Si el bosque solo iguala en recall cálido y no gana en colateral y LOFO, la regla gana por auditable: en un hospital, "bloqueado porque ratio 6, puerto 123, 468 B" vale más que 3714 nodos.

Alternativa estructural que consideramos la correcta para v3: **factorizad**. Etapa 1: estado de presión — regla explícita y auditable sobre la EWMA que ya vive en el kernel (y donde el warm-up frío se arregla sin re-entrenar nada). Etapa 2: clasificador condicional que separa flujos atacantes de inocentes DENTRO de una víctima en presión, entrenado solo con filas en presión. El bosque actual mezcla las dos preguntas y por eso re-aprende la lógica de umbral. Medid flat vs factorizado en la misma tabla; esperamos bosque más pequeño, frío arreglado en etapa 1 y etapa 2 posiblemente un árbol de profundidad 3.

## 6. ¿Sacar el arranque del entrenamiento?

Del entrenamiento: correcto — esas filas son benignas-equivalentes y entrenar con ellas enseña a marcar rasgos benignos. Pero el titular debe ser la **latencia y el recall integral**: reportad tiempo-hasta-primera-marca por ataque (p50/p95 — vuestro 0,5-1,5 s), paquetes/bytes de ataque antes de la primera marca, y recall con y sin arranque. 1,4 s sobre 90 s = 1,6 %; los mismos 1,4 s sobre un burst de 5 s = 28 %. Reportad recall frente a duración del ataque.

Enmascara solo si publicáis el condicional sin el integral. Dos condiciones para que sea limpio: que los 2 s deriven del lag medido (1 ventana + margen), no constante mágica — verificadlo con el plot de disponibilidad de rasgos vs onset; y que el contrato defina qué ve un paquete de la ventana en curso (snapshot de la ventana completada anterior), porque es fuente clásica de divergencia Python/C++ si no se fija.

## 7. Lo que se os ha pasado

1. Todo lo de los hallazgos A-D: evidencia fría invalidada por contrato, colateral sin medir, ausencia de rasgos de diversidad de fuentes.
2. **IC y semillas:** 0 FP en n filas → cota 3/n. Vuestro "0 %" con ~900 filas es ≤ 0,33 % — el diseño lo aguanta solo por el AND de presión. Y las comparaciones 99,45 vs 100 con una sola semilla: repetid con ≥ 10 semillas y reportad dispersión antes de declarar diferencias.
3. **`flow_packet_count` es un umbral de escala escondido:** vuestros flujos de ataque tienen 5-9·10³ paquetes, el inocente 2·10³; un backup real llega a 10⁵-10⁶. Sin benigno bulk en el entrenamiento, ese rasgo vota "ataque" en producción justo cuando más duele. Normalizadlo (tasa por flujo o log1p) o cruzadlo en el dataset.
4. **Rampas lentas:** para una rampa exponencial de constante T (ventanas), el ratio en régimen es ≈ 1 + 1/(αT). Con α = 0,1, toda rampa con T ≥ 10 s mantiene ratio ≤ 2: nunca entra en presión y absorbe la línea base. Un atacante que suba ×10 en un minuto es invisible por diseño. Si importa, segunda línea base lenta (τ ~ 1 h) como rasgo v3; si no, declaradlo como exclusión de alcance.
5. **Alcance declarado:** esta cabeza es volumétrica/reflexión. Slowloris y low-rate aplicacional quedan fuera por construcción — ponedlo por escrito para que nadie confunda "cabeza DDoS" con "todo el DDoS".
6. La ponderación 50/50 rompe la calibración: no uséis probabilidades del bosque como riesgo; decisión binaria + política, como ya hacéis.
7. Lo que está bien y no conviene tocar: etiqueta por origen (el .51 durante el ataque es la etiqueta correcta y es la que hace medible el colateral), split por corridas completas, 0 pérdidas de captura medidas, y el diagnóstico propio de que aprendéis firmas — es correcto y es la mitad de la solución.

**Veredicto:** B sin victim_pps ratificado para sombra. Condiciones: re-captura fría con v2, EWMA congelada en suelo hasta madurez, colateral en el dashboard, stump-AUC como health-check del dataset, disyuntor de saturación en el E2E, y la factorización presión+condicional como v3. El Consejo no vota: deja arriba las predicciones para que las matéis o las confirméis con datos.