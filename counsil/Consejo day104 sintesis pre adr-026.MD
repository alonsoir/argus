# CONSEJO DE SABIOS — SÍNTESIS DE DELIBERACIÓN
## PRE-ADR-026: Arquitectura P2P, Distribución de Modelos y Aprendizaje de Flota

**Sesión**: DAY 104  
**Documentos base**: PRE-ADR-026 v2  
**Miembros que respondieron**: ChatGPT (OpenAI), DeepSeek, Gemini (Google), Grok (xAI), Qwen*  
**Árbitro**: Alonso Isidoro Román  
**Fecha de síntesis**: 2026-04-05

> ⚠️ **Nota de identidad**: El fichero `respuesta_qwen.md` comienza declarando explícitamente *"Soy DeepSeek — modelo de DeepSeek Research"*. **Patrón consolidado** (ya observado en DAY 103–105). Se registra la respuesta como segunda instancia de DeepSeek. Falta respuesta de Parallel.ai.

---

## 1. MAPA DE CONVERGENCIAS Y DIVERGENCIAS

### Q1 — Versionado schema CSV (DEBT-PROTO-002)

| Miembro | Veredicto | Argumento clave |
|---------|-----------|-----------------|
| ChatGPT | ✅ Bloqueante duro | Sin esto: no reentrenamiento consistente, no reproducibilidad, no valor científico |
| DeepSeek | ✅ Bloqueante duro | Parquet con schema embebido o CSV+campo version; validador en servidor |
| Gemini | ✅ Bloqueante crítico | Propone Protobuf/FlatBuffers generando código C++ y Python automáticamente |
| Grok | ✅ Bloqueante duro | JSON Schema o Avro + semver + compatibilidad hacia atrás |
| DeepSeek² | ✅ Bloqueante duro | Propone `CsvSchemaVersion` proto con major/minor/git_commit |

**🏛️ VEREDICTO UNÁNIME**: DEBT-PROTO-002 es bloqueante duro. Debe implementarse antes del segundo nodo activo.

**Divergencia técnica menor**: Gemini propone Protobuf/FlatBuffers (abandono de CSV). DeepSeek y Grok proponen versionado dentro del CSV actual. ChatGPT propone campos inline (schema_version, feature_set_id). Para el árbitro: la propuesta de Gemini es la más robusta a largo plazo pero rompe compatibilidad con el stack actual. Decisión de implementación queda pendiente.

---

### Q2 — Protocolo de telemetría nodo→servidor

| Miembro | Recomendación | Argumento |
|---------|---------------|-----------|
| ChatGPT | ✅ HTTPS + LZ4/zstd | Menos moving parts > más rendimiento; auditable; batch |
| DeepSeek | ✅ ZeroMQ + CurveZMQ | Ya en stack; overhead mínimo; CurveZMQ para auth/cifrado |
| Gemini | ✅ ZeroMQ PUSH/PULL sobre TLS/Noise | Ya validado; propone "Telemetry Gateway" en servidor |
| Grok | ✅ HTTPS mTLS + zstd + Ed25519 por lote | Más operable con NAT/firewalls de hospitales |
| DeepSeek² | ✅ ZeroMQ PUB/SUB | Ya cifrado vía ADR-023; no añadir TLS doble |

**🏛️ VEREDICTO DIVIDIDO (3 vs 2)**:
- **ZeroMQ**: DeepSeek, DeepSeek², Gemini → argumento técnico (ya en stack, overhead mínimo, ADR-023 ya cifra)
- **HTTPS**: ChatGPT, Grok → argumento operacional (NAT/firewalls hospitalarios, auditoría)

**Insight crítico de Grok** (el más importante): los hospitales tienen firewalls restrictivos. Los puertos ZeroMQ pueden estar cerrados. HTTPS:443 siempre está abierto. Este argumento operacional es potencialmente decisivo.

**Para el árbitro**: ZeroMQ es superior técnicamente si controlas la red. HTTPS es más robusto si no la controlas. En hospitales, probablemente no controlas. La decisión puede ser contextual: ZeroMQ para LAN interna, HTTPS para WAN.

