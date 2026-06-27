## DeepSeek — Respuesta a ADR-017 (Consulta sobre Jerarquía de Interfaces)

---

### Prefacio

El inventario está completo y las preguntas están bien planteadas. Coincido con Claude en que las skills de rag-security son un sistema ad-hoc y que los validadores de ADR-003 están fuera de scope. Mi voto se guía por tres principios:

1. **Ortogonalidad**: separar mecanismos que son fundamentalmente distintos (dlopen vs libbpf, skills vs plugins)
2. **Evolución incremental**: Opción C (solo primero-partido en PHASE 2) es la más segura para plugins de terceros
3. **Especificidad de contexto**: contextos tipados por componente (Opción A) evitan errores y son más documentables

---

### PREGUNTA 1 — Contextos tipados por componente

**Recomendación:** **Opción A** (un contexto por familia, con estructuras específicas y bien tipadas).

**Razonamiento:**
- **Type safety:** el compilador protege contra confusiones entre familias (ej: pasar un `SnifferContext*` a un plugin de ml-detector).
- **Auto-documentación:** cada estructura define exactamente qué datos están disponibles para cada tipo de plugin.
- **Performance:** acceso directo a campos, sin casting `void*` ni saltos de indirección.

La Opción B (contexto único con `void*` y tag) es más flexible pero abre la puerta a errores en tiempo de ejecución y requiere que el plugin conozca estructuras internas del core — rompe la abstracción.

**Riesgos:**
- La proliferación de estructuras puede llevar a código duplicado si no se factorizan campos comunes (ej: `src_ip`, `dst_ip`). Se puede mitigar con un `NetworkTuple` base incluido en cada contexto.
- Si en el futuro aparece un nuevo tipo de plugin no previsto, toca añadir una nueva estructura y un nuevo `plugin_component_type` — pero eso es evolución controlada.

**Blocker:** Ninguno. La decisión no afecta a las otras preguntas; es ortogonal.

---

### PREGUNTA 2 — Función de entrada por familia

**Recomendación:** **Sí, separar funciones de entrada por familia**, como se propone (`plugin_process_packet`, `plugin_predict`, `plugin_enrich`, `plugin_execute`).

**Razonamiento:**
- **Semántica clara:** un plugin de ml-detector no "procesa paquetes", predice. La función de entrada debe reflejar su propósito.
- **Contrato estable:** el loader puede verificar que el símbolo requerido existe según `plugin_component_type()`. Si falta, el plugin se rechaza.
- **Facilita testing:** se pueden mockear las distintas familias independientemente.

**Riesgos:**
- Aumenta el número de símbolos que el loader debe resolver, pero es marginal.
- Si en el futuro un plugin quisiera ofrecer más de un punto de entrada (ej: `predict` + `enrich`), habría que decidir si se permite. Por ahora, cada plugin tiene una única responsabilidad (principio de única responsabilidad).

**Blocker:** Ninguno. Esta decisión es coherente con la Opción A de la Pregunta 1.

---

### PREGUNTA 3 — Gestión de plugins futuros con contratos desconocidos

**Recomendación:** **Opción C** (solo primero-partido en PHASE 2, terceros en PHASE 3).

**Razonamiento:**
- **Reducción de riesgo:** en PHASE 2, los plugins los desarrolla el equipo core; sabemos exactamente sus inputs y outputs. Podemos definir contratos precisos.
- **Maduración:** la experiencia con esos plugins nos enseñará qué abstracciones son realmente necesarias para la extensibilidad de terceros.
- **Alta deuda potencial:** diseñar una arquitectura "genérica" para terceros sin casos reales lleva a over-engineering.

La Opción A (solo familias predefinidas) es una variante de la C, pero más restrictiva a largo plazo. La Opción B (familia "generic" con JSON schema) es atractiva pero añade complejidad de validación y aumenta la superficie de ataque (plugins arbitrarios). Diferimos esa decisión hasta tener experiencia.

**Riesgos:**
- En PHASE 3 puede ser necesario un rediseño menor de la API para soportar terceros. Pero ese rediseño estará informado por casos reales, no por especulación.

