¡Perfecto! Aquí tienes la **versión pulida y operativa de ADR-028**, lista para revisión final del Consejo de Sabios. He mantenido el nivel de rigor de ADR-025 (invariantes duros, TDH, threat model tabular, contratos claros, tests obligatorios) mientras he mejorado:

- Claridad y precisión técnica (eliminando redundancias y ambigüedades).
- Consistencia con el proyecto (asimetría, hardware limitado, plugins no confiables, crypto ya existente).
- Fortaleza del threat model y mitigaciones, incorporando prácticas reales contra poisoning en RAG/FAISS (validación determinista fuerte, metadatos de provenance, deduplicación, rate limiting, auditabilidad).
- Estructura más limpia y accionable (contratos explícitos, invariantes numeradas con enforcement).
- Enfoque pragmático: prioriza protección de la memoria semántica sin bloquear el momentum actual (READ-ONLY en PHASE 2b).

---

# ADR-028: RAG Ingestion Trust Model (FAISS Integrity & Anti-Poisoning)

**Estado**: PROPUESTO — Pendiente aprobación Consejo de Sabios  
**Fecha**: 2026-04-06  
**Autor**: Alonso Isidoro Román  
**Rama**: `feature/plugin-crypto`  
**Componentes afectados**: rag-ingester, plugin-loader  
**ADR relacionados**:
- ADR-012 (Plugin Loader Architecture)
- ADR-023 (CryptoTransport)
- ADR-025 (Plugin Integrity Verification via Ed25519)
- ADR-026 (P2P Fleet Learning Architecture)
- ADR-027 (CTX_ETCD_TX/RX Symmetry)

---

## 1. Contexto y Motivación

El componente `rag-ingester` transforma eventos de red (flows, metadatos, narrativas) en embeddings y los persiste en FAISS, que actúa como **memoria semántica de largo plazo** del sistema.

A diferencia de componentes efímeros (sniffer, firewall-acl-agent, ml-detector), la ingestión RAG tiene una propiedad crítica:

> **Persistencia acumulativa del conocimiento.**

Cualquier contaminación (poisoning) no es efímera: se propaga a todas las consultas futuras del LLM (Track 2 de ADR-026) y puede causar sesgo acumulativo, prompt injection indirecto o corrupción semántica persistente.

Con la introducción de plugins (ADR-025), aunque sea en modo READ-ONLY, se abre un vector de influencia sobre qué eventos se aceptan o rechazan. Esto exige un **modelo formal de confianza** para proteger la integridad de FAISS.

---

## 2. Problema

Sin un trust model explícito, un plugin comprometido o evento malicioso podría:

- Permitir ingestión de datos envenenados que pasen filtros iniciales.
- Introducir patrones que sesguen el espacio vectorial o inyecten instrucciones sutiles.
- Contaminar la memoria de forma persistente, afectando explicaciones y razonamiento del LLM.

Una vez en FAISS no existe distinción entre datos confiables y contaminados, ni mecanismos sencillos de auditoría o rollback.

---

## 3. Decisión

Se establece el **RAG Ingestion Trust Model** con las siguientes decisiones obligatorias:

### D1 — Clasificación de confianza (Trust Level) obligatoria e inmutable

Todo evento recibe un `trust_level` interno (no modificable por plugins):

- `TRUST_INTERNAL` — Generado directamente por componentes validados del sistema.
- `TRUST_PIPELINE` — Proveniente del pipeline propio (default para eventos de sniffer/ml-detector).
- `TRUST_EXTERNAL` — Origen externo o desconocido (requiere validación estricta adicional).

Este campo forma parte del metadato interno y se firma/protege vía CryptoTransport donde aplique.

### D2 — Contrato estricto de plugins en rag-ingester: READ-ONLY + Decisión binaria

Los plugins **solo** pueden:
- Inspeccionar metadatos del `MessageContext` (src_ip, dst_ip, protocol, timestamps, etc.).
- Establecer `result_code` (0 = aceptar, ≠0 = rechazar) y `annotation`.

**Prohibiciones explícitas**:
- NO acceso al payload (se pasa `nullptr` / `payload_len=0`).
- NO modificación de ningún campo del contexto.
- NO generación de nuevos eventos ni transformación de datos.

Se formaliza en la API:

```cpp
enum class PluginMode { NORMAL, READONLY };

struct MessageContext {
    // ...
    PluginMode mode = PluginMode::READONLY;  // rag-ingester siempre usa READONLY
    // ...
};
```

### D3 — Separación estricta de fases (enforcement en código)

Pipeline obligatorio e inalterable:

```
Evento → Plugin (READ-ONLY) → Validation Layer (determinista) → (si PASS) FAISS ingest
```

El plugin **no puede** saltarse la validation layer.

### D4 — Validation Layer determinista (obligatoria y antes de FAISS)

Validaciones mínimas no-ML (rápidas, audibles y deterministas):

- Tamaño de campos dentro de límites.
- Coherencia sintáctica (IPs válidas, puertos, protocolos conocidos, timestamps razonables).
- Ratios y umbrales físicos plausibles (bytes/paquete, paquetes/segundo, etc.).
- Ausencia de patrones obvios de inyección o anomalías básicas.

Si falla → DROP + log `RAG_INGEST_REJECTED_SECURITY`.

### D5 — Invariantes duras de ingestión (fail-fast)

1. Ningún evento con `trust_level` bajo entra sin validación completa.
2. Ningún plugin puede modificar el contexto ni el payload.
3. Toda ingestión debe ser auditable (metadatos + logs estructurados).
4. Toda decisión de ingestión es reversible vía metadatos (rollback lógico por `event_id` o ventana temporal).

Violación de cualquier invariante en producción → `std::terminate()` (o abort con core dump).

