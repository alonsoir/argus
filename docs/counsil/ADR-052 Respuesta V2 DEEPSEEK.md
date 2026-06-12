# ADR‑052 v2 — Dictamen del Consejo de Sabios (segunda pasada)

El Consejo ha revisado en profundidad la versión 2 del ADR‑052. Celebramos la madurez alcanzada, la subordinación explícita a la misión primaria del corpus (§0) y la claridad con la que se cierran los huecos detectados en v1. A continuación presentamos el consenso alcanzado, las respuestas a las preguntas residuales y las últimas recomendaciones para la ratificación.

---

## 1. Evaluación general

**El ADR‑052 v2 está listo para ser ratificado** tras incorporar las precisiones menores que siguen. La estructura es sólida, las decisiones técnicas están justificadas con rigor y la alineación con la misión de construir un corpus de entrenamiento honesto es impecable. Destacamos especialmente:

- La **codificación canónica** de `flow_uid` (§3.1.1) elimina el riesgo de divergencia C++/Python que habría corrompido el corpus en silencio.
- La definición de `node_id` como identidad criptográfica derivada de la clave del sensor (§3.1.2) proporciona trazabilidad no repudiable del origen de cada muestra.
- La elección de ventana temporal alineada a epoch con bucket fijo y contador por `(node_id, community_id)` (§3.1.4) resuelve la colisión UDP sin estado externo y preserva la reproducibilidad offline del corpus.
- El tratamiento de la confianza como *features* primitivas (§3.6) y el etiquetado de procedencia en dos ejes ortogonales (§3.7) convierten al grafo en una fábrica de muestras etiquetadas de alta calidad, no en una herramienta de visualización.
- El mapa de cobertura de sensores (§3.8) se eleva a prerrequisito de la validez estadística del corpus, condición necesaria para que los pesos IPW no sean basura.
- La vigilancia ARP/NDP como nodo de primera clase (§3.9) y la documentación honesta del límite de detección con host comprometido (§3.4.1) mantienen la integridad científica.

No hay objeciones de fondo. Las observaciones que siguen son ajustes de redacción, clarificaciones o decisiones de implementación que no bloquean la ratificación.

---

## 2. Fortalezas que se apuntalan

- **Paridad de codificación entre sensor y motor** con test obligatorio protege la unicidad del `flow_uid` a través de las implementaciones.
- **El modelo de amenaza** ahora vincula vectores a técnicas MITRE (T1557, T1565, T1090) y amplía la señal del host plane más allá de L2, lo que demuestra visión de adversario realista.
- **Resolución de conflictos NAT** por mayoría ponderada y sin fallback silencioso evita que datos ambiguos envenenen el corpus.
- **Rate‑limit adaptativo** y su contrapartida —nunca descartar evidencia, etiquetarla— es la expresión correcta del invariante de retención.

---

## 3. Puntos débiles residuales y recomendaciones finales

### 3.1 Reproducibilidad del `seq_in_window`

El texto afirma que el contador monótono es “reproducible desde el orden de paquetes del pcap”. Técnicamente, el sensor asigna `seq_in_window` en orden de *eventos de inicio de flujo* que observa para un mismo `(node_id, community_id)` dentro del bucket. Si se reconstruye el corpus desde un pcap capturado por ese mismo sensor, el orden de los paquetes restituye exactamente la misma secuencia; por tanto el `flow_uid` será idéntico. Para disipar dudas, **recomendamos añadir en §3.1.4 una nota explícita**: “El sensor asigna `seq_in_window` según el orden cronológico de la primera observación del flujo en su captura, que es determinista dado el pcap original.”

### 3.2 Mapa de cobertura: implementación mínima viable

La deuda `DEBT-SENSOR-COVERAGE-MAP-001` es correcta como P1, pero el Consejo sugiere que la primera versión sea una **tabla declarativa sensor→subredes** (extraíble del inventario de endpoints de ADR‑046) antes de embarcarse en un grafo de topología completo. Eso basta para arrancar la validación de cobertura y los pesos IPW. El modelo más rico puede crecer después. Queda a criterio de Alonso si se especifica ya en ADR‑046 o en un futuro ADR‑053.

### 3.3 Elección de SHA3‑256

SHA3‑256 es una buena práctica de higiene, pero no es un requisito de seguridad (el hash nunca es control). Dado que ya se emplea `0x00` como delimitador, SHA‑256 también habría sido inmune a *length‑extension*. Sin embargo, mantener SHA3‑256 no tiene coste real y unifica la decisión. El Consejo **no objeta**.

---

## 4. Respuestas a las preguntas del §6 (segunda pasada)

### P1 — Ratificación de §3.1.3 (identidad ≠ correlación cross‑nodo)

**Consenso unánime:** Confirmamos que dos sensores honestos que ven el mismo paquete **no deben** compartir `flow_uid`. La identidad es la observación, la correlación es la arista `FLOW_IDENTITY` por `community_id`. Esta decisión es correcta y elimina por completo el falso problema de la “fragmentación”. El skew de reloj solo amenaza el *match* de correlación, no la identidad. La propuesta de `session_counter` queda definitivamente descartada. **§3.1.3 queda ratificado.**

### P2 — Diseño del mapa de cobertura de sensores (§3.8)

