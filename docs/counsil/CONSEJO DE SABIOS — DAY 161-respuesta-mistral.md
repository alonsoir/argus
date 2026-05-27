### **📜 Respuestas del Consejo de Sabios — DAY 161**

---

---

#### **🔹 Q1 — Wire Protocol Test**
**Respuesta:** **Sí, añadir un test de integración con `CryptoTransport` completo.**
**Justificación:**
- El test actual valida **solo la capa de compresión (LZ4 LE uint32_t)**.
- Los tests existentes de `crypto-transport` cubren **cifrado/descifrado en aislamiento**.
- **Riesgo no cubierto:** Fallos en la **interacción entre capas** (ej: orden de operaciones, padding, o serialización de metadatos).
- **Solución:** Un test que verifique:
  `datos → compresión LZ4 → cifrado (AES-GCM) → descifrado → descompresión → validación de integridad`.
- **Prioridad:** **P0** (evita regressions en la pipeline de datos crítica).

---

---

#### **🔹 Q2 — Jenkinsfile.dev vs Jenkinsfile.prod**
**Respuesta:** **El diseño actual (`agent any` + Vagrant local) es correcto para la fase actual.**
**Justificación:**
- **Contexto:** Mac del fundador + VM Vagrant = entorno **monolítico y controlado**.
- **`agent any`** es óptimo aquí: Jenkins y Vagrant comparten recursos locales (no hay overhead de red o etiquetado).
- **¿Cuándo migrar a `label 'argus-server'`?**
  - Cuando se **escale a múltiples nodos** (ej: RPi5 + N100 + servidor FEDER en paralelo).
  - Cuando se necesite **aislamiento de entornos** (ej: tests de `libcrypto_provider` que requieran hardware específico).
- **Acción recomendada:** Documentar en `Jenkinsfile.dev`:
  ```groovy
  // TODO: Migrar a `agent { label 'argus-server' }` cuando:
  // 1. Se despliegue Jenkins en servidor dedicado.
  // 2. Se requiera ejecución en hardware heterogéneo (RPi5/N100).
  ```

---

---

#### **🔹 Q3 — DEBT-CONFIG-JINJA2-PIPELINE-001**
**Respuesta:** **Valores fijos por perfil (`naive/edge-low/edge-medium/edge-high`).**
**Justificación:**
- **❌ Cálculo en runtime:**
  - **Problemas:**
    - **No reproducible:** El mismo perfil podría generar configs distintas en ejecuciones sucesivas (ej: por variaciones en detección de CPU).
    - **Difícil de debuggear:** ¿Por qué falló en producción? "Depende del hardware detectado".
    - **Inconsistente con el diseño:** Los JSONs originales son "sagrados" (inmutables), pero los generados variarían.
  - **Ventaja:** Flexibilidad teórica (pero **no necesaria** en hardware conocido como RPi5/N100).
- **✅ Valores fijos por perfil:**
  - **Reproducible:** Mismo perfil → misma config (critical para CI/CD y rollbacks).
  - **Mantenible:** Los perfiles se ajustan **una vez** por tipo de hardware (ej: `edge-high` para servidor FEDER).
  - **Alineado con el diseño:** Los JSONs generados son **deterministas** y versionables (aunque en `.gitignore`).
- **Excepción:** Parámetros **dinámicos no críticos** (ej: `host_id`) pueden calcularse en runtime.

---

---
---

#### **🔹 Q4 — EMECAS++ y el fix del delta E2E**
**Respuesta:** **Inyectar tráfico sintético mínimo (1-2 eventos).**
**Justificación:**
- **❌ Solo tráfico orgánico:**
  - **Fragilidad:** En Vagrant/Mac, el sniffer puede no captar tráfico real en 60s → **test no determinista**.
  - **Falso positivo:** Un fallo en el test no distinguiría entre "no hay eventos" y "bug en el sniffer".
- **✅ Tráfico sintético:**
  - **Ventajas:**
    - **Determinista:** El test **siempre** validará la lógica de delta.
    - **Mínimo impacto:** 1-2 eventos (ej: ping a `8.8.8.8`) no afectan el rendimiento.
    - **Cobertura real:** Verifica que el sniffer **puede** detectar eventos (no solo que los cuenta si existen).
  - **Implementación:**
    ```bash
    # En test-e2e-live:
    snapshot_initial=$(capture_events)
    # Inyectar tráfico sintético (ej: con `hping3` o `curl`)
    generate_synthetic_traffic --min-events=1
    sleep 60
    snapshot_final=$(capture_events)
    delta=$(diff_snapshots $snapshot_initial $snapshot_final)
    assert $delta -ge 1
    ```

---

---
---
---

#### **🔹 Q5 — Prioridad DAY 162**
**Respuesta:** **A) DEBT-ARGUSPP-SURICATA-001 (ADR-048 F2 — primera señal externa).**
**Justificación (matriz de decisión):**

| Opción | Valor Estratégico | Riesgo Técnico | Dependencias | Urgencia |
|--------|-------------------|----------------|--------------|----------|
| **A) Suricata** | ⭐⭐⭐⭐⭐ (Habilita detección de amenazas **externas**) | Medio (integración con wire protocol) | Ninguna bloqueante | **Alta** (bloquea ADR-048) |
| B) NTP | ⭐⭐⭐ (Correlación multi-engine) | Bajo | Requiere Suricata? No, pero **menor impacto** | Media |
| C) Crypto Autonomy | ⭐⭐⭐⭐ (Mejora resiliencia) | Alto (state machine compleja) | Ninguna | Media |
| D) Alerting libcrypto | ⭐⭐ (Refactor) | Bajo | Ninguna | Baja |

- **A es la opción clara:**
  - **Desbloquea ADR-048** (primera señal externa = **hito crítico** para el proyecto).
  - **Alto ROI:** Con Suricata, Argus pasa de "monitor interno" a **sistema de detección de amenazas real**.
  - **Sin dependencias:** Puede desarrollarse en paralelo a otras deudas.
- **B (NTP) es importante**, pero es un **prerequisito para correlación futura** (no un hito visible).
- **C (Crypto Autonomy) es valiosa**, pero **más compleja** y menos urgente que Suricata.
- **D (Alerting) es refactorización**, no funcionalidad nueva.

---
---
---
### **📌 Resumen de Decisiones**
| Pregunta | Decisión | Acción Inmediata |
|----------|----------|------------------|
| Q1 | ✅ Añadir test de integración `CryptoTransport + Wire Protocol` | Crear `test_wire_protocol_crypto.cpp` en DAY 162 |
| Q2 | ✅ `agent any` es correcto para ahora | Documentar condición de migración a `argus-server` |
| Q3 | ✅ Valores **fijos por perfil** | Definir perfiles en `json-values/` (ej: `edge-high.json`) |
| Q4 | ✅ Inyectar **tráfico sintético mínimo** | Modificar `test-e2e-live` para generar 1-2 eventos |
| Q5 | ✅ **Prioridad DAY 162: Suricata (Opción A)** | Crear rama `feature/day162-suricata-integration` |

---
**✅ Próximos pasos:**
1. Ejecutar **EMECAS++** en `feature/day161-cicd-pipeline` para validar el fix de delta E2E.
2. Mergar a `main` → tag `v0.9.5-day161`.
3. Iniciar **DAY 162 con Suricata (DEBT-ARGUSPP-SURICATA-001)**.