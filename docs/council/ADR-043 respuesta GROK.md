**Opinión experta — ADR-0043 v3**

**Valoración general: 9.2/10** — Excelente evolución.

La v3 es una **versión muy madura y lista para pasar a "Accepted"** con solo ajustes menores. Incorpora de forma limpia y pragmática casi todas las recomendaciones clave de la revisión anterior (identidad estable por MAC, idempotencia fuerte, key versioning ligero, eliminación de PRECEDES, timestamps UTC ns, etc.). El documento ha ganado claridad, precisión operativa y madurez legal/arquitectónica.

### Fortalezas destacadas (mejoras notables vs v2)

- **Identidad basada en MAC (D2)**: Decisión excelente y correcta para el dominio. La jerarquía de resolución (MAC → hostname → IP) es robusta y realista. La distinción `Host` vs `NetworkPresence` es semánticamente valiosa y evita contaminación del grafo. Muy buen manejo del caso IoT/DHCP.

- **Idempotencia por firma Ed25519 del batch completo (D4a)**: Elegante y fuerte. Soluciona de raíz el problema de reintentos y conectividad intermitente. Es criptográficamente verificable y no requiere almacenar hashes adicionales complejos.

- **Key rotation con versioning + :PREVIOUS_IDENTITY**: Muy buena mitigación. Evita migraciones masivas costosas y mantiene trazabilidad. El cooldown coordinado por Jenkins es coherente con el resto del sistema.

- **Timestamps como int64 epoch ns UTC**: Correcto y profesional. Elimina ambigüedad de zonas horarias y facilita ordenación/ventanas temporales en Neo4j y Parquet.

- **Eliminación de relación PRECEDES**: Acierto. Reduce ruido en el grafo y mejora rendimiento. Usar comparación lexicográfica de `period` es suficiente y más eficiente.

- **Flujo GDPR Art. 17 (D8)**: Muy bien estructurado. Es un punto frecuentemente olvidado y aquí está tratado con seriedad.

- **Schemas Parquet candidatos**: Gran avance. Dan un contrato claro y permiten avanzar en la implementación. Los campos elegidos son sensatos.

### Áreas de mejora / Riesgos restantes

1. **OQ-1 (conectividad intermitente)** — Debe cerrarse antes de producción
   - Recomendación fuerte: el nodo edge debe mantener una cola local persistente de batches pendientes (LevelDB, SQLite o incluso directorio con archivos + índice).
   - Política razonable: retener hasta 90 días (3 ciclos). Si el batch del mes M se pierde porque SQLite ya rotó los datos, se genera un batch "partial" con metadata explícita `partial: true, missing_days: [...]`.
   - El central debe aceptar batches parciales y marcarlo en el nodo `Batch`.

2. **Volumen y rendimiento de ingesta**
   - Con granularidad por flow/paquete, los Parquet pueden crecer mucho en instalaciones grandes.
   - Sugerencias:
      - Agregar al schema un campo `aggregation_level` o permitir dos modos (detailed + aggregated).
      - En Neo4j, considerar **graph projections** temporales o una capa de agregación en ClickHouse/TimescaleDB para queries analíticas pesadas, dejando Neo4j solo para relaciones de entidades y causalidad.

3. **Federated Learning (todavía ligero)**
   - El plugin desactivado por defecto es correcto. Recordar que cualquier agregación (FedAvg u otra) debe incluir **defensa contra envenenamiento** (especialmente en infra crítica). Mínimo: robust aggregation + outlier detection + validación de modelo antes de redistribuir.

4. **Auditoría y observabilidad**
   - Añadir recomendación de registrar en Neo4j (o mejor, en una tabla de auditoría inmutable) todos los eventos relevantes: batch ingest, erase requests, key rotations, vault restorations. Esto ayuda enormemente en auditorías GDPR y forenses.

5. **DEBT-GDPR-ERASURE-001 y DEBT-LEGAL-DATA-RETENTION-001**
   - Pregunta clave para el jurista: ¿es suficiente la destrucción certificada del Vault local + evidencia de que no existen backups de K_pseudo para considerar los datos en Neo4j como anonimizados? La respuesta condiciona la política de retención histórica.

### Recomendaciones menores de redacción / Mejora

- En D5, hacer explícito que los `Episode` también pueden llevar propiedades como `batch_signature` y `ingested_at` para trazabilidad.
- Añadir al schema Parquet un campo `anonymization_version` (int) para facilitar futuras rotaciones de K_pseudo.
- En metadatos del batch, considerar incluir `parquet_row_count` y `total_bytes` para detección temprana de anomalías.
- Documentar tamaño esperado de batch (estimación baja/media/alta) una vez validado DEBT-PARQUET-SCHEMA-001.

### Conclusión y Voto

**Voto: Aprobar con modificaciones menores** (principalmente cerrar OQ-1 con la estrategia de cola persistente y las recomendaciones de volumen/auditoría).

La arquitectura queda **sólida, defendible y alineada con las restricciones del proyecto** (GDPR, bajo presupuesto, misión crítica, coherencia temporal). Cumple muy bien los objetivos de investigación aplicada del FEDER.

Está lista para implementación. El siguiente cuello de botella real es **DEBT-PARQUET-SCHEMA-001** — una vez validado contra datos reales, el resto fluye de forma bastante directa.

Si quieres, puedo:
- Ayudar a redactar la respuesta detallada a OQ-1
- Proponer Cypher más completo para la ingesta idempotente
- Revisar el esquema Parquet definitivo cuando lo tengas
- Ayudar a escribir el runbook de key rotation / vault recovery

Enhorabuena al autor (Alonso). La v3 refleja muy buen nivel de ingeniería de sistemas distribuidos.