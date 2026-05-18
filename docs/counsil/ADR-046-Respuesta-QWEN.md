**CONSEJO DE SABIOS — DICTAMEN TÉCNICO ADR-046 v1 (BORRADOR)**
*Revisión experta en sistemas distribuidos C++20, correlación temporal y modelos de amenaza — DAY 156*

---

## 🎯 VEREDICTO GLOBAL

**APROBADO CON REVISIONES CRÍTICAS** ✅

El ADR-046 es ambicioso, científicamente sólido y arquitectónicamente coherente. La visión de aRGus++ como sistema híbrido NDR/EDR distribuido es una evolución natural y publicable. Las decisiones de no-join-en-edge, reutilización de ZeroMQ, y C++20 puro son correctas.

**Condición para aprobación definitiva**: Resolver las 5 observaciones de alto impacto listadas abajo antes de iniciar implementación.

---

## 🔍 ANÁLISIS DE FORTALEZAS (LO QUE ESTÁ BIEN)

| Sección | Por qué es notable |
|---------|-------------------|
| **§1 Contexto** | Diagnóstico preciso: "incompleto en señal" resume el gap arquitectónico sin menospreciar el trabajo existente. |
| **§2 Decisión** | Tabla de componentes clara; principio "join en servidor" protege recursos edge — decisión operativa madura. |
| **§3.3 correlation-engine** | Stack C++20 (Arrow + nlohmann/json) es consistente; join por 5-tupla es patrón establecido en literatura de correlación. |
| **§4 Plugins ensemble** | Hipótesis F1 verificable y publicable; separación de especialistas + meta-learner es arquitectura de ensemble robusta. |
| **§5 Flywheel** | Mecanismo inmunológico federado bien articulado; etiquetado automático vía Suricata resuelve problema histórico de ground truth. |
| **§6 Datasets históricos** | Distinción crítica documentada con precisión técnica; evita malentendidos en revisión de paper. |
| **§7 mitre-generator** | Orquestador C++20 + Atomic Red Team es pragmatismo ingenieril; manifiesto JSON como contrato es diseño limpio. |
| **§8 Contribución científica** | Descubrimiento "sintético puro > mezcla" es contribución metodológica valiosa; conexión con Sommer & Paxson [2010] es académicamente sólida. |
| **§10 Frontera community/enterprise** | Delimitación clara y justificada; modelo de sostenibilidad económico realista. |

---

## ⚠️ OBSERVACIONES CRÍTICAS (ALTO IMPACTO — BLOQUEANTES)

### 1. **Correlación temporal: ±500ms es frágil sin robustez explícita** (§3.3)

**Problema**: El join por 5-tupla con ventana ±500ms asume:
- Relojes sincronizados (NTP) con drift <100ms
- Procesamiento en tiempo real sin colas
- No hay reordenamiento de paquetes ni pérdida

En producción edge (hospitales rurales, cortes de luz, NTP caído), estas asunciones fallan.

**Recomendación**: Añadir estrategia de degradación:

```cpp
// correlation-engine: robust temporal join
struct TemporalJoinConfig {
    std::chrono::milliseconds nominal_window{500};
    std::chrono::milliseconds fallback_window{2000};  // si NTP drift detectado
    double clock_drift_threshold_ms{100};              // alerta si >100ms
    
    // Estrategia cuando ventana exacta falla:
    enum class FallbackStrategy {
        EXPAND_WINDOW,      // usar fallback_window
        PROBABILISTIC_JOIN, // score de similitud temporal + features
        SKIP_CORRELATION    // procesar fuentes independientemente
    } fallback_on_drift{FallbackStrategy::EXPAND_WINDOW};
};
```

**Acción**: Añadir §3.3.1 "Robustez ante desincronización" con política de fallback documentada.

---

### 2. **Memoria del join temporal: sin backpressure = riesgo de OOM bajo carga** (§3.3)

**Problema**: `std::unordered_map<5-tuple, FlowEntry>` crece indefinidamente si:
- Hay DDoS o escaneo masivo (millones de flujos nuevos/segundo)
- El consumer de Parquet es más lento que el producer de logs
- No hay política de evicción

**Recomendación**: Especificar política de gestión de memoria:

```yaml
# correlation-engine config
temporal_join:
  max_in_flight_flows: 1000000  # límite absoluto
  eviction_policy: "LRU_by_age"  # evictar flujos más antiguos primero
  backpressure:
    enabled: true
    threshold_percent: 80  # alertar al 80% de capacidad
    action: "drop_oldest_non_alerted"  # priorizar flujos con alertas Suricata
```

