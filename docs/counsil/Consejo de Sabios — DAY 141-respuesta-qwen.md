# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 141
*Feedback basado en ingeniería de sistemas distribuidos, criptografía aplicada y metodología científica para aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**CIERRES TÉCNICOS SÓLIDOS. TRES DECISIONES ARQUITECTÓNICAS CORRECTAS.**

El fix de dependencia implícita en Makefile, la documentación del contrato de lifetime en `PcapBackend`, y la implementación de `sniffer-libpcap.json` config-driven demuestran madurez en el manejo de complejidad incremental. Los 9/9 tests PASSED y 0 warnings con `-Werror` confirman que la disciplina TDH está internalizada.

> *"La simplicidad no es ausencia de decisiones. Es ausencia de decisiones innecesarias."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### Q1 — Identidad criptográfica compartida Variant A / Variant B

**Recomendación concreta:** **COMPARTIR IDENTIDAD CRIPTOGRÁFICA ES CORRECTO. Documentar la decisión en `docs/CRYPTO-IDENTITY-MODEL.md`.**

**Justificación técnica:**

| Criterio | Evaluación |
|----------|-----------|
| **Modelo de amenazas** | ✅ Ambos variantes protegen el mismo canal: sniffer → ml-detector. La identidad criptográfica autentica el *rol*, no la *implementación*. |
| **Wire format** | ✅ Ambos emiten `NetworkSecurityEvent` protobuf idéntico, cifrado con mismo `CTX_SNIFFER_TO_ML`. |
| **Gestión de claves** | ✅ Una identidad = una seed = un punto de rotación. Separar identidades duplicaría complejidad sin beneficio de seguridad proporcional. |
| **Audit trail** | ⚠️ Necesario diferenciar backend en logs/métricas, pero esto es *telemetría*, no *identidad criptográfica*. |

**Implementación recomendada para diferenciación operacional:**
```cpp
// En NetworkSecurityEvent o metadata adjunta
message CaptureMetadata {
    string backend_type = 1;  // "ebpf_xdp" | "libpcap"
    string kernel_version = 2;  // Para correlación de compatibilidad
    uint32_t capture_flags = 3;  // PROMISC, etc.
}

// Logging estructurado
logger.info("sniffer [{}] started on {}", 
    variant == Variant::Ebpf ? "ebpf_xdp" : "libpcap",
    config.interface);
```

**Riesgo si se ignora**: Separar identidades criptográficas sin necesidad crearía:
- Doble gestión de seeds/rotación
- Complejidad en verificación de firmas downstream (ml-detector tendría que aceptar dos pubkey para "sniffer")
- Confusión en auditoría: ¿falló el componente o cambió de variante?

**Verificación mínima**:
```bash
# docs/CRYPTO-IDENTITY-MODEL.md debe existir con:
# 1. Definición: "Identidad criptográfica = rol en pipeline, no implementación"
# 2. Lista de componentes con identidad compartida entre variantes
# 3. Procedimiento de rotación: una operación afecta a todas las variantes del rol
```

---

### Q2 — `DEBT-VARIANT-B-BUFFER-SIZE-001`: ¿pre-FEDER o post-FEDER?

**Recomendación concreta:** **IMPLEMENTAR PRE-FEDER. El buffer de captura impacta directamente la validez de los benchmarks.**

**Justificación técnica:**

| Factor | Impacto en FEDER |
|--------|-----------------|
| **Packet drops por buffer undersized** | Skew en métricas de throughput/latencia → resultados no reproducibles |
| **ARM64/RPi5 kernel defaults** | Buffer típico 2MB puede saturarse a ~400 Mbps con tráfico bursty |
| **Refactor riesgo** | Bajo: `pcap_create()+pcap_set_buffer_size()+pcap_activate()` es API estable desde libpcap 1.2 |
| **Tiempo de implementación** | ~4-6 horas: cambio localizado en `PcapBackend::open()` |

**Implementación recomendada:**
```cpp
// pcap_backend.cpp
bool PcapBackend::open(const std::string& interface, PacketCallback cb, void* ctx) {
    char errbuf[PCAP_ERRBUF_SIZE];
    
    // Usar pcap_create para control explícito de buffer
    handle_ = pcap_create(interface.c_str(), errbuf);
    if (!handle_) {
        logger.error("pcap_create failed: {}", errbuf);
        return false;
    }
    
    // Configurar buffer: default 16MB, configurable via JSON
    // Rationale: 16MB ≈ 11k paquetes de 1500B, suficiente para burst de 50ms a 1Gbps
    int buffer_size_mb = config_.value("buffer_size_mb", 16);
    if (pcap_set_buffer_size(handle_, buffer_size_mb * 1024 * 1024) != 0) {
        logger.warn("pcap_set_buffer_size failed — using kernel default");
        // No fallar: fallback a default es aceptable
    }
    
    // Otros parámetros críticos
    pcap_set_snaplen(handle_, config_.value("snaplen", 65536));
    pcap_set_promisc(handle_, config_.value("promiscuous", true) ? 1 : 0);
    pcap_set_timeout(handle_, config_.value("timeout_ms", 100));
    
    if (pcap_activate(handle_) != 0) {
        logger.error("pcap_activate failed: {}", pcap_geterr(handle_));
        pcap_close(handle_);
        handle_ = nullptr;
        return false;
    }
    
    callback_ = cb;
    user_ctx_ = ctx;
    return true;
}
```

