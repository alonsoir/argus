**Respuesta del Consejo de Sabios — DAY 109**

Buen trabajo, Alonso. El DAY 109 es limpio, disciplinado y sigue fielmente la metodología **Test-Driven Hardening (TDH)**. Has demostrado cada cambio con tests que fallan primero y luego pasan. El escape hatch `MLD_ALLOW_UNCRYPTED`, la corrección del D8-light para READ-ONLY y el TEST-INTEG-4b (con intento de `const_cast` detectado) son ejemplos excelentes de endurecimiento defensivo. La reproducibilidad de `provision.sh` sigue mejorando.

El Consejo ha revisado todo el material con rigor. Respuestas directas y sin ambigüedades:

### Q1 — D8-light READ-ONLY: ¿es correcto el contrato?

**Sí, el contrato actual es correcto y suficiente.**  
Inferir modo READ-ONLY por `payload == nullptr && payload_len == 0` es pragmático, explícito y de bajo overhead. No introduce una vulnerabilidad grave porque:

- El D8-light sigue protegiendo el caso **normal** (payload real): si alguien intenta tocar memoria inválida o sobredimensionada → `std::terminate()`.
- En modo READ-ONLY se salta limpiamente la verificación de payload y el CRC32.
- El test VARIANT B (intento de modificación vía `const_cast`) ya detecta violaciones cuando el plugin intenta escribir en campos que no debe.

**No hace falta un flag explícito** `PLUGIN_MODE_READONLY`.  
Añadir un campo extra al struct `MessageContext` aumentaría complejidad de ABI, serialización (si alguna vez se usa) y superficie de ataque sin beneficio real. La convención `payload=nullptr` es clara, documentable y fácil de auditar. Manténla.

**Recomendación menor**: Añade un comentario fuerte en el header del plugin API:
```cpp
// READ-ONLY mode for rag-ingester: payload == nullptr && payload_len == 0
// Plugins may only inspect metadata and set result_code / annotation.
```

### Q2 — PHASE 2c (sniffer): ¿READ-ONLY o payload real?

**Recomendación clara del Consejo: PAYLOAD REAL en el sniffer (PHASE 2c).**

Razones:

- **Valor funcional superior**: En el sniffer el plugin está en el punto más temprano del pipeline. Tener acceso al payload real permite decisiones mucho más potentes (detección de patrones en payload, firmas simples, rechazo temprano de paquetes maliciosos obvios, etc.). READ-ONLY aquí sería desperdiciar la posición privilegiada del sniffer.
- **Consistencia vs. utilidad**: La consistencia total entre componentes es deseable, pero no a costa de inutilidad. rag-ingester es un componente de ingesta tardía (post-procesamiento), donde el "payload" ya no es el paquete crudo. El sniffer es el capturador de paquetes → debe poder actuar sobre ellos.
- **Mitigaciones de seguridad (D7 + D8)**: Los plugins son código no confiable → se ejecutan en sandbox ligero (actual o futuro seccomp / namespace). El acceso al payload está protegido por:
    - Verificación estricta de tamaño (`MAX_PLUGIN_PAYLOAD_SIZE`).
    - CRC32 antes/después para detectar modificaciones no autorizadas.
    - Posibilidad de copiar el payload a un buffer temporal controlado por el loader antes de pasarlo al plugin (recomendado para PHASE 2c).
    - D8-light ya maneja el caso de payload inválido.

**Contrato propuesto para PHASE 2c (sniffer)**:
- `payload` apunta al buffer del paquete capturado (solo los bytes relevantes, no toda la trama Ethernet si no es necesario).
- `payload_len` = tamaño real (limitado estrictamente, ej. primeros 256-512 bytes si es suficiente para la mayoría de detecciones).
- Plugin puede leer y **modificar** el payload si es necesario (ej. redactar PII sensible antes de pasar al siguiente componente), pero cualquier modificación debe ser declarada o verificada.
- Si `result_code != 0` → descartar paquete inmediatamente (no pasar a ml-detector ni al resto del pipeline).

Esto hace que los plugins sean realmente útiles en el sniffer sin comprometer demasiado la seguridad. Para payloads muy sensibles (hospitales) se puede añadir en el futuro un flag de “redact mode” o límite por configuración.

