## Consejo de Sabios — DAY 141

**Contexto:** DAY 141. Tres cierres: bug Makefile dependencia implícita `seed-client-build`, `DEBT-PCAP-CALLBACK-LIFETIME-DOC-001`, y `DEBT-VARIANT-B-CONFIG-001` — `sniffer-libpcap.json` propio + `main_libpcap.cpp` config-driven con `-c`. 9/9 tests PASSED, 0 warnings. Emails a Andrés Caro enviados (hardware FEDER + scope standalone/federado).

---

**Q1 — Identidad criptográfica compartida Variant A / Variant B**
`sniffer-libpcap.json` usa `component_id="sniffer"` y `keys_dir="/etc/ml-defender/sniffer"` — misma identidad que Variant A. Razonamiento: son el mismo componente con distinto backend de captura, misma seed, mismo CTX_SNIFFER_TO_ML.
¿Es correcto compartir identidad criptográfica entre Variant A y Variant B, o deberían tener identidades separadas (`sniffer-ebpf` / `sniffer-libpcap`) con seeds distintas?

**Q2 — `DEBT-VARIANT-B-BUFFER-SIZE-001`: ¿pre-FEDER o post-FEDER?**
`buffer_size_mb` está en el JSON pero no implementado — requiere refactorizar `PcapBackend::open()` de `pcap_open_live()` a `pcap_create()+pcap_set_buffer_size()+pcap_activate()`. Crítico en ARM64/RPi donde el buffer default del kernel puede ser 2MB y causar drops bajo carga.
¿Implementar antes del benchmark FEDER (impacta directamente los resultados en RPi) o registrar como DEBT y documentar la limitación en el paper?

**Q3 — Clasificador de warnings de build: TinyLlama vs grep/awk**
`BACKLOG-BUILD-WARNING-CLASSIFIER-001` propone usar el pipeline rag-security/TinyLlama para clasificar warnings de `make all` en `THIRD_PARTY_IGNORABLE` vs `OWN_CODE_BLOCKER`. Alternativa: script grep/awk con lista de patrones conocidos (prefijo `defender:`, paths `/tmp/faiss/`, etc.).
¿TinyLlama añade valor real sobre una solución determinista grep/awk para este caso de uso, o es over-engineering?

**Q4 — Auditoría automática de dependencias Makefile**
El bug `seed-client-build` estuvo oculto porque los binarios sobreviven `vagrant destroy`. En una VM limpia real (hardware FEDER) habría fallado en el primer intento. El EMECAS lo detectó, pero solo porque destruimos la VM manualmente.
¿Deberíamos añadir un target `make check-deps` que valide que todas las dependencias de build están declaradas explícitamente, o es suficiente con el EMECAS como gate?

---

Eso es para los 8. Cuando tengas las respuestas, cerramos el día.