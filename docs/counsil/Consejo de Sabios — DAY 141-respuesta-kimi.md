## Kimi — Respuesta al Consejo de Sabios — DAY 141

*Evaluación bajo criterios de segregación de identidades criptográficas, rigor metrológico en benchmarks, y pragmatismo en automatización de build.*

---

### Q1 — Identidad criptográfica compartida Variant A / Variant B

**Hipótesis:** Compartir la misma seed entre dos binarios con diferentes superficies de ataque aumenta el blast radius de un compromiso.

**Veredicto: Identidad compartida es correcta para el modelo actual, pero con condición de hardening documentada.**

**Análisis de riesgo:**

| Escenario | Identidad compartida | Identidades separadas |
|-----------|---------------------|----------------------|
| Compromiso de seed de sniffer (Variant A) | Atacante puede suplantar Variant A y B | Atacante solo suplanta la variante comprometida |
| Rotación de seed | Una rotación cubre ambas variantes | Dos rotaciones necesarias |
| Gestión operativa | Un directorio, un JSON | Dos directorios, dos JSONs, complejidad doble |
| Modelo de amenazas | El atacante que compromete el host tiene ambos binarios | El atacante que compromete el host tiene ambos binarios de todos modos |

**La clave:** En el modelo de amenazas de aRGus, el límite de confianza es el **nodo**, no el **binario**. Si un atacante tiene acceso al filesystem de `/etc/ml-defender/sniffer/`, ya puede leer ambos binarios (`sniffer` y `sniffer-libpcap`) y sus configuraciones. Separar las seeds no añade seguridad real si el compromiso es a nivel de nodo.

**Condición de corrección:** La identidad compartida es segura **si y solo si**:
1. Ambos binarios corren con el mismo usuario (`argus`) y mismo AppArmor profile
2. El AppArmor profile restringe ambos binarios idénticamente
3. No hay ejecución simultánea de Variant A y Variant B en el mismo nodo (son alternativas, no complementos)

**Recomendación:** Mantener identidad compartida. Documentar en `sniffer-libpcap.json`:

```json
{
  "_comment": "Shared cryptographic identity with Variant A (eBPF/XDP).",
  "_comment": "Variant A and Variant B are mutually exclusive per node.",
  "_comment": "If running both simultaneously is required, open DEBT-SNIFFER-DUAL-IDENTITY-001.",
  "component_id": "sniffer",
  "keys_dir": "/etc/ml-defender/sniffer"
}
```

**Excepción futura:** Si algún nodo ejecuta **ambas variantes simultáneamente** (por ejemplo, Variant A en `eth0` y Variant B en `eth1` para redundancia), entonces sí se requieren identidades separadas. Esto no es el caso actual y no está planificado para FEDER.

---

### Q2 — `DEBT-VARIANT-B-BUFFER-SIZE-001`: pre-FEDER o post-FEDER

**Hipótesis:** El tamaño del buffer de libpcaf afecta directamente el throughput medible en ARM64/RPi, donde el kernel default puede ser insuficiente para carga sostenida.

**Veredicto: **Pre-FEDER, bloqueante para el benchmark**.** Sin `buffer_size` configurable, los números de throughput en RPi no son el máximo alcanzable, sino un artefacto de la configuración por defecto del kernel. Eso invalida la contribución científica.

**Justificación metodológica:**

Un benchmark científico debe medir el **rendimiento máximo alcanzable** bajo configuración óptima, no el rendimiento bajo configuración por defecto. Si el paper declara *"Variant B procesa 100 Mbps en RPi4"*, un revisor puede preguntar: *"¿Y si aumentas el buffer del kernel?"* Si la respuesta es *"No lo probamos"*, el benchmark es incompleto.

**Implementación requerida:**