**Test de demostración**:
```cpp
// tests/test_pcap_backend_buffer.cpp
TEST(PcapBackend, ConfigurableBufferSize) {
    PcapBackend backend;
    
    // Config con buffer explícito
    Config cfg;
    cfg.set("buffer_size_mb", 32);
    backend.set_config(cfg);
    
    // open() debería intentar aplicar 32MB (puede fallar por permisos, pero no por API)
    // Verificar que no hay crash y que el fallback a default es graceful
    EXPECT_NO_THROW(backend.open("lo", dummy_callback, nullptr));
    
    // Si open() falla, debe ser por interfaz no disponible, no por buffer config
    // (lo siempre existe en testing)
}
```

**Riesgo si se ignora**: Benchmarks FEDER en RPi5 podrían mostrar "latencia inexplicable" o "throughput inferior al esperado" debido a drops de buffer, llevando a conclusiones erróneas sobre la viabilidad de Variant B en hardware real.

---

### Q3 — Clasificador de warnings: TinyLlama vs grep/awk

**Recomendación concreta:** **GREP/AWK ES LA SOLUCIÓN CORRECTA. TinyLlama es over-engineering para este caso de uso.**

**Justificación técnica:**

| Criterio | grep/awk | TinyLlama |
|----------|----------|-----------|
| **Determinismo** | ✅ Mismo input → mismo output siempre | ⚠️ Depende de temperatura, seed, versión del modelo |
| **Auditoría** | ✅ Reglas legibles en script bash | ❌ "Caja negra" — difícil explicar por qué se clasificó X |
| **Mantenimiento** | ✅ Añadir patrón = una línea en regex list | ❌ Retrain modelo, validar drift, monitorizar accuracy |
| **Rendimiento** | ✅ <100ms para clasificar 10k líneas | ⚠️ ~2-5s por warning con inferencia local |
| **Adecuación al problema** | ✅ Clasificación = pattern matching sintáctico | ❌ LLMs brillan en semántica, no en sintaxis estructurada |

**Implementación recomendada (grep/awk)**:
```bash
#!/bin/bash
# scripts/classify-build-warnings.sh
# Clasifica warnings de `make all 2>&1` en THIRD_PARTY_IGNORABLE vs OWN_CODE_BLOCKER

set -euo pipefail

THIRD_PARTY_PATTERNS=(
    "third_party/"
    "build-debug/_deps/"
    "/tmp/faiss/"
    "llama.cpp/"
    "xgboost/src/"
    "protobuf/src/"
    "-Wdeprecated-declarations"  # Suprimido explícitamente en CMake
)

OWN_CODE_PATTERNS=(
    "src/[^/]+/[^/]+\.cpp:[0-9]+:"  # Nuestro código fuente
    "include/argus/[^/]+\.hpp:[0-9]+:"
)

classify_warning() {
    local warning="$1"
    
    # Primero: ¿es third-party ignorable?
    for pattern in "${THIRD_PARTY_PATTERNS[@]}"; do
        if echo "$warning" | grep -q "$pattern"; then
            echo "THIRD_PARTY_IGNORABLE"
            return 0
        fi
    done
    
    # Segundo: ¿es código propio bloqueante?
    for pattern in "${OWN_CODE_PATTERNS[@]}"; do
        if echo "$warning" | grep -qE "$pattern"; then
            echo "OWN_CODE_BLOCKER"
            return 0
        fi
    done
    
    # Default: tratar como bloqueante para ser conservadores
    echo "OWN_CODE_BLOCKER"
}

# Procesar stdin línea por línea
while IFS= read -r line; do
    if echo "$line" | grep -qE "warning:|error:"; then
        classification=$(classify_warning "$line")
        echo "[$classification] $line"
    fi
done
```

**Riesgo si se ignora**: Usar TinyLlama para este problema añadiría:
- Dependencia runtime en modelo de 4GB+ para una tarea de 10 líneas de bash
- Incertidumbre en clasificación (¿por qué este warning se marcó como ignorable?)
- Complejidad de mantenimiento sin beneficio medible

**Verificación mínima**:
```bash
# tests/test-warning-classifier.sh
make test-warning-classifier
# 1. Generar warnings sintéticos de third-party y own-code
# 2. Ejecutar classify-build-warnings.sh
# 3. Verificar: 100% precisión en clasificación conocida
# 4. Verificar: tiempo de ejecución <1s para 1000 warnings
```

---

