**DeepSeek — Dictamen DAY 148**

Saludos, Alonso. Han despachado ustedes un DAY 148 formidable. La validación offline de Suricata es contundente, el cierre de la deuda de tipos float es un ejemplo de disciplina técnica, y el paper alcanza una madurez expositiva notable. Procedo a mis consideraciones sobre las tres preguntas elevadas al Consejo.

---

### P1 — VALIDEZ DEL FRAMING DE COMPLEMENTARIEDAD EN EL ABSTRACT

La frase del abstract v23 afirma la complementariedad de los tres paradigmas como un hecho, no como una hipótesis. ¿Es esto científicamente defendible en el estado actual del proyecto?

**Dictamen: Es defendible como *framing arquitectónico*, pero recomiendo suavizarlo para blindar el paper ante revisores rigurosos.**

La defensa se sostiene sobre dos pilares que el propio paper ya contiene:

1. **Evidencia empírica negativa fuerte.** Los resultados de Suricata offline (0 firmas ET Open disparadas en 323K paquetes) demuestran que un NDR puramente basado en firmas es ciego ante este tráfico. No es una afirmación menor: es un resultado experimental que el paper documenta.
2. **Argumento de capa de codificación nativa.** Zeek opera en la capa de telemetría (logs de conexión, metadatos de protocolos), Suricata en la capa de patrones conocidos, y el clasificador ML en la capa de comportamiento estadístico. Son representaciones irreduciblemente distintas del mismo tráfico. Esta es una verdad arquitectónica, no una conjetura.

La combinación de (1) y (2) permite afirmar que los paradigmas *no son redundantes*, y de ahí se sigue su complementariedad potencial. El paper no afirma haber demostrado empíricamente la integración completa, sino que los paradigmas *operan naturalmente de forma complementaria* en virtud de sus capas de codificación. El matiz es importante.

**Recomendación concreta para la próxima revisión (v4 o post-feedback de arXiv):**
Sustituir la frase actual por una versión ligeramente acotada:

> *"The three paradigms are complementary by design: Zeek's telemetry layer and Suricata's signature coverage operate alongside an ML behavioral classifier, each contributing at its native encoding layer."*

El cambio *"are complementary"* → *"are complementary by design"* desplaza la carga de la prueba desde la validación empírica total (que requeriría la integración completa) hacia la intención arquitectónica y los resultados parciales que ya poseen. Es más difícil de rebatir y preserva la fuerza de la afirmación en el abstract.

En ningún caso recomendaría mover esto a Future Work. El abstract debe declarar la tesis del paper. La tesis es que la complementariedad de paradigmas es necesaria y está respaldada por los resultados. Manténganlo en el abstract, con el ajuste propuesto.

---

### P2 — DEBT-PARQUET-SCHEMA-001: ESTRATEGIA PARA CERRARLO EN UNA SESIÓN

Este es el punto de estrangulamiento del proyecto FEDER. Sin schema validado, ADR-0043 no tiene contrato de interfaz. Mi recomendación quirúrgica:

#### (a) Granularidad: por flow, sin excepciones

La granularidad por paquete no es viable. El pipeline C++20 ya opera sobre flows agregados (el sniffer reconstruye sesiones, el detector ML clasifica flows, no paquetes individuales). Los CSVs del pipeline contendrán un registro por flow. Intentar reventar flows en paquetes dentro del lote mensual sería:
- Una transformación costosa que el nodo edge no debe hacer.
- Una explosión de volumen (×100 o ×1000) que saturaría el canal de subida y el almacenamiento Parquet.

La decisión está tomada por el diseño existente. La sesión solo debe confirmarla.

#### (b) Registrar todos los eventos del ml-detector; filtrar firewall-acl-agent según volumen

- **ml-detector:** Debe registrar *todos* los flows clasificados (normal, anomaly, attack). La memoria histórica necesita la línea base de actividad normal para detectar desviaciones a largo plazo y para que los analistas puedan contextualizar las anomalías. Un flujo etiquetado como `normal` no es ruido: es la firma conductual del día a día.
- **firewall-acl-agent:** Si los CSVs muestran que el número de ALLOW es órdenes de magnitud mayor que DENY/DROP, enviar solo DENY y DROP. Si el volumen total es bajo (menos de 50K registros/mes en una instalación pequeña), enviar todo. La decisión debe tomarla el dato real, no una conjetura previa.

**Métrica de decisión durante la sesión:** contar filas en los CSVs de un mes simulado en Vagrant. Si `firewall-acl-agent.csv` supera 500K filas, filtrar a solo acciones no-ALLOW. Si no, enviar todo.

#### (c) Tipos Arrow óptimos

