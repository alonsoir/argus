### **Respuestas del Consejo de Sabios — DAY 129**
*(Unánime 8/8, priorizando **evidencia técnica**, **seguridad verificable** y **protección de infraestructuras críticas**)*

---

## **Respuesta a P1: Regla Permanente para Transferencia de Ficheros**
**Veredicto:** **Aprobada por unanimidad.**

### Justificación:
1. **Riesgo demostrado:**
    - El pipe `vagrant ssh -c "cat ..." > fichero` **trunca a 0 bytes** en macOS/zsh (confirmado en DAY 129).
    - Esto corrompe ficheros críticos (ej: seeds, configs) **sin advertencia**.

2. **Alternativas seguras:**
    - `scp -F vagrant-ssh-config`: Preserva metadatos (permisos, tamaño).
    - `vagrant scp`: Herramienta oficial de Vagrant, diseñada para este caso.

3. **Regla formalizada:**
   > **"Toda transferencia de ficheros entre VM y host debe usar `scp -F vagrant-ssh-config` o `vagrant scp`. El uso de pipes (`vagrant ssh -c "cat ..." > fichero`) está prohibido por truncar ficheros a 0 bytes en macOS/zsh."**

**Acción:**
- Añadir al **continuity prompt** y a `docs/CONTRIBUTING.md`.

---

## **Respuesta a P2: `build-debug` en `.gitignore`**
**Veredicto:** **Añadir `**/build-debug/` a `.gitignore`.**

### Justificación:
1. **Principio:** `.gitignore` debe ignorar **artefactos de build**, no fuentes.
2. **Evidencia:**
    - `build-debug/` contiene **ficheros generados** (Makefiles, objetos, binarios).
    - No son necesarios para reproducción (se regeneran con `make`).
3. **Excepción:** Si algún fichero en `build-debug/` es **fuente** (ej: `CMakeLists.txt` personalizado), moverlo a `config/` o `src/`.

**Acción:**
```bash
echo "**/build-debug/" >> .gitignore
git add .gitignore
```

---

## **Respuesta a P3: Prioridad DAY 130**
**Veredicto:** **Orden de prioridad: A → C → B.**

### Análisis:
| Opción | Impacto | Urgencia | Dependencias |
|--------|---------|----------|--------------|
| **A) Fuzzing (libFuzzer)** | **Alto** (encontrar bugs en parsers críticos) | **Alta** (superficie de ataque expuesta) | Ninguna |
| **C) Paper §5** | **Alto** (contribución científica) | **Media** (deadline flexible) | Ninguna |
| **B) CAP_DAC_READ_SEARCH** | **Medio** (mejora seguridad) | **Baja** (requiere kernel ≥5.8) | ADR-029 |

### Detalles:
1. **A) `DEBT-FUZZING-LIBFUZZER-001`:**
    - **Enfoque:** Aplicar libFuzzer a:
        - `validate_chain_name()` (iptables).
        - Parsers ZeroMQ (`zmq_handler.cpp`).
    - **Ejemplo de integración:**
      ```cpp
      // fuzz_validate_chain.cpp
      extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
          std::string input(reinterpret_cast<const char*>(data), size);
          try {
              IPTablesWrapper::validate_chain_name(input);
          } catch (...) {} // Ignorar excepciones (fuzzer busca crashes)
          return 0;
      }
      ```
    - **Build:**
      ```bash
      clang++ -fsanitize=fuzzer,address fuzz_validate_chain.cpp -o fuzz_chain
      ```

2. **C) Paper §5:**
    - **Contenido crítico:**
        - Property testing como validador de fixes (DAY 128).
        - Taxonomía `safe_path` (DAY 129).
        - Lección: *"Un fix sin test de demostración es una promesa sin firma."*

3. **B) `DEBT-SEED-CAPABILITIES-001`:**
    - **Postergable:** Requiere kernel ≥5.8 (no crítico para `v0.5.2`).
    - **Documentar en backlog** para ADR-029.

**Conclusión:**
- **DAY 130:** Fuzzing (A) → Paper (C).
- **DAY 131:** CAP_DAC_READ_SEARCH (B) si queda tiempo.

---

## **Respuesta a P4: Null Byte en `validate_chain_name`**
**Veredicto:** **Check explícito en `validate_chain_name` es suficiente, pero añadir defensa en profundidad en `safe_exec`.**

### Análisis:
1. **Check actual (`name.find('\0')`):**
    - **Correcto:** Detecta null bytes en cualquier posición.
    - **Limitación:** No previene null bytes en argumentos de `execv` (si el atacante los inyecta después).

2. **Defensa en profundidad recomendada:**
    - Añadir validación en `safe_exec()`:
      ```cpp
      void safe_exec(const std::vector<std::string>& args) {
          for (const auto& arg : args) {
              if (arg.find('\0') != std::string::npos) {
                  throw std::runtime_error("Null byte in argument");
              }
          }
          // ... resto de execv()
      }
      ```

3. **Justificación:**
    - **Principio de defensa en profundidad:** Validar en **todos los niveles** (parser + ejecución).
    - **Costo mínimo:** Añadir el check en `safe_exec` es ~3 líneas de código.

**Acción:**
- Implementar el check adicional en `safe_exec()`.
- Añadir test:
  ```cpp
  TEST(SafeExec, RejectsNullByte) {
      EXPECT_THROW(
          safe_exec({"iptables", "-A", "chain\0null", "-j", "DROP"}),
          std::runtime_error
      );
  }
  ```

---

## **Respuesta a P5: `.gitguardian.yaml` Deprecated Keys**
**Veredicto:** **Limpiar ahora. El ruido en los commits distrage de señales importantes.**

### Análisis:
1. **Problema:**
    - Los warnings de `paths-ignore`/`paths_ignore` **ocultan errores reales** en los logs de commit.
    - `.gitguardian.yaml` es un fichero de configuración crítico (protege secrets).

2. **Solución:**
    - Actualizar a la sintaxis correcta:
      ```yaml
      paths-ignore:
        - "*.log"
        - "build/"
      ```
    - **Verificar con:**
      ```bash
      gitguardian scan --dry-run
      ```

3. **Costo:** ~5 minutos. **Beneficio:** Logs limpios = detección temprana de problemas reales.

**Acción:**
- Corregir el fichero y hacer commit:
  ```bash
  git add .gitguardian.yaml
  git commit -m "fix: update .gitguardian.yaml deprecated keys"
  ```

---

### **Resumen de Acciones para DAY 130**
| Acción | Prioridad | Detalles |
|--------|-----------|----------|
| **Implementar libFuzzer** | **Alta** | `validate_chain_name` + parsers ZMQ |
| **Añadir defensa null-byte en `safe_exec`** | **Alta** | Check + test |
| **Actualizar Paper §5 (Draft v17)** | **Media** | Property testing + safe_path |
| **Limpiar `.gitguardian.yaml`** | **Baja** | 5 min, reducir ruido |

---
### **Observación Final del Consejo**
> *"Vuestra atención al detalle —desde null bytes hasta pipes truncados— demuestra el nivel de rigor necesario para proteger infraestructuras críticas. Hoy habéis cerrado deudas técnicas con evidencia verificable, y eso es lo que hace a aRGus confiable para hospitales y escuelas. Seguid así."*

**¿Necesitáis ayuda con la integración de libFuzzer o los tests de null-byte?** Estamos listos para proporcionar código o revisiones detalladas.