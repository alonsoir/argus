## DeepSeek — Respuesta a PRE-ADR-026 (Arquitectura P2P para Distribución de Modelos)

Gracias por compartir este borrador. La claridad conceptual —especialmente la distinción entre LLM para explicabilidad y RF para detección, y la asimetría nodo/servidor— es un acierto. El planteamiento es sólido y realista para el horizonte de 1-3 años.

A continuación, mis respuestas a las 7 preguntas abiertas, con criterio técnico y pensando en el dominio objetivo (hospitales, escuelas).

---

### 1. Versionado del schema CSV (DEBT-PROTO-002) – ¿bloqueante?

**Sí, es bloqueante duro.** Sin un schema versionado explícito, cualquier cambio en las features (nuevas columnas, tipos, semántica) corrompe el histórico de telemetría acumulado. Los RF specialists entrenados con una versión no podrán consumir datos de otra.

**Recomendación:**
- Adoptar un formato tipo **Parquet con schema embebido** (en lugar de CSV) o un **CSV con cabecera fija + campo `version` en el nombre del fichero**.
- Implementar un validador de schema en el servidor central que rechace telemetría con versión incompatible.
- Documentar la política de evolución: solo añadir columnas al final, nunca eliminar ni cambiar tipo.

**Prioridad:** Alta. Debe hacerse antes de desplegar el segundo nodo.

---

### 2. Protocolo de telemetría nodo→servidor

**Recomendación:** **ZeroMQ con CurveZMQ** (ya en stack) para producción; gRPC como alternativa futura si se necesita streaming bidireccional.

**Razonamiento:**
- ZeroMQ ya está integrado, es ligero y funciona bien en hardware limitado.
- CurveZMQ proporciona autenticación y cifrado (complementario al cifrado de payload).
- El overhead es bajo: un `PUSH/PULL` socket con mensajes comprimidos (LZ4) y firmados (Ed25519) es suficiente.

**Contra gRPC:** gRPC añade dependencias pesadas (HTTP/2, protobuf sobre HTTP) y mayor latencia. No lo justifica el volumen de telemetría (KB por nodo al día).

**Contra HTTPS simple:** Requiere gestión de certificados TLS y no está integrado con el pipeline actual.

**Decisión:** Mantener ZeroMQ. Documentar como estándar para telemetría en ADR futuro.

---

### 3. Threshold de validación de plugins

**Recomendación:** **No un solo threshold, sino un conjunto de criterios por tipo de ataque.**

Propuesta mínima:

| Métrica | Umbral | Condición |
|---------|--------|-----------|
| F1 | > 0.95 | Obligatorio |
| Precisión | > 0.90 | Obligatorio |
| Recall | > 0.95 | Obligatorio |
| FPR | < 0.001 (0.1%) | Obligatorio |
| Tamaño modelo | < 50 MB | Obligatorio (hardware limitado) |
| Latencia inferencia | < 100 ms en CPU N100 | Obligatorio |
| Evaluación en dataset de retención | > 0.90 F1 | Obligatorio (evita overfitting) |

**Además:**
- Validación en **datos reales de al menos 2 nodos** (no solo datos sintéticos).
- Umbrales por familia: WannaCry puede tolerar FPR ligeramente superior (0.5%) porque el bloqueo es agresivo; tráfico benigno no.

**Mecanismo de rollback:** El servidor debe retener la última versión válida del plugin y poder reinstalarla en la flota si la nueva degrada (monitorización de F1 en campo). Ver pregunta 7.

---

### 4. Privacidad de telemetría (LOPD / GDPR)

**Recomendación:** **Anonimización por hash salado + seudonimización, pero no suficiente; se necesita análisis legal formal antes de recoger telemetría real de hospitales.**

**Pasos concretos:**
1. **Hash salado de IPs** (con sal por nodo) – permite correlación intra-nodo pero no entre nodos ni reidentificación directa.
2. **Agregación temporal** – enviar estadísticas por ventana (ej. cada 10 min) en lugar de flows individuales.
3. **Exclusión de campos sensibles** – payloads, URLs, dominios DNS (si se capturan).
4. **Consentimiento informado** – si los datos se usan para investigación (mejora del modelo), debe haber un proceso de opt-in institucional.

**Acción inmediata:** Consultar con un experto en cumplimiento LOPD/GDPR. El proyecto puede operar con datos sintéticos hasta tener ese análisis. Documentar en el ADR que la telemetría real requiere aprobación institucional.

---

### 5. FT-Transformer vs XGBoost para detección tabular avanzada

**Recomendación:** **XGBoost primero, FT-Transformer solo si hay evidencia empírica de mejora sustancial en datos reales.**

**Razonamiento:**
- XGBoost es maduro, interpretable, rápido en CPU, y tiene soporte para datos tabulares con missing values (sentinel -9999.0f).
- FT-Transformer requiere GPU para entrenamiento (aunque inferencia puede ser CPU, es más pesada).
- En benchmarks (Gorishniy et al., 2021), FT-Transformer supera a XGBoost en algunos datasets tabulares, pero la diferencia suele ser < 2% en AUC. Para NIDS, el coste de implementación y mantenimiento no lo justifica en hardware limitado.

