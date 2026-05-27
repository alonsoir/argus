**Respuesta del Consejo — DAY 141**

Participación confirmada. Respuestas técnicas directas, basadas en experiencia en sistemas distribuidos C++, seguridad de despliegue, y trade-offs de ingeniería.

### **Q1 — Identidad criptográfica compartida Variant A / Variant B**

**Recomendación: NO compartir identidad.** Deben tener identidades separadas.

**Razonamiento:**

- Aunque conceptualmente son “el mismo sniffer con distinto backend”, en runtime son **binarios diferentes** con ciclos de vida, permisos y superficies de ataque distintas (eBPF requiere CAP_SYS_ADMIN / bpf(), libpcap requiere CAP_NET_RAW + promiscuo).
- Compartir seed/llaves viola el principio de **least privilege** y complica revocación/rotación. Si comprometen el binario libpcap (más expuesto por pcap_open_live), arrastran la identidad del eBPF.
- CTX_SNIFFER_TO_ML puede seguir siendo el mismo topic/channel, pero la autenticación debería ser por **component_id + variant** (`sniffer-ebpf` vs `sniffer-libpcap`).
- Impacto práctico: dos directorios de keys (`/etc/ml-defender/sniffer-ebpf`, `/etc/ml-defender/sniffer-libpcap`) o un único directorio con archivos nombrados por variant. Muy bajo coste.

**Decisión propuesta:** Crear identidades separadas + mismo `component_family="sniffer"`. Actualizar `sniffer-libpcap.json` en consecuencia.

### **Q2 — DEBT-VARIANT-B-BUFFER-SIZE-001: ¿pre-FEDER o post-FEDER?**

**Implementar antes del benchmark FEDER.**

**Razonamiento:**

- En ARM64/RPi el buffer por defecto del kernel (a menudo 2 MiB) es **catastrófico** bajo tráfico real. Los resultados del benchmark FEDER quedarían contaminados y no serían comparables con Variant A (eBPF suele tener ring buffers más grandes y controlables).
- El refactor `pcap_open_live()` → `pcap_create() + pcap_set_buffer_size() + pcap_set_snaplen() + pcap_activate()` es **estándar** y de bajo riesgo (documentado en la propia man de libpcap).
- Tiempo estimado: 1-2 horas + tests de drops bajo carga con `tcpreplay` o similar.
- Documentar la limitación actual en el paper es válido, pero los números que salgan en FEDER serán usados como referencia futura. Mejor tener datos limpios.

**Acción:** Cerrar este DEBT antes de lanzar el benchmark en hardware FEDER.

### **Q3 — Clasificador de warnings: TinyLlama vs grep/awk**

**Solución determinista (grep/awk + patrones) es suficiente y preferible.**

**Razonamiento:**

- Este caso de uso es **altamente estructurado**: warnings de third-party conocidos, paths predecibles (`/tmp/faiss/`, `build/_deps/`, etc.), prefijos propios (`defender:`), categorías repetitivas (unused parameter en templates, deprecated en dependencias, etc.).
- Un script `make classify-warnings` con un archivo de patrones (`warning-patterns.conf`) es:
    - Determinista → reproducible en CI.
    - Rápido (milisegundos).
    - Fácil de mantener y auditar.
    - Sin dependencias adicionales ni latencia.

TinyLlama añade valor real solo en escenarios de **análisis semántico profundo** (warnings ambiguos, nuevos patrones sin precedentes, explicación en lenguaje natural para juniors). Aquí no aplica. Es **over-engineering** claro.

**Recomendación:** Implementar el clasificador grep/awk + lista de patrones. Registrar como backlog el uso futuro de LLM para análisis de logs de producción o fuzzing reports.

### **Q4 — Auditoría automática de dependencias Makefile**

**Añadir `make check-deps` como gate obligatorio.**

**Razonamiento:**

- El bug `seed-client-build` es clásico de Makefiles con reglas implícitas y binarios que sobreviven a `vagrant destroy`. En hardware FEDER (sin estado previo) habría fallado en cold build.
- EMECAS es bueno pero reactivo y depende de destrucción manual de VM. No es un gate fiable.
- Solución sencilla y efectiva:
  ```make
  check-deps:
      @./scripts/check-build-deps.sh
  ```
  Donde el script verifica existencia de herramientas/compiladores/bibliotecas de sistema listadas en un `BUILD_DEPS` explícito (o parsea el Makefile + `apt-get` / `dnf` equivalentes).

Alternativa más robusta (recomendada a medio plazo): migrar las dependencias de sistema a **Nix** o **Docker** para desarrollo/FEDER, pero mientras tanto `make check-deps` es barato y evita regresiones.

**Decisión:** Añadir el target y engancharlo en `make all` (o como paso previo en CI/EMECAS).

---

**Cierre propuesto del día:**

- Q1 → identidades separadas.
- Q2 → implementar buffer_size antes de FEDER.
- Q3 → grep/awk (rechazar TinyLlama aquí).
- Q4 → añadir `make check-deps`.

¿Algún miembro quiere matizar o hay consenso? Cuando cerremos, actualizamos DEBTs y procedemos.