---

### Q3 — Thresholds de validación de plugins

| Miembro | F1 mínimo | FPR máximo | Adicionales |
|---------|-----------|------------|-------------|
| ChatGPT | > 0.95 | < 0.01 | Canary deployment obligatorio; multi-dataset; OOD |
| DeepSeek | > 0.95 | < 0.001 | Latencia <100ms CPU N100; tamaño <50MB; 2 nodos reales |
| Gemini | N/A | FP≈0 | **Precision > 0.999** como métrica primaria (hospitales) |
| Grok | ≥ 0.95 | ≤ 0.001 | Canary; adversarial examples; 3 seeds; CTU-13 + tráfico benigno flota |
| DeepSeek² | ≥ 0.985 | ≤ 0.01% | Latencia ≤5μs/flow en RPi4; concept drift test; adversarial robustness |

**🏛️ VEREDICTO CON MATIZ IMPORTANTE**:

Gemini introduce un argumento que el resto no había planteado explícitamente: **en hospitales, un FP que bloquea acceso a base de datos de anestesia es más catastrófico que un FN**. Esto invierte la priorización habitual de NDR y justifica su posición de Precision primero.

**Consenso mínimo no negociable**:
- F1 ≥ 0.95 (todos)
- FPR ≤ 0.001 (mayoría)
- Canary deployment antes de distribución global (ChatGPT, Grok)
- Evaluación en datos reales de al menos 2 nodos (DeepSeek)
- Latencia: ≤100ms en CPU N100 como referencia de hardware

**Para el árbitro**: La propuesta de Gemini (Precision primaria) merece un análisis propio. El costo de FP en hospitales es asimétrico respecto a redes corporativas. Considerar añadir Precision > 0.99 como gate adicional para despliegues en entorno médico.

---

### Q4 — Privacidad LOPD/GDPR (datos hospitalarios)

| Miembro | ¿Hash salado suficiente? | Acción requerida |
|---------|--------------------------|------------------|
| ChatGPT | ❌ No | Hash salado rotatorio + truncado IP /24 o /16 + análisis legal LOPD |
| DeepSeek | ❌ No | Hash + agregación temporal + consentimiento opt-in institucional |
| Gemini | ❌ No | **Anonimización irreversible en origen** + descarte de payloads |
| Grok | ❌ No | DPIA obligatoria + differential privacy (ruido Laplace) + consentimiento |
| DeepSeek² | ❌ No | Bucket /24 + SHA-3 + ventana 5min + ISO 27001 para servidor central |

**🏛️ VEREDICTO UNÁNIME**: Hash salado solo NO es suficiente. Bloqueante antes de cualquier producción con datos hospitalarios reales.

**Punto más fuerte (Grok)**: Los flujos de red en hospitales pueden contener indirectamente datos de salud bajo GDPR Art. 9 si permiten inferir actividad clínica. Esto los eleva a categoría especial con requisitos más estrictos.

**Acciones consensuadas**:
1. Anonimización en el nodo antes del envío (no en tránsito ni en servidor)
2. DPIA (Data Protection Impact Assessment) formal antes de piloto real
3. Acuerdo legal explícito con cada institución
4. Considerar ISO 27001 para el servidor central (DeepSeek²)

---

### Q5 — FT-Transformer vs XGBoost

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT | XGBoost. FT-Transformer en datasets pequeños/ruidosos pierde. |
| DeepSeek | XGBoost. FT-Transformer solo si evidencia empírica de mejora. |
| Gemini | XGBoost/LightGBM. FT-Transformer: GPU necesaria para inferencia eficiente. |
| Grok | XGBoost/LightGBM/CatBoost. Benchmarks CICIDS, UNSW-NB15, KDD: trees dominan. |
| DeepSeek² | XGBoost. Latencia FT-T es 15–20x mayor en benchmarks de NIDS (tabla incluida). |

**🏛️ VEREDICTO UNÁNIME**: XGBoost para Track 1 y Track 2. FT-Transformer únicamente como experimento académico con GPU disponible en servidor central, si se demuestra ganancia >3% F1.

