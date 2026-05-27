## Respuesta del Consejo de Sabios – DAY 114 (11 Abril 2026)

El Consejo ha revisado el acta de DAY 114. Valoramos muy positivamente la rápida corrección de las deficiencias señaladas (TEST-INTEG-4d, signal safety, merge) y la apertura ordenada de PHASE 3. A continuación, las respuestas a las preguntas, con el nivel de exigencia y honestidad que caracteriza a este Consejo.

---

## Q1 – DEBT-SIGN-AUTO: diseño del mecanismo de firma automática

**Veredicto:** El diseño es sólido, pero necesita dos extensiones para cubrir todos los casos edge.

**Riesgos identificados y soluciones propuestas:**

| Riesgo | Propuesta de mitigación |
|--------|------------------------|
| **Firma de plugins no desplegados** (ej. `libplugin_hello.so` presente en `plugins/` pero no en el destino final) | `check-plugins` debe operar sobre el directorio de destino real (`/usr/lib/ml-defender/plugins/`) y también verificar que los plugins listados en los JSON configs existen y están firmados. Si un plugin está en la configuración pero no en el sistema, fallar explícitamente (no firmar automáticamente un inexistente). |
| **Rotación de clave pública** (cambio de clave en el binario) | Si la clave pública incrustada cambia (por ejemplo, tras un `--reset`), todos los plugins existentes con firma antigua deben ser **re‑firmados**. El mecanismo debe detectar que la firma actual no corresponde a la clave pública activa (no solo existencia de `.sig`). Propuesta: almacenar el key ID en el propio plugin (ej. en una sección ELF) o comparar la clave pública usada para firmar (guardada en un archivo de metadatos). Simplificación: al hacer `provision.sh sign` sin argumentos, siempre regenerar todas las firmas con la clave actual. La idempotencia se basa en que la clave no cambia a menudo. |
| **Carreras durante la ejecución concurrente** (ej. `make check-and-sign-plugins` mientras el pipeline está corriendo) | El mecanismo debe ser atómico: usar un lock de archivo (`flock`) o no modificar archivos `.so` mientras están en uso. Mejor aún: ejecutar `check-and-sign-plugins` solo durante el provisionamiento y antes de arrancar el pipeline, no durante la operación normal. |

**Recomendación final:**
- Aceptar el diseño con las dos salvaguardas: (1) verificar que todo plugin referenciado en JSON existe y está firmado; (2) tras un cambio de clave pública, re‑firmar todos los plugins de forma explícita (no automática, sino a través de `provision.sh sign --force`).
- Documentar en `CLAUDE.md` que el operador debe ejecutar `make sign-plugins` después de cualquier actualización del plugin loader o cambio de clave.

---

## Q2 – DEBT-HELLO-001: eliminación de `libplugin_hello.so` en producción

**Veredicto:** **Opción C (ambas: CMake flag + JSON sin referencia).** Unanimidad.

**Justificación:**
- **CMake flag `BUILD_DEV_PLUGINS`** garantiza que el plugin hello ni siquiera se compile en los artefactos de producción. Reduce superficie de ataque y tamaño de la imagen.
- **Eliminar de los JSON configs** evita que un operador despistado copie accidentalmente un JSON de desarrollo a producción, causando que el pipeline busque un plugin inexistente.
- **Impacto en ADR-012:** ADR-012 (arquitectura plugin) no requiere que el plugin hello esté presente en producción; solo exige que el mecanismo de carga funcione con un ejemplo. Ese ejemplo puede seguir existiendo en el repositorio y compilarse en modo desarrollo. La validación de ADR-012 se hace en entornos de CI, no en producción.

**Acción concreta:**
- Añadir `option(BUILD_DEV_PLUGINS "Build development plugins (hello-world)" OFF)` en el `CMakeLists.txt` principal.
- En `plugins/CMakeLists.txt`, envolver `add_subdirectory(hello)` con `if(BUILD_DEV_PLUGINS)`.
- En los JSON de producción (ej. `config/firewall-acl-agent.json`), eliminar la entrada `"libplugin_hello.so"`. Mantenerla solo en `config/dev/` o en un ejemplo documentado.

**Nota adicional:** Asegurarse de que los tests de integración (TEST-INTEG-4a–4e) no dependan de `libplugin_hello.so`. Si dependen, mover el plugin hello a una sección de tests o crear un plugin de prueba específico que se compile solo para tests.

---

## Q3 – PHASE 3: priorización del backlog

**Veredicto:** **El orden propuesto es correcto, pero con una dependencia oculta y un ajuste de prioridad.**

**Análisis ítem por ítem:**

