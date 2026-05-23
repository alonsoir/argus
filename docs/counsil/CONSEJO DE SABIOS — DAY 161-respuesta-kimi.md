# RESPUESTA DEL CONSEJO DE SABIOS — DAY 161

*Sesión extraordinaria · 2026-05-23*

---

## Q1 — Wire Protocol Test: ¿Integración cifrado + compresión?

**Veredicto: SÍ. Crear `test-wire-crypto-pipeline` como test de integración, no sustitutivo sino complementario.**

**Razonamiento:**
El bug del DAY 98 (`DEBT-FIREWALL-CRYPTO-FORMAT-001`) no ocurrió ni en la capa de cifrado pura ni en la compresión pura — ocurrió en la **frontera** entre ambas. Los tests unitarios de `crypto-transport` y los tests de `wire-protocol` validan cada capa por separado, pero el sistema productivo las apila.

Un test de integración que ejecute `plaintext → CryptoTransport::seal → LZ4Frame::compress → wire → LZ4Frame::decompress → CryptoTransport::open → plaintext` es la única forma de detectar regresiones en el orden de operaciones, padding inter-capa o corrupción de buffers.

**Recomendación técnica:**
- Nombre: `test-wire-crypto-integration.cpp`
- Debe usar vectores de prueba deterministas (no random) para reproducibilidad.
- No reemplaza los tests existentes; se ejecuta en stage `Integration` del Jenkinsfile.dev.

---

## Q2 — Jenkinsfile.dev: ¿`agent any` vs `label 'argus-server'`?

**Veredicto: `agent any` en dev es CORRECTO para la fase actual. Mantener hasta que exista un nodo Jenkins dedicado con hardware target.**

**Razonamiento:**
En la arquitectura actual (Mac del fundador + Vagrant local), forzar `label 'argus-server'` rompería el pipeline dev porque no existe ese nodo. El propósito del `Jenkinsfile.dev` es validar la rama antes del merge, no emular producción.

**Cuándo migrar a `agent { label 'argus-server' }`:**
1. Cuando el servidor FEDER tenga un nodo Jenkins registrado con label `argus-server`.
2. Cuando el pipeline dev necesite acceso a hardware físico (RPi5, N100, tarjetas de red específicas) que no existen en la Mac.
3. Cuando las credenciales `vault-enterprise-token` deban estar restringidas por nodo (security boundary).

**Recomendación técnica:**
- Mantener `agent any` en `Jenkinsfile.dev`.
- Añadir un stage opcional `Hardware-Smoke` en `Jenkinsfile.dev` que se ejecute solo si existe el label `argus-edge` (usando `when { expression { ... } }`), de modo que el mismo pipeline pueda aprovechar hardware cuando esté disponible sin fallar cuando no lo está.

---

## Q3 — DEBT-CONFIG-JINJA2: ¿Runtime detection vs perfiles fijos?

**Veredicto: PERFILES FIJOS. La detección de hardware debe usarse solo para SELECCIONAR el perfil, no para CALCULAR valores en runtime.**

**Razonamiento:**
Argus es un sistema de seguridad. La no-determinismo en producción es un riesgo operacional mayor que la suboptimalidad de un perfil fijo. Si un UEx en campo se comporta de forma errática, necesitas poder reproducir exactamente su configuración en laboratorio.

**Arquitectura recomendada:**
```
Runtime: detect_hardware() → selecciona perfil (naive/edge-low/edge-medium/edge-high)
         → carga JSON generado correspondiente
         → NUNCA calcula thresholds, buffers ni timeouts en runtime
```

Los "valores óptimos" deben computarse **offline** (por ejemplo, un script `tools/calibrate-profile.py` que analiza benchmarks y genera nuevos JSONs para `json-values/`), no en el binario de producción. Esto mantiene los JSONs originales sagrados, los generados versionables (si se desea) y el runtime predecible.

---

## Q4 — EMECAS++ fix E2E: ¿Tráfico sintético vs orgánico?

**Veredicto: INYECTAR TRÁFICO SINTÉTICO MÍNIMO. Un test E2E que depende de tráfico orgánico es un test flaky por diseño.**

**Razonamiento:**
El objetivo de `test-e2e-live` es validar que el pipeline completo (captura → normalización → correlación → storage → query) funciona cuando hay **al menos un evento**. No es un test de red para verificar que tu Mac genera tráfico ICMP.

**Implementación recomendada:**
- En el `setUp()` del test E2E, inyectar 1-3 eventos sintéticos vía loopback o interfaz virtual (`tun`/`tap` o incluso un socket raw local).
- El modo `snapshot → 60s → check` debe verificar `delta ≥ eventos_inyectados`.
- Crear un segundo test separado, opcional, `test-e2e-live-organic` que NO bloquee CI y que sirva para validación manual en entornos con tráfico real.

Esto desacopla la validez del pipeline de la meteorología de red de tu red doméstica.

---

## Q5 — Prioridad DAY 162

**Veredicto: A) `DEBT-ARGUSPP-SURICATA-001` (ADR-048 F2 — primera señal externa).**

**Razonamiento estratégico:**

| Opción | Valor a corto plazo | Bloquea otros hitos | Impacto demo FEDER |
|--------|---------------------|---------------------|-------------------|
| **A) Suricata** | **Alto** — demuestra integración heterogénea | No bloquea, habilita | **Diferenciador claro** |
| B) NTP | Medio — prerequisite técnico | Bloquea correlación multi-engine, pero aún no hay multi-engine desplegado | Invisible para demo |
| C) Crypto Autonomy | Medio-Alto — research | No bloquea funcionalidad actual | Demostrable pero riesgoso a 4 meses de deadline |
| D) AlertClient refactor | Bajo — deuda técnica | No bloquea | Invisible |

Con deadline FEDER en septiembre 2026, necesitas **hitos visibles y diferenciadores** antes que infrastructure prerequisites. Suricata como "primera señal externa" demuestra que Argus no es un silo, sino una plataforma de fusión de señales. Eso es narrativa potente para una demo.

**Orden recomendado:**
1. **DAY 162-163:** Suricata integration (A)
2. **DAY 164-165:** NTP prerequisite (B), ya que para entonces tendrás Suricata + detector nativo y necesitarás correlación temporal
3. **DAY 166+:** Crypto Autonomy (C) como research paralelo
4. **DAY 170+:** AlertClient refactor (D) cuando el codebase estabilice post-demo

---

*El Consejo queda a la espera de la ejecución de EMECAS++ en `feature/day161-cicd-pipeline` para validar el merge a `v0.9.5-day161`.*

*Que el build sea verde.* 🟢