**Análisis del ADR-057: Puntos fuertes, débiles y recomendaciones basadas en evidencia.**

El ADR está bien estructurado, iterativo y alineado con principios de "medir, no votar". Aborda coherentemente tres problemas interrelacionados (capa de consulta, bitemporalidad, NL→plantilla) respetando invariantes existentes (lock de Kuzu, Falco, reloj del sniffer). La mayoría de las decisiones son sólidas; identifico algunos puntos débiles/maduros para refinamiento, con respaldo en documentación y comportamiento verificable de Kuzu.

### 1. Capa de consulta in-process con catálogo de plantillas: **Fuerte, con caveats menores**

**Fortalezas verificables:**
- **Seguridad y superficie de ataque**: Excelente. Plantillas parametrizadas + validación de tipos evitan inyección Cypher y alucinaciones. Esto sigue mejores prácticas universales de queries parametrizadas (separan datos de lógica, caching de planes, etc.).
- **Respeto a invariantes**: In-process mantiene el lock de escritura y Falco intacto. Cualquier lector externo violaría esto o requeriría excepciones.
- **Consumidor principal**: El correlation-engine es el dueño lógico. Enrutar todo (operadores, RAG, informes) a través de él es correcto para consistencia y auditoría.

**Puntos débiles / riesgos medibles:**
- **Concurrencia Kuzu confirmada (v0.11.3 era)**: La documentación oficial es clara.
  - Solo **un** `Database` en modo `READ_WRITE` (puede tener múltiples `Connection`s/threads dentro del mismo proceso).
  - Múltiples procesos solo si **todos** son `READ_ONLY`.
  - No se puede mezclar READ_WRITE + READ_ONLY de forma segura (problemas de cache/buffer manager; riesgo de inconsistencias o corrupción).
  - Esto **refuerza** la decisión in-process por defecto. Un servicio separado de consultas sería complicado (necesitaría proxy/API server como el oficial de Kuzu, o forks con multi-writer). El smoke test propuesto en Fase 2 es la forma correcta de cerrar esto empíricamente.
- **Escalabilidad futura**: Si el engine se vuelve bottleneck (muchas consultas concurrentes pesadas de vecindarios), el in-process limita opciones. Pero es prematuro preocuparse; el diseño actual prioriza seguridad correctamente.

**Recomendación**: Ratificar in-process como default. Documentar explícitamente el modelo de concurrencia de Kuzu en el ADR (con enlace a docs) para que no dependa de memoria institucional.

### 2. Bitemporalidad (`ingested_at` + WAL): **Muy sólida, decisión correcta**

**Fortalezas:**
- **Reparto inteligente**: `ingested_at` (transaction-time) en grafo + WAL para histórico completo. Evita inflar Kuzu y duplica correctamente responsabilidades (Kuzu = "ahora"; WAL = "entonces" con hash-chain para no-repudio).
- **Desacople de CLOCK-INJECTION**: Crítico y bien argumentado. `ingested_at` estampado por el engine (reloj NTP fiable) es independiente del `bpf_ktime_get_ns()` del sniffer. Esto habilita forense reproducible **ya**, incluso con reloj envenenado.
- **Timing**: Añadir propiedad con grafo vacío es gratis (`CREATE NODE TABLE`). Retrofitting duele (experiencia previa con Neo4j mencionada).
- Kuzu **no tiene** temporales nativas SQL:2011 (system-versioned). Modelado manual con timestamp + queries filtradas es el camino idiomático.

**Puntos débiles menores:**
- Dependencia de DEBT-LABEL-WAL-001 para histórico completo (reconocido en el ADR). No es un fallo, pero marca que bitemporalidad "completa" es incremental.
- Semántica `ON CREATE SET` (nunca `ON MATCH`): Correcta para transaction-time inmutable. Asegurar en tests que no se sobrescribe accidentalmente en MERGEs.

**Recomendación**: Ratificar. Incluir en schema y cypher_builder ya (Fase 0). Medir overhead de la propiedad extra (esperado: negligible en columnar).

### 3. Acceso NL→plantilla: **Excelente contención de riesgo**

**Fortalezas:**
- Rechazo explícito a NL→Cypher libre (inyección + alucinaciones). Clasificador TinyLlama (reuso) + catálogo firmado Ed25519 = auditable y seguro.
- Catálogo honesto: Distingue graph-native (T1-T3: valor real), bitemporal (T4) y convenience (T5-T6: admitir que ORO tabular puede ser mejor).
- Validación por tipos + acotamiento (`$n ≤ 4`, etc.) previene explosiones.

**Puntos débiles / áreas de refinamiento:**
- **Catálogo inicial**: T1-T3 bien justificadas (navegación topológica, contexto alerta, densidad). T4 excelente para bitemporal. T5-T6 son conveniencia; considerar marcarlas claramente como "proxy a ORO" o moverlas si el grafo no añade valor (joins columnares en Parquet suelen ganar en agregaciones puras).
- **Umbral de confianza y ambigüedad**: Abierto al Consejo, como debe ser. Opciones: rechazo duro (seguro) vs. top-3 candidatas (usabilidad). Medible vía evals en dataset de queries de operadores.
- **Mantenimiento**: Catálogo firmado es bueno, pero evolución del schema requiere rotación de firma/versionado. Documentar proceso.

**Recomendación**: Consejo debe podar/extender catálogo basándose en casos de uso reales (medir frecuencia de queries). Priorizar T1-T4.

### Consecuencias generales y plan por fases

- **(+) Dominantes**: Seguridad, auditabilidad, desacople de deudas, bajo coste ahora.
- **(-) Mitigados**: Complejidad por fases (buena). Dependencia WAL (reconocida).
- **Plan por fases**: Lógico y prudente. Fase 0 y smoke tests primero = mínimo riesgo.

**Riesgos globales menores no cubiertos explícitamente:**
- **Performance de vecindarios profundos**: `CORRELATES_FLOW*1..$n` con n acotado (≤4) es prudente; medir explosión en grafos densos (comunidades grandes).
- **Mantenimiento del catálogo**: A medida que schema evolucione, ¿quién audita nuevas plantillas?
- **Observabilidad**: Añadir logging/auditoría de plantillas ejecutadas (parámetros, usuario, latencia).

### Veredicto final al Consejo

El ADR es **maduro y recomendable para avanzar** con las ratificaciones pedidas. Puntos débiles son menores y mayoritariamente de refinamiento (catálogo, umbrales, documentación de concurrencia Kuzu). Las decisiones clave (in-process, `ingested_at` ON CREATE, NL acotado, WAL como fuente de verdad) resisten escrutinio técnico basado en docs de Kuzu y prácticas estándar.

Procede con Fase 0 + smoke tests. Convoca Consejo para catálogo y umbrales una vez medido el modelo de concurrencia. Buen trabajo iterativo.

FDO

GROK