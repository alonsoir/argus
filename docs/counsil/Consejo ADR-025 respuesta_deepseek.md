## DeepSeek — Revisión del borrador ADR-025 (Plugin Integrity Verification)

El borrador está sólido. La pregunta al Consejo es precisa y el análisis de vectores es exhaustivo. Solo sugiero algunos matices y una corrección menor antes de enviarlo.

---

### Puntos fuertes del ADR-025

- **Eliminación del TOCTOU** mediante `open()` + `dlopen("/proc/self/fd/N")` es el estándar de facto y funciona en Linux.
- **Uso de Ed25519** es correcto para firmas; libsodium ya está en el proyecto.
- **Fail-closed** (el plugin no se carga, el componente sigue) es coherente con el comportamiento actual (símbolo ausente, API mismatch). No introducimos un nuevo modo de fallo.
- **Los 8 vectores de ataque** están bien identificados y clasificados.

---

### Correcciones y matices

**1. SHA-256 redundante?**  
La firma Ed25519 ya se calcula sobre el contenido del `.so`. No es necesario un hash SHA-256 adicional a menos que quieras separar la verificación de integridad de la autenticidad. Sugiero eliminarlo del texto o dejarlo como opcional ("verificación de integridad adicional opcional").

**2. Canonical path validation (Vector 4)**  
No basta con `std::filesystem::canonical()`. Un atacante podría usar symlinks dentro del directorio permitido que apunten fuera. La validación debe:
- Resolver el path canónico.
- Verificar que el prefijo es exactamente `/usr/lib/ml-defender/plugins/` (o el directorio configurado).
- Además, comprobar que el descriptor de archivo (`fd`) corresponde a un archivo regular dentro de ese directorio (con `fstat()` y verificando `st_dev`/`st_ino` con el directorio base, aunque es más complejo). Para PHASE 2, la validación de prefijo es suficiente; se documenta como mitigación.

**3. Mantener fd abierto (Vector 5)**  
Correcto. La secuencia: `open()` → verificar firma (leyendo del fd) → `dlopen("/proc/self/fd/N")` → `close(fd)`.  
**Importante:** `dlopen()` puede fallar si el fd ya no es válido o el archivo fue modificado. Al mantenerlo abierto, garantizamos que el contenido verificado es exactamente el que se carga.

**4. Stripping LD_PRELOAD (Vector 6)**  
En producción, el daemon debería ejecutarse con `sudo -E` o limpiando el entorno. Añadir al launcher: `unset LD_PRELOAD LD_LIBRARY_PATH` antes de `exec`. Esto es fácil de implementar y no requiere seccomp.

**5. Firma offline vs on-host (Vector 1)**  
El ADR debe especificar que **la clave privada nunca reside en el host de producción**. El `provision.sh` debe generar las firmas en el entorno de build y solo copiar el `.so` y el `.sig`. La clave pública se incorpora en el binario del plugin-loader (o en un fichero de configuración firmado). Documentarlo es crítico.

**6. JSON schema: campo `signature`**  
En lugar de un campo separado, se podría inferir automáticamente añadiendo `.sig` al path del `.so`. Esto simplifica la configuración y evita errores. Propuesta:
- Si el JSON proporciona `signature`, se usa.
- Si no, se construye como `plugin_path + ".sig"`.
- Así, el campo es opcional y la configuración legacy (sin firma) sigue funcionando (aunque con warning).

**7. ¿Qué ocurre si el `.sig` no existe o la firma falla?**  
El ADR dice "plugin no carga → warning en stderr". ¿El componente sigue arrancando? Para un plugin de cifrado (futuro), sería fail-closed. Pero para plugins opcionales (hello plugin), está bien. Propuesta: hacerlo configurable por plugin en el JSON: `"require_signature": true/false`. Por defecto `true` para plugins en producción, `false` para desarrollo.

**8. Protección contra rollback de versión**  
Si un atacante puede sustituir el `.so` por una versión anterior firmada válidamente (con la misma clave), el mecanismo no lo detecta. Eso es un ataque de rollback. Mitigación: incluir un número de versión o timestamp en la firma (ej. el campo `annotation` de `MessageContext` o un metadato en el `.sig`). No es crítico para PHASE 2, pero conviene mencionarlo como work in progress.

---

### Pregunta para el Consejo (refinada)

Propongo enviar esta versión ligeramente ajustada:

> **Pregunta al Consejo:**  
> Dado el mecanismo propuesto en ADR-025 (firma Ed25519 offline + verificación en runtime + dlopen desde fd), enumera todos los vectores de ataque que podrían bypassar esta verificación, ordenados por viabilidad. Para cada vector indica:
> - Si es mitigable en diseño ahora (con los recursos actuales).
> - Si es diferible a la imagen Debian hardened (AppArmor, IMA, seccomp).
> - Si está fuera de scope (ej. supply chain).
>
> Además, valora las siguientes decisiones de diseño:
> 1. ¿Inferir automáticamente la ruta del `.sig` añadiendo `.so` → `.sig`, o exigir campo explícito en JSON?
> 2. ¿Hacer la verificación obligatoria para todos los plugins en producción, o configurable por plugin?
> 3. ¿Cómo manejar la rotación de claves públicas (ej. si la clave privada se compromete)?
> 4. ¿Es necesario un mecanismo anti-rollback (números de versión en firma)?

---

### Veredicto final

El ADR-025 está listo para enviar al Consejo con los matices anteriores incorporados. No es necesario un rediseño, solo aclarar algunos puntos y añadir las mitigaciones propuestas (V1, V4, V5, V6) como parte del diseño, no como trabajo futuro.

**Mi recomendación:**
- Añade un párrafo que describa la mitigación de V1 (firma offline, clave privada solo en build).
- Especifica la validación de path canónico (V4).
- Describe la disciplina de fd (V5).
- Menciona el stripping de `LD_PRELOAD` (V6).
- Deja el SHA-256 como opcional.
- Envía la pregunta refinada al Consejo.

Una vez recibas el feedback, el ADR-025 podrá cerrarse y proceder a la implementación.

— DeepSeek, miembro del Consejo de Sabios