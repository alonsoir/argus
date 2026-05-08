## Consejo de Sabios — DAY 141 — Voto de Claude (Anthropic)

---

**Q1 — Identidad criptográfica compartida Variant A / Variant B**

**Voto: Compartida es correcto. Mantener `component_id="sniffer"`.**

Razón: la identidad criptográfica representa *quién habla*, no *cómo captura*. Variant A y Variant B producen el mismo wire format, usan el mismo `CTX_SNIFFER_TO_ML`, y el receptor (ml-detector) no sabe ni le importa qué backend usó el sniffer. Separar identidades implicaría dos seeds distintas, dos keypairs, doble gestión en provision.sh, doble entrada en etcd — complejidad sin beneficio de seguridad real.

La separación tendría sentido si los dos backends corrieran simultáneamente en el mismo nodo. No es el caso — son variantes mutuamente excluyentes por despliegue.

**Posición diferenciada:** si en el futuro existe un nodo híbrido que corre ambos backends (improbable pero no imposible), la separación sería necesaria. Registrar como nota en el ADR, no como DEBT activa.

---

**Q2 — `DEBT-VARIANT-B-BUFFER-SIZE-001`: ¿pre-FEDER o post-FEDER?**

**Voto: Pre-FEDER. Implementar antes del benchmark.**

Razón: si el buffer default del kernel en RPi5 es 2MB y el benchmark mide drops, los resultados estarán contaminados por una limitación artificial del software, no por el hardware real. El paper diría "RPi5 tiene drops a X Mbps" cuando la causa real sería "PcapBackend no configura el buffer". Eso es un error metodológico publicable.

La refactorización `pcap_open_live()` → `pcap_create()+pcap_set_buffer_size()+pcap_activate()` es mecánica — 30-45 minutos, test existente cubre el comportamiento. El riesgo es bajo, el impacto metodológico es alto.

Propuesta: abrir como `DEBT-VARIANT-B-BUFFER-SIZE-001` P1, resolver en la misma sesión que `DEBT-VARIANT-B-CONFIG-001` estaba prevista o en la siguiente antes de tener el hardware.

---

**Q3 — Clasificador warnings: TinyLlama vs grep/awk**

**Voto: grep/awk determinista. TinyLlama es over-engineering para este caso.**

Razón: el problema es clasificar strings de compilación con patrones perfectamente predecibles — prefijo `defender:`, paths `/tmp/faiss/`, `libtool:`. Esto es exactamente lo que grep/awk resuelve con coste cero, sin dependencia de servicio, sin latencia, sin falsos negativos.

TinyLlama añade valor donde hay ambigüedad semántica — análisis de logs de runtime, clasificación de eventos de red, correlación de incidentes. Para strings de compilador que siguen formatos fijos no hay ambigüedad que modelar.

La regla correcta: si un determinista de 5 líneas resuelve el problema, no usar ML. Actualizar `BACKLOG-BUILD-WARNING-CLASSIFIER-001` a "implementar como script grep/awk" y cerrar la idea de TinyLlama para este caso.

---

**Q4 — `make check-deps` vs EMECAS como gate**

**Voto: Ambos, pero en ese orden de prioridad. EMECAS es suficiente por ahora; `make check-deps` como backlog post-FEDER.**

Razón: el EMECAS detectó el bug exactamente como debe — destroy completo, VM limpia, build from scratch. Es el gate correcto y ya está en el protocolo obligatorio. Un `make check-deps` automatizado sería más rápido de detectar en CI, pero requiere introspección del grafo de dependencias de make, que es no trivial de implementar correctamente en GNU Make.

El coste del bug fue mínimo — lo detectamos en EMECAS DAY 141, se corrigió en 20 minutos. El riesgo real es en hardware FEDER sin destroy previo, que el EMECAS ya cubre por protocolo.

Propuesta: registrar `BACKLOG-MAKEFILE-DEP-AUDIT-001` como post-FEDER, bajo prioridad. Cuando haya servidor CI con Jenkinsfile activo, un `make clean && make all` en VM limpia en cada PR es equivalente al EMECAS y cubre el gap.

---

*Claude (Anthropic) · DAY 141 · 4 Mayo 2026*