### D6 — Metadatos obligatorios en cada embedding almacenado en FAISS

Cada entrada debe contener al menos:

- `event_id` (único y trazable)
- `timestamp` (UTC, con precisión)
- `source_component`
- `trust_level`
- `pipeline_version`
- `plugin_result_code`
- `schema_version`
- `ingest_hash` (CRC32 o SHA-256 del contenido original para deduplicación)

Estos metadatos permiten filtrado en retrieval, auditoría y rollback lógico.

### D7 — Protecciones baseline anti-poisoning

- **Deduplicación**: por hash de contenido + event_id (evita replays).
- **Rate limiting**: por subnet/origen (ej. máximo eventos por minuto configurable).
- **Límite temporal**: ventana deslizante de ingestión (evita floods).
- **Logging estructurado**: todo evento genera `RAG_INGEST_DECISION` con trust_level, resultado y motivo.

### D8 — Prohibición estricta de escritura por plugins (fase actual)

Plugins **NO** pueden generar eventos, modificar embeddings ni alterar metadatos.  
Cualquier capacidad de escritura futura requerirá:
- Nuevo ADR explícito (extensión de este).
- Capability granular + sandboxing reforzado.

### D9 — Observabilidad y auditabilidad

Todo decisión relevante produce log estructurado (JSON o spdlog con campos clave) para facilitar monitoreo y forense.

---

## 4. Threat Model

| Vector | Descripción | Mitigación principal |
|--------|-------------|----------------------|
| V1 — Plugin bias | Plugin permite eventos maliciosos | READ-ONLY + Validation Layer determinista |
| V2 — Data poisoning persistente | Eventos envenenados acumulados en FAISS | Validación + dedup + metadatos de trust + rate limiting |
| V3 — Prompt injection indirecto | Instrucciones sutiles via embeddings | Trust filtering en retrieval + sanitización básica |
| V4 — Semantic drift / ruido acumulativo | Degradación lenta del espacio vectorial | Metadatos + futuros TTL/scoring |
| V5 — Replay attacks | Reinyeción de eventos válidos | Deduplicación por hash |
| V6 — Plugin mutation | Intento de modificar contexto/payload | D8-light + CRC + invariantes + `std::terminate()` |

---

## 5. Límites del modelo (Out of Scope)

Este ADR **no protege contra**:
- Compromiso root o acceso físico al host.
- Manipulación directa del archivo FAISS en disco (requiere hardening del SO y backups firmados).
- Ataques a la supply chain del modelo de embeddings o librerías subyacentes.

Estos se abordan en hardening general del sistema y ADRs futuros de almacenamiento.

---

## 6. Alternativas consideradas y rechazadas

- **Permitir plugins write-capable en rag-ingester**: Rechazada — aumenta superficie de ataque masivamente y complica auditoría (incompatible con PHASE 2 actual).
- **Validación puramente ML**: Rechazada por ahora — no determinista, difícil de auditar y crea bootstrap problem.
- **Ingestión sin validation layer**: Rechazada — permite contaminación directa de FAISS.

---

## 7. Consecuencias

**Positivas**:
- Protege la memoria semántica como parte del TCB lógico.
- Mantiene plugins como código no confiable sin sacrificar utilidad en modo READ-ONLY.
- Facilita auditoría, rollback y futuro filtrado por trust_level en retrieval.
- Alineado con la filosofía de asimetría y determinismo del proyecto.

**Negativas / Trade-offs**:
- Ligero overhead en ingestión (validación determinista es barata).
- Posible rechazo de eventos borderline legítimos (mitigable con tuning conservador).
- Necesidad de mantener reglas de validación actualizadas con evolución del tráfico.

---

## 8. Tests obligatorios (Test-Driven Hardening)

- **TEST-RAG-POISON-1**: Evento malformado o con patrones sospechosos → debe ser rechazado por validation layer.
- **TEST-RAG-PLUGIN-MUTATION-2**: Plugin intenta modificar contexto (incluso vía const_cast) → D8-light violation + terminate.
- **TEST-RAG-REPLAY-3**: Evento duplicado (mismo hash) → deduplicado y logueado.
- **TEST-RAG-TRUST-4**: Evento `TRUST_EXTERNAL` sin pasar validación completa → reject.
- **TEST-RAG-INVARIANT-5**: Violación de invariante → fail-fast en producción.

Integrar en `make rag-integ-test` o suite equivalente.

---

## 9. Principio Rector

> **El sistema no solo debe ser seguro en lo que ejecuta, sino también en lo que aprende y recuerda.**

---

## 10. Conclusión

ADR-028 completa la capa de seguridad iniciada en ADR-025:

- ADR-025 protege la **ejecución** de código no confiable.
- ADR-028 protege la **integridad del conocimiento** persistente.

Una vez aprobado, se implementa inmediatamente después de cerrar PHASE 2b (o en paralelo con 2c si no bloquea). No es bloqueante para plugins READ-ONLY actuales.

---

**Estado recomendado tras revisión**: APROBADO con posibles ajustes menores.

---

### Sugerencias adicionales para el Consejo

Esta versión es **operativa**: se puede implementar directamente con bajo riesgo.

**Preguntas que recomiendo al Consejo responder**:
1. ¿Aprobamos tal cual o queremos ajustar algún invariante/threshold de validación?
2. ¿Añadimos ya un campo `ingest_signature` (Ed25519 ligera) en metadatos para futuro-proofing fuerte?
3. ¿El rate limiting por subnet debe ser configurable vía etcd desde el principio?

¿Quieres que prepare un diff con los cambios exactos respecto al borrador original, o que proponga snippets de código concretos (ej. la Validation Layer o el struct actualizado de MessageContext)?

El ADR ya está en un estado sólido y coherente con el rigor del proyecto. ¡Listo para el Consejo!