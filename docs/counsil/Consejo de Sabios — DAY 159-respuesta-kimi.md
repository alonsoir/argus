**Dictamen del Consejo — DAY 159**  
*Kimi (Moonshot AI) — voto emitido con miras a la integridad del pipeline y la seguridad de los operadores finales.*

---

### 1. Wire protocol conformance test: SÍ, obligatorio, no negociable.

**Voto: Añadir el test de integración.** El E2E gate de 90 minutos es un oráculo de última línea, no un detector de regresión temprana. Que un bug de endianness haya sobrevivido 61 días demuestra que el pipeline tiene un "hueco de test" entre unitario y E2E. El wire protocol (header LZ4 + cifrado ChaCha20 + framing ZMQ) es un contrato binario que cruza procesos. Necesita un test de integración dedicado que:

- Valide la serialización/deserialización del header contra un golden binary fixture.
- Fuerce ambos endianness y falle explícitamente si el detector escribe LE y el firewall espera BE.
- Corra en segundos como parte de `make test-all`, no en minutos.

El E2E que tienes valida que "el sistema entero funciona", pero no te dice *dónde* se rompió el contrato. 61 días de drop rate 100% invisible es exactamente el tipo de fallo que mata la confianza en una demo FEDER. **Recomendación:** Crear `test_wire_protocol.cpp` que lea `ml_detector_output.proto`, genere un frame, y lo pase por el parser del firewall. Si no coincide byte-a-byte, RED.

---

### 2. `check-abs` en `test-e2e-live`: NO aceptable. Cambiar a delta o híbrido.

**Voto: Modo absoluto es una trampa de falso positivo.** Si el pipeline procesó 2M paquetes hace 3 horas y ahora está muerto, `check-abs` pasa. Eso es peor que no tener test, porque genera confianza infundada.

Para una VM de desarrollo — donde reiniciás, debuggeás, dejás corriendo — necesitás saber si hay **actividad reciente**, no **actividad histórica acumulada**.

**Recomendación:** Implementar modo `check-delta` con ventana deslizante:
- Tomar snapshot A, esperar 30s, tomar snapshot B.
- Si `B - A < threshold` → FAIL.
- Conservar `check-abs` solo como guarda de mínimo absoluto (ej: "si lleva 5 minutos corriendo y el contador total es 0, fail").

Esto detecta stalls sin importar cuánto tiempo lleve el pipeline arriba.

---

### 3. `DEBT-ALERTING-LIBCRYPTO-PROVIDER-001`: P1, no P0. Etcd-server como alertador único es suficiente para FEDER.

**Voto: Degradar a P1.** El riesgo operativo de FEDER es que nadie se entere si hay un incidente. Si `etcd-server` puede alertar a Discord/Telegram, ese riesgo está cubierto. No necesitás que el sniffer, el firewall o el RAG ingester alerten individualmente para una demo de septiembre.

El costo de hacerlo P0 ahora es distracción de deudas genuinamente bloqueantes (ej: `DEBT-ETCD-HA-QUORUM-001`, `DEBT-ALERTING-EDGE-SOS-001`).

**Recomendación:** Mantenerlo en backlog P1 explícito. Aceptar que post-FEDER, cuando el pipeline pase de "demo" a "operación 24/7 en edge nodes", cada componente DEBE alertar. Pero hasta el 22-09-2026, un único canal desde etcd-server es aceptable si está documentado.

---

### 4. `synthetic_ml_output_injector`: SÍ a auto-adaptación completa, por la misma razón del endianness.

**Voto: Leer todo el contrato del wire protocol desde config compartida.** El injector sintético no es un mock estático; es un **emulador de comportamiento**. Si emite frames con compresión LZ4 + cifrado ChaCha20 y el detector real cambia a sin compresión o rotación de nonce, el injector debe adaptarse o los tests E2E se vuelven fantasmas.

**Recomendación:** Unificar la lectura de config. El `synthetic_ml_output_injector` debe consumir el mismo schema JSON que consume `ml-detector` para definir:
- `compression` (LZ4/none)
- `encryption` (ChaCha20/none)
- `endianness` (LE/BE) — **crítico tras DAY 159**
- `zmq_endpoint`

Esto convierte el injector en un "cliente canónico" del wire protocol. Si cambia el protocolo, el injector se rompe inmediatamente en `make test-all`, no 61 días después en `make test-e2e`.

---

### 5. Paralelización E2E en Jenkins: NO. Estado compartido = carrera peligrosa.

**Voto: Secuencial, con VMs independientes si se necesita velocidad.** 90 minutos es largo pero predecible. Paralelizar `test-e2e-synthetic-full` y `test-e2e-synthetic-firewall` sobre el mismo filesystem de logs, el mismo pipeline ZMQ, y el mismo estado de iptables es invitar a Heisenbugs que te harán perder más tiempo debuggeando CI que ganando en velocidad.

**Recomendación:**
- **Opción A (conservadora, recomendada):** Mantener secuencial. 90 min en nightly/merge es aceptable para un sistema de esta criticidad.
- **Opción B (si el tiempo es bloqueante):** No paralelizar tests, paralelizar **jobs**. Dos workers Jenkins con VMs Vagrant independientes, cada uno corre una suite E2E distinta. Cero estado compartido. Costo: 2× infraestructura. Beneficio: 2× velocidad sin riesgo de races.
- **Opción C (híbrida):** Separar `make test-e2e` en stages: unit+integration (rápido, ~10 min, gate inmediato) → E2E firewall (~30 min) → E2E full (~50 min). Si falla un stage, abortar. Así no esperás 90 min para descubrir un error de compilación.

---

**Resumen ejecutivo para DAY 159:**

| # | Decisión | Prioridad |
|---|----------|-----------|
| 1 | Wire protocol conformance test | **P0 — antes del próximo merge** |
| 2 | `check-delta` en `test-e2e-live` | **P0 — antes del próximo merge** |
| 3 | Alerting en libcrypto_provider.so | **P1 — post-FEDER** |
| 4 | Auto-adaptación completa del ml injector | **P0 — unificar config** |
| 5 | Paralelización E2E | **NO — mantener secuencial o VMs independientes** |

El cierre del bug de endianness es un éxito, pero la lección de los 61 días es que el pipeline necesita **defensa en profundidad en testing**: unitario rápido + integración de contrato binario + E2E lento pero completo. No confíes en que el E2E te va a atrapar todo; es demasiado tarde en el feedback loop.

*— Kimi, Consejo de Sabios, DAY 159*