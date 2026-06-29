Alonso, gracias por incluirme como miembro del Consejo de Sabios con atribución correcta. Soy **DeepSeek** — no Qwen, no Grok — y valoro profundamente tu transparencia al documentar cada decisión técnica con rigor científico.

He analizado FEAT-PLUGIN-CRYPTO-1 con atención. Es una decisión arquitectónica crítica que define la evolución a largo plazo del sistema de plugins. Mi recomendación es clara:

---

## 🔑 Respuesta a Q1 — Opción A es la decisión correcta

✅ **Recomendación: Opción A (`MessageContext` nuevo) — no Opción B**

**Razonamiento técnico:**

| Criterio | Opción A (`MessageContext`) | Opción B (ampliar `PacketContext`) |
|----------|-----------------------------|-------------------------------------|
| **Separación de capas** | ✅ Correcta: red ≠ transporte | ❌ Violada: mezcla semántica |
| **Testing aislado** | ✅ Plugin crypto testeable sin paquetes | ❌ Requiere PacketContext falso |
| **Extensibilidad futura** | ✅ Nuevo hook para cada capa (ej: aplicación) | ❌ `PacketContext` se hincha indefinidamente |
| **Claridad para devs** | ✅ `plugin_process_message()` = cifrado | ❌ ¿Por qué crypto necesita `src_ip`? |
| **Deuda técnica** | ✅ Una vez pagada, API estable | ❌ Acumulativa — cada nuevo hook agrava la impureza |

**El argumento decisivo:**  
El cifrado **no es una feature de red** — es una transformación de *transporte*. Forzarlo en `PacketContext` viola el principio de responsabilidad única que justificó la arquitectura de plugins desde ADR-012. La pureza semántica no es academicismo — es la diferencia entre un sistema mantenible y uno que acumula deuda técnica hasta colapsar.

**Trade-off honesto:**  
Sí, Opción A requiere un breaking change. Pero este es el **momento correcto** para pagarlo:
- Solo existe 1 plugin real (`libplugin_hello.so`)
- El paper aún no está publicado — no hay usuarios externos bloqueados
- PHASE 2 es el momento natural para evolucionar la API

Postergar el breaking change a PHASE 3 o 4 sería más costoso: más plugins existentes, más usuarios dependientes, mayor riesgo de regresión.

---

## 🔐 Respuesta a Q2 — Gestión del breaking change

✅ **Recomendación: `plugin_process_message()` es OPCIONAL en PLUGIN_API_VERSION=1 → OBLIGATORIO en PLUGIN_API_VERSION=2**

**Estrategia de transición:**

```cpp
// plugin_loader.cpp — dispatch inteligente
if (dlsym(handle, "plugin_process_message") != nullptr) {
    // Plugin PHASE 2 — usa MessageContext
    invoke_message_hook(ctx_msg);
} else {
    // Plugin PHASE 1 — solo PacketContext
    invoke_packet_hook(ctx_pkt);
}
```

**Ventajas:**
- Plugins PHASE 1 siguen funcionando sin cambios
- Plugins PHASE 2 pueden implementar ambos hooks para máxima compatibilidad
- `PLUGIN_API_VERSION` se incrementa a 2 cuando se retire el fallback PHASE 1 (PHASE 3)

**Documentación crítica en `plugin_api.h`:**
```c
// PLUGIN_API_VERSION=1 — PHASE 1 (feature extraction only)
//   Required: plugin_process_packet()
//   Optional: plugin_process_message() — if present, used for transport layer

// PLUGIN_API_VERSION=2 — PHASE 2+ (multi-layer plugins)
//   Required: plugin_process_message() for transport-layer plugins
//   Required: plugin_process_packet() for network-layer plugins
//   Rationale: semantic separation of concerns (ADR-024)
```

Esto evita el "big bang" del breaking change mientras prepara el camino para una API limpia en PHASE 3.

---

## ⚙️ Respuesta a Q3 — Estrategia de migración dual-mechanism

✅ **Recomendación: Estrategia correcta con un refinamiento crítico**

Tu propuesta de transición es sólida:

```
PHASE 2a: CryptoTransport (core) + CryptoPlugin (paralelo)
          Gate: TEST-INTEG-4 — round-trip idéntico cifrado/descifrado

PHASE 2b: CryptoTransport desactivado (config flag)
          Gate: 72h sin regresiones en bare-metal

PHASE 2c: CryptoTransport eliminado del código
```

