A sus órdenes, miembros del Consejo de Sabios. He revisado el trabajo presentado en la rama `feature/day157-autonomy-state-persistence` y, tras un análisis detallado, procedo a compartir mis valoraciones sobre las cinco cuestiones planteadas.

---

### 1. Sobre la lectura fail-safe y la expiración de 24h (DEBT-AUTONOMY-STATE-PERSISTENCE-001)

La implementación de la lectura fail-safe es sólida y sigue el principio de "fail closed" (fallar hacia el estado más seguro). La deserialización y verificación se realizan en un único paso, tratando cualquier anomalía (archivo ausente, JSON corrupto, firma inválida) como una vuelta al estado `NORMAL`, lo cual es una práctica excelente. Un vector de ataque que merece una reflexión adicional es la **vulnerabilidad temporal en la ventana de reemplazo atómico (TOCTOU)**. Aunque la escritura es atómica (`write → fsync → rename`), un atacante con acceso al sistema de archivos `/var/lib/argus/` podría, en teoría, reemplazar el archivo `.json` por otro válido pero antiguo justo en el instante entre la verificación de la firma y la lectura del timestamp. Dado que la operación de verificación y la posterior comprobación de edad no son atómicas a nivel de sistema, una solución adicional podría ser bloquear el directorio o validar el inodo.

Respecto al umbral de 24 horas para el estado `AUTONOMOUS`, es un punto de partida sensato, pero para un entorno de producción hospitalaria debe ajustarse en base a un análisis de riesgos más granular. La caducidad debe alinearse con los Acuerdos de Nivel de Servicio (ANS) de la conectividad de red y los objetivos de tiempo de recuperación (RTO) de los servicios de los que depende (como Vault). Un enfoque más matizado podría considerar una **expiración progresiva**: por ejemplo, mantener el estado `AUTONOMOUS` con plenas capacidades durante las primeras 4 horas (ventana de interrupción típica), pasar a un modo `DEGRADED` (menos privilegios) hasta las 24 horas, y finalmente forzar `NORMAL` (aunque Vault no esté listo) para evitar una autonomía perpetua no supervisada.

### 2. Verificación de firma de `bootstrap-status.json` en `ExecStartPost=` (DEBT-BOOTSTRAP-STATUS-SIGNATURE-001)

La lógica es correcta: si el archivo se borra tras `g_server->start()`, verificarlo en `ExecStartPost=` es inútil. La verificación debe ocurrir **antes** de que el servicio principal (etcd-server) arranque.

Para el caso de uso descrito, donde se busca verificar la integridad del archivo de estado de arranque antes de lanzar servicios dependientes, el lugar adecuado en una unidad de systemd es `ExecStartPre=`. El orden lógico sería:

1.  **`ExecStartPre=`**: Ejecutar un script (`check-bootstrap-status.sh`) que verifique la firma Ed25519 del archivo `bootstrap-status.json`. Si la verificación falla, el script debe terminar con un código de error distinto de cero, lo que provocará que systemd marque el servicio como fallido y no continúe con el arranque. Esto es coherente con el patrón de diseño de validación temprana.
2.  **`ExecStart=`**: El binario principal (`etcd-server`), que arranca y borra el archivo como parte de su inicialización.

Esto se alinea con la recomendación de la industria de tratar `ExecStartPre` como una puerta de validación previa al inicio, no como una tarea de post-arranque.

### 3. Política de keypair en `staging` (DEBT-KEYPAIR-LIFECYCLE-PROD-001)

La política propuesta (`dev`/`staging` iguales, `prod` estricto) es pragmática y sigue las mejores prácticas de separación de entornos. Para este proyecto, la distinción clave es entre entornos "de juguete" y "reales".

*   **`dev` y `staging`**: La política actual es correcta. En estos entornos, la generación automática de un keypair si no existe es aceptable. La principal preocupación de seguridad aquí es el aislamiento: un keypair de `dev` jamás debe funcionar en `staging`, y viceversa. Esto se puede garantizar mediante el uso de `ARGUS_ENV` como parte del material de derivación de claves. La recomendación de generar keypairs únicos por entorno sigue siendo válida, pero la generación automática no representa un riesgo.
*   **`prod`**: La política `exit 1` es la correcta. En producción, la existencia del keypair debe ser un prerrequisito explícito, gestionado fuera de banda (fuera del pipeline de provisión automática). Esto evita la generación accidental de material criptográfico en un entorno real y obliga a un proceso de despliegue controlado y consciente.

