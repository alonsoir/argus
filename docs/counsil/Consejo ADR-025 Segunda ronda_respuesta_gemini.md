REVISOR: Gemini (Google) / Perfil: Sistemas Distribuidos & cs.CR
FECHA: 2 de abril de 2026

VEREDICTO GLOBAL ADR-025 (Segunda Ronda): **DISEÑO CONSOLIDADO CON ÉNFASIS EN OPERACIONES**

Alonso, Claude, esta segunda ronda de consultas al **Consejo de Sabios** aborda la tensión clásica entre **Seguridad Máxima** y **Viabilidad Operativa**. En un entorno de recursos limitados (hospitales/escuelas), un sistema que "se rompe" por un proceso de rotación complejo es un sistema que acaba siendo desactivado.

Aquí están las resoluciones del Consejo para las preguntas de la Fase 2:

---

### 🛡️ Resolución del Consejo — Segunda Ronda ADR-025

#### P1 — Trigger de rotación: ¿Manual o Cron?
**Veredicto: OPERACIÓN EXCLUSIVAMENTE MANUAL.**
* **Razonamiento:** En un sistema donde la rotación implica recompilar y redesplegar binarios, el **Cron es el enemigo**. Una rotación automática fallida un domingo a las 03:00 AM podría dejar al hospital sin protección NDR hasta que el admin llegue el lunes.
* **Acción:** `provision.sh --reset` debe requerir el flag `--force-confirm` y solo ejecutarse en el entorno de build (CI/CD). El "recordatorio" de rotación debe ser un log de nivel `NOTICE` en el pipeline: *"Clave actual generada hace X días. Considere rotación programada"*.

#### P2 — Coste operacional de D7 (Hardcoded)
**Veredicto: D7 MANTENIDO (Hardcoded es el estándar de oro).**
* **Razonamiento:** La rotación en **aRGus** no es una tarea de mantenimiento rutinaria (como rotar logs), es un **Cambio de Estado del Sistema**. Si aceptamos que la clave pública esté en un fichero (aunque sea `root-only`), abrimos la puerta a ataques de persistencia donde un atacante con privilegios elevados cambia la clave para validar sus propios plugins maliciosos.
* **Compromiso:** El coste de recompilar es despreciable en un pipeline moderno de C++20. El "coste" real es el redespliegue, el cual debe ser tratado como una actualización de firmware. Es aceptable dado el perfil de riesgo.



#### P3 — Comportamiento de `provision.sh --reset`
**Veredicto: INVALIDACIÓN ACTIVA Y BLOQUEO FAIL-CLOSED.**
1.  **Confirmación:** El script debe imprimir el *Fingerprint* de la clave antigua y la nueva, exigiendo confirmación manual.
2.  **Invalidación:** Al generar una nueva clave, el script **DEBE borrar todos los archivos `.sig` existentes** en el workspace de build. Esto fuerza al administrador a ejecutar el proceso de firma de nuevo.
3.  **Bloqueo de Arranque:** El `PluginLoader` debe comparar el resultado de la verificación contra la clave pública hardcoded. Si el `.sig` fue firmado con una clave anterior, la firma fallará criptográficamente por diseño. El sistema debe dar un error `FATAL: Plugin signature mismatch with hardware-root-of-trust`.

#### P4 — Falco y el Threat Model de Root
**Veredicto: FALCO COMO CAPA DE OBSERVABILIDAD COMPLEMENTARIA.**
* **Razonamiento:** El ADR-025 debe declarar formalmente que su objetivo es la **Integridad del Binario y Plugins**. Si el usuario `root` está comprometido, el atacante puede parchear el binario en memoria o modificar el kernel.
* **Decisión:** Incluir una sección en el ADR-025: *"Capa de Mitigación Superior: Se delega a la política de Falco/AppArmor (ADR-Future) la monitorización de intentos de escritura en el directorio de plugins y la ejecución de procesos no autorizados"*. Esto delimita el alcance (scope) del plugin-loader sin ignorar la realidad del sistema.

---

### 🏛️ Síntesis Técnica para el Cierre del ADR-025

Alonso, tu intuición sobre la máquina de CICD es la correcta. La **Clave Privada** es el "Corazón" del sistema: si late fuera de la caja fuerte (máquina de build), el sistema muere.

**Flujo de Trabajo Final Aprobado:**
1.  **Build Machine:** `provision.sh --reset` -> Genera Ed25519 -> Invalida `.sig` antiguos.
2.  **Build Machine:** Genera `pubkey.h` -> Compila `plugin_loader` -> Firma plugins `.so`.
3.  **Despliegue:** Se envían los nuevos binarios y los nuevos `.sig` al host productivo.
4.  **Runtime:** El binario carga los plugins vía FD, verifica contra la clave embebida.



### 📝 Posición de Minoría (Registro Gemini)
*"Sugiero que `provision.sh` guarde un histórico (log) local de cuándo se rotaron las claves, incluyendo el hash del binario resultante. Esto facilitará las auditorías forenses en caso de que un hospital necesite demostrar cuándo y por qué se cambió la raíz de confianza."*

**¿Damos por cerrada la fase de diseño del ADR-025 y procedemos a la implementación de la firma Ed25519 en el pipeline?** Alonso, con esto el "Legado" es un poco más indestructible hoy. 🏛️🛡️🚀