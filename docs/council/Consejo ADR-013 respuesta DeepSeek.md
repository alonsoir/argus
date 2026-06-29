## DeepSeek — Retroalimentación DAY 98

Excelente progreso. Migrar 6 componentes en un solo día manteniendo 22/22 tests verdes es un ritmo impresionante. La pregunta 1 es efectivamente urgente — es el tipo de error que en producción se traduce en silencios inexplicables. Vayamos por partes.

---

### Pregunta 1 — Simetría de contextos HKDF (URGENTE)

**Diagnóstico:** Tienes razón en que el esquema actual es incorrecto. Si el sniffer cifra con `"ml-defender:sniffer:v1:tx"` y el ml-detector descifra con `"ml-defender:ml-detector:v1:rx"`, las claves derivadas serán diferentes porque el contexto es diferente. Ambos usan el mismo `seed.bin` (provision.sh SSOT), pero HKDF es determinista: cambia un byte del contexto, cambia toda la clave.

**La solución correcta es la Opción A, pero con una precisión:**

No se trata de que ambos usen el mismo contexto *literal*, sino de que el contexto que define la clave simétrica debe ser el mismo en ambos extremos. En un par emisor-receptor, el contexto es una propiedad del **canal**, no de los componentes individuales.

Propuesta concreta:

- Definir contexto por **par de componentes**: `"ml-defender:sniffer->ml-detector:v1"`
- Sniffer: cifra con `tx` usando ese contexto
- ml-detector: descifra con `rx` usando **exactamente el mismo contexto**

Esto mantiene la separación semántica (cada par tiene su propia clave) y garantiza simetría.

Si prefieres mantener la convención `{component}:{direction}`, entonces el contexto debe ser idéntico en ambos lados: por ejemplo, tanto sniffer como ml-detector usan `"ml-defender:sniffer-ml:v1"` como contexto, y dentro de cada componente se asigna a `tx` o `rx` según corresponda (pero la clave derivada es la misma porque el contexto es el mismo).

**Recomendación inmediata:** Antes de los tests E2E, unifica los contextos en todos los pares. Documenta en el ADR que el contexto es **compartido por emisor y receptor**, y que la distinción `tx/rx` es solo para el nonce, no para la derivación.

---

### Pregunta 2 — LZ4 cabecera vs frame estándar

**Recomendación:** Mantén el formato custom por ahora.

**Razonamiento:**
- Todos los componentes son internos, no hay interoperabilidad con herramientas externas prevista en PHASE 2.
- El frame estándar de LZ4 añade overhead y complejidad (checksum, opciones, etc.) que no necesitas.
- El formato custom `[uint32_t orig_size LE]` ya es consistente en los 6 componentes.
- Si en el futuro necesitas interoperabilidad con herramientas externas (ej: logs inspeccionables con herramientas CLI), puedes añadir un exportador que convierta, pero no es prioritario.

**Decisión:** Aceptado como está. Documentar en ADR-020 el formato custom como estándar interno.

---

### Pregunta 3 — Modo degradado en EventLoader y RAGLogger

**Recomendación:** **Error fatal** en producción; modo degradado solo para desarrollo.

**Razonamiento:**
- El threat model de hospitales y escuelas asume que el sistema debe fallar de forma segura (fail-closed). Si el seed no está presente, la confidencialidad de los logs (que pueden contener datos sensibles de pacientes) no está garantizada.
- En desarrollo, tener que provisionar manualmente antes de cada test es una fricción. Por tanto, se puede mantener el modo degradado solo cuando se detecta un entorno de desarrollo (ej: variable `MLD_DEV_MODE=1` o si el binario se ejecuta con `--dev`).
- En producción, la ausencia de `seed.bin` debe impedir el arranque del componente con un mensaje claro que indique ejecutar `sudo provision.sh`.

**Decisión:** Modo degradado deshabilitado por defecto; flag explícito para desarrollo.

---

### Pregunta 4 — Herramientas en `tools/` con CryptoManager

**Recomendación:** Migrar con menor prioridad, pero migrar antes de arXiv.

**Razonamiento:**
- Las herramientas de stress test no son parte del pipeline de producción, pero son parte del material reproducible que acompañará al preprint.
- Si en el paper muestras resultados de stress test, esos tests deben usar el mismo esquema criptográfico que el sistema en producción. De lo contrario, podrían ocultar problemas de rendimiento asociados al cifrado.
- Propuesta: crear un `tools/seed_client_tools.cpp` que lea de un archivo de configuración separado (`/etc/ml-defender/tools/tools.json` o `./tools_seed.bin`) y migrar las herramientas una por una, priorizando `synthetic_sniffer_injector` (usado en los stress tests).

**Decisión:** P2 (antes de arXiv, no bloqueante para DAY 98).

---

### Pregunta 5 — TEST-INTEG-1/2 como gate de release

**Recomendación:** **Gate obligatorio** antes de submission a arXiv.

**Razonamiento:**
- La cadena de confianza `provision.sh → seed.bin → HKDF → CryptoTransport` solo está probada unitariamente. Un test E2E que envía un mensaje real del sniffer al ml-detector y verifica que se descifra correctamente es la única manera de garantizar que la simetría de contextos (Pregunta 1) está resuelta.
- Sin este test, el riesgo de que la migración falle en producción es alto.
- No es un trabajo enorme: un test que arranque dos componentes en procesos separados (o un solo proceso con dos hilos simulando los componentes), provisione seeds temporales, envíe un protobuf conocido, y verifique el round-trip.

**Decisión:** TEST-INTEG-1 debe estar verde antes de dar el preprint por finalizado. Puede hacerse en paralelo con otros trabajos, pero es condición necesaria para la release.

---

### Resumen ejecutivo

1. **Contextos HKDF:** corrige ahora antes de los tests E2E. Usa contexto compartido por par de componentes.
2. **LZ4:** formato custom es aceptable.
3. **Modo degradado:** solo en desarrollo; en producción, fail-closed.
4. **Tools:** migrar antes de arXiv, prioridad media.
5. **Test integración:** gate obligatorio para arXiv.

El trabajo de DAY 98 es sólido; la migración en sí está bien ejecutada. Los puntos abiertos son de validación y ajuste fino, no de replanteamiento. Con los tests E2E verdes mañana, estarás listo para cerrar ADR-013.

Sigue así. La cadena de confianza está a punto de quedar sellada.

— DeepSeek, miembro del Consejo de Sabios