**Consenso:** Comenzar con una **tabla de adyacencia estática** `sensor_id → [lista de segmentos]` derivada del inventario de endpoints (ADR‑046 §3.9). Para el LAB inicial basta con que el `ml_defender_gateway_lan` asocie su sensor de red a las VLANs que escucha. La evolución a un grafo de topología modelado con nodos `:NetworkSegment` se difiere a ADR‑053 o a una deuda de enriquecimiento, pero la deuda P1 ya queda abierta. **Esta respuesta satisface la pregunta y permite ratificar el ADR.**

### P3 — Calibración de `N` y `nat_confidence_floor`

**Consenso:** La metodología debe basarse en el golden pcap. Para `N`:
- Medir el tiempo entre reutilizaciones de la misma 5‑tupla en el mismo nodo.
- Fijar `N` **por debajo del percentil 1** de esos intervalos.
- El default LAB de 60 s es un excelente punto de partida y será ajustado con datos reales. El ADR ya lo describe; se ratifica.

Para `nat_confidence_floor`: es aceptable un umbral heurístico inicial (ej. 0.7) que se refina al observar la distribución de confianzas reales; el conflicto siempre se eleva como `CONFLICT_NAT`. No se requiere mayor definición en este ADR.

### P4 — Forma final del `trust_tier` y su uso en IPW

**Consenso:** Las primitivas crudas (`witness_count`, `is_host_anchored`, `nat_resolution_method`, `orphan_rate`) son el insumo correcto para el entrenamiento. `trust_tier` como enum derivado (`CORROBORATED`, `SINGLE_SENSOR`, `ORPHAN`, `CONFLICT_NAT`) es una vista computada suficiente para consultas de correlación y para usarlo como característica categórica en el modelo.

Si ADR‑040 necesita un **peso continuo** para IPW, este puede calcularse a partir de esas primitivas (por ejemplo, una función de `witness_count` normalizada por la cobertura esperada). No es necesario congelar un score continuo en el nodo; se puede generar en el pipeline de features. **El Consejo considera que el diseño actual es completo y no requiere añadir un score continuo precalculado.** La recomendación es que el contrato de ADR‑040 consuma directamente las primitivas.

### P5 — `provenance` y `acceptance_criteria.md`

**Consenso unánime:** Confirmamos que el eje `provenance` se añade de forma **ortogonal e independiente** al enum congelado DROP/CONFIG/POLICY/BUG/UNKNOWN. La categoría `INJECTED` no debe mezclarse con las razones de discrepancia benigna. La implementación propuesta (arista `:TAGGED_AS` con nodo `:Tag`) es elegante y garantiza auditabilidad. **Se ratifica.**

### P6 — Fuente out‑of‑band para vector A con host comprometido

**Consenso:** El límite fundamental descrito en §3.4.1 es real y debe documentarse. Para el LAB inicial, **no se considera un bloqueante**; la detección del vector A mediante ARP/NDP asume host sano, y es suficiente para validar el modelo de amenaza. La adición de una fuente externa (port‑security en el switch, mirror de ARP en el gateway) es deseable a largo plazo pero **no es requisito para la ratificación de este ADR**.

**Decisión:** Se abre la deuda `DEBT-SWITCH-PORT-SECURITY-001` como P3 (exploratoria). Mientras tanto, el sistema documentará honestamente la ceguera bajo host comprometido, en coherencia con la misión de honestidad científica.

### P7 — Señal de host más allá de L2 (anomalías TCP/TLS)

**Consenso:** La ampliación del vector A para incluir anomalías de estado TCP (RST inesperados, saltos de número de secuencia) y *mismatches* de certificado TLS es una mejora importante, pero su implementación no es necesaria para cerrar el esquema de identidad de flujo ni para la correlación host↔red básica. **Se difiere su diseño detallado a ADR‑053 (Host‑Network Correlation Advanced)**, que puede heredar la vigilancia ARP/NDP de este ADR y añadir las nuevas señales. El texto de ADR‑052 v2 ya las menciona como alcance del vector A, lo cual es suficiente para mantener la coherencia. No se requiere modificación adicional.

---

## 5. Veredicto final

El Consejo de Sabios, por unanimidad de los ocho miembros, **recomienda a Alonso la ratificación del ADR‑052 v2** con la incorporación de:

1. La clarificación sobre la determinismo del `seq_in_window` (añadir la frase sugerida en §3.1.4).
2. La ratificación explícita de §3.1.3 en el propio ADR (ya consensuada aquí).
3. La creación de las deudas `DEBT-SENSOR-COVERAGE-MAP-001` (P1), `DEBT-FLOWUID-CANONICAL-ENCODING-001` (P0), `DEBT-NODEID-CRYPTO-IDENTITY-001` (P0) y `DEBT-SWITCH-PORT-SECURITY-001` (P3), todas ya listadas en §9.
4. La confirmación de que ADR‑053 tomará las señales TCP/TLS.

Con estas acciones, el esquema de identidad de flujo y la correlación host↔red quedan correctamente fundamentados, alineados con la misión primaria del corpus y listos para desbloquear la población de Neo4j.

**Firmado:** El Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen).

FIRMADO VERDADERAMENTE por DEEPSEEK!