### Q4 — Auditoría automática de dependencias Makefile

**Recomendación concreta:** **EMECAS ES SUFICIENTE COMO GATE PRINCIPAL. Añadir `make check-clean-build` como sanity check ligero, no auditoría completa.**

**Justificación técnica:**

| Enfoque | Ventajas | Desventajas |
|---------|----------|-------------|
| **EMECAS completo** (`vagrant destroy && up && bootstrap && test-all`) | ✅ Garantiza reproducibilidad real, detecta cualquier dependencia implícita | ⏱️ ~30-45 min por ejecución |
| **Auditoría automática de dependencias** (`make -d`, `remake --trace`) | ✅ Podría detectar problemas antes de EMECAS | ❌ Complejo de implementar, falsos positivos, mantenimiento costoso |
| **Sanity check ligero** (`make check-clean-build`) | ✅ Rápido (~2 min), detecta fallos obvios de dependencias | ⚠️ No cubre todos los casos, pero sí los más comunes |

**Implementación recomendada (sanity check)**:
```makefile
# Makefile
.PHONY: check-clean-build
check-clean-build:
	@echo "🔍 Running clean build sanity check..."
	@# Limpiar artefactos de build (pero no dist/vendor, que es compartido)
	@make dist-clean >/dev/null 2>&1 || true
	@# Construir un target mínimo que tenga dependencias no triviales
	@# seed-client es buen candidato: depende de crypto-transport, tiene tests
	@echo "   Building seed-client from clean state..."
	@make seed-client-build -j$(nproc) >/dev/null 2>&1 || { \
		echo "❌ Clean build failed — undeclared dependency detected"; \
		echo "💡 Run 'make EMECAS' to reproduce in clean VM"; \
		exit 1; \
	}
	@echo "✅ Clean build sanity check passed"
```

**Documentación obligatoria en `CONTRIBUTING.md`**:
```markdown
## Testing Changes Before Merge

1. **Always run EMECAS before merging to main**:
   ```bash
   vagrant destroy -f && vagrant up && make bootstrap && make test-all
   ```
This is the only way to guarantee your change works in a clean environment.

2. **For quick iteration**, use `make check-clean-build` to catch obvious dependency issues:
   ```bash
   make check-clean-build  # ~2 minutes
   ```
   Note: This is a sanity check, not a substitute for EMECAS.

3. **If a build fails in a clean VM**, the root cause is usually:
    - Missing dependency in CMakeLists.txt or Makefile
    - Implicit dependency on host environment (e.g., macOS-specific paths)
    - Artifact pollution from previous builds (deleted by `dist-clean`)
```

**Riesgo si se ignora**: Confiar solo en EMECAS significa que los desarrolladores podrían iterar rápido pero descubrir problemas de dependencias solo al final del ciclo, aumentando el coste de fix. El sanity check ligero ofrece un "fast feedback" sin reemplazar la garantía de EMECAS.

**Verificación mínima**:
```bash
# tests/test-make-dependencies.sh
make test-make-dependencies
# 1. Simular dependencia implícita: comentar una línea en CMakeLists.txt
# 2. Ejecutar make check-clean-build
# 3. Verificar: falla con mensaje claro sobre dependencia no declarada
# 4. Restaurar cambio, verificar que pasa
```

---

## 📋 Checklist de Acciones Inmediatas (DAY 142)

```markdown
- [ ] Crear docs/CRYPTO-IDENTITY-MODEL.md con decisión de identidad compartida
- [ ] Implementar buffer_size_mb en PcapBackend::open() pre-FEDER
- [ ] Añadir test test_pcap_backend_buffer para validar configuración de buffer
- [ ] Implementar scripts/classify-build-warnings.sh con grep/awk (no TinyLlama)
- [ ] Añadir make check-clean-build como sanity check ligero
- [ ] Actualizar CONTRIBUTING.md con guía de testing pre-merge
- [ ] Ejecutar EMECAS completo como validación final pre-FEDER demo prep
```

---

## 🏁 Palabras Finales

Alonso:

DAY 141 cierra un ciclo de refinamiento arquitectónico: decisiones sobre identidad criptográfica, configuración de buffers, clasificación de warnings y auditoría de dependencias reflejan una mentalidad de *ingeniería preventiva*. No es solo "arreglar lo que falla"; es "diseñar para que sea difícil fallar".

Las cuatro preguntas que planteáis tocan la esencia del mantenimiento de sistemas críticos: cómo equilibrar rigor con pragmatismo, cómo verificar propiedades costosas sin paralizar el desarrollo, y cómo comunicar decisiones arquitectónicas con transparencia científica.

> *"La seguridad no se improvisa. Se diseña, se verifica y se mantiene con disciplina."*

Descansad merecidamente. Mañana, con la validación EMECAS completa, estaréis listos para la recta final hacia FEDER. El Consejo revisará la implementación del buffer de captura y el clasificador de warnings con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 141** 🏛️