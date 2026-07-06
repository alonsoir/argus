**ACTA DEL CONSEJO DE SABIOS — RESPUESTA A LA PROPUESTA VIA APPIA**

*Reunión celebrada en el Día 209. Presentes: Arquitectura, Datos, Ciberseguridad e Ingeniería de Calidad.*
*Veredicto: Unánime.*

Hemos leído la propuesta. Es un ejercicio de diagnóstico excepcional. En un ecosistema donde suele primar la especulación o la intuición sobre los modelos de ML, habéis hecho lo único que importa: **abrir el capó, leer los tipos de datos y trazar la línea entre lo que el modelo aprendió y lo que el código le da de comer.**

El hallazgo del §2 (el desajuste ontológico entre host y red) no es un bug menor; es un fallo de arquitectura de dominio. El contraste del §5 (DDoS sí, Ransomware no) es la prueba definitiva que blindará este diagnóstico ante cualquier revisión externa.

A continuación, respondemos a las cinco preguntas planteadas para desbloquear la ejecución.

---

### 1. ¿Desactivar la cabeza de ransomware embebida actual?
**DECISIÓN: SÍ. Desactivación inmediata (`enabled: false`).**

**Razonamiento:** Un modelo que toma una decisión basada en un 36% de peso en una feature inventada (varianza de paquetes simulando entropía de disco) no está degradado, está *alucinando matemáticamente*. Dejarlo activo, incluso con una etiqueta de "no fiable", es un riesgo para la operativa: genera ruido, contamina las métricas globales del sistema y cualquier analista de SOC que vea un *score* de ransomware de aRGus estará tomando decisiones sobre arena.

**Acción requerida:**
1. Cambiar `enabled: false` en el config.
2. Abrir un ADR (Architecture Decision Record) titulado: *"Desactivación del detector L2 de ransomware por desajuste de dominio (Host vs. Red)"*. Enlazar este documento como evidencia empírica.

### 2. ¿Registrar `DEBT-RANSOMWARE-PROTO-ALIGNED-DEAD-001` y autorizar `git rm`?
**DECISIÓN: SÍ.**

**Razonamiento:** Un modelo de 45 features anónimas convertido "a pelo" desde un notebook es deuda técnica radiactiva. Si nadie sabe qué es, no se puede auditar, no se puede reproducir y no se puede mantener. Sin embargo, el Consejo aplaude la aplicación estricta del principio de trazabilidad: las cosas no desaparecen en silencio.

**Acción requerida:**
1. Crear el DEBT explicando su origen (hipótesis antigua de red pura), por qué falló (falta de contrato de features) y por qué es irrecuperable.
2. Ejecutar `git rm` (nunca `rm`) para que el artefacto muera, pero su historia quede grabada en el repositorio para la posteridad arqueológica del proyecto.

### 3. ¿Registrar `DEBT-DDOS-FEATURES-CONSTANT-001` sin acción inmediata?
**DECISIÓN: SÍ.**

**Razonamiento:** El diagnóstico es impecable. El DDoS es un "herido que camina": sus features estelares (simetría, ratios SYN/ACK) son legítimas y le permiten funcionar, pero arrastra tres features muertas (incluida una comparación que el compilador optimiza a `false`). En ingeniería de calidad, no se toca al paciente que se está estabilizando solo para quitarle una venda sucia si no hay infección.

**Acción requerida:** Registrar el DEBT. Añadir un comentario en el código fuente (`// DEBT-DDOS-FEATURES-CONSTANT-001: Hardcoded placeholder, pending cleanup`) y cerrar el frente. Se abordará en la próxima refactorización grande de la capa L2.

### 4. ¿Autorizar entrenar un modelo comportacional DE VERDAD? (Opción A vs Opción B)
**DECISIÓN: OPCIÓN A. Estrictamente Red.**

**Razonamiento:** La Opción B (Híbrido con Wazuh) es científicamente correcta, pero arquitectónicamente suicida para el plazo pre-FEDER. Introducir telemetría de host en un pipeline de red (NDR) a estas alturas cambia la naturaleza del sistema, requiere renegotiar scopes, latencias y contratos de datos.

La Opción A es la madurez que necesitáis: **redefinir qué significa "detectar ransomware" para un NDR**. No es detectar el cifrado (T1486), es detectar la *infraestructura y el ciclo de vida previo/posterior* del ransomware (reconocimiento T1046, exfiltración T1048, C2 T1071). Eso *sí* cruza `eth1`, eso *sí* lo puede entrenar aRGus con Atomic Red Team, y eso encaja en el presupuesto y tiempo actual.

### 5. ¿Aprobar la línea MITRE ATT&CK / Atomic Red Team como trabajo pre-FEDER?
**DECISIÓN: SÍ. Aprobación unánime y prioritaria.**

**Razonamiento:** Esta es la jugada maestra de la propuesta. En lugar de esconder que aRGus no ve el cifrado, **construíis un experimento para demostrarlo científicamente y publicarlo**. La matriz de ablación (qué sensor ve qué técnica) es un entregable de altísimo valor para Andrés y para la justificación científica del proyecto FEDER. Convierte un fallo de ingeniería del pasado en un paper de arquitectura de sensores del presente.

**Salvedad del Consejo para la ejecución:**
Para que este experimento sea irrefutable, debéis garantizar una cosa en la matriz: **la separación estricta de dominios durante la inyección**. Atomic Red Team permite ejecutar atomics de red puro y de host puro. Cuando ejecutéis el atomic de T1486 (cifrado de disco), aRGus, Suricata y Zeek *deben* callar. Si alguno dispara un falso positivo por el ruido del protocolo del atomic en lugar de la técnica en sí, el experimento se contaminará. El silencio de los NDR ante el cifrado es el resultado que validará toda vuestra tesis.

---

### Resumen del Consejo

Habéis encontrado la falla geológica del sistema. No es que el modelo fuera malo, es que **le pusisteis un termómetro para medir la velocidad de un coche**.

El Consejo autoriza las 5 acciones. Cerrad el frente del ransomware de host (muerto y enterrado con honor en un ADR), limpiad los cadáveres de código muerto, dejad al DDoS en paz, y concentrad toda la artillería en la **Opción A**: construir un modelo de red que cazue las fases de red del ransomware, validado por la matriz MITRE ATT&CK con Atomic Red Team.

Id a medir. El escudo agradecerá conocer exactamente dónde están sus sombras.

*— Via Appia Quality — Concilium Sapientium*

fdo
glm