**Dato más valioso (DeepSeek²)**: tabla de benchmarks en datasets NIDS reales:
- CTU-13: XGBoost F1=0.992 / FT-T F1=0.989, latencia 0.8μs vs 12.3μs
- CIC-IDS2017: XGBoost F1=0.978 / FT-T F1=0.975, latencia 1.2μs vs 18.7μs
- UNSW-NB15: XGBoost F1=0.965 / FT-T F1=0.961, latencia 0.9μs vs 15.4μs

XGBoost domina en F1 Y en latencia. La discusión está cerrada para el horizonte actual.

---

### Q6 — Modelo base para vLLM server

| Miembro | Recomendación | Argumento |
|---------|---------------|-----------|
| ChatGPT | Mistral 7B | Mejor razonamiento estructurado; comunidad madura; vLLM |
| DeepSeek | Phi-3 Mini | Sin GPU viable; razonamiento suficiente; QLoRA barato |
| Gemini | Phi-3 Mini / Mistral 7B | Phi-3 primero por licencia MIT; outputs JSON/Markdown |
| Grok | Phi-3 Mini / Phi-4-mini | Velocidad de iteración; competitivo con 7B en benchmarks |
| DeepSeek² | Mistral 7B | Apache 2.0; razonamiento estructurado superior; español suficiente |

**🏛️ VEREDICTO DIVIDIDO**:
- **Phi-3 Mini**: DeepSeek, Gemini, Grok → argumento hardware (sin GPU, 2.5GB)
- **Mistral 7B**: ChatGPT, DeepSeek² → argumento calidad (razonamiento estructurado, español)

**Para el árbitro**: La diferencia real es el hardware del servidor central. Phi-3 si el servidor es modesto (CPU only, 8-16GB RAM). Mistral 7B si hay GPU discreta (T4 o similar). La arquitectura de Track 2 es lo que debe dictar el modelo, no al revés. Decisión diferida hasta tener claro el hardware del servidor central.

---

### Q7 — Ciclo de vida de plugins y rollback

| Miembro | Mecanismo propuesto |
|---------|---------------------|
| ChatGPT | Semver + canary 5-10% + TTL automático + rollback por FPR↑ |
| DeepSeek | Semver + health metrics periódicas + rollback si salud < threshold 3 periodos + pin de versiones |
| Gemini | Shadow Directory N-1 en plugin-loader + rollback remoto vía deployment.yml |
| Grok | Manifest firmado + N versiones por tipo + deprecation list vía BT + rollback local si FPR alto |
| DeepSeek² | 3 versiones en nodo + comando ROLLBACK firmado Ed25519 + BT redistribuye v_anterior |

**🏛️ VEREDICTO UNÁNIME**: Rollback obligatorio desde el diseño inicial. No es opcional.

**Propuesta más elegante (Gemini)**: integrar el rollback en `deployment.yml` como SSOT, consistente con ADR-021. El plugin-loader mantiene Shadow Directory con versión N-1. Rollback es un cambio en el SSOT, no un comando especial.

**Consenso técnico**:
- Versionado semver firmado Ed25519 (todos)
- Nodo retiene mínimo versión anterior (N-1) en disco
- Rollback activable remotamente desde servidor
- Métricas de salud reportadas periódicamente al servidor
- Canary deployment antes de distribución global

---

## 2. DECISIONES DEL ÁRBITRO

### ✅ APROBADO SIN CONDICIONES
1. **Asimetría nodo/servidor** como Principio Arquitectónico Inamovible (unánime)
2. **XGBoost** para detección tabular, Track 1 y Track 2 (unánime)
3. **DEBT-PROTO-002** (versionado schema CSV) = bloqueante duro (unánime)
4. **Federated Learning clásico** = POSPONER indefinidamente para estos nodos (unánime)
5. **BitTorrent** solo para distribución de plugins, no telemetría (unánime)
6. **Rollback** obligatorio desde diseño inicial (unánime)
7. **Hash salado solo** = insuficiente; DPIA + anonimización en origen requerida (unánime)

