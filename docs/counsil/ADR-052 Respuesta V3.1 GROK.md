**ADR-052 v3.1 está listo para ratificación.** Es la versión más limpia, coherente y honesta del documento hasta la fecha. Las auto-correcciones (C1–C4) son de alta calidad y resuelven los últimos puntos débiles de v3 sin introducir nueva complejidad innecesaria. El ADR ahora tiene una madurez excelente: equilibra rigor distribuido, pensamiento adversarial, disciplina científica (corpus primero) y pragmatismo de implementación.

### Fortalezas a Apuntalar (Destacadas en v3.1)
- **Simplificación del `node_id` (C1)**: Decisión correcta. Usar un string canónico legible y declarado (`argus-sensor-gw-lan-01`) es superior: auditable en forense, estable ante rebuilds, y evita cualquier componente mutable en el hash. La continuidad de rol gana, como debe ser para el corpus.
- **Separación explícita en §3.6 (C3)**: Excelente refinamiento. Distinguir `corroboration_confidence` (sube con testigos) del **peso de de-duplicación** (baja con testigos) y dejar el verdadero IPW a ADR-040 es una corrección de categoría muy importante. Evita confusiones futuras en el pipeline ML.
- **Acotamiento de TLS (C2)**: Honesto y profesional. Reconocer que el mismatch TLS requiere un *cert-expectation store* y limitarlo a destinos gestionados evita scope creep y mantiene integridad con §0.
- **WAL hash-chain detallada (C4)**: Muy buena especificación (`prev_hash` + verificación periódica). Da dos detecciones independientes (cadena rota vs divergencia grafo-WAL). Esto eleva el no-repudio a nivel producción-grade.
- **Consistencia general**: Todas las secciones ahora alinean mejor con la misión del corpus. Los tests de validación están completos y bloqueantes donde corresponde.

### Puntos Débiles / Riesgos Residuales (Bajos)
1. **Complejidad operativa**: Sigue siendo un ADR rico (WAL, mapa versionado, NAT conflictos, primitivas + dos derivadas de confianza, señales TCP/TLS acotadas). El riesgo principal es que el equipo de implementación cometa errores sutiles en ingest o en la materialización grafo↔WAL.
2. **`seq_in_window` persistido**: Sigue dependiendo de DEBT-SEQWINDOW-PERSIST-001. Un crash del sensor justo después de computar el contador pero antes de emitir podría ser delicado.
3. **Dependencias load-bearing**: Mapa de cobertura, NTP, inventario firmado y WAL son críticos. Si cualquiera falla, varias métricas (`orphan_rate`, IPW, provenance) se degradan.
4. **TLS parcial**: La acotación es correcta, pero introduce una deuda (DEBT-CERT-EXPECTATION-STORE-001) que debe priorizarse si se quiere cobertura completa del vector A ampliado.

Ninguno de estos riesgos es bloqueante para ratificar. Son esperables en un sistema de esta ambición.

### Comentarios Específicos
- **§3.1.2 (`node_id` legible)**: Excelente. Legible en el grafo facilita forense humano y depuración del corpus.
- **§3.6**: Ahora muy claro. La nota de honestidad sobre las dos cantidades opuestas es valiosa.
- **§3.7 (WAL)**: Suficientemente especificado para implementación. La hash-chain con la misma `H` del proyecto es elegante.
- **§3.11**: Delimitación perfecta tras C2. Buena tabla separando TCP (ligero) y TLS (condicionado).
- **Validación**: Tests sólidos, especialmente estabilidad `node_id`, paridad con `seq_in_window` transportado, y las dos detecciones de manipulación del etiquetado.
- **Deudas**: Bien priorizadas y claras. Las P0 son las que realmente desbloquean poblar el grafo.

### Confirmación de Fidelidad (§6)
**Sí, refleja fielmente el consenso de la 2ª pasada** y deja muy claras las anulaciones/decisiones del árbitro:
- Función de hash anclada a libsodium congelada.
- Inclusión de señales TCP/TLS (con acotamiento honesto en v3.1).
- Ratificaciones de Q1 y Q5.

Las auto-correcciones (C1–C4) mejoran el documento sin contradecir el consenso previo. No se necesita tercera deliberación completa.

### Tareas Accionables Recomendadas (Post-Ratificación)
1. **Ratificar formalmente** (Alonso) y pasar a **v4 Approved**.
2. **P0 Inmediatas** (bloqueantes para poblar Neo4j):
   - Implementar + testear codificación `flow_uid` (DEBT-FLOWUID-CANONICAL-ENCODING-001), incluyendo paridad con `seq_in_window` transportado.
   - Definir y versionar el inventario de `node_id` declarados.
   - Crear constraint compuesto Neo4j sobre `(node_id, flow_uid)`.

3. **P1 Críticas**:
   - DEBT-SENSOR-COVERAGE-MAP-001 (tabla/cache + versionado + beacons).
   - DEBT-LABEL-WAL-001 (implementación etcd/Raft + verificación periódica).
   - DEBT-ARGUSPP-HOST-TCP-001 (anomalías RST/seqnum).

4. **Calibración y Pruebas**:
   - Campaña en golden pcaps + escenarios MITRE para `N` por protocolo (TCP/UDP), ventanas asimétricas y `nat_confidence_floor`.
   - Medir memoria y throughput del rate-limiter de cardinalidad exacta.

5. **Documentación / Mejoras Menores**:
   - Añadir un diagrama de alto nivel (evento → `flow_uid` → ingest → WAL → Neo4j).
   - Formalizar `FlowObservation` vs `FlowIdentity` (DEBT-ARCH-FLOW-OBSERVATION-001).
   - Detallar estrategia de storage por niveles (§7).

**Conclusión**: **ADR-052 v3.1 está listo para ratificar**. Es un documento de arquitectura sobresaliente que el proyecto puede estar orgulloso de tener. Proporciona una base sólida, reproducible y científicamente honesta para el grafo de correlación y, sobre todo, para el corpus de entrenamiento que es la verdadera misión.

Si Alonso lo ratifica, el siguiente paso natural es cerrar las deudas P0 y comenzar a poblar el grafo de forma controlada (primero en entorno LAB con golden sets).

¿Quieres que prepare el texto final limpio para v4 Approved, ejemplos de Cypher para el esquema/constraints, o pseudocódigo para el WAL/verificación? Estoy a disposición.

FDO

GROK