**Blocker:** Ninguno. Esta decisión es independiente de las demás.

---

### PREGUNTA 4 — Unificar skills de rag-security bajo plugin-loader

**Recomendación:** **No unificar.** Mantener las skills como mecanismo separado por ahora.

**Razonamiento:**
- **Ciclo de vida distinto:** las skills son invocadas síncronamente por el LLM y devuelven JSON; los plugins se cargan una vez y pueden procesar eventos en flujo continuo.
- **Seguridad:** las skills ya tienen un allowlist de comandos (ADR-010). Unificarlas bajo `dlopen` podría introducir la necesidad de verificar que un skill no está ejecutando código arbitrario no autorizado — es un vector adicional.
- **Simplicidad:** el sistema actual de skills funciona y es suficiente. No hay un problema real que resolver unificándolos, solo "limpieza arquitectónica". La limpieza puede esperar a que el sistema madure.

**Riesgos:**
- Posible duplicación de mecanismos a largo plazo. Pero podemos reevaluar en PHASE 3, cuando tengamos más experiencia con plugins y skills en producción.

**Blocker:** Ninguno. Esta decisión no afecta a las demás preguntas.

---

### PREGUNTA 5 — Plugins eBPF de kernel-telemetry: ¿mismo ADR-017 o ADR-018?

**Recomendación:** **ADR-018 separado.** Los plugins eBPF de kernel-telemetry merecen su propio ADR por las diferencias técnicas y de ciclo de vida.

**Razonamiento:**
- **Mecanismo de carga distinto:** `libbpf` vs `dlopen`. Unificar en el mismo documento diluiría las especificidades de cada uno.
- **Ciclo de vida:** los programas eBPF requieren attach/detach a interfaces, pin en BPF fs, y gestión de permisos en kernel. Eso no es un simple `dlopen`.
- **Conceptual:** aunque son "plugins" en sentido amplio, son un tipo de extensión cualitativamente diferente. Separarlos en ADR-018 permite diseñar su interfaz con la libertad que necesitan.

**Riesgos:**
- Riesgo de inconsistencia si en el futuro ambos sistemas evolucionan por separado. Se puede mitigar estableciendo una **interfaz común de identidad** (nombre, versión, etc.) que compartan, aunque el mecanismo de carga sea distinto.

**Blocker:** Ninguno. Esta decisión es independiente.

---

### Comentarios sobre la propuesta preliminar de jerarquía

- **Estructura general:** válida y bien segmentada.
- **EbpfUprobePlugin como subfamilia de SnifferPlugin:** correcto, porque el `SnifferContext` puede ser extendido para llevar información de uprobes si se necesita.
- **Falta de `RagIngesterPlugin`:** se menciona como futuro, OK.
- **Falta de `MlDetectorPlugin` de tipo "ensemble"** (ej: combinar varios modelos). No lo veo necesario hoy, pero podría aparecer. La jerarquía actual permite añadirlo como subfamilia de `InferencePlugin` más adelante.
- **Validadores de ADR-003 fuera de jerarquía:** correcto.

**Naming convention:** `lib{family}_{name}_v{N}.so` es adecuado. Sugiero que la `family` coincida con el `plugin_component_type()` (ej: `sniffer`, `ml-inference`, `ml-enrich`). Para skills, usar otro esquema (ej: `skill_*.lua` o similar) si no se unifican.

---

### Veredicto final sobre ADR-017

El ADR-017 debe centrarse en definir los contratos para las familias **SnifferPlugin** y **MlDetectorPlugin** (con sus subfamilias), con la Opción A de contextos tipados y funciones de entrada específicas. Las skills de rag-security y los plugins eBPF deben ir a ADRs separados (o aplazarse). Los validadores de ADR-003 quedan fuera del scope.

La decisión sobre extensibilidad de terceros (Pregunta 3) se aplaza a PHASE 3, con la Opción C.

Esta estrategia mantiene el foco en lo que se necesita para PHASE 2, evita over-engineering, y respeta el principio de no tocar el core legacy.

---

*DeepSeek — 22 marzo 2026*