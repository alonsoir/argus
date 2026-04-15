Estado muy sólido. DAY 111 marca transición clara a sistema maduro. Las preguntas que planteas son las correctas; aquí sí merece ajuste fino.

---

# Q1-112 — `rag-security` en READONLY vs NORMAL

## Veredicto

→ **READONLY es correcto y debe mantenerse como invariante**

---

## Razón técnica (clave)

`rag-security` no es un componente de filtrado, es:

> **consumidor de conocimiento + interfaz de decisión humana (LLM)**

Permitir `PLUGIN_MODE_NORMAL` aquí implica:

* Plugins podrían bloquear respuestas del LLM
* Plugins podrían sesgar explicabilidad
* Plugins se convierten en autoridad sobre memoria semántica

👉 Eso rompe el modelo de confianza definido en ADR-028.

---

## Riesgo concreto si permites NORMAL

Un plugin podría hacer:

```cpp
ctx.result_code = -1;
```

Resultado:

* El LLM no responde
* El sistema queda “ciego” sin fallo explícito
* Debug extremadamente difícil

---

## Conclusión

```text
rag-security:
- SIEMPRE READONLY
- Plugins = observadores, nunca árbitros
```

---

## Recomendación adicional (muy buena inversión)

Hazlo **invariante duro en código**:

```cpp
if (component == RAG_SECURITY && ctx.mode != PLUGIN_MODE_READONLY) {
    std::terminate();
}
```

---

# Q2-112 — Testing de SIGTERM (async-signal-safe)

## Veredicto

→ **Opción A (fork + kill + waitpid) es la correcta**

---

## Por qué

### Opción A (fork)

✔ Testea comportamiento real del sistema
✔ Aísla efectos del signal
✔ Reproduce condiciones reales
✔ No depende de timing frágil

---

### Opción B (alarm)

✘ Dependiente de timing
✘ No determinista
✘ Puede fallar en CI

---

### Opción C (simulación)

✘ No testea signal handler real
✘ Falsa sensación de seguridad

---

## Patrón recomendado (limpio)

```cpp
pid_t pid = fork();

if (pid == 0) {
    // child
    run_component();
    exit(0);
} else {
    sleep(1); // dejar arrancar
    kill(pid, SIGTERM);

    int status;
    waitpid(pid, &status, 0);

    ASSERT_TRUE(WIFEXITED(status) || WIFSIGNALED(status));
}
```

---

## Mejora opcional (nivel pro)

Validar side-effect observable:

* logs escritos
* recursos liberados
* no corrupción de estado

---

## Conclusión

→ **A es correcta, robusta y alineada con TDH**

---

# Q3-112 — arXiv Replace timing

## Contexto importante

arXiv no rompe DOI al hacer replace, pero:

* Indexadores (Google Scholar, Semantic Scholar) tienen latencia
* El primer snapshot influye en citabilidad inicial

---

## Veredicto

→ **Esperar 7–10 días antes de Replace**

---

## Razón

* Permite indexación de v1
* Evita inconsistencias en metadatos
* No penaliza calidad científica

---

## Cuándo subir antes

Solo si:

* Hay error técnico grave
* Hay inconsistencia que invalida resultados

(No es el caso aquí)

---

## Recomendación práctica

```text
Día 0: publicación (hecho)
Día 7–10: Replace v13
```

---

# Observaciones adicionales (no pedidas, pero importantes)

## 1. ml-detector → src_ip/dst_ip = 0

Esto es correcto ahora, pero:

👉 puede romper plugins que asumen IP válida

---

### Recomendación

Documentar explícitamente:

```text
ctx.src_ip/dst_ip pueden ser 0 → usar network_features()
```

o introducir:

```cpp
ctx.has_network_features = true;
```

---

## 2. MAX_PLUGIN_PAYLOAD_SIZE (64KB)

Muy buena decisión.

Pequeño detalle:

👉 documentar si es:

* tamaño antes o después de compresión
* tamaño del protobuf serializado

Evita bugs futuros.

---

## 3. ADR-029 — orden de inicialización

Muy bien definido:

> loader → global → signals

👉 esto es crítico, mantenlo como invariante duro (assert en debug).

---

# Conclusión global

## Estado del sistema

* ✔ Seguridad coherente extremo a extremo
* ✔ Contratos bien definidos
* ✔ Tests cubriendo casos reales
* ✔ Arquitectura consistente

---

## Respuestas finales

| Pregunta | Respuesta                            |
| -------- | ------------------------------------ |
| Q1-112   | READONLY obligatorio en rag-security |
| Q2-112   | Opción A (fork + kill + waitpid)     |
| Q3-112   | Esperar 7–10 días antes de Replace   |

---

## Veredicto final

→ **DAY 111: APROBADO SIN CONDICIONES**

El sistema ya no está en fase experimental.
Ahora estás en fase de **endurecimiento fino y estabilidad a largo plazo**.

Si quieres, en el siguiente paso puedo ayudarte a diseñar:

* timeouts por plugin
* budget de CPU por invocación
* o sandboxing ligero (seccomp) antes de que metas plugins reales no controlados
