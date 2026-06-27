**CONSEJO DE SABIOS — DICTAMEN SOBRE PLAN DE IMPLEMENTACIÓN (DAY 196)**  
*Sesión extraordinaria, 2026-06-27*

Recibido el documento «PLAN — Circuito completo aguas abajo». Actuamos como adversarios según se solicita, sin concesiones. Cada decisión será escrutada; cada supuesto, cuestionado.

---

### 1. Sobre la ratificación de la opción B (formato de salida `correlation_v1`)

**Dictamen:** Se ratifica la opción B.  
**Condiciones y exigencias:**

- El contrato `correlation_v1` está sellado con 19 columnas. Cualquier cambio estructural futuro requerirá una nueva versión de contrato, documento de migración y plan de coexistencia durante la transición. No se admitirán parches «por una columna más».
- El Consejo exige que se demuestre, antes del Eslabón 4, que el `community_id` producido por Suricata y Zeek coincide efectivamente con el de aRGus para los mismos flujos **en el entorno de integración**, no solo en teoría. Se aportarán logs de validación cruzada. La coincidencia simétrica es condición necesaria para el join cross-engine; cualquier discrepancia invalidaría el circuito de correlación de flujo y obligaría a rediseñar el oro.
- **Cuestión no resuelta en el plan: encuadre ZMQ de la línea CSV.** El plan afirma que el adapter emitirá «filas `correlation_v1`». ¿Una fila CSV por mensaje ZMQ? ¿Mensaje con múltiples filas? ¿Separador de trama? Esto no es un detalle menor: afecta a la propiedad *at-least-once* y a la granularidad del checkpoint. Se requiere una especificación explícita del framing antes de codificar el Eslabón 6. Sin ella, el contrato de transporte es incompleto y AdapterSpec v1.1 sería papel mojado.

---

### 2. Forma del oro: join en Arrow vs join en Kuzu

El Consejo observa que se propone *oro-como-ledger* + join en Kuzu, pero los argumentos son insuficientes para una decisión irreversible en este momento.

**Objeciones y exigencias:**

- «Kuzu existe para hacer joins» es una verdad a medias. Kuzu está diseñado para consultas de grafo sobre datos ya relacionados. No hay evidencia en el plan de la complejidad computacional de materializar `:NetworkFlow` compartido a partir de millones de eventos de múltiples sensores con community_id, especialmente cuando los flujos de Zeek llegan con 5 minutos de retraso. Exigimos un **prototipo de carga y consulta con datos sintéticos a escala** (al menos 1M de filas por sensor) que mida tiempo de ingesta, uso de memoria y latencia de las consultas previstas para el dashboard, antes de descartar el join en Arrow.
- El argumento de la Via Appia (oro inmutable, Kuzu reconstruible) es válido, pero ignora que un oro pre-join en Arrow también es inmutable y reconstruible: el join se computa, se materializa en Parquet y se versiona. La diferencia es dónde reside la complejidad del join y quién paga el coste en consultas posteriores.
- Si se elige Kuzu para el join, el Consejo exige que el esquema del grafo (nodos, aristas, propiedades) se especifique formalmente y se someta a revisión **antes** del Eslabón 2. No aceptaremos «lo definiremos al implementar».
- Se deja abierta la posibilidad de un enfoque híbrido: oro-como-ledger para la preservación cruda, y una vista materializada *dentro de la LZ* (en Parquet) para consultas analíticas batch que no necesiten grafo. Esta vista sería un producto derivado, no el oro canónico.

**Decisión preliminar:** Se autoriza continuar con la exploración del diseño oro-como-ledger + join en Kuzu, pero el Eslabón 2 no se considerará cerrado hasta que se presente el prototipo de rendimiento exigido y el esquema de grafo detallado. La elección final se revisará en un nuevo Consejo.

---

### 3. Centinela numérico

**Dictamen:**
- Se confirma `-1` como centinela para las columnas numéricas ausentes en CSV (`src_port`, `dst_port`, scores, etc.). El valor `0` queda **prohibido** por su ambigüedad semántica (score nulo vs score de inactividad, puerto 0 válido en algunos contextos).
- Se exige que la capa de conversión a Parquet (Eslabón 1) transforme el centinela `-1` a `null` tipado de Arrow **sin excepciones**. La documentación del esquema Parquet debe declarar explícitamente qué columnas admiten nulos por este motivo.
- El reader C++ y el grafo Kuzu deberán tratar los nulos como «no aplica», no como error, y las consultas Cypher del dashboard deberán contemplar esta semántica. Cualquier agregación que ignore nulos (lo estándar) es aceptable, pero deberá quedar documentada para evitar interpretaciones erróneas de «score medio».

---

### 4. Rotación y seguimiento del fichero bronce

El plan expone dos opciones: que el engine vigile el directorio o que el lanzador recalcule el datado. Ambas son insuficientemente robustas tal cual se describen.

**Dictamen y requisitos:**

- El engine **debe vigilar el directorio** como fuente primaria de nuevos datos, utilizando mecanismos del sistema operativo (inotify o similar) para detectar la aparición de un nuevo fichero diario. No se admite un recalculo puntual en el arranque; eso garantiza perder el corte de medianoche si el engine está corriendo.
- Adicionalmente, el engine debe mantener internamente el offset de lectura dentro del fichero actual y ser capaz de reanudar tras reinicio (checkpoint de posición en fichero + hash de la última línea procesada). Esto es crítico para cumplir *at-least-once* sin reprocesar el día entero.
- El lanzador podrá seguir proporcionando un `--bronze` inicial, pero solo como semilla para el primer arranque; después el engine gestionará la rotación autónomamente.
- Se abre deuda técnica `ROTATION-FOLLOW` con prioridad P1, y se añade como condición para cerrar el Eslabón 0: la configuración JSON que sustituya el hardcode del writer deberá incluir también el patrón de naming de ficheros para que el engine pueda derivar la lista de ficheros a vigilar sin ambigüedades.

