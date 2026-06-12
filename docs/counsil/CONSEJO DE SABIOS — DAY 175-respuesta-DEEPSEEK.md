A la atención de Alonso, Lead Developer de aRGus NDR, y al resto del Consejo.

Enhorabuena por el cierre del día 175. Habéis transformado un diseño limpio en una cadena de datos viva y verificada, y además habéis medido donde otros habrían presupuesto. Celebro especialmente el hallazgo de la clave de producción frente al falso verde del test unitario: esa cicatriz es justo el tipo de lección que convierte un proyecto en un sistema resiliente.

Paso a analizar las tres preguntas, aportando criterio y las sugerencias solicitadas.

---

### Q1 — Orden de batalla: ¿inyectores primero (A) o lado consumidor (B)?

Comparto vuestro instinto, Alonso. **Primero (A), los injectors sintéticos.**  
La razón de peso no es solo el coste del replay ni el determinismo, sino la *velocidad del bucle de realimentación*. Sin injectors que generen tráfico bronce válido, cualquier avance en (B) se validará contra un goteo de pcaps reales que no cubrirá caminos excepcionales (community_id vacío, HMAC corrupto, eventos de diverso `authoritative_source`). Al inyectar, se puede probar el file_watch, el parseo, la conversión Avro y hasta la ingesta en Kuzu con volúmenes controlados y fallos inyectados en CI.

Dicho esto, (A) no es un bloqueante absoluto para empezar (B): se puede avanzar el reader de bronce con test harnesses que inyecten eventos válidos usando la clave real de etcd, algo que ya casi tenéis con el `parse_and_verify`. Pero eso no sustituye un flujo continuo sintético. Por tanto:

**[SUGERENCIA-CONSEJO-NDR: Aprobar orden (A) → (B). Avanzar primero los injectors con community_id (empezando por el mecanismo oficial). En paralelo, permitir un spike ligero del lado consumidor que lea la clave de etcd y valide el HMAC para cerrar la deuda `DEBT-BRONZE-KEY-PROVISIONING-001`, sin llegar aún a Kuzu. Así desacoplamos la clave del resto del pipeline.**]

---

### Q2 — `authoritative_source`: ¿int crudo o nombre simbólico?

Aquí vuestra decisión de preservar el int en bronce y delegar la semántica a la capa gold es acertada, con un matiz crucial. El int es compacto, rápido y a prueba de cambios de nomenclatura, siempre que el mapeo sea inmutable. Pero el riesgo no es solo un cambio futuro del valor del enum en el .proto: es que dos componentes compilen contra definiciones distintas del enum y generen silenciosamente incoherencias. Bronce debe poder autodescribirse lo suficiente para que un lector sin acceso al .proto original pueda interpretarlo años después.

Por tanto, recomiendo mantener el int, pero añadir en la cabecera del fichero CSV o en la definición del esquema Avro un campo de versión del mapeo (`source_enum_version`) y, opcionalmente, una tabla de lookup en un archivo de metadatos acompañante. Esto da legibilidad sin inflar cada fila.

**[SUGERENCIA-CONSEJO-NDR: Seguir con `authoritative_source` como entero. Incluir en la especificación del contrato bronce una versión semántica del enum (ej. `1.0.0`) y publicar el mapeo canónico. Si algún día se añade un nuevo valor al enum, se incrementa la versión y el lector sabrá que el mapeo cambió. No usar strings en el registro; eso lo hace frágil frente a refactorizaciones cosméticas.**]

---

### Q3 — Clave HMAC simétrica y modelo de confianza multinodo

Esta es la pregunta que más me inquieta, y aplaudo que la hayáis elevado ahora y no cuando Kuzu central rechace el 30% del tráfico de un hospital.

El HMAC simétrico *por sensor* funciona en un solo nodo porque el productor y el consumidor comparten secreto vía etcd. En un despliegue multinodo con un servidor central que ingiere bronce de cientos de sensores, ese modelo tiene dos fallos graves:
1. **Gestión de secretos:** el servidor central debe conocer la clave HMAC de cada sensor. Eso lo convierte en un objetivo de altísimo valor y multiplica la superficie de ataque.
2. **No repudio atenuado:** un sensor puede afirmar que él no generó un registro, pues la clave la tiene también el servidor. La firma asimétrica da no repudio técnico (el sensor firmó con su privada y solo él la posee).

Ya que usáis Ed25519 para plugins, la coherencia arquitectónica es clara: **cada sensor firma los registros bronce con su clave privada Ed25519**. El servidor central solo necesita la clave pública de cada sensor (distribuible sin riesgo). El HMAC podría permanecer como integridad local dentro del sensor, pero la verificación cross-node se haría con la firma. Esto se alinea con una arquitectura medallion federada: bronce firmado, silver/plata con validación de firma, gold con correlación.

Conviene redactar un ADR ahora, porque cambiar de HMAC a firma asimétrica impacta el writer, el formato de registro (se añade un campo `signature`), y el arranque del correlation-engine (buscar la clave pública, no el secreto). La deuda `DEBT-BRONZE-KEY-PROVISIONING-001` no se resuelve solo con aprovisionar la clave actual; se convierte en la semilla de ese ADR.

**[SUGERENCIA-CONSEJO-NDR: Abrir ADR titulado “Firma de eventos bronce con Ed25519 para despliegues multinodo” antes de implementar el lado consumidor. El esquema propuesto: sensor firma cada lote o cada registro con su clave privada; el correlation-engine central valida con la clave pública obtenida de etcd (`/secrets/<sensor_id>/pubkey`). Mantener opcionalmente el HMAC para coherencia interna, pero el contrato de confianza federado se basa en la firma. Esto cierra la grieta de diseño que Alonso intuye.**]

---

Como reflexión final: la filosofía de *medir, no presuponer* se ha convertido en el escudo del proyecto. Hoy habéis medido la clave, el cableado y el round-trip. Mañana medid la firma asimétrica con un test similar al paso 3. El bronce ya corre de verdad; ahora asegurémonos de que cuando corra desde cien sensores, el corazón de Kuzu no se pare.

Gracias por 175 días de disciplina.

— *Sabio-NDR, en nombre del Consejo*

FDO

DEEPSEEK