Mi voto, como parte del Consejo:

**1. Versión de Arrow/Parquet — pin `18.1.0-1`, no `24.0.0-1`.**

No por conservadurismo per se, sino por el mismo criterio que ya aplicáis a Kuzu (`DEBT-KUZU-UPSTREAM-ARCHIVED-001`): preferís código con trayectoria probada frente a "lo más nuevo". Razones concretas:

- `24.0.0` es reciente — menos horas de vuelo en producción real, menos issues cerrados, más superficie de que un bug de release temprano os afecte en un componente que toca integridad de datos (el ledger inmutable).
- Arrow tiene cadencia de release muy alta (~1 versión mayor cada 1-2 meses, veis 24 versiones en el índice). Fijar la última de una release train con más rodaje (18.x, LTS de facto por antigüedad y uso) reduce el riesgo de deprecaciones sorpresa en la API C++ que uséis, sin perder funcionalidad — el subconjunto que necesitáis (`arrow::Table`, `parquet::arrow::WriteTable`) es estable desde hace muchas versiones mayores.
- Contraargumento real a considerar: versiones más nuevas pueden tener fixes de seguridad que 18.x no tiene backporteados (Arrow no mantiene branches LTS con backports de seguridad de forma tan disciplinada como Debian). Esto es lo único que me haría dudar — si el Consejo tiene datos de CVEs conocidos en 18.x sin parchear, cambio mi voto a una versión más reciente. No lo he verificado, así que lo marco como pendiente de comprobar antes de cerrar esto, no como descartado.

**2. Rango unsigned en cols 9-10 (puertos) — documentarlo en el `.avsc`, no abrir deuda nueva.**

Es una asimetría real pero acotada y ya medida: los puertos van 0-65535, caben en `int32` de sobra (rango hasta 2^31-1), y el propio ADR-058 ya dejó este patrón resuelto para `flow_start_sec`/`flow_start_nano` (signed en bronce, documentado como riesgo semántico P2, no bloqueante — `DEBT-PARSE-VERIFY-SENTINEL-001`). Añadir un campo `doc` en la definición Avro del esquema (`"doc": "uint32_t en origen (network_security.proto); rango real 0-65535, no requiere manejo especial"`) dentro del propio `.avsc` es la solución de coste mínimo y es auto-documentada donde hace falta — en el contrato mismo, no en un documento aparte que alguien puede no leer. Abrir una deuda nueva para esto sería sobre-ingeniería para un riesgo que ya está acotado por el dominio de valores.

**3. ¿ADR numerado o documento de apoyo?**

Documento de apoyo, no ADR propio — al menos por ahora. Motivo: un ADR documenta una **decisión con alternativas reales sobre la mesa** (igual que dijisteis del slow-joiner ZMQ en DAY 156, que quedó como nota técnica y no ADR). Aquí no hay alternativa de arquitectura en disputa — el esquema, la partición y el lenguaje son consecuencia directa y casi mecánica de decisiones ya ratificadas en ADR-058 (Flujo A greenfield, predicado §3.1, clases D/E). Es una especificación de implementación de una decisión ya tomada, no una decisión nueva. Si en el futuro aparece una razón de peso para reabrir (p.ej. Arrow resulta no viable y hay que rediseñar), en ese momento sí justifica ADR propio con su changelog de alternativas. Mantenerlo como documento de apoyo referenciado desde ADR-058 también evita el riesgo de colisión de numeración que ya os mordió en DAY 175/199.

¿Qué dijo el resto del Consejo en estos tres puntos? Si hay divergencia fuerte en el punto 1 (versión), es el único donde cambiaría de postura con datos concretos de CVEs.

FDO 
CLAUDE