**Decisión:** Usar XGBoost como base para el Track 2 (detección avanzada). FT-Transformer se evaluará como experimento académico si se dispone de GPU en el servidor central.

---

### 6. Modelo base para vLLM (explicabilidad)

**Recomendación:** **Phi-3 Mini (3.8B) con QLoRA 4-bit.**

| Criterio | Phi-3 Mini | Mistral 7B | Llama 3.1 8B |
|----------|------------|------------|---------------|
| Memoria (inferencia) | ~2.5 GB | ~4.5 GB | ~5.5 GB |
| Razonamiento estructurado | Bueno | Muy bueno | Excelente |
| Licencia | MIT | Apache 2.0 | Llama 3 Community |
| Fine-tuning en español | Limitado | Limitado | Limitado |

**Por qué Phi-3:**
- Suficientemente pequeño para correr en un servidor modesto (16 GB RAM, sin GPU).
- Razonamiento competente para tareas de explicabilidad (generar texto a partir de contexto estructurado).
- El coste de fine-tuning con QLoRA es bajo (puede hacerse en una instancia T4 de Colab).

**Plan:** Empezar con Phi-3 Mini cuantizado (4-bit). Si se necesita mejor razonamiento, migrar a Mistral 7B. Llama 3.1 8B es overkill para este dominio.

---

### 7. Ciclo de vida de plugins (rollback ante drift)

**Recomendación:** **Mecanismo de versionado + monitorización de rendimiento en campo + rollback automático por consenso de la flota.**

**Propuesta concreta:**
- Cada plugin tiene un número de versión (semver) y un hash del modelo.
- Los nodos reportan periódicamente al servidor: `(plugin_id, version, num_invocations, num_errors, avg_confidence)`.
- El servidor calcula una **métrica de salud** (ej. tasa de alertas por día vs baseline). Si la salud cae por debajo de un umbral durante 3 periodos consecutivos:
    - Marca el plugin como "sospechoso".
    - Envía un comando de rollback a la flota (revertir a la versión anterior).
    - Notifica al administrador.

**Para rollback en la flota:** Los nodos deben conservar al menos la versión anterior del plugin en disco (o tener acceso a un repositorio local). El servidor puede distribuir el plugin anterior como un nuevo plugin (versión `-1`).

**Precaución:** El rollback automático debe ser configurable (puede desactivarse en entornos sensibles). También debe haber un mecanismo de "pin" para versiones estables.

---

### Comentarios adicionales sobre la arquitectura

- **BitTorrent para distribución de plugins:** Elegante y resiliente. Pero ten en cuenta que los hospitales suelen tener firelines restrictivos (puertos de BT cerrados). Alternativa: servir los plugins vía HTTPS desde el servidor central y usar BT solo internamente en la flota si la red lo permite.
- **Asimetría nodo/servidor:** Es la premisa correcta. Sin embargo, considera que algunos nodos (ej. hospitales grandes) podrían tener capacidad para ser "nodos agregadores" regionales, formando una jerarquía. Eso podría reducir la carga del servidor central.
- **Ciclo de vida de features:** Añade un campo `required_features` en el plugin. Si un nodo tiene un schema de features incompatible, no debe cargar el plugin.

---

### Resumen de respuestas para el Consejo

| # | Pregunta | Respuesta resumida |
|---|----------|-------------------|
| 1 | Versionado CSV | Bloqueante. Usar Parquet o CSV con versionado explícito. |
| 2 | Protocolo telemetría | ZeroMQ + CurveZMQ. No gRPC. |
| 3 | Threshold validación | Múltiples criterios (F1>0.95, FPR<0.001, etc.) y validación en datos reales. |
| 4 | Privacidad | Anonimización + hash salado, pero necesario análisis LOPD antes de producción. |
| 5 | FT-Transformer vs XGBoost | XGBoost primero. FT-Transformer solo si hay evidencia empírica de mejora. |
| 6 | LLM para explicabilidad | Phi-3 Mini (3.8B) con QLoRA. |
| 7 | Rollback por drift | Versiones, monitorización de salud, rollback automático opcional. |

---

### Conclusión

El PRE-ADR-026 es un documento de visión bien fundamentado. Las decisiones más inmediatas (1, 2, 3, 5) son factibles en el horizonte de 1 año. Las otras requieren más experimentación. Recomiendo convertir las respuestas del Consejo en un ADR formal (ADR-026) que sirva como hoja de ruta, con hitos claros.

El trabajo actual debe seguir enfocado en ADR-025 (plugin integrity) y en estabilizar el pipeline. Este PRE-ADR no debe distraer de esos objetivos inmediatos.

— DeepSeek, miembro del Consejo de Sabios