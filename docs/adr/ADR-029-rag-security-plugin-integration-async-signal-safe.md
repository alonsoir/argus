# ADR-029: rag-security Plugin Integration (g_plugin_loader + async-signal-safe)

**Estado:** APROBADO
**Fecha:** 2026-04-08
**Autor:** Alonso Isidoro Román
**Rama:** `feature/plugin-crypto`
**Aprobado por:** Consejo de Sabios DAY 110 — REC-1 (DeepSeek, unanimidad implícita)
(Claude · ChatGPT5 · DeepSeek · Gemini · Grok · Qwen)
**Componentes afectados:** `rag-security`
**ADR relacionados:**
- ADR-012 (Plugin Loader Architecture)
- ADR-023 (CryptoTransport)
- ADR-025 (Plugin Integrity Verification via Ed25519)
- ADR-028 (RAG Ingestion Trust Model)

---

## 1. Contexto y Motivación

`rag-security` es el único componente del pipeline que usa un global
`g_plugin_loader` en lugar del patrón member `plugin_loader_` + setter usado
en sniffer, rag-ingester y ml-detector.

La razón es arquitectónica: `rag-security` instala signal handlers POSIX
(`SIGTERM`, `SIGINT`) que deben invocar `plugin_loader.shutdown()` de forma
async-signal-safe. Un puntero global es el único mecanismo que permite acceso
al loader desde dentro de un signal handler sin violar las restricciones
POSIX de async-signal-safety.

Este ADR documenta formalmente el patrón, sus restricciones y sus garantías
antes de implementar PHASE 2e.

---

## 2. Problema

Los signal handlers POSIX imponen restricciones severas:

> Solo funciones listadas en `signal-safety(7)` pueden llamarse desde un
> signal handler. En particular, **NO** están permitidas:
> - Operaciones con mutex (`std::mutex`, `pthread_mutex_lock`)
> - Allocaciones de memoria (`malloc`, `new`)
> - Operaciones de I/O estándar (`printf`, `std::cout`)
> - Lanzamiento de excepciones C++

`PluginLoader::shutdown()` llama `dlclose()` + logging. `dlclose()` es
async-signal-safe según POSIX. El logging debe ser suprimido o redirigido
a `write()` directo (async-signal-safe).

Sin este ADR documentado, un implementador podría aplicar el patrón member
+ setter (correcto para otros componentes) y romper la seguridad del signal
handler de forma sutil.

---

## 3. Decisiones

### D1 — Global `g_plugin_loader` obligatorio en rag-security

`rag-security` declara:

```cpp
// ADR-029: global requerido para async-signal-safe signal handler
static ml_defender::PluginLoader* g_plugin_loader = nullptr;
```

Este es el único componente donde se usa este patrón. Los demás componentes
usan member + setter (ADR-012).

### D2 — Signal handler: solo operaciones async-signal-safe

El signal handler de `rag-security` se limita a:

```cpp
static void signal_handler(int sig) {
    // async-signal-safe: write() directo, sin std::cerr ni printf
    const char msg[] = "[rag-security] signal received — shutting down\\n";
    write(STDERR_FILENO, msg, sizeof(msg) - 1);
    if (g_plugin_loader != nullptr) {
        g_plugin_loader->shutdown();  // dlclose() — async-signal-safe
    }
    // Restaurar handler por defecto y re-enviar señal (terminación limpia)
    signal(sig, SIG_DFL);
    raise(sig);
}
```

Prohibido dentro del handler: `std::cerr`, `logger_->`, `std::mutex`,
`new`, `delete`, llamadas a funciones no listadas en `signal-safety(7)`.

### D3 — Asignación de g_plugin_loader antes de instalar signal handlers

El orden de inicialización es obligatorio:

```
1. PluginLoader construido e inicializado
2. g_plugin_loader = &plugin_loader  ← asignación atómica implícita (alineación)
3. signal(SIGTERM, signal_handler)   ← instalación del handler
4. signal(SIGINT,  signal_handler)
```

Invertir el orden 2 y 3 crea una race condition: el handler podría ejecutarse
con `g_plugin_loader == nullptr`.

### D4 — invoke_all en rag-security: modo READONLY

A diferencia de sniffer y ml-detector (PLUGIN_MODE_NORMAL), rag-security
invoca plugins en modo READONLY — los plugins observan el evento pero no
pueden modificar el payload ni detener el flujo con result_code != 0.

Justificación: rag-security es el guardián de la memoria semántica. Ningún
plugin externo tiene autoridad para bloquear la ingestión de seguridad.

### D5 — invoke_all NO se llama desde el signal handler

La invocación de plugins ocurre exclusivamente en el loop de procesamiento
normal, nunca desde el signal handler. El signal handler solo llama
`shutdown()`.

---

## 4. Alternativas descartadas

### A1 — Member + setter (patrón estándar)
Descartado: el member vive en el objeto principal, inaccesible desde el
signal handler sin violar async-signal-safety.

### A2 — std::atomic<PluginLoader*>
Considerado. Un puntero raw alineado en arquitecturas x86-64/ARM64 tiene
escritura/lectura atómica implícita para tamaño de palabra. `std::atomic`
añadiría claridad semántica pero requiere C++ en el signal handler.
Decisión: puntero raw con comentario explícito es suficiente y más portable.

### A3 — pipe() + self-pipe trick
Correcto para signal handling complejo. Sobredimensionado para shutdown
simple. Reservado para roadmap si se necesita más lógica en el handler.

---

## 5. Consecuencias

- PHASE 2e puede implementarse con seguridad siguiendo D1-D5.
- El patrón global está **aislado** a rag-security — ningún otro componente
  lo replica.
- Cualquier modificación futura al signal handler de rag-security debe
  revisarse contra `signal-safety(7)`.
- TEST requerido antes de merge: TEST-INTEG-4e (ver sección 6).

---

## 6. Tests requeridos (TEST-INTEG-4e)

| Test | Descripción | Gate |
|------|-------------|------|
| Caso A | READONLY + evento real → PLUGIN_OK, result_code ignorado | PASS obligatorio |
| Caso B | g_plugin_loader=nullptr → invoke_all no llamado, no crash | PASS obligatorio |
| Caso C | SIGTERM durante procesamiento → shutdown limpio, no deadlock | PASS obligatorio |

---

## 7. Deuda técnica generada

Ninguna nueva. Este ADR cierra la deuda documentada en REC-1 (Consejo DAY 110).

---

*Via Appia Quality — documentar antes de implementar.*