| Ítem | Prioridad propuesta | Observación |
|------|---------------------|-------------|
| 1. systemd units | 1 | Correcto. Es la base para que los componentes se recuperen de fallos. |
| 2. AppArmor profiles | 2 | Correcto. Debe ir después de systemd porque los perfiles pueden necesitar ajustes según cómo systemd lance los binarios. |
| 3. TEST-PROVISION-1 | 3 | Correcto. CI gate que valida todo el provisionamiento. **Dependencia oculta:** necesita que los ítems 1 y 2 estén estables para que la prueba pase. |
| 4. provision.sh --reset | 4 | Correcto. Es una función administrativa, no crítica para el funcionamiento base. |
| 5. DEBT-SIGN-AUTO | 5 | **Debería subir al puesto 3.5** (después de TEST-PROVISION-1 pero antes de --reset). Motivo: sin firma automática, el pipeline puede romperse silenciosamente tras un cambio de plugin loader, como ocurrió hoy. La robustez operativa es más urgente que la rotación de claves. |
| 6. DEBT-HELLO-001 | 6 | Correcto. Limpieza cosmética, puede esperar. |

**Dependencia oculta:**
- `TEST-PROVISION-1` (CI gate) debería ejecutar `check-and-sign-plugins` como parte de su flujo. Si DEBT-SIGN-AUTO no está implementado, el CI fallará al no encontrar plugins firmados. Por tanto, **DEBT-SIGN-AUTO debe completarse antes o simultáneamente con TEST-PROVISION-1**.

**Orden revisado:**
1. systemd units
2. AppArmor profiles
3. DEBT-SIGN-AUTO (firma automática idempotente)
4. TEST-PROVISION-1 (CI gate, incluye check-and-sign)
5. provision.sh --reset
6. DEBT-HELLO-001

**Plazo sugerido para los tres primeros:** 3-5 días.

---

## Q4 – Troubleshooting documentation (DEBT-OPS-002)

**Veredicto:** El árbol de diagnóstico es un buen comienzo, pero debe ampliarse y adoptar un formato estructurado.

**Casos adicionales a incluir:**

```
Pipeline no arranca o componente crash →
  ¿Logs muestran "Failed to load plugin: ..."? →
    ¿Es un plugin propio o del sistema? →
      Si es propio: make plugin-hello-build (o el que corresponda)
      Si es del sistema: reinstalar paquete ml-defender-plugins
  ¿Logs muestran "cannot open shared object file: No such file or directory"? →
    Verificar LD_LIBRARY_PATH o rpath del binario (objdump -x binario | grep RPATH)
    Verificar que libplugin_loader.so está en /usr/lib/ml-defender/
  ¿Logs muestran "segmentation fault" o "std::terminate" sin mensaje claro? →
    Ejecutar con gdb: gdb --args /usr/bin/ml-defender-sniffer
    O usar LD_DEBUG=libs para ver carga de bibliotecas
  ¿El componente arranca pero no procesa eventos? →
    Verificar ZeroMQ sockets: netstat -lntp | grep <puerto>
    Verificar que los demás componentes están vivos (systemctl status ml-defender-*)
  ¿Problema específico de firma? (tu árbol ya cubre bien esta rama)
```

**Formato recomendado:**
- **Markdown** dentro del repositorio, en `docs/troubleshooting.md`.
- Incluir un enlace desde `README.md` y desde `CLAUDE.md`.
- Añadir una **sección de “Comandos de diagnóstico rápido”** (por ejemplo, `make check-plugins`, `provision.sh check-plugins --verbose`).
- Para errores conocidos, incluir la salida exacta que produce el log y la solución.

**Propuesta de estructura:**
```markdown
# Troubleshooting aRGus NDR

## Síntoma: El pipeline no arranca (systemctl status muestra failed)
- [Árbol de decisión como el propuesto]

## Síntoma: Los componentes arrancan pero no se ven eventos
- ...

## Síntoma: Alto consumo de CPU o memoria
- ...

## Comandos útiles
- `make check-and-sign-plugins`
- `provision.sh sign --force`
- ...
```

**Acción inmediata:** Crear el esqueleto de `docs/troubleshooting.md` y vincularlo en `CLAUDE.md` como parte de PHASE 3.

---

## Conclusión y felicitaciones

El Consejo felicita al equipo por haber cerrado las deudas críticas, por el merge exitoso de ADR-025 y por la publicación del Replace en arXiv. La apertura de PHASE 3 con una planificación clara es el camino correcto.

**Recordatorios finales:**
- No olvidar que `TEST-INTEG-4d` debe ejecutarse en CI de forma automática.
- Verificar que los signal handlers de sniffer y ml-detector usan `write(STDERR_FILENO, ...)` y que no hay ningún `std::cout` residual (el análisis con objdump es suficiente).
- El árbol de troubleshooting debe ser validado por un operador que no conozca el proyecto (prueba de usabilidad).

*“La verdad por delante, siempre” – y hoy, también la eficiencia.*

El Consejo queda a la espera del acta DAY 115.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta redactada: 11 Abril 2026*