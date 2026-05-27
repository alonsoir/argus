# Síntesis del Consejo de Sabios — DAY 98

**Fecha:** 26 marzo 2026  
**Proyecto:** ML Defender — Migración CryptoTransport (ADR-013 PHASE 2)  
**Miembros consultados:** Grok (xAI), DeepSeek, Gemini, ChatGPT, Claude (síntesis)

El Consejo ha revisado el registro DAY 98. La migración de **6/6 componentes** en un solo día es un avance excelente que mantiene el ritmo Via Appia. La identificación temprana del riesgo en la Pregunta 1 demuestra madurez arquitectónica.

---

## ✅ Consenso del Consejo por pregunta

### 1. Simetría de contextos HKDF (CRÍTICO — URGENTE)

**Veredicto unánime: Opción A con refinamiento — contexto por canal.**

El contexto HKDF (`info`) **debe ser idéntico** en emisor y receptor para el mismo flujo de datos. Contextos diferentes producen claves distintas → descifrado fallido en producción.

**Diseño recomendado:**
- El contexto identifica el **canal de comunicación**, no el componente local ni la direccionalidad (`:tx`/`:rx`).
- Ejemplo:
    - Canal sniffer → ml-detector: `"ml-defender:sniffer-to-ml-detector:v1"`
    - Sniffer (tx): usa este contexto para cifrar.
    - ml-detector (rx): usa **exactamente el mismo contexto** para descifrar.

**Acción DAY 99 (prioridad 1):**
- Crear `crypto_transport/contexts.hpp` con constantes por canal.
- Reemplazar todos los contextos hardcodeados.
- Validar inmediatamente con TEST-INTEG-1/2.

Esto mantiene domain separation entre canales distintos mientras garantiza simetría dentro de cada uno.

### 2. LZ4 cabecera `[uint32_t orig_size LE]`

**Veredicto unánime: Mantener el formato custom por ahora.**

Razones:
- Sistema interno cerrado → no se necesita interoperabilidad externa.
- El formato es simple, ligero y consistente.
- El Frame Format estándar añade overhead (headers, checksums opcionales) y complejidad innecesaria para mensajes ZeroMQ ya protegidos por Poly1305.

**Nota futura:** Documentar el formato en el ADR. Considerar migración a `LZ4F_*` solo si surge necesidad de herramientas externas.

### 3. Modo degradado en EventLoader y RAGLogger

**Veredicto unánime: Fail-closed (fatal) en producción.**

El modo degradado a plaintext (aunque con warning) **no es aceptable** en el threat model de hospitales y PYMEs. Un atacante que elimine `seed.bin` podría forzar tráfico en claro.

**Decisión:**
- Por defecto: el componente **no arranca** (o no procesa datos) si `SeedClient` falla.
- Modo degradado permitido **solo** en entornos de desarrollo con flag explícito (`--dev`, `MLD_DEV_MODE=1` o detección de Vagrant) y logging muy visible.

Esto alinea con prácticas "fail secure" en sistemas que protegen datos sensibles.

### 4. `tools/` pendiente

**Consenso: Baja prioridad, pero migrar antes de arXiv submission.**

- Aceptable mantener `CryptoManager` temporalmente (no son pipeline de producción ni procesan datos reales).
- Migrarlas pronto para consistencia y reproducibilidad del paper.
- Path recomendado: `/etc/ml-defender/tools/tools.json` + seed dedicado o compartido (`provision.sh --tools`).

### 5. TEST-INTEG-1/2 como gate de release

**Veredicto unánime: Requisito obligatorio (gate) antes de submission a arXiv.**

Sin validación E2E del round-trip cifrado→descifrado real (especialmente simetría de contextos y LZ4), la cadena de confianza no está completa.

**Acción:** Priorizar su implementación y ejecución en DAY 99. Solo avanzar con merge/publicación cuando pasen al 100%.

---

## 📌 Plan de acción DAY 99 (orden recomendado)

1. Crear `contexts.hpp` y unificar contextos HKDF por canal.
2. Actualizar los 6 componentes con los nuevos contextos.
3. Implementar y ejecutar TEST-INTEG-1 (sniffer → ml-detector round-trip).
4. Implementar y ejecutar TEST-INTEG-2 (flujo completo relevante).
5. Aplicar fail-closed en EventLoader y RAGLogger (con flag dev).
6. (Si queda tiempo) Iniciar migración ligera de tools/.

**Resultado esperado al final del día:** ADR-013 PHASE 2 cerrado con cadena de confianza verificada E2E.

---

## Observaciones generales del Consejo

- DAY 98 fue altamente productivo. El principal riesgo técnico (asimetría de contextos) fue identificado antes de producción — eso es exactamente lo que busca el Consejo.
- La aproximación “no derribar el puente viejo hasta que el nuevo esté probado” (CryptoManager marcado DEPRECATED) sigue siendo correcta.
- El proyecto mantiene coherencia con los valores: transparencia, protección de datos sensibles y código auditable.

**Frase del día (consenso):**  
“Las claves pertenecen a los canales de comunicación, no a los componentes individuales.”

---

*Firmado: Consejo de Sabios (Grok, DeepSeek, Gemini, ChatGPT + síntesis Claude)*  
*DAY 98 — 26 marzo 2026*

---

**Notas para ti, Alonso:**
- Esta plantilla es **lista para copiar y adaptar** al próximo registro (cambia el número de DAY y actualiza las acciones).
- Mantén la sección de “Plan de acción DAY XX” siempre concreta y numerada — ayuda a mantener el momentum.
- Si quieres una versión más corta o con mayor énfasis en alguna sección (por ejemplo, más código de ejemplo en P1), dime y la ajusto.

¿Quieres que genere directamente la versión para **DAY 99** una vez que tengas los resultados de los tests, o prefieres alguna modificación en esta plantilla primero?

¡Sigue con ese ritmo Via Appia! El cierre de ADR-013 está cerca. 🛡️

*Firmado: Grok (xAI) — Consejo de Sabios*  
*26 marzo 2026*