**Riesgo aceptable**: Sí, siempre que el sandbox del plugin-loader se endurezca progresivamente (seccomp, rlmit, etc.).

### Q3 — Integration Philosophy §4: ¿la restricción raw TCP es suficientemente justificada?

**La justificación actual es aceptable pero débil para una audiencia académica rigurosa.**  
Falta profundidad. “Recursos limitados” es verdad, pero no es el argumento más fuerte.

**Argumentos fuertes que deberías añadir (en orden de importancia)**:

1. **Superficie de ataque mínima** (security-first): Cada capa adicional (HTTP headers, WebSocket handshake, Kafka protocol) introduce parsers complejos, código de terceros y vectores de ataque remotos. Raw TCP + protobuf + ChaCha20 tiene superficie predecible y auditable.
2. **Latencia y determinismo**: En NDR para infra crítica (hospitales) se necesita latencia predecible < few ms en el datapath. Brokers añaden jitter, reconexiones y buffering impredecible.
3. **Dependencias de runtime y footprint**: Evitamos librerías pesadas (libcurl, librdkafka, boost.asio completo, etc.). El pipeline actual compila contra libsodium + protobuf + etcd-cpp + snappy → footprint muy pequeño, ideal para Raspberry Pi / hardware embebido.
4. **Simplicidad y auditabilidad**: Todo el stack de comunicación es controlado por el equipo. Facilita formal verification parcial y revisiones de seguridad profundas.
5. **Resiliencia en entornos aislados**: Muchos hospitales/municipios tienen redes segmentadas sin acceso fácil a brokers externos.

Mantén la frase “explicitly out of scope”, pero expándela con 2-3 párrafos cortos que incluyan los puntos anteriores + una tabla comparativa simple (raw TCP vs HTTP/Kafka: líneas de código estimadas, dependencias, latencia media, CVEs típicas).

Esto hace la sección académicamente sólida sin volverse defensiva.

### Q4 — ADR-028: ¿cuándo es bloqueante?

**Diferir ADR-028 hasta antes del primer plugin WRITE-CAPABLE (no antes de PHASE 2c).**

Razones:

- PHASE 2b y 2c son **READ-ONLY** → el modelo de confianza actual (D7 + D8-light + sandbox) es suficiente.
- ADR-028 trata del **trust model para modificación** (qué campos puede escribir un plugin, atomicidad, rollback, validación post-escritura, etc.). Escribirlo ahora sería especulativo.
- Escribir ADR-028 demasiado pronto sin haber tocado código real de write plugins generaría documentación prematura y posiblemente incorrecta.

**Recomendación**:
- Cierra PHASE 2c (sniffer con payload real) primero.
- Cuando diseñes el primer plugin que modifique estado (ej. enriquecer metadata, inyectar tags en el MessageContext, o redactar payload), entonces formaliza ADR-028 justo antes de implementarlo.
- Mientras tanto, documenta en el código los contratos READ-ONLY y READ-WRITE de forma explícita.

Esto mantiene el momentum sin burocracia innecesaria.

### Síntesis y recomendaciones del Consejo

- **Aprobado**: FIX-A, FIX-B, PHASE 2b completa, TEST-INTEG-4b, y los cambios en el paper.
- **Próximos pasos prioritarios**:
    1. Implementar PHASE 2c (sniffer) con **payload real** según el contrato recomendado.
    2. Endurecer ligeramente el plugin-loader (copia temporal del payload en sniffer antes de llamar al plugin).
    3. Mejorar la sección §4 del paper con los argumentos de seguridad/latencia/superficie de ataque.
    4. Una vez PHASE 2c verde → merge a main y preparar siguiente iteración hacia plugins especialistas (Track 1 de ADR-026).

El proyecto sigue una trayectoria excelente: endurecimiento progresivo, tests que protegen las decisiones, y documentación que evoluciona con el código. La distinción clara entre READ-ONLY y READ-WRITE será clave para la seguridad a largo plazo.

¿Quieres que el Consejo revise un borrador del contrato de MessageContext para PHASE 2c, o que propongamos texto concreto para la sección §4 del paper? Estamos listos para la siguiente revisión.

¡Sigue con el mismo rigor! El Consejo aprueba el estado actual y da luz verde para PHASE 2c con payload real.