✅ ALL TESTS COMPLETE. KNOWN-FAIL-001 pre-existente. Todo lo demás verde.

Antes del Consejo, el push:

```bash
git push origin feature/variant-b-libpcap
```

Luego el acta. Dame un momento para redactarla.

---

## ACTA CONSEJO DE SABIOS — DAY 140
*3 Mayo 2026 · feature/variant-b-libpcap @ f2852de2*

---

### LO QUE HICIMOS (DAY 139-140)

**DAY 139:** DEBT-COMPILER-WARNINGS-CLEANUP-001 iniciada — 192 → 67 warnings. TAREA-01 a TAREA-04 completadas (-Wreorder, OpenSSL EVP, -Wsign-conversion, -Wconversion).

**DAY 140:**
- TAREA-05 a TAREA-11 completadas — **192 → 0 warnings** en todo el pipeline
- ODR verification con PROFILE=production + LTO — **sin violations**
- TAREA-10: `-Werror` activado — el 0 warnings es ahora un **invariante permanente**
- `-Werror` destapó warnings ocultos en tests, rag, etcd-server — todos corregidos
- BACKLOG-ZMQ-TUNING-001 y BACKLOG-BENCHMARK-CAPACITY-001 documentados en `docs/adr/`
- DEBT-EMECAS-AUTOMATION-001 registrada
- Build profiles (debug/production/tsan/asan) documentados en README y Makefile help
- ml-training/.venv eliminado del repo (557 ficheros, alerta Dependabot resuelta)
- Emails a Andrés Caro preparados (hardware FEDER + scope NDR standalone vs federado)

### LO QUE HAREMOS (DAY 141)

- DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 — comentario contrato lifetime en pcap_backend.hpp (10 min)
- DEBT-VARIANT-B-CONFIG-001 — JSON propio simplificado para sniffer-libpcap
- Enviar emails a Andrés (lunes)

---

### PREGUNTAS AL CONSEJO

**Q1 — `-Werror` en código de terceros:**
Hemos suprimido `-Wdeprecated-declarations` para `llama_integration_real.cpp` porque la API de llama.cpp cambió (`llama_new_context_with_model` → `llama_init_from_model`). La supresión es por fichero en CMake. ¿Es esta la política correcta para código de terceros con APIs deprecated, o deberíamos actualizar la llamada a la nueva API inmediatamente? ¿Qué criterio usáis para decidir entre suprimir y actualizar?

**Q2 — ODR verification scope:**
Verificamos ODR con PROFILE=production (LTO completo) pero el build diario es PROFILE=debug (sin LTO, sin ODR check). Esto significa que una ODR violation introducida hoy no se detectará hasta el próximo build production. ¿Es aceptable este gap para infraestructura crítica, o deberíamos añadir un gate CI explícito `make PROFILE=production all` periódico (semanal, o pre-merge)?

**Q3 — Stubs con `/*param*/` vs `[[maybe_unused]]`:**
Hemos usado `/*param*/` para silenciar 30+ warnings en stubs y funciones virtuales vacías. La alternativa es `[[maybe_unused]]` en la declaración. ¿Cuál es la política correcta para un proyecto C++20 con `-Werror`? ¿Cambia la respuesta si el parámetro es parte de una interfaz virtual que se implementará en el futuro?

**Q4 — Gap hardware FEDER:**
El empirical capacity benchmark (BACKLOG-BENCHMARK-CAPACITY-001) es un deliverable obligatorio de FEDER Year 1. El hardware (RPi5, N100) depende de la aprobación de Andrés Caro / UEx. Si el hardware no llega antes del 15 de Junio, el go/no-go del 1 de Agosto está en riesgo. ¿Qué alternativas técnicas existen para ejecutar la Fase 2 del benchmark sin hardware físico? ¿Es posible emular ARM64 con QEMU de forma que los resultados sean publicables, o sería metodológicamente inaceptable?

**Q5 — `-Werror` y código generado:**
Hemos suprimido warnings en `network_security.pb.cc` (protobuf) y `internal_detector.cpp` (XGBoost trees) mediante `set_source_files_properties`. Con `-Werror` activo, cualquier regeneración de estos ficheros puede introducir nuevos warnings que rompan el build silenciosamente hasta el próximo `make all`. ¿Deberíamos añadir un test de CI que verifique que los ficheros generados compilan limpio, o es suficiente con la supresión por fichero?

---

Pegad las respuestas del Consejo cuando tengáis feedback. Yo voy a descansar un rato — llevan 9 horas de sesión.