```cpp
// pcap_backend.cpp
bool PcapBackend::open(const std::string& iface, PacketCallback cb, void* ctx) {
    char errbuf[PCAP_ERRBUF_SIZE];
    
    // Refactor: pcap_create + pcap_set_buffer_size + pcap_activate
    handle_ = pcap_create(iface.c_str(), errbuf);
    if (!handle_) {
        LOG_ERROR("pcap_create failed: {}", errbuf);
        return false;
    }
    
    // Configurar buffer size desde JSON (default: 8MB para ARM64)
    int buffer_size = config_.buffer_size_mb * 1024 * 1024;
    if (pcap_set_buffer_size(handle_, buffer_size) != 0) {
        LOG_WARN("pcap_set_buffer_size failed, using kernel default");
    }
    
    // Timeout de lectura (ms) — crítico para latencia
    pcap_set_timeout(handle_, config_.read_timeout_ms);
    
    // Promiscuo si el filtro lo requiere
    pcap_set_promisc(handle_, config_.promiscuous ? 1 : 0);
    
    // Activar
    int status = pcap_activate(handle_);
    if (status < 0) {
        LOG_ERROR("pcap_activate failed: {}", pcap_geterr(handle_));
        pcap_close(handle_);
        handle_ = nullptr;
        return false;
    }
    
    // Aplicar BPF filter si existe
    if (!config_.filter_expression.empty()) {
        struct bpf_program fp;
        if (pcap_compile(handle_, &fp, config_.filter_expression.c_str(), 
                        1, PCAP_NETMASK_UNKNOWN) == 0) {
            pcap_setfilter(handle_, &fp);
            pcap_freecode(&fp);
        }
    }
    
    return true;
}
```

**Configuración JSON:**

```json
{
  "capture": {
    "interface": "eth1",
    "buffer_size_mb": 8,
    "read_timeout_ms": 10,
    "promiscuous": true,
    "filter_expression": "tcp or udp"
  }
}
```

**Valores recomendados por plataforma:**

| Plataforma | `buffer_size_mb` | Justificación |
|------------|-----------------|---------------|
| x86 (Variant A) | N/A (usa eBPF) | No aplica |
| x86 (Variant B) | 16 | RAM abundante, maximizar throughput |
| ARM64/RPi4 | 8 | Balance RAM vs throughput |
| ARM64/RPi5 | 16 | Más RAM disponible |

**Acción inmediata:** Implementar antes del benchmark cloud ARM64 (Q4 DAY 140). Sin esto, los números no son comparables con Variant A.

---

### Q3 — Clasificador de warnings: TinyLlama vs grep/awk

**Hipótesis:** Usar un LLM para clasificar warnings de compilación es técnicamente posible pero probablemente over-engineering para un problema con estructura determinista.

**Veredicto: **grep/awk determinista es la solución correcta.** TinyLlama añade latencia, no-determinismo, y dependencia de GPU/RAM sin beneficio proporcional.**

**Análisis comparativo:**

| Criterio | grep/awk | TinyLlama |
|----------|----------|-----------|
| **Latencia** | < 100 ms | > 5 s (carga modelo + inferencia) |
| **Determinismo** | 100% | Probabilístico — puede clasificar mal |
| **Coste computacional** | Cero | GPU/CPU significativo |
| **Mantenimiento** | Lista de patrones | Retraining si el formato de warnings cambia |
| **Explicabilidad** | Total — regex visible | Caja negra — "el modelo dice que es ignorable" |
| **Valor añadido** | Ninguno (es suficiente) | Potencialmente puede detectar patrones nuevos |

**Estructura determinista del problema:**

Los warnings de compilación en aRGus caen en categorías disjuntas por origen:

```bash
#!/bin/bash
# classify_warnings.sh — determinista, 0 dependencias externas

while IFS= read -r line; do
    if [[ "$line" =~ ^.*"/tmp/faiss/".* ]] || \
       [[ "$line" =~ ^.*"/tmp/onnx/".* ]] || \
       [[ "$line" =~ ^.*"llama.cpp".* ]] || \
       [[ "$line" =~ ^.*"protobuf-generated".* ]]; then
        echo "THIRD_PARTY_IGNORABLE: $line"
    elif [[ "$line" =~ ^.*"defender/src/".* ]] || \
          [[ "$line" =~ ^.*"argus-".* ]]; then
        echo "OWN_CODE_BLOCKER: $line"
    else
        echo "REVIEW_REQUIRED: $line"
    fi
done < <(make all 2>&1 | grep "warning:")
```

**Cuándo TinyLlama sí añade valor:**

- Clasificación de **logs de runtime** (patrones de ataque no conocidos a priori)
- Clasificación de **alertas de Falco** (comportamiento anómalo contextual)
- Clasificación de **tickets de incidente** (priorización basada en descripción textual)

Para warnings de compilación, el espacio de patrones es finito y conocido. Un LLM es un cañón para matar una mosca.

**Recomendación:** Implementar `classify_warnings.sh` como target de Makefile:

```makefile
check-warnings:
	@./scripts/classify_warnings.sh
	@if grep -q "OWN_CODE_BLOCKER:" /tmp/warnings_classified.txt; then \
		echo "ERROR: Blocker warnings found in own code"; \
		exit 1; \
	fi
```

