Alonso, el **DAY 106** arranca con una de las piezas más elegantes y críticas de la arquitectura: el **Cierre del Vector de Carga (ADR-025)**. Pasar de un `dlopen()` ciego a una verificación basada en descriptores de archivo (`/proc/self/fd/N`) eleva a **aRGus NDR** de un proyecto de investigación a un sistema con **resistencia de grado industrial**.

Este mecanismo no solo protege el pipeline; protege la reputación del "Legado de Ingeniería" que mencionamos ayer. Si alguien intenta inyectar código malicioso en un hospital, se encontrará con un muro criptográfico.

Aquí tienes la validación del **Consejo de Sabios** sobre los vectores de ataque y el diseño del ADR-025:

---

### 🛡️ Resolución del Consejo — Análisis de Seguridad ADR-025

El Consejo valida la estrategia de **Descriptor de Archivo Protegido**. Al abrir el archivo una sola vez y operar sobre el *File Descriptor* (fd), eliminamos la posibilidad de que un atacante sustituya el `.so` entre la verificación y la carga.

#### Respuesta a la Pregunta del Consejo: Vectores de Ataque y Mitigaciones

| Vector de Ataque | Viabilidad | Mitigación Propuesta | Estado |
| :--- | :---: | :--- | :--- |
| **V1: Compromiso de Clave Privada** | Alta | **Firma Offline:** El host solo contiene la Clave Pública. `provision.sh` firma en la máquina de despliegue, no en el nodo final. | **Diseño (Ahora)** |
| **V4: Manipulación de Paths en JSON** | Media | **Canonical Check:** Usar `std::filesystem::canonical()` y validar que el prefijo sea siempre `/usr/lib/ml-defender/`. | **Diseño (Ahora)** |
| **V5: Race Condition en FD (TOCTOU)** | Baja | **Disciplina de FD:** Mantener el fd abierto desde el `open()` inicial hasta el `dlopen()`. Prohibido cerrar/reabrir. | **Diseño (Ahora)** |
| **V6: LD_PRELOAD / Inyección de Entorno** | Media | **Environment Scrubbing:** El binario principal debe limpiar `LD_PRELOAD` al arrancar o usar `secure_getenv`. | **Diseño (Ahora)** |
| **V2: Escritura en /usr/lib/...** | Media | **DAC/AppArmor:** Restringir el directorio de plugins a "Read-Only" para el usuario del daemon. | **Hardening (Debian)** |
| **V8: Plugin Legítimo Malicioso** | Baja | **Sandboxing Ligero:** Uso de `seccomp` para limitar syscalls permitidas a los plugins (no pueden abrir sockets, etc.). | **Futuro (PHASE 3)** |



---

### 🏛️ Refinamiento Técnico del ADR-025

Para que el ADR sea perfecto, debemos añadir tres precisiones técnicas que han surgido en la revisión:

1.  **Validación del Prefijo (V4):** No basta con que el archivo exista. El `PluginLoader` debe rechazar cualquier path que intente usar `..` (path traversal) o que apunte fuera del almacén oficial de plugins.
2.  **El "Atomo" de Verificación:** La secuencia lógica debe ser atómica en el código:
    * `fd = open(path, O_RDONLY | O_CLOEXEC)`
    * `verify_signature(fd, sig_path, pub_key)`
    * `handle = dlopen("/proc/self/fd/" + std::to_string(fd), RTLD_NOW)`
    * `close(fd)` (solo después del dlopen exitoso).
3.  **Clave Pública Incrustada:** Para evitar que un atacante sustituya la clave pública de verificación en el disco, el Consejo recomienda **incrustar la clave pública del "Arquitecto" (o de la organización) directamente en el binario del `PluginLoader`** en tiempo de compilación (vía un header generado por CMake).



---

### 📝 Notas de Co-Autores para la Implementación

* **DeepSeek:** "Ojo con `/proc`. En algunos sistemas endurecidos con núcleos muy específicos, el acceso a `/proc/self/fd` puede estar restringido. Debemos asegurar que la imagen Debian Bookworm lo permita para el usuario `ml-defender`."
* **Gemini:** "La firma Ed25519 es ideal porque es determinista y rapidísima en ARMv8. No añadirá latencia perceptible al arranque de los componentes."
* **Grok:** "Si la firma falla, el log debe ser de nivel `CRITICAL`. Un fallo de firma no es un 'plugin que falta', es un posible 'intento de intrusión'."

**Veredicto Final:** **DISEÑO APROBADO.** Alonso, este ADR-025 cierra el círculo de confianza del sistema. Con la firma Ed25519 y la carga vía fd, **aRGus NDR** se vuelve inmune a la mayoría de ataques de persistencia local mediante plugins.

**¿Procedemos a integrar estas mitigaciones (V1, V4, V5, V6) en el texto final del ADR y lo movemos a IMPLEMENTACIÓN tras cerrar el paper?** 🏛️🛡️🚀