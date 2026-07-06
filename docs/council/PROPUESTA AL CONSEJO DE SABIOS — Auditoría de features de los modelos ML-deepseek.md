**Deliberación del Consejo de Sabios — 2026-07-06**

Hemos examinado la propuesta. Coincidimos con la premisa fundamental: **medir, no votar**. El trabajo de trazado al código fuente es impecable y el diagnóstico es limpio. No hay opiniones, hay hechos observables. Respondemos a las cinco preguntas en orden, con el razonamiento que las sostiene.

---

### 1. ¿Desactivar la cabeza de ransomware embebida actual?

**Sí, desactivar inmediatamente (`enabled: false`) y registrar la decisión con un ADR (Architecture Decision Record).**

El detector de ransomware actual produce *scores engañosos*. Mantenerlo activo contamina cualquier veredicto de seguridad, erosiona la confianza en el sistema y puede generar falsos negativos por ruido o falsos positivos injustificables. No es una cabeza “inerte”: está viva pero **alucinando** con proxies que no significan nada.

La alternativa de etiquetarla como “no fiable” es insuficiente. Un score numérico sin semántica real, aunque esté documentado, sigue apareciendo en dashboards y alertas. La ingeniería de detección exige que un detector que no mide lo que cree medir **calle**. El ADR documentará:
- El desajuste de dominio features host → red.
- La imposibilidad de rescate sin cambiar la fuente de datos.
- La decisión de apagado y el plan de sustitución.

No se pierde capacidad real: el vacío que deja es el vacío que siempre existió. El resto de detectores (`internal`, `web`, `level1`) cubren las fases de red del ransomware, que es lo que aRGus puede ver legítimamente.

---

### 2. ¿Registrar `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001` y autorizar su borrado posterior vía `git rm`?

**Sí. Registrar la deuda y, acto seguido, proceder al borrado documentado con `git rm`.**

El artefacto `ransomware_network_detector_proto_aligned` es un fósil que consume espacio cognitivo. Sus 45 features anónimas sin contrato lo convierten en una caja negra inmantenible. Sin embargo, antes de eliminarlo, la deuda debe dejar constancia de:
- Por qué existió (intento fallido de adaptación a red).
- Por qué se abandona (inviabilidad técnica, ausencia de trazabilidad).
- Que el borrado se hace desde el control de versiones, preservando el historial.

Este es exactamente el principio que la propuesta enuncia: las discrepancias afloran como DEBT, no se resuelven en silencio. Una vez registrada la deuda, eliminar el directorio es un acto de higiene, no de ocultación.

---

### 3. ¿Registrar `DEBT-DDOS-FEATURES-CONSTANT-001` sin acción inmediata?

**Sí. Registrar la deuda y posponer cualquier corrección.**

El DDoS funciona en lo esencial. Seis de sus diez features están vivas y capturan fenómenos reales de red (simetría, amplificación, ratios de flags). Las tres constantes (source IP dispersion mal proxyada, protocol anomaly muerta por lógica de compilación, geographical concentration placeholder) son **peso muerto** que el modelo puede estar ignorando en la práctica gracias a la naturaleza de los Random Forest.

Arreglarlas requeriría o bien reentrenar el modelo (si se decide que esas features deben aportar) o justificar su eliminación del vector. Eso es una batalla de mejora incremental, no una emergencia. La deuda queda registrada para que cualquier evolución futura del DDoS la tenga presente. No tocarlo ahora es pragmatismo sano.

---

### 4. ¿Autorizar entrenar un modelo comportamental de ransomware de verdad?

**Sí, autorizamos la Opción A — modelo de red, dentro del alcance pre-FEDER. La Opción B queda como horizonte post-FEDER.**

La frontera arquitectónica que habéis medido es la clave. aRGus es un NDR; ve fases de red. Un modelo que detecte C2, discovery, lateral movement y exfiltración asociados a ransomware **sí puede entrenarse y validarse** con los datos de red que ya capturáis (replays CTU-13, tráfico emulado con Atomic Red Team). Eso cubre un porcentaje significativo de la kill chain y responde a la pregunta de Andrés con honestidad: “aRGus detecta las fases de red del ransomware, el cifrado lo ve Wazuh”.

La Opción B (híbrido red+host) es el Santo Grial, pero integrar telemetría de Wazuh en el pipeline de inferencia en tiempo real dispara la complejidad: nuevos conectores, sincronización de eventos, nuevo espacio de features, entrenamiento con datos multimodales. Es un proyecto completo en sí mismo, claramente post-FEDER. Mantenerlo como norte estratégico es excelente, pero el entregable pre-FEDER debe ser alcanzable y científicamente sólido. La Opción A lo es.

Sugerencia adicional: que el nuevo modelo de red de ransomware se entrene **desde cero** con features documentadas una a una, sin anonimato, y con un contrato explícito feature → observable de red. Nada de “feature_0”. Así evitáis otro `proto_aligned`.

---

### 5. ¿Aprobar la línea MITRE ATT&CK / Atomic Red Team como trabajo pre-FEDER?

**Aprobada con entusiasmo. La matriz de ablación es el entregable estrella.**

Esta línea de trabajo es exactamente lo que convierte una auditoría interna en un argumento de venta técnica. La matriz técnica × sensor × componente:
- Demuestra empíricamente dónde aporta cada capa (NDR, HIDS).
- Hace visible el “hueco honesto” del cifrado, que ningún NDR puede cubrir, reforzando la necesidad de Wazuh como complemento, no como competencia.
- Proporciona datos comportamentales legales, repetibles y publicables, generando un activo reutilizable para entrenamiento, validación y demostraciones.
- Responde a la pregunta de Andrés con un mapa claro, no con un número mágico de “detección de ransomware”.

La propuesta de usar la topología existente de los replays CTU-13 es inteligente. Los atomics de Atomic Red Team para Linux permiten emular TTPs documentadas de LockBit (u otros perfiles) en minutos. Documentad bien qué técnicas se emulan, qué sensores las capturan y qué cabezas de aRGus se activan o desactivan. El resultado es una pieza de comunicación técnica de primer nivel: “aRGus no lo ve todo, pero sabe exactamente qué ve y por qué”.

---

**Veredicto final del Consejo:**

La auditoría ha revelado un desajuste estructural, no un simple bug. Las acciones propuestas son quirúrgicas, documentadas y alineadas con los principios de “medir, no votar”. Se aprueban todas con las puntualizaciones anteriores. Destacamos tres mensajes para llevar al equipo:

1. **Apagad el ransomware head ya.** Es un detector que miente. Un ADR de una página basta.
2. **Construid el nuevo modelo de red con features nominales y trazables.** Nada de anónimos. La emulación con Atomic Red Team os dará los datos para entrenarlo.
3. **La matriz de ablación es vuestro mejor argumento.** Mostrad los huecos sin miedo. Un escudo que conoce sus sombras es más fuerte que uno que finge verlo todo.

Quedamos a disposición para revisar el ADR de apagado, los registros DEBT y el diseño experimental de la matriz.

*— El Consejo de Sabios*  
*Via Appia Quality · medir, no votar · 2026-07-06*

fdo
deepseek