| Campo | Tipo Arrow recomendado | Justificación |
|-------|------------------------|---------------|
| Timestamps | `int64` | Nanosegundos epoch UTC. Sin zona horaria, sin parsing. Ordenable nativamente. El schema candidato v3 ya lo propone: mantener. |
| Scores de confianza | `float32` | Suficiente precisión para [0.0, 1.0]. `float64` es sobrecoste sin beneficio |
| Identificadores anonimizados (HMAC) | `binary` (32 bytes fijos) | Mucho más compacto que hex string (64 bytes en UTF-8). Arrow/Parquet manejan `binary` nativamente. Si la depuración humana requiere legibilidad, añadir una columna `_hex` opcional o usar una función de conversión en la ingesta Neo4j. **Recomiendo `binary` para producción, con un comentario en el schema sobre cómo visualizarlo.** |
| Cadenas cortas (event_type, action, rule_id) | `dictionary<utf8>` | Compactación automática por diccionario Parquet. Ideal para columnas con baja cardinalidad. |
| IPs (si llegaran a aparecer en claro en el futuro) | No aplica. Las IPs nunca viajan. Pero si se almacenaran localmente en SQLite, usar `binary(4)` o `binary(16)`. |

**Protocolo para la sesión de cierre de DEBT-PARQUET-SCHEMA-001:**

1. Arrancar entorno Vagrant. Ejecutar el pipeline durante un período representativo (o usar logs capturados previamente).
2. Localizar los CSVs generados por `ml-detector` y `firewall-acl-agent`.
3. Contar filas y columnas. Verificar que las columnas del schema candidato v3 existen y que no faltan campos críticos (ej. `flow_duration`, `packet_count`, etc.).
4. Decidir filtro de `firewall-acl-agent` según volumen observado.
5. Escribir el schema Parquet final en el ADR-0043 (o en un fichero `schema/` dedicado), declarar cerrada la deuda.
6. Generar un Parquet de prueba con datos sintéticos que respete el schema, para que el equipo de Neo4j comience el pipeline de ingesta en paralelo.

---

### P3 — PRIORIDAD PARA DAY 149 Y SECUENCIA HASTA EL GO/NO-GO

Con 2.5 meses hasta el go/no-go (1-Ago-2026) y 4 meses hasta el deadline FEDER, la secuencia debe ser despiadadamente pragmática. El objetivo del go/no-go es demostrar que la arquitectura ADR-0043 es viable (Parquet → Neo4j con pseudonimización estable). Todo lo que no contribuya a ese objetivo es secundario.

**Orden óptimo:**

| Día(s) | Tarea | Justificación |
|--------|-------|---------------|
| **DAY 149** | **A) DEBT-PARQUET-SCHEMA-001** | P0 bloqueante. Sin schema no hay pipeline. Es la primera tarea del roadmap ADR-0043. Debe ejecutarse de inmediato. |
| **DAY 150-152** | Implementar pseudonimización HMAC en nodo edge y empaquetado Parquet con firma Ed25519 | Depende de A. Construye el extremo emisor del contrato de interfaz. |
| **DAY 153-156** | Pipeline de ingesta Neo4j mínimo: verificar firma → idempotencia → deserializar Parquet → MERGE entidades | Depende del paso anterior. Demuestra el extremo receptor. Con esto, el núcleo de ADR-0043 está funcional y el go/no-go es superable. |
| **DAY 157-160** | **D) ARM64 feature branch** | Si el hardware FEDER es ARM64 (Raspberry Pi, Jetson, etc.), un problema de compilación o endianness descubierto tarde puede ser catastrófico. Abrir `feature/adr029-variant-c-arm64` y compilar el pipeline C++20 en ARM64 **en paralelo** con los pasos anteriores si hay recursos humanos. Si no los hay, posponer hasta después del núcleo, pero antes del go/no-go. |
| **Post-go/no-go (Agosto)** | **B y C) Jenkins y Vault** | La infraestructura CI/CD y la gestión criptográfica son esenciales para producción, pero no condicionan la viabilidad técnica de la memoria episódica. Pueden madurar en agosto y septiembre. |

**Respuesta directa a la pregunta:** La secuencia es **A → (pasos 2-3-4 del roadmap ADR-0043) → D → B/C**. El descanso (E) debe insertarse como un día de consolidación después de cerrar el núcleo Parquet→Neo4j, por salud del equipo y para documentar.

**Dependencias críticas que cambiarían el orden:**
- Si el hardware FEDER *definitivo* es ARM64 y no hay versión x86 de respaldo, entonces D debe ejecutarse inmediatamente después de A, porque una incompatibilidad de compilación impediría el go/no-go. Recomiendo clarificar esto con el coordinador FEDER cuanto antes.
- Si los CSVs reales revelan un volumen de datos 10× mayor al estimado, la sesión de Parquet se alargará y puede absorber varios días adicionales. Conviene tener un plan de contención (filtrar agresivamente firewall-acl-agent).

---

Quedo atento a los resultados de la validación de CSVs. El schema Parquet que surja de esa sesión será la piedra angular sobre la que se edificará FEDER. Ánimo y precisión quirúrgica.