**Refinamiento crítico — el gate de PHASE 2a debe incluir:**

```bash
# TEST-INTEG-4a: round-trip idéntico (tu gate actual)
sniffer → CryptoPlugin → ml-detector → CryptoPlugin → sniffer
assert ciphertext_bytes == original_ciphertext_bytes

# TEST-INTEG-4b: semantic equivalence (nuevo gate obligatorio)
sniffer → CryptoTransport → ml-detector → CryptoTransport → sniffer
sniffer → CryptoPlugin    → ml-detector → CryptoPlugin    → sniffer
assert ml_detector_sees_identical_features_in_both_paths
```

**¿Por qué TEST-INTEG-4b es obligatorio?**  
Un plugin de cifrado podría producir ciphertexts idénticos pero con nonces diferentes, timestamps alterados, o metadatos modificados que afecten la lógica del ml-detector (ej: `pipeline_tracking.total_processing_latency`). La equivalencia semántica — no solo byte-a-byte — es el verdadero gate de seguridad.

**Riesgo no considerado en tu propuesta:**  
Si el plugin falla durante el descifrado (MAC failure), ¿qué hace el componente receptor?
- ❌ **Incorrecto:** Continuar procesando el payload cifrado como si fuera plaintext → corrupción silenciosa
- ✅ **Correcto (ADR-022 fail-closed):** `std::terminate()` inmediato — el sistema prefiere no funcionar antes que funcionar inseguro

Este comportamiento debe validarse explícitamente en TEST-INTEG-4c:
```bash
# TEST-INTEG-4c: fail-closed on MAC failure
corrupt_ciphertext_tag(ciphertext);
ml_detector.receive(ciphertext);
assert process_terminated_with_signal(SIGABRT);
```

---

## 🔒 Restricciones ADR-012 y ADR-022 — validación

| Restricción | Aplicación al plugin crypto | Veredicto |
|-------------|-----------------------------|-----------|
| **ADR-012:** Plugins no deciden bloqueo | ✅ El plugin crypto transforma mensajes, no decide bloquear | Compatible |
| **ADR-022:** Fail-closed | ✅ MAC failure → `std::terminate()` (no modo degradado) | Obligatorio |

El plugin crypto es **compatible con ambas restricciones** porque:
1. No toma decisiones de seguridad — solo aplica transformaciones criptográficas
2. Falla de forma segura (terminación) ante corrupción detectada

---

## 📐 Propuesta de ADR-024 (recomendada)

Esta decisión merece su propio ADR para documentar la evolución de la API:

```
ADR-024: Multi-Layer Plugin Architecture
─────────────────────────────────────────
Status: PROPOSED
Date: 2026-03-30

Context:
PHASE 1 plugins operate at network layer (PacketContext). PHASE 2 requires
transport-layer plugins (cryptography, compression) and potentially
application-layer plugins (RAG skills). A single context type cannot
semantically represent all layers without impurity.

Decision:
Introduce layer-specific contexts with dedicated hooks:
- PacketContext → plugin_process_packet()   [network layer]
- MessageContext → plugin_process_message() [transport layer]
- SkillContext → plugin_execute_skill()     [application layer, future]

Consequences:
+ Semantic purity: each plugin operates in its natural layer
+ Testability: transport plugins testable without network stack
+ Extensibility: new layers added without polluting existing contexts
- Breaking change: requires PLUGIN_API_VERSION bump (managed via optional
  symbol detection in PHASE 2 transition)
```

---

## 🏛️ Conclusión honesta

FEAT-PLUGIN-CRYPTO-1 es una decisión de **diseño a largo plazo**, no solo una refactorización técnica. La Opción A paga una deuda arquitectónica pequeña hoy para evitar una deuda técnica insostenible mañana. La pureza semántica en sistemas de seguridad no es academicismo — es la diferencia entre un sistema que se puede auditar y uno que se vuelve una caja negra.

Tu estrategia de transición dual-mechanism es sólida, pero debe incluir:
1. ✅ Gate de equivalencia semántica (no solo byte-a-byte)
2. ✅ Gate de fail-closed explícito ante MAC failure
3. ✅ Documentación clara del optional → mandatory transition path

Bien hecho al plantear esta consulta *antes* de implementar. Eso es *Via Appia Quality*: diseñar la piedra antes de colocarla.

🛡️ — DeepSeek, miembro del Consejo de Sabios  
*Piano piano — cada capa en su lugar, cada contexto con su semántica.*