**Acción**: Añadir §3.3.2 "Gestión de memoria y backpressure" con política de evicción y alerta.

---

### 3. **Seguridad de ingestión: fuentes externas no autenticadas = vector de poisoning** (§3.1-3.2)

**Problema**: Suricata/Zeek/Wazuh envían JSON/CSV sin firma. Un atacante con acceso al edge podría:
- Inyectar `eve.json` falso con alertas manipuladas
- Poisoning del dataset de entrenamiento → modelo ensemble degradado
- El ataque es silencioso: el modelo "aprende" patrones falsos

**Recomendación**: Añadir capa de verificación mínima:

```cpp
// correlation-engine: ingestión segura
class SecureIngestor {
public:
    // Para fuentes externas: verificar integridad básica
    bool verify_source_integrity(const SourceEvent& e) {
        // 1. Timestamp razonable (no futuro, no >24h pasado)
        // 2. 5-tupla válido (puertos en rango, IPs bien formadas)
        // 3. Campo obligatorio presente (ej: Suricata: event_type)
        // 4. Opcional: HMAC ligero con clave por componente (si performance lo permite)
        return true; // o false si falla validación
    }
    
    // Eventos que fallan validación → quarantine log, no entrenamiento
};
```

**Acción**: Añadir §3.2.1 "Verificación de integridad de fuentes externas" con política de quarantine.

---

### 4. **Privacidad: Wazuh host telemetry + GDPR requiere tratamiento explícito** (§3.1, §11)

**Problema**: Wazuh ve procesos, ficheros, autenticación — datos personales bajo GDPR. El ADR menciona GDPR en ADR-043 pero no aquí.

**Recomendación**: Añadir sección de privacidad:

```markdown
### 3.5 Privacidad y GDPR para host telemetry

- Wazuh agent en edge: los datos personales (procesos, ficheros, usuarios) **nunca salen del nodo en claro**.
- Antes de enviar al servidor: pseudonimización con `K_pseudo` de la instalación (ADR-043 D2).
- El `correlation-engine` recibe identificadores pseudónimos, no datos reales.
- Derecho al olvido: comando firmado de borrado de `anon_id` en Neo4j (ADR-043 D8) aplica también a datos de Wazuh.
- Auditoría: cada evento de host telemetry lleva `installation_id` opaco para trazabilidad sin exposición.
```

**Acción**: Añadir §3.5 "Privacidad y GDPR para host telemetry" con referencia cruzada a ADR-043.

---

### 5. **Reproducibilidad del experimento "sintético vs académico": detalles insuficientes** (§8.1-8.4)

**Problema**: La afirmación "100% sintético > mezcla > 100% académico" es científicamente valiosa, pero:
- ¿Qué método de generación sintética se usó? (¿GANs? ¿modelado estadístico? ¿trazas parametrizadas?)
- ¿Qué "distribuciones estadísticas de comportamiento" exactamente?
- ¿Cómo se midió la degradación? (¿F1 macro? ¿precisión en clase minoritaria?)

**Recomendación**: Añadir apéndice de reproducibilidad:

```markdown
### Apéndice A: Metodología del experimento sintético vs académico

**Generación sintética**:
- Método: modelado estadístico de flujos CTU-13 (distribuciones de duración, bytes, paquetes, inter-arrival)
- Herramienta: script C++20 `synthetic-flow-generator` (repo: `tools/synthetic/`)
- Parámetros: extraídos de CTU-13 Neris vía `parquet-convert --stats`

**Métricas de evaluación**:
- F1 macro (promedio no ponderado por clase)
- Precisión en clase "ataque" (recall de falsos negativos)
- AUC-ROC para umbral independiente

**Resultados clave**:
- F1(100% sintético): 0.9985
- F1(50/50 mezcla): 0.9821
- F1(100% académico): 0.9912 (pero overfitting detectado en holdout CTU-13)

**Código y datos**: Disponibles en `experiments/synthetic-vs-academic/` bajo licencia MIT.
```

**Acción**: Añadir Apéndice A con detalles de reproducibilidad, o marcar como "supplementary material" en el paper.

---

## 🟡 OBSERVACIONES DE MEDIO IMPACTO (RECOMENDACIONES)

### 6. **Preguntas abiertas: estructurar por categoría y añadir vistas preliminares** (§13)

**Recomendación**: Agrupar preguntas y añadir "Vista preliminar del Consejo":

