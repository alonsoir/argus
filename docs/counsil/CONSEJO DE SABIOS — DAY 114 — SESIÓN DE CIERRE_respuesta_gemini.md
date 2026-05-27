Como **Gemini (Consejo de Sabios)**, he analizado el acta del **DAY 114**. La transición a la **PHASE 3** y la resolución de las deudas técnicas de señales (`std::atomic`, `write()`) demuestran que el proyecto ha alcanzado una madurez operativa donde los detalles "invisibles" (seguridad en condiciones de pánico) son la prioridad.

Aquí tienes mi análisis directo y proactivo sobre tus interrogantes:

---

### 🏛️ Veredictos del Consejo DAY 114

#### Q1 — Mecanismo de Firma Automática (`DEBT-SIGN-AUTO`)
**Veredicto: Diseño Sólido con un Matiz de Seguridad.**
* **Análisis:** El diseño es correcto y necesario para evitar el "rozamiento" operativo. Sin embargo, la lógica de "Si .sig es inválido → firmar" debe ser **estrictamente local**.
* **Riesgo:** Si el script firma automáticamente cualquier cosa que encuentre en `/usr/lib/ml-defender/plugins/`, un atacante que logre depositar un `.so` malicioso y luego dispare un rebuild/provision (ej. reiniciando un contenedor o forzando un re-provision) obtendría una firma legítima para su malware.
* **Recomendación:** La firma automática solo debe ocurrir durante el **Build/Deploy Time** (dentro del Makefile/Vagrant) usando los artefactos recién compilados. **Nunca** firmar automáticamente en un nodo de producción "en caliente" basándose solo en lo que hay en la carpeta de plugins. El script debe distinguir entre "Firma desde Source" y "Verificación en Host".

#### Q2 — Estrategia de Eliminación de `libplugin_hello.so`
**Veredicto: Opción C (Flag CMake + JSON Limpio).**
* **Análisis:** La **Opción C** es la única que respeta el principio de "Defensa en Profundidad".
   1. **CMake Flag:** Evita que el binario siquiera se genere en la imagen de producción (reducción de superficie de ataque física).
   2. **JSON Limpio:** Evita que el `PluginLoader` intente abrir un recurso inexistente, eliminando ruido en los logs de arranque.
* **Implicación ADR-012:** La validación de la arquitectura de plugins debe moverse a la **CI Pipeline**. El `hello-plugin` debe ser el corazón de los tests de integración en desarrollo, pero su ausencia en producción es, de hecho, un test de "configuración limpia".

#### Q3 — Priorización de PHASE 3
**Veredicto: Acuerdo Total, pero con una Agrupación Lógica.**
El orden propuesto es correcto, pero sugiero un ligero "swap" por dependencias:
1. **DEBT-SIGN-AUTO** + **DEBT-HELLO-001**: Resuelve la estabilidad del build antes de tocar la orquestación.
2. **systemd units**: Asegura que el proceso sea resiliente.
3. **AppArmor profiles**: Es el ítem más complejo. Requiere que `systemd` y las rutas de ficheros estén estables.
4. **DEBT-ADR025-D11**: La rotación de claves es vital, pero puede esperar al final de la fase de hardening.
5. **TEST-PROVISION-1**: Como cierre de fase para garantizar que todo lo anterior es reproducible.

#### Q4 — Troubleshooting Documentation
**Veredicto: Formato `docs/TROUBLESHOOTING.md` + Referencia en `CLAUDE.md`.**
* **Casos adicionales a incluir:**
   * **"Plugin ABI Mismatch":** El plugin carga pero falla al resolver símbolos (ej. compilado con otra versión de headers).
   * **"Insufficient permissions on .sig":** El proceso `ml-defender` no tiene lectura sobre el archivo de firma.
   * **"Atomic Flag Shutdown":** El componente no cierra tras SIGTERM (revisar estado del `std::atomic<bool>`).
* **Sugerencia Proactiva:** Implementa un flag de línea de comandos `--check-config` en cada componente que instancie el `PluginLoader` y valide las firmas sin arrancar el pipeline completo. Esto ahorraría esos 30 minutos de diagnóstico.



---

### 🛡️ Observación Crítica sobre `DEBT-SIGNAL-001/002`

La corrección de `std::cout` a `write(STDERR_FILENO)` es **excelente**. Usar `std::cout` en un signal handler es un riesgo de *deadlock* si la señal llega mientras el hilo principal tiene bloqueado el mutex de `stdout`. Confirmar con `objdump` la llamada a `write@plt` es el nivel de rigor que este Consejo espera.



### 🏁 Estado del Veredicto

**PROXIMOS PASOS (DAY 115):**
1. Implementar la **Opción C** para `libplugin_hello.so`.
2. Refinar el Makefile para que el target `sign-plugins` sea una dependencia de `install`, garantizando que nunca haya un despliegue sin firma.
3. Iniciar el borrador de la unidad de `systemd` para el `sniffer`.

Alonso, el merge a `main` y el tag `v0.3.0` marcan el fin de la "adolescencia" del código. Estamos construyendo una fortaleza.

**¿Empezamos con los perfiles de AppArmor o prefieres cerrar primero la automatización del Build?** 🏛️🛡️🚀