---

### 5. Wazuh y el contrato `correlation_v1`

La postura del plan es correcta al identificar que Wazuh **no cabe** en el contrato actual, pero la propuesta de extender `correlation_v1` con `host_key` (creando `correlation_v2`) es rechazada de plano por este Consejo.

**Argumentos y decisión:**

- `correlation_v1` es un contrato sellado para el dominio de red. Abrirlo para añadir un campo de host contaminaría su semántica, obligaría a migrar todos los productores y consumidores existentes, y rompería la compatibilidad hacia atrás. La Via Appia exige que los contratos sean estables; no se alteran por acumulación.
- Wazuh pertenece a un dominio ontológico distinto: eventos de host, no flujos de red. Forzar su encaje mediante un campo foráneo es un antipatrón de modelado. La arista entre host y flujo es legítima, pero debe representarse en el grafo, no en el esquema de ingesta.
- Se ordena la creación de un nuevo contrato **`host_domain_v1`** (o similar) específico para eventos de host, con su propio medallón, su propia zona bronce y su propio pipeline. La conexión con el dominio de red se realizará exclusivamente en Kuzu, materializando relaciones `HostEvent –[INVOLVES_IP]– NetworkFlow` mediante consultas Cypher que correlacionen IPs y ventanas temporales.
- La deuda `DEBT-CORRELATION-V1-HOSTKEY-001` se transforma en la tarea de diseño de este nuevo contrato. El Eslabón 5 (Wazuh) no comenzará hasta que ese contrato esté ratificado por el Consejo.

---

### 6. Andrés (stub)

El contrato negativo es aceptable como contención de alcance, pero el Consejo no tolerará incertidumbre indefinida.

**Exigencias:**

- Las 5 incógnitas listadas (naturaleza, transporte, community_id, clave de join, staleness SLO) deben ser respondidas por el responsable del motor Andrés en un plazo máximo de 15 días naturales desde la fecha de este dictamen. Si no hay respuesta, el stub se considerará abandonado y se eliminará del plan para no generar deuda fantasma.
- Mientras tanto, el adapter correspondiente no se implementará; el código contemplará un punto de extensión documentado (interface + mock) pero sin lógica alguna. Cualquier intento de codificar un adapter sin esas respuestas será vetado.

---

### 7. Decisiones adicionales (extraídas del cuerpo del plan)

**Enmienda AdapterSpec v1 → v1.1**  
Se aprueba con las siguientes correcciones vinculantes:
- Debe especificar explícitamente que el formato de salida de un adapter **puede** ser `correlation_v1` CSV+HMAC **o** un contrato de dominio específico (como el futuro `host_domain_v1`), eliminando toda referencia al inexistente protobuf `SecurityEvent`.
- La sección de checkpoint (§6) debe aclarar si el checkpoint es responsabilidad del adapter o del engine, y cómo se implementa para un adapter basado en fichero CSV (offset, rotación). Hasta que no esté claro, la especificación no estará completa.
- La deuda `DEBT-ADAPTERSPEC-ENVELOPE-001` se cierra condicionalmente a que la enmienda refleje estos cambios y se verifique que ningún otro documento hace referencia al envelope protobuf desaparecido.

**Hardcode de configuración (`DEBT-CONFIG-BRONZE-HARDCODE-001`)**  
Se exige que el Eslabón 0 se complete antes de cualquier otro eslabón que toque datos. La verificación de que writer y engine resuelven al mismo path **no será visual**; se exigirá un test de integración automático que ejecute el flujo completo y compruebe que los ficheros producidos son exactamente los consumidos, con hash HMAC válido, tanto en arranque como tras rotación simulada de medianoche.

**Separación adapter-argus / lógica ML**  
El Consejo refuerza el principio «co-ubicado sí, indistinto no». Exigimos que cuando se migre a ZMQ PUB/SUB, el adapter-argus sea un publicador independiente dentro del proceso `ml-detector`, con su propio socket y bucle de envío, que no comparta estado mutable con el motor de inferencia. Cualquier acoplamiento detectado en la revisión de código será motivo de bloqueo del merge.

---

### Resumen de condiciones para proceder

1. Prototipo de rendimiento de Kuzu con datos a escala (previo al cierre del Eslabón 2).
2. Esquema formal del grafo Kuzu (previo al Eslabón 2).
3. Especificación del framing ZMQ para CSV (previo al Eslabón 6).
4. Implementación del Eslabón 0 con test de rotación automatizado (previo a cualquier otro eslabón).
5. Nuevo contrato `host_domain_v1` diseñado y ratificado (previo al Eslabón 5).
6. Respuesta vinculante sobre Andrés en 15 días o eliminación del stub.

Este Consejo no dará «palmaditas en la espalda». El plan es ambicioso y contiene aciertos de arquitectura, pero las lagunas identificadas deben cerrarse con evidencia, no con buenas intenciones. Quedamos a la espera de las pruebas solicitadas.

— *El Consejo de Sabios*

FDO

DEEPSEEK