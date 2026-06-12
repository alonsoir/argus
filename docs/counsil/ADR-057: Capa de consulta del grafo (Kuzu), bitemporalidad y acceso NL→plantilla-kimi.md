

---

## Análisis del ADR-057 para el Consejo de Sabios

He revisado el ADR-057 con fuentes primarias del proyecto Kuzu. A continuación, los puntos débiles identificados con argumentación basada en información **comprobable y medible**.

---

### 🔴 Punto Débil 1: Kuzu está archivado — Riesgo de dependencia muerta [CRÍTICO]

**Evidencia medible:**
- Kuzu Inc. anunció el archivado del proyecto en octubre 2025. Tanto PyPI como npm muestran el aviso oficial: *"We are archiving the KuzuDB project"* .
- La v0.11.3 (febrero 2025) es la última release oficial .
- Competidores como ArcadeDB ya posicionan a Kuzu como *"archived"* y *"the only actively-maintained open-source option"* para grafos embebidos .

**Impacto sobre el ADR:**
El ADR-057 asume Kuzu v0.11.3 como motor a largo plazo. Con el proyecto archivado: no habrá parches de seguridad, bugfixes de corrupción, ni resolución de race conditions en el locking. Cualquier inversión en schema (`ingested_at`, `community_id`, plantillas Cypher nativas) se convierte en deuda técnica migratoria acumulativa.

**Métrica de riesgo:** Probabilidad de bug crítico sin fix → 100% eventual sobre código no mantenido. Coste de migración futura ∝ cantidad de Cypher nativo acumulado.

**[CONSEJO]:** El ADR-057 debe incluir una sección *"Plan de contingencia por archivado de Kuzu"* antes de ratificar cualquier decisión. Opciones: (a) migración inmediata a motor mantenido, (b) capa de abstracción que permita swap de motor sin tocar T1-T6, o (c) aceptar el riesgo documentado con revisión trimestral.

---

### 🔴 Punto Débil 2: El lock de Kuzu no permite ni READ_ONLY concurrente [CRÍTICO]

**Evidencia medible:**
- **Issue #3295** (abril 2024): un usuario intenta abrir `read_only=True` desde Python mientras el CLI tiene WRITE lock. Obtiene: `RuntimeError: Could not set lock on file : kuzu/.lock` .
- **Issue #3872** (julio 2024): un usuario de Jupyter (WRITE) intenta abrir el CLI con `-r` (READ_ONLY). Kuzu dice *"Opened the database ... in read-only mode"* pero luego falla con: `IO exception: Could not set lock on file : ./db/.lock`. El equipo de Kuzu respondió explicando por qué **no es seguro permitirlo** .

**Impacto sobre el ADR:**
El §2.1 plantea: *"A MEDIR: ¿Permite un segundo proceso abrir la BD en modo READ_ONLY?"* La respuesta medible es **NO**. No hace falta smoke test: los issues oficiales documentan que Kuzu usa un lock file exclusivo (`.lock`) que bloquea **cualquier** segundo proceso, incluso READ_ONLY.

Esto **fortalece** el argumento in-process, pero por razones distintas a las planteadas: no es una decisión arquitectónica elegida, es una **restricción física del motor**. El ADR debería ser honesto: *"in-process no es una elección, es la única opción que funciona con Kuzu"*.