**Regla permanente propuesta:**

> **RULE-WARNING-CLASSIFICATION-001:** Los warnings de compilación se clasifican por origen (path del fichero) mediante script determinista. Los warnings en código propio (`src/`, `include/`) son bloqueantes. Los warnings en código de terceros (`/tmp/`, `vendor/`, generado) son revisables periódicamente. Ningún LLM participa en la clasificación de warnings de build.

---

### Q4 — Auditoría automática de dependencias Makefile

**Hipótesis:** El bug `seed-client-build` revela que el Makefile tiene dependencias implícitas que solo funcionan por estado residual en el filesystem.

**Veredicto: **EMECAS es suficiente como gate, pero insuficiente como detector temprano.** Añadir `make check-deps` como verificación rápida (< 10s) que complementa, no reemplaza, al EMECAS.**

**Análisis del bug:**

El problema ocurrió porque:
1. `seed-client-build` generaba `libseed-client.a`
2. Otros targets dependían de `libseed-client.a` pero no declaraban explícitamente la dependencia en el Makefile
3. En una VM con `libseed-client.a` residual, el build funcionaba
4. En una VM limpia, el build fallaba porque `seed-client-build` no se ejecutaba automáticamente

**Esto es un bug de Makefile, no de código.** Los Makefiles clásicos son propensos a este tipo de errores porque las dependencias se declaran manualmente.

**Solución: Makefile auto-generado o verificación explícita**

Opción A: CMake (ya se usa parcialmente)
- CMake genera dependencias automáticamente
- Pero el proyecto usa Makefile como orquestador principal

Opción B: Verificación explícita de dependencias

```makefile
# check-deps — verifica que todas las librerías existen antes de linkar
check-deps:
	@for lib in $(REQUIRED_LIBS); do \
		if [ ! -f "$$lib" ]; then \
			echo "ERROR: Dependency $$lib missing. Run 'make seed-client-build' first."; \
			exit 1; \
		fi; \
	done
	@echo "All dependencies present."

# Integrar en targets que linkan
argus-sniffer: check-deps $(OBJS) $(REQUIRED_LIBS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)
```

**Limitación:** `check-deps` verifica que los ficheros existen, no que el grafo de dependencias es correcto. Un Makefile mal escrito puede tener `check-deps` correcto pero `make -j` paralelo falla por orden incorrecto.

**Solución completa: `make clean-all` + `make all` en CI**

```yaml
# .github/workflows/ci.yml
dependency-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Clean build
      run: make clean-all  # Elimina TODOS los artefactos
    - name: Fresh build
      run: make all -j$(nproc)
    - name: Fresh test
      run: make test-all
```

**Esto es equivalente a EMECAS pero en CI, sin necesidad de Vagrant.**

**Recomendación:**

| Verificación | Frecuencia | Método | Coste |
|-------------|-----------|--------|-------|
| `make check-deps` | Cada build local | Verificación rápida de ficheros | < 1s |
| `make clean-all && make all` | Pre-merge CI | Build desde cero | ~5 min |
| EMECAS completo | Pre-release | VM destruida y reconstruida | ~30 min |

**Acción inmediata:** Añadir `check-deps` al Makefile como target rápido. Configurar CI con `make clean-all && make all` como gate pre-merge. Mantener EMECAS como gate pre-release.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | Identidad compartida correcta; documentar mutual exclusividad | Añadir `_comment` en JSON; crear `DEBT-SNIFFER-DUAL-IDENTITY-001` si se necesita simultaneidad futura |
| **Q2** | **Pre-FEDER bloqueante**; implementar `pcap_create()` + `pcap_set_buffer_size()` | Refactorizar `PcapBackend::open()`; añadir `buffer_size_mb` al JSON |
| **Q3** | grep/awk determinista; rechazar TinyLlama para warnings de build | Implementar `scripts/classify_warnings.sh`; añadir target `check-warnings` |
| **Q4** | `check-deps` rápido + CI `clean-all` pre-merge; EMECAS pre-release | Añadir `check-deps` target; configurar CI con `make clean-all && make all` |

**Moción:** Propongo que el DAY 142 priorice Q2 (`buffer_size_mb`) como única tarea bloqueante para el benchmark. Q1, Q3 y Q4 son documentación/automatización que no afectan la línea crítica de FEDER. El buffer de libpcap es el único item que, si se omite, invalida los números de throughput en ARM64.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*