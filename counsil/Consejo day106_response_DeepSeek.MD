## DeepSeek — Retroalimentación DAY 106

Excelente cierre de PHASE 2a. Las cuatro condiciones del Consejo se han implementado con rigor, y el preprint ya está en arXiv. El proyecto avanza a buen ritmo. Respondo a las tres preguntas.

---

### Q1 — PHASE 2b sequencing: rag-ingester

**Recomendación:** Seguir el patrón idéntico de tres ficheros (`CMakeLists.txt`, `main.cpp`, `config/*.json`) establecido en firewall-acl-agent. No hay razón para diverger en rag-ingester.

**Razonamiento:**
- rag-ingester no tiene particularidades que justifiquen un enfoque diferente. El FAISS ingestion path es aguas abajo del cifrado; el plugin loader actúa en la capa de transporte (MessageContext), igual que en firewall.
- Mantener la uniformidad reduce la carga cognitiva y facilita la replicación del patrón en los componentes restantes (ml-detector, sniffer, etc.) cuando se migren a PHASE 2b/c.

**Condición previa:** Asegurarse de que el `rag-ingester` tenga la misma dependencia explícita en el Makefile (ya añadida en DAY 106). Fuera de eso, adelante.

---

### Q2 — CRC32 scope: ¿retener en Release?

**Recomendación:** No. En Release builds, la verificación de integridad del payload debe limitarse a la comparación de punteros (D8 original) y, opcionalmente, una comprobación rápida de `payload_len`. CRC32 solo en debug/desarrollo.

**Razonamiento:**
- El propósito de D8 es detectar modificaciones no autorizadas de campos read-only por parte de un plugin. En producción, asumimos que los plugins están firmados (ADR-025) y, por tanto, son de confianza. La verificación adicional en producción añade latencia y complejidad sin beneficio real.
- En cambio, en desarrollo (donde se cargan plugins sin firmar o se está depurando), CRC32 es una herramienta valiosa.
- **Propuesta intermedia:** Mantener la comprobación de punteros y de `payload_len` (que es barata) en Release, pero no el CRC. De hecho, la comparación de punteros ya detecta si el plugin ha modificado el puntero para apuntar a otra región. CRC32 solo añade valor si se modifica el contenido in-place sin cambiar el puntero — un escenario que en producción debería estar cubierto por la firma y la revisión de código.

**Decisión:** Mantener CRC32 bajo `MLD_ALLOW_DEV_MODE`. En Release, solo punteros + length.

---

### Q3 — test_config.json ownership: ¿convención o fixture factory?

**Recomendación:** Formalizar como convención para pruebas de plugins, pero documentar claramente.

**Razonamiento:**
- El enfoque actual (test_config.json aislado) es simple y funciona. Cada test de plugin puede tener su propio JSON en un subdirectorio `tests/config/` sin interferir con los archivos de producción.
- Una fábrica de fixtures (builder pattern) sería más elegante pero también más compleja de implementar y mantener. Para el número actual de pruebas, es overkill.
- **Convención propuesta:**
  - Cada plugin de prueba residirá en `plugins/test-<name>/` con su propio `CMakeLists.txt`.
  - Los ficheros de configuración de prueba se ubicarán en `plugins/test-<name>/test_config.json`.
  - El test runner cargará ese JSON explícitamente, sin tocar los directorios de configuración del sistema.

**Extensión futura:** Si el número de pruebas crece y se vuelve tedioso mantener JSONs manuales, se puede introducir un generador de configuraciones en el propio test (una función `create_test_config()`). Pero por ahora, la convención es suficiente.

---

### Comentarios adicionales

- **arXiv submission:** Enhorabuena por el envío. La corrección de la especificación del hardware (i9, 32GB) es importante para la reproducibilidad. Los diagramas TikZ son un gran plus.
- **PHASE 2b orden:** Después de rag-ingester, el siguiente lógico sería ml-detector (por ser el consumidor principal de mensajes descifrados) y luego sniffer. Pero el orden no es crítico siempre que se sigan los mismos patrones.
- **Test plugin de 3 variantes:** Excelente trabajo. Variante B (D8 violation) y C (error return) validan el comportamiento fail-closed. Asegúrate de que en producción `result_code != 0` siempre lleva a `std::terminate()`, incluso si el plugin no tiene `require_signature`. Eso ya está cubierto por D1 de ADR-023.

---

### Resumen ejecutivo

| Q | Decisión | Acción |
|---|----------|--------|
| Q1 | Seguir patrón estándar en rag-ingester | Proceder con la misma plantilla de 3 ficheros |
| Q2 | CRC32 solo en debug. Release: punteros + length | Añadir `#ifdef MLD_ALLOW_DEV_MODE` alrededor de CRC; mantener comparación de punteros siempre |
| Q3 | Convención de `test_config.json` aislado | Documentar en `TESTING.md` la ubicación y uso; no construir fixture factory todavía |

El proyecto está en un punto excelente para continuar con PHASE 2b. El preprint ya está en manos de arXiv. Enhorabuena al equipo.

— DeepSeek, miembro del Consejo de Sabios