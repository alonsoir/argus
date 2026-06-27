Recibido el parte del **DAY 175** de aRGus NDR. A continuación, mi análisis como miembro del Consejo de Sabios, respondiendo a tus tres preguntas con criterio.

---

## Resumen ejecutivo del día

Cierre sólido. Los cuatro pasos están bien justificados y el aprendizaje del paso 4 (falso verde por clave hardcodeada vs. clave real de etcd) es exactamente el tipo de lección que justifica la filosofía de "medir, no presuponer". La deuda `DEBT-BRONZE-KEY-PROVISIONING-001` está bien anclada.

---

## Respuestas al Consejo

### Q1 — Orden de batalla: ¿(A) injectors o (B) lado consumidor primero?

**[SUGERENCIA-CONSEJO: Priorizar (A) injectors, con un criterio adicional de riesgo.]**

Coincido plenamente con tu instinto. Sin injectors que poblen `community_id`, el bronce no es ejercitable en CI de forma determinista, y eso convierte a (B) en una tarea que solo se puede validar con infraestructura real (pcap + eBPF), lo cual es caro y frágil.

**Criterio adicional:** No trates (A) como "rellenar un campo". Trátalo como **contrato de inyección**: cada injector sintético que toque `NetworkSecurityEvent` debe garantizar que el `community_id` que genera es coherente con el que el sniffer real generaría (formato `1:wKZ...=`). Si los injectors fabrican IDs sintéticos con un formato distinto, estarás entrenando el pipeline de correlación con datos que no representan la realidad del eBPF. Sugiero definir un `SyntheticCommunityIdGenerator` reutilizable (quizás derivado de un hash del flujo sintético) para que el bronce de CI sea isomorfo al bronce de producción.

**(B) puede avanzar en paralelo solo hasta el file_watch → lectura de clave etcd**, pero sin (A) no hagas el salto a Kuzu. Kuzu con datos malformados o sin `community_id` es peor que Kuzu vacío.

---

### Q2 — `authoritative_source` como int crudo (columna 17)

**[SUGERENCIA-CONSEJO: Mantener int en bronce, pero anclar el mapeo en un archivo de contrato versionado.]**

Tu trade-off está bien planteado. Mi criterio:

- **Bronce debe preservar, no interpretar.** Ese principio es correcto. El bronce es un espejo de lo que el detector emitió; convertir a string simbólico en bronce sería una primera interpretación (y una primera oportunidad de desincronización si el .proto cambia).
- **Pero:** el contrato int→enum debe ser **explícito y versionado**, no implícito en el código del reader. Recomiendo un archivo `bronze_schema_v1.yaml` (o similar) que declare:
  ```yaml
  authoritative_source:
    type: int32
    enum_mapping:
      0: UNKNOWN
      4: ML_PRIORITY
      6: DIVERGENCE
    source_proto: DetectorSource  # referencia al .proto de origen
    proto_version: "v2.3.1"       # versión del .proto en el momento de la escritura
  ```
  Esto hace que el bronce sea **auto-descriptivo sin ser verboso**, y permite al consumidor (Kuzu, o un debugger humano) reconstruir el significado sin adivinar.

Si en el futuro el enum cambia de valores, el `proto_version` te permite detectar bronce escrito con un mapeo antiguo y migrarlo antes de gold. Sin este anclaje, el int crudo es una bomba de tiempo silenciosa.

---

### Q3 — `DEBT-BRONZE-KEY-PROVISIONING-001` y modelo de confianza multi-nodo

**[SUGERENCIA-CONSEJO: Sí, es una grieta de diseño. Anclar en ADR antes de escribir el consumidor. No esperar a "miles de nodos" para decidir.]**

Tu intuición es correcta: el HMAC simétrico por-componente no escala a la arquitectura medallion multi-tenant que describes. Hoy funciona porque writer y reader son el mismo proceso lógico (o al menos el mismo nodo Vagrant). Cuando el consumidor sea un servidor central que ingiere bronce de N sensores, compartir un secreto simétrico global es:
1. **Un único punto de compromiso** (una fuga de etcd central invalida N sensores).
2. **Imposible de rotar** sin coordinar N nodos simultáneamente.
3. **Sin no-repudio:** el servidor central no puede demostrar ante un tercero qué sensor firmó qué fila.

**Recomendación de ADR:** No usar Ed25519 directamente sobre cada fila de bronce (sería lento y el bronce es alto volumen), sino una **jerarquía de claves**:
- Cada sensor tiene un par Ed25519 (ya lo usáis para plugins).
- El sensor deriva una clave simétrica de corta vida (HMAC) firmada con su Ed25519, y la publica en etcd junto con la firma.
- El servidor central valida la firma Ed25519 una vez por clave de sesión, y luego usa el HMAC simétrico para validar el volumen de filas.

Esto da lo mejor de ambos mundos: velocidad del HMAC simétrico para el dato, no-repudio y rotación granular del asimétrico para el provisioning. Si no ancláis esto en ADR ahora, el consumidor se escribirá asumiendo el HMAC simétrico compartido, y la deuda de migración será dolorosa.

---

## Cierre

El DAY 175 es un hito real: bronce cableado, verificado con datos reales, y con una deuda explícita. Mi única advertencia es que no dejes que la euforia del "cierre real" del paso 4 disminuya la prioridad de (A). Un pipeline que solo se valida con pcap real es un pipeline que no se valida en cada commit.

¿Queréis que profundice en alguno de los tres puntos, o que bosqueje el esquema de la jerarquía de claves para el ADR de Q3?

— *Miembro del Consejo*

FDO KIMI