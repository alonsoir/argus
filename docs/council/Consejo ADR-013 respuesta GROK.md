¡Excelente ritmo, Alonso! DAY 98 con **6/6 componentes migrados** en un solo día es un avance sólido y fiel al espíritu Via Appia: avanzar con decisión, pero sin derribar el puente viejo hasta que el nuevo esté firme. La cadena `provision.sh → seed.bin → SeedClient → HKDF-SHA256 → CryptoTransport` ya está operativa en compilación y unit tests. Queda el punto crítico de la simetría en producción, que los TEST-INTEG-1/2 de mañana deberían iluminar.

Aquí van mis recomendaciones como miembro del Consejo de Sabios, priorizando la pregunta 1 (urgente) y respondiendo al resto con pragmatismo para entornos con recursos limitados (hospitales, escuelas, PYMEs).

### 1. Simetría de contextos HKDF (la más urgente)

**Recomendación clara: Opción A con refinamiento.**

El contexto (`info` en HKDF) **debe ser idéntico** en el emisor (tx) y receptor (rx) para que ambos deriven **exactamente la misma clave**. Esto es fundamental en HKDF (RFC 5869 y prácticas estándar): el parámetro `info` proporciona domain separation y contexto, pero para una comunicación **simétrica punto-a-punto** (un flujo unidireccional sniffer → ml-detector), el `info` debe coincidir en ambos extremos.

- **Arquitectura correcta propuesta:**
    - Sniffer (emisor): usa contexto `"ml-defender:sniffer-to-ml-detector:v1"` (o simplemente `"ml-defender:sniffer:v1:tx"`) para derivar la clave de encriptación.
    - ml-detector (receptor): usa **el mismo contexto** `"ml-defender:sniffer-to-ml-detector:v1"` (o el equivalente acordado) para derivar la clave de desencriptación.

  Evita incluir direccionalidad (`:tx` / `:rx`) en el contexto compartido, porque eso rompe la simetría. La direccionalidad se puede manejar en el wire format (por ejemplo, un campo de tipo de mensaje o un prefijo en el payload), pero **no** en el `info` de HKDF.

- Por qué no B: Contextos separados intencionales sin handshake adicional complicarían innecesariamente el diseño. No hay mención a un protocolo de intercambio de claves asimétrico en el ADR-013 actual.

- Por qué no C: Aunque el seed es el mismo (SSOT via provision.sh), contextos diferentes producen claves diferentes. Sin handshake o acuerdo previo, el descifrado fallará consistentemente. Mejor mantenerlo simple y determinista.

**Acción inmediata sugerida:**  
Estandariza un esquema de contextos en un header compartido (por ejemplo, en `crypto_transport/contexts.h`):
- Para flujos unidireccionales: `"ml-defender:<source>:<destination>:v1"`
- Para bidirectional si surge: incluir session ID o nonce en el info.

Esto mantiene la predictibilidad y evita claves divergentes. Una vez alineado, los TEST-INTEG-1/2 deberían pasar sin problemas.

### 2. LZ4 cabecera custom vs Frame Format estándar

**Recomendación: Mantén el formato custom por ahora, pero prepara migración futura.**

El custom (`[uint32_t orig_size LE] + compressed data`) es simple, ligero y consistente con el diseño interno. Para componentes 100% controlados, es suficiente y evita overhead del frame format (magic numbers, checksums opcionales, etc.).

Ventajas del estándar LZ4 Frame Format (`LZ4F_*` API):
- Interoperabilidad con herramientas externas (lz4 CLI, otros lenguajes).
- Soporte nativo para checksums, content size (hasta 16 EB), y streaming más robusto.
- Mejor para debug y posibles extensiones futuras (ej. exportar artifacts).

Dado que el proyecto es interno y prioriza recursos limitados + simplicidad, el custom está bien **en esta fase**. Documenta claramente el formato y considera un flag futuro (ADR-020 o similar) para soportar ambos.

Si en algún momento necesitas interoperabilidad (por ejemplo, con herramientas de análisis externas), migra al frame format — la API libsodium + LZ4 lo facilita.

### 3. Modo degradado en EventLoader y RAGLogger

**Recomendación: Hazlo fatal (fail-closed) en producción; mantén degradado solo en dev/test con flag explícito.**

Para el threat model de organizaciones objetivo (datos sensibles de pacientes, estudiantes, etc.):
- **Fail-closed es preferible** en contextos de seguridad: si no hay seed.bin válido, el componente **no debe arrancar** (o al menos no procesar datos reales). Un warning + plaintext expone tráfico a eavesdropping, lo que derrota parcialmente el propósito de ML Defender.

- Excepción razonable: En entornos de desarrollo o pruebas, el modo degradado es útil para no bloquear iteraciones rápidas.

Solución práctica:
- Por defecto: fatal si SeedClient falla.
- Flag explícito en config JSON (ej. `"allow_degraded_mode": true`) solo para entornos no-prod, con logging fuerte y warning visible.
- En hospitales/PYMEs, la disponibilidad es importante, pero la confidencialidad de datos de red también lo es. Mejor alertar y detener que silenciosamente exponer.

Esto alinea con prácticas "fail secure" en sistemas de detección de intrusiones.

### 4. tools/ pendiente

**Recomendación: Migración de baja prioridad, pero hazla pronto.**

Estas son herramientas de stress test/sintéticas, no parte del pipeline crítico de producción. Mantener `CryptoManager` temporalmente es **aceptable** para no bloquear el ritmo actual.

Sin embargo:
- Migralas en los próximos 1-2 días (no dejes que se acumule deuda técnica).
- Path de configuración sugerido: `/etc/ml-defender/tools/tools.json` (o similar, bajo un subdirectorio tools/). Usa el mismo `SeedClient` con seed.bin compartido si es posible, o un seed dedicado para tools (generado via provision.sh --tools).
- Una vez migradas, unifícalas bajo CryptoTransport para consistencia en tests.

### 5. TEST-INTEG-1/2 como gate de release

**Recomendación: Hazlos requisito obligatorio (gate) antes de arXiv submission.**

La migración criptográfica es el cambio más sensible. Sin validación E2E de round-trip cifrado→descifrado real entre componentes (especialmente simetría HKDF y LZ4), existe riesgo de regresiones sutiles en producción.

- Prioriza implementarlos mañana (DAY 99).
- Úsalos como gate: solo merge/submission cuando pasen 100%.
- Beneficio adicional: servirán como documentación viva del flujo completo.

### Resumen y próximo paso

DAY 98 fue productivo. El riesgo principal (simetría HKDF) se resuelve fácilmente adoptando **contextos idénticos** por par emisor-receptor. Con eso + TEST-INTEG-1/2, la migración quedará sólida.

**Acciones para DAY 99 sugeridas:**
1. Alinear contextos HKDF (Opción A refinada).
2. Implementar y correr TEST-INTEG-1/2.
3. Decidir sobre modo degradado y tools.
4. Documentar los contextos estandarizados.

Si los tests confirman el problema de descifrado, el fix debería ser rápido. ¡Sigue con ese momentum!

¿Quieres que profundicemos en el código de ejemplo para los nuevos contextos, o en cómo estructurar los TEST-INTEG? Estoy listo para la siguiente iteración.

*Firmado: Grok (xAI) — Consejo de Sabios*  
*26 marzo 2026*