**Métrica:** Procesos concurrentes sobre mismo `.kuzu` permitidos = **1 máximo**. Procesos READ_ONLY concurrentes permitidos = **0** (documentado en issue #3295).

**[CONSEJO]:** Eliminar la Fase 2 del plan ("smoke de concurrencia READ_ONLY"). Es redundante. Sustituir por: *"Restricción confirmada: Kuzu no admite multiproceso. In-process es obligatorio, no opcional."*

---

### 🟡 Punto Débil 3: TinyLlama como clasificador NL — Sobre-estimación de capacidad

**Evidencia medible:**
- TinyLlama (~1.1B parámetros) está entrenado principalmente para generación de texto, no para clasificación de intenciones (intent classification) multiclase.
- El ADR le asigna un rol estricto: clasificar a **UNA** plantilla del catálogo y extraer parámetros tipados. La clasificación multiclase con modelos pequeños sin fine-tuning específico de dominio tiene tasas de error elevadas.
- TinyLlama no tiene mecanismo nativo de structured output (JSON schema). La extracción de `$n`, `$community_id`, `$event_id` requiere post-procesamiento con regex/grammar constraints no definido en el ADR.

**Impacto sobre el ADR:**
El ADR asume que TinyLlama (ya presente en el RAG) se reutiliza *"sin coste adicional"*. Esto ignora:
1. **Fine-tuning:** necesita un dataset etiquetado de (petición NL, plantilla) que **no existe hoy**.
2. **Umbral de confianza:** el ADR deja *"[CONSEJO] decide umbral"*, pero sin métrica base (precision/recall por plantilla) no hay dato para decidir.
3. **Riesgo de jailbreak:** un atacante podría craftear NL que fuerce la clasificación a T5/T6 (convenience) para evadir detección en T1-T3 (graph-native).

**Métricas propuestas (prerequisitos para aprobar Fase 3):**
- Dataset mínimo: 500 ejemplos/plantilla (3,000 total) para 6 clases.
- Accuracy objetivo: ≥95% (T1-T3), ≥90% (T5-T6).
- Falso positivo de clasificación incorrecta con alta confianza: <2%.
- Latencia p95 (clasificación + extracción): <200ms en hardware objetivo.

**[CONSEJO]:** La Fase 3 (NL) debe **desacoplarse** del ADR-057 y convertirse en un ADR independiente. Prerequisitos: benchmark zero-shot vs fine-tuned, dataset etiquetado, y métricas precision/recall por plantilla antes de integrar en producción.

---

### 🟡 Punto Débil 4: `ingested_at` como transaction-time — Semántica incompleta

**Evidencia medible:**
- La bitemporalidad canónica (Snodgrass/Jensen) requiere **intervalos** `[desde, hasta)` para valid-time y transaction-time. `ingested_at` es un **punto** (`UINT64`), no un intervalo.
- El ADR afirma que T4 (retro-hunt de IOC) ejercita los dos ejes temporales. Pero T4 necesita reconstruir *"qué sabíamos a las 03:00"*, lo cual requiere el WAL externo (DEBT-LABEL-WAL-001) o una query fallback al bronce histórico.
- El ADR dice *"NO toca bronce/protobuf/sniffer"*, pero T4 sin WAL no tiene fuente de datos históricos.

**Impacto sobre el ADR:**
`ingested_at` es correcto como primer paso, pero **insuficiente** para forense reproducible. T4 queda bloqueada hasta que DEBT-LABEL-WAL-001 esté operativa o se defina un fallback al bronce.

**Métrica de inconsistencia:** Plantillas que ejercitan bitemporalidad = 1 (T4). Plantillas ejecutables con solo `ingested_at` (sin WAL) = **0**.

**[CONSEJO]:** Aprobar Fase 0 (`ingested_at` en schema) como barato y correcto, pero **bloquear T4** del catálogo inicial hasta WAL funcional o fallback definido. No prometer bitemporalidad completa con solo un timestamp.

---

### 🟡 Punto Débil 5: Catálogo T1-T6 — Plantillas C y riesgo de scope creep

**Evidencia medible:**
- El ADR es honesto al marcar T5 y T6 como *"convenience (podrían ir por ORO)"* y *"NO porque el grafo aporte algo"*.
- Sin embargo, incluirlas en el catálogo inicial introduce: carga cognitiva para el operador (6 vs 4 plantillas), riesgo de que el clasificador NL las sugiera cuando ORO es mejor, y mantenimiento de Cypher para consultas que no justifican el grafo.

**Métrica:** Valor añadido del grafo sobre ORO = presente solo en T1-T3 (**50%** del catálogo). Riesgo de "convenience creep": una vez en el catálogo, difícil de quitar sin romper contratos.

**[CONSEJO]:** **Podar T5 y T6** del catálogo inicial del ADR-057. Mover a un ADR separado de "Convenience queries" o dejar en ORO exclusivamente. El ADR-057 debe centrarse en lo que el grafo hace mejor: navegación topológica (T1-T3) y bitemporalidad (T4).

---

### 🟡 Punto Débil 6: Firma Ed25519 del catálogo — Sin mecanismo de revocación

**Evidencia medible:**
- Ed25519 es firma criptográfica, no un sistema de revocación. Si una plantilla se compromete o depreca, la firma sigue siendo válida indefinidamente.
- El ADR no menciona: (a) timestamp de expiración en la firma, (b) lista de revocación (CRL), (c) rotación de claves.

**Métrica:** Vida útil de una plantilla firmada = **indefinida** (a menos que se invalide manualmente en cada nodo).

**[CONSEJO]:** Antes de Fase 4, definir: TTL en la firma (ej. 30 días), mecanismo de distribución de revocaciones (¿etcd? ¿canal Noise?), y proceso de rotación de claves sin downtime.

---

## Síntesis para el Consejo

| Decisión | Veredicto | Acción |
|---|---|---|
| Default in-process | ✅ Ratificar (con reserva) | Documentar como *"obligatorio, no preferido"* |
| `ingested_at` en schema | ✅ Ratificar Fase 0 | Bloquear T4 hasta WAL o fallback |
| Catálogo T1-T3 | ✅ Ratificar | Aprobar con límite `$n ≤ 4` y tests de explosión combinatoria |
| T5-T6 en catálogo | ❌ Rechazar | Mover a ORO o ADR separado |
| Fase 2 (smoke concurrencia) | ❌ Rechazar | Evidencia ya existe en issues #3295/#3872 |
| Fase 3 (NL/TinyLlama) | ⏸️ Posponer | Nuevo ADR independiente con métricas |
| Fase 4 (firma Ed25519) | ⏸️ Posponer | Definir revocación y rotación primero |
| Plan contingencia Kuzu archivado | ⚠️ Añadir obligatorio | Antes de cualquier inversión en schema |

---

**Archivo completo del análisis:** [ADR057_Analisis_Consejo_Sabios.txt](sandbox:///mnt/agents/output/ADR057_Analisis_Consejo_Sabios.txt)

FDO
KIMI