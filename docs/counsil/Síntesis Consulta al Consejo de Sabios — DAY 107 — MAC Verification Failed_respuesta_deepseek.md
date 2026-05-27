## DeepSeek — Análisis post-mortem y respuestas al Consejo (DAY 107)

Felicidades por la resolución. El bug era insidioso: un campo de configuración sin setear que silenciosamente desactivaba el cifrado, enviando LZ4 en claro. El hexdump de Gemini fue la prueba de concepto que rompió la ambigüedad. Ahora, a las preguntas.

---

### Respuesta a Pregunta 1 — Swap CTX en etcd-server

**Recomendación:** **Sí, revierte el swap y prueba con solo el fix de `component_config_path`.** El swap fue una intervención basada en una hipótesis (contextos asimétricos) que resultó no ser la causa raíz. Tener dos cambios entrelazados es peligroso: si en el futuro vuelve a fallar, no sabremos qué cambio lo está causando.

**Procedimiento sugerido:**
1. Revertir el swap en `etcd-server/src/component_registry.cpp` (volver a `tx_` con `CTX_ETCD_TX`, `rx_` con `CTX_ETCD_RX`).
2. Recompilar solo etcd-server.
3. Verificar que el pipeline sigue funcionando (debería, porque el verdadero problema era la falta de cifrado en el cliente, no la simetría de contextos).
4. Si falla, entonces el swap era necesario por otra razón (quizás el cliente estaba usando `CTX_ETCD_RX` por error). En ese caso, habrá que investigar por qué la simetría esperada no se cumple.

**Riesgo de no revertir:** Dejar el swap puede enmascarar futuros errores de configuración de contexto en otros componentes. Mejor tener el diseño limpio.

---

### Respuesta a Pregunta 2 — Dos paths de carga del seed

**Recomendación:** **No, no es arquitectónicamente correcto.** El sniffer debería usar `SeedClient` igual que los demás.

**Razonamiento:**
- `SeedClient` unifica la lógica de lectura de `seed.bin`, verificación de permisos (0600), y manejo de errores (fail-closed).
- Tener una implementación ad-hoc en `get_encryption_seed()` introduce duplicación y riesgo de desviación (ej. olvidar verificar permisos).
- Además, el sniffer ya tenía la dependencia de `SeedClient` por otros motivos (lo usa en `main` para inicializar `CryptoTransport`). No hay razón para no usarlo también para obtener el seed.

**Acción:** Refactorizar `sniffer/src/userspace/etcd_client.cpp` para que use `SeedClient` en lugar de su propia lectura de fichero. Esto unifica el comportamiento y facilita el mantenimiento.

---

### Respuesta a Pregunta 3 — Permisos `640` vs `0600` para `seed.bin`

**Recomendación:** **`SeedClient` debe aceptar `640` como válido cuando el grupo es `root` o `vagrant`, pero emitir una advertencia.** En producción, el estándar debe ser `0600` (solo root).

**Razonamiento:**
- `640` (root:vagrant) permite a cualquier usuario del grupo `vagrant` leer el seed. En un entorno de desarrollo con Vagrant, eso es aceptable y práctico (evita tener que hacer `sudo` constantemente).
- En producción, el grupo no debería contener usuarios no root, por lo que `640` sería equivalente a `600` en la práctica (si el grupo es solo root). Pero para ser estrictos, lo correcto es `0600`.
- **Propuesta:**
    - En producción (detectado por `MLD_PRODUCTION=1` o ausencia de `MLD_DEV_MODE`): solo aceptar `0600`. Cualquier otro permiso → error fatal.
    - En desarrollo: aceptar `640` y `0600`, pero loguear un `WARNING` si no es `0600`.

**Cambio en `SeedClient`:** Añadir una comprobación de permisos con `fstat()` después de abrir el fichero, y aplicar la política anterior.

---

### Recomendaciones adicionales para `provision.sh` y la reproducibilidad

El problema de fondo que reveló este bug es que **`provision.sh` no está sincronizando los seeds entre componentes** y no está configurando los permisos correctamente. Para que el pipeline sea reproducible tras `vagrant up`, necesitas:

1. **Sincronización de seeds:** Todos los componentes deben compartir el mismo `seed.bin` (porque las claves de sesión se derivan del mismo material). `provision.sh` debe generar un único seed y copiarlo a todos los directorios de componentes, no generar uno independiente por componente.

2. **Permisos estandarizados:**
    - Directorios `/etc/ml-defender/*/`: `755 root:root`
    - Ficheros `seed.bin`: `600 root:root` (o `640 root:vagrant` en desarrollo, con la política de la P3)
    - Los JSON de configuración: `644 root:root`

3. **Symlinks o copia de configuraciones:** Decidir si los JSON de configuración se copian a `/etc/` o se usan symlinks. Para un entorno reproducible, lo más limpio es que `provision.sh` copie los JSON desde el repositorio a `/etc/ml-defender/` (no symlinks, porque el repositorio podría no estar en `/vagrant` en producción). En desarrollo, los symlinks son cómodos, pero `provision.sh` debería crearlos solo si existe una variable `MLD_DEV_MODE`.

4. **Verificación de versión de `libcrypto_transport.so`:** Añadir un paso en `provision.sh` que compile e instale la biblioteca si su versión es anterior a la esperada, o al menos verifique que la fecha de modificación es reciente.

**Acción prioritaria:** Revisar `tools/provision.sh` para implementar estos puntos. De lo contrario, el pipeline no será reproducible fuera de tu sesión manual actual.

---

### Resumen ejecutivo

| Pregunta | Respuesta | Acción |
|----------|-----------|--------|
| Q1: Swap CTX | Revertir y probar solo con fix de `component_config_path` | Revertir cambio en etcd-server, recompilar, validar |
| Q2: Dos paths seed | Incorrecto. Unificar en `SeedClient` | Refactorizar `get_encryption_seed()` del sniffer |
| Q3: Permisos 640 | Aceptar en desarrollo con warning; en producción solo 0600 | Modificar `SeedClient` para política por entorno |
| Provisionamiento | Sincronizar seeds, permisos estandarizados, copiar configs | Actualizar `provision.sh` antes de `vagrant destroy` |

Enhorabuena por la caza del bug. Ahora toca consolidar la infraestructura de provisionamiento para que el arranque sea reproducible. ¿Procedemos con la actualización de `provision.sh` como siguiente paso?

— DeepSeek, miembro del Consejo de Sabios