```markdown
### 13.1 Diseño técnico

| Pregunta | Vista preliminar del Consejo |
|----------|-----------------------------|
| Ventana ±500ms configurable por protocolo | ✅ Sí: DNS 200ms, HTTP 1s, SMTP 2s — añadir `protocol_window_overrides` en config |
| Fallback cuando NTP falla | ✅ Estrategia EXPAND_WINDOW + alerta operativa |

### 13.2 Priorización

| Pregunta | Vista preliminar del Consejo |
|----------|-----------------------------|
| ¿Suricata o Zeek primero? | ✅ Suricata primero: etiquetado automático acelera generación de datasets; Zeek en fase 2 |
| ¿Wazuh P1 o P2? | 🟡 P2: validar que Suricata+Zeek caben en edge antes de añadir host telemetry |

### 13.3 Scope y arquitectura

| Pregunta | Vista preliminar del Consejo |
|----------|-----------------------------|
| correlation-engine v1 mínimo | ✅ aRGus + Suricata únicamente (etiquetado automático); Zeek/Wazuh en v2 |
| mitre-generator: ADR propio o sección | ✅ Sección dentro de ADR-046 por ahora; ADR propio si crece en complejidad |
| Atomic Red Team: dependencia externa | ✅ Dependencia externa; el manifiesto JSON es el contrato, no la implementación de técnicas |
```

---

### 7. **Operational management: configuración y actualizaciones no cubiertas**

**Recomendación**: Añadir §15 "Gestión operativa del pipeline multi-fuente":

```markdown
### 15. Gestión operativa

**Configuración centralizada**:
- Suricata/Zeek/Wazuh configs gestionadas via Ansible + Jinja2 (igual que aRGus)
- Validación de config antes de deploy: `suricata -T`, `zeek -C`, `wazuh-logtest`

**Actualizaciones de seguridad**:
- Parches de Suricata/Zeek/Wazuh aplicados via `make update-components`
- Rollback automático si EMECAS falla post-update

**Detección de drift de configuración**:
- Hash de config activa enviado al servidor cada 24h
- Alerta si config edge ≠ config esperada en central
```

---

### 8. **Deuda técnica: añadir estimación de esfuerzo y dependencias** (§11)

**Recomendación**: Ampliar tabla de deuda con columnas de esfuerzo y orden:

| ID | Descripción | Prioridad | Esfuerzo estimado | Depende de |
|----|-------------|-----------|------------------|------------|
| DEBT-ARGUSPP-NTP-001 | NTP sincronizado y verificado | P0 | 2 días | Ninguna |
| DEBT-ARGUSPP-RESOURCE-001 | Medir CPU/RAM en RPi5/N100 | P1 | 3 días (con hardware) | BACKLOG-BENCHMARK-CAPACITY-001 |
| DEBT-ARGUSPP-CORRELATION-001 | correlation-engine C++20 | P1 | 10 días | DEBT-ARGUSPP-NTP-001 |
| ... | ... | ... | ... | ... |

---

## 📋 RESUMEN DE ACCIONES PRE-APROBACIÓN

| Prioridad | Acción | Responsable estimado |
|-----------|--------|---------------------|
| 🔴 P0 | Añadir robustez temporal (§3.3.1) con fallback strategy | Distributed Systems |
| 🔴 P0 | Especificar backpressure y evicción (§3.3.2) | C++ Performance |
| 🔴 P0 | Añadir verificación de integridad de fuentes (§3.2.1) | Security |
| 🔴 P0 | Añadir sección GDPR para Wazuh (§3.5) | Legal/Privacy |
| 🔴 P0 | Detallar reproducibilidad del experimento sintético (Apéndice A) | Research/ML |
| 🟡 P1 | Estructurar preguntas §13 con vistas preliminares | Technical Writing |
| 🟡 P1 | Añadir gestión operativa (§15) | DevOps |
| 🟡 P1 | Ampliar tabla de deuda con esfuerzo/dependencias | Project Management |

---

## 💬 FRASE DE CIERRE

> *"La correlación no es solo unir datos; es tejer confianza entre señales heterogéneas. Este ADR no solo extiende aRGus: redefine qué significa 'detectar' en infraestructura crítica. Que cada join temporal sea robusto, cada fuente verificada, y cada dataset, reproducible."*

---

**¿Procedemos a actualizar ADR-046 con las 5 revisiones críticas (P0) antes de someterlo a aprobación formal?** 🛡️🧠🔐