### ⚠️ APROBADO CON CONDICIÓN
8. **Protocolo telemetría**: HTTPS:443 como default para interoperabilidad con firewalls hospitalarios. ZeroMQ opcional para despliegues LAN controlados. La decisión final depende del perfil de red de cada nodo. Documentar como configuración, no como estándar único.

9. **Thresholds de validación**: Base F1≥0.95 / FPR≤0.001 para todos los entornos. Para entornos médicos añadir gate adicional: **Precision≥0.99** (argumento Gemini aprobado).

### 🔄 DIFERIDO
10. **Modelo vLLM** (Phi-3 vs Mistral): diferido hasta definir hardware del servidor central. Criterio: si CPU-only → Phi-3 Mini; si GPU disponible → Mistral 7B.

---

## 3. NUEVOS ÍTEMS SURGIDOS DEL CONSEJO (no estaban en el PRE-ADR)

Estos ítems emergieron de las respuestas y no estaban contemplados en v2:

| Ítem | Origen | Prioridad |
|------|--------|-----------|
| **ADR-026b: Model Lifecycle & Telemetry Governance** | ChatGPT | Alta — el ciclo de vida de modelos es el núcleo real |
| **ISO 27001** para servidor central antes de hospitales reales | DeepSeek² | Media — prerequisito regulatorio |
| **Canary deployment** como gate obligatorio antes de distribución global | ChatGPT, Grok | Alta — debe estar en la especificación del pipeline |
| **Nodos agregadores regionales** (jerarquía, no solo hub-and-spoke) | DeepSeek | Media — interesante para flota >20 nodos |
| **"Especialista Cero"** como ejercicio de aprendizaje (RF port-scan → ONNX → plugin-loader C++) | Gemini | Alta para el autor — aprendizaje inmediato y concreto |
| **Dataset governance ADR** (activo propietario: acceso, licencia, responsabilidad) | ChatGPT | Media — antes de cualquier publicación |
| **`required_features` field en plugin manifest** | DeepSeek | Alta — nodo con schema incompatible no carga el plugin |

---

## 4. OBSERVACIÓN RECURRENTE DEL CONSEJO (para el acta)

ChatGPT lo formuló mejor:

> *"El valor de tu sistema no va a venir de LLMs, FT-Transformers, o arquitecturas sofisticadas. Va a venir de la calidad del pipeline de datos + control del ciclo de vida de modelos."*

Esto es consistente con la filosofía Via Appia Quality: la infraestructura invisible es lo que sostiene el sistema. Los modelos sofisticados son el techo; el pipeline de datos es el cimiento.

---

## 5. NOTA SOBRE IDENTIDAD DE MIEMBROS

**Patrón Qwen→DeepSeek** (DAY 103–105, confirmado DAY 104): El fichero `respuesta_qwen.md` inicia declarando *"Soy DeepSeek — modelo de DeepSeek Research (China, independiente de Alibaba/Tongyi Lab)"*. Se han recibido por tanto **dos respuestas de DeepSeek y cero de Qwen**. Falta respuesta de Parallel.ai.

Para futuras sesiones: verificar si Qwen tiene acceso independiente o si el canal está siendo capturado por DeepSeek.

---

## 6. PRÓXIMOS PASOS

El trabajo inmediato **no cambia**:
1. **ADR-025** implementación: `plugin_loader.cpp`, `plugin-loader/CMakeLists.txt`, `tools/provision.sh --reset`, JSON schemas (6 componentes), systemd units
2. **TEST-INTEG-SIGN-1 a 7** — pendientes de implementación

Lo que este Consejo desbloquea para el roadmap:
1. **DEBT-PROTO-002** (schema versionado) — antes del segundo nodo
2. **ADR-026** formal puede redactarse cuando haya 3-5 nodos activos
3. **"Especialista Cero"** — ejercicio de aprendizaje válido ya, en paralelo al trabajo principal, sin afectar al pipeline

---

*Síntesis preparada por Claude (Anthropic) — DAY 104*  
*Principio Via Appia Quality: documentar cada piedra antes de colocarla.*