### 4. Timeout de staleness en el reconciliador (DEBT-CRYPTO-RECONCILIATION-001)

La preocupación es muy pertinente. Que `poll_callback` retorne el último modo conocido ante la muerte silenciosa del publicador ZMQ es un fallo de diseño en un sistema de control. Un reconciliador que actúa sobre información "zombie" es un vector de fallo catastrófico.

**No es suficiente para FEDER ni para ningún entorno de producción.** El reconciliador debe ser capaz de distinguir entre "el último modo conocido es X" y "no sé cuál es el modo actual porque el publicador no responde". Para ello, es necesario implementar un mecanismo de **detección de frescura (staleness detection)**:

*   **Heartbeat a nivel de aplicación**: El publicador (`etcd-server`) debe enviar periódicamente un mensaje de heartbeat (p. ej., cada 1 segundo) por el mismo canal ZMQ. El suscriptor debe monitorizar el tiempo desde el último heartbeat recibido. Si este tiempo supera un umbral (p. ej., 3x el intervalo de heartbeat), el reconciliador debe considerar los datos como "obsoletos" (stale) y pasar a un estado seguro predefinido (que podría ser `DEGRADED` o directamente `NORMAL`, notificando la condición de error).
*   **Alternativa con monitor de heartbeat separado**: Un hilo ligero puede monitorizar el `zmq_poll` con un timeout, actualizando un timestamp atómico `last_heartbeat_ts`. El reconciliador consulta este timestamp antes de usar el `shared_mode`.
*   **Uso de ZMQ `ZMQ_HEARTBEAT_IVL`**: Si se configura adecuadamente en el socket, ZMQ puede gestionar heartbeats a nivel de protocolo y cerrar la conexión si fallan, lo cual puede ser detectado por el suscriptor.

La esencia es que el reconciliador no debe operar con datos potencialmente obsoletos sin ser consciente de ello.

### 5. Inconsistencias entre las deudas cerradas

A primera vista, no se observan inconsistencias graves. Las cuatro deudas son coherentes con una arquitectura que prioriza la integridad y la seguridad. No obstante, hay un área de fricción potencial que merece una revisión cruzada:

*   **Cadena de confianza y raíz de confianza**: La deuda `DEBT-AUTONOMY-STATE-PERSISTENCE-001` usa una clave Ed25519 interna para firmar el estado, mientras que `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` firma un artefacto efímero. La pregunta es: ¿ambas firmas derivan de la misma clave raíz de confianza? Si no es así, se introducen múltiples raíces de confianza, lo cual es un antipatrón de seguridad. Asegurar que ambas firmas se verifican con la misma clave pública raíz (o una cadena de certificación bien definida) unificaría el modelo de confianza y simplificaría la auditoría.

*   **Confianza en el sistema de archivos local**: Tanto `DEBT-AUTONOMY-STATE-PERSISTENCE-001` como `DEBT-BOOTSTRAP-STATUS-SIGNATURE-001` depositan una confianza significativa en la integridad del sistema de archivos `/var/lib/argus/`. Si un atacante consigue acceso de escritura a ese directorio, la firma digital se convierte en una defensa insuficiente, ya que el atacante podría reemplazar tanto el archivo de estado como la clave pública utilizada para verificarlo. Considerar el uso de un **TPM (Módulo de Plataforma Confiable)** o un **HSM (Módulo de Seguridad de Hardware)** para almacenar la clave de firma añadiría una capa adicional de defensa en profundidad, especialmente relevante para el despliegue hospitalario.

Dicho esto, el trabajo realizado es de alta calidad técnica. Las preguntas planteadas demuestran una excelente conciencia situacional.

Quedo a la espera de cualquier otra duda o aclaración.

— El Consejero