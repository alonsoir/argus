**Dictamen del Consejo de Sabios — ADR-0043 v3**
*10 de mayo de 2026 | Respuesta unificada*

---

---

## **📜 Veredicto General**
**✅ APROBADO CON AJUSTES MENORES.**
La versión **v3 del ADR-0043** incorpora **todas las recomendaciones del Consejo** de manera satisfactoria, con mejoras significativas en:
- **Precisión técnica** (ej: uso de MAC como identidad primaria, `idempotency_key` basada en firma Ed25519).
- **Claridad legal** (ej: flujo de derecho al olvido en D8, `DEBT-GDPR-ERASURE-001`).
- **Detalles de implementación** (ej: schema Parquet candidato, ontología Neo4j mínima).

**Puntos destacados:**
✔ **MAC como identidad primaria** (D2) resuelve el problema de coherencia temporal con DHCP.
✔ **`idempotency_key` determinista** (D4a) garantiza estabilidad en reintentos.
✔ **Schema Parquet candidato** (D4b) es **técnicamente sólido** y alinea con las mejores prácticas (Apache Arrow).
✔ **Flujo de derecho al olvido** (D8) es **completo y alineado con GDPR**.
✔ **Ontología Neo4j mínima** (D5) es **suficiente** para el MVP.

**Ajustes requeridos:**
⚠ **Aclaraciones menores** en D2 (jerarquía de identidad), D4 (fragmentación de batches), y D7 (recuperación de Vault local).
⚠ **Priorización de deudas** (especialmente `DEBT-PARQUET-SCHEMA-001`).
⚠ **Respuesta a OQ-1** (conectividad intermitente).

---

---

---

## **🔍 Análisis por Sección**

---

### **📌 D2 — Identidad de entidad: MAC como campo primario**
**✅ APROBADO CON ACLARACIÓN MENOR.**
- **Puntos fuertes:**
    - **MAC como identidad primaria** es **correcto** para entornos de infraestructura crítica (donde la randomización de MAC está desactivada).
    - **Jerarquía de resolución** (MAC → hostname → IP) es **robusta**.
    - **Distinción entre `Host` y `NetworkPresence`** es **semánticamente precisa**.

- **Ajuste requerido:**
    - **Aclarar el manejo de MACs multicast/broadcast:**
        - En el schema actual, se usa `MAC_src` como identidad, pero **MACs multicast (ej: `01:00:5E:...` para IPv6) o broadcast (`FF:FF:FF:FF:FF:FF`)** no deben usarse como identidad.
        - **Propuesta:**
            - **Filtrar MACs no unicast** en la jerarquía de resolución:
              ```python
              def is_unicast_mac(mac):
                  # El primer byte: bit 0 = 0 (unicast), bit 1 = 0 (global)
                  return (int(mac[0:2], 16) & 0x03) == 0x00
      
              def resolve_identity(registro):
                  if registro.mac_src and is_unicast_mac(registro.mac_src):
                      return HMAC-SHA256(K_pseudo, registro.mac_src)
                  elif registro.hostname:
                      return HMAC-SHA256(K_pseudo, registro.hostname)
                  else:
                      return HMAC-SHA256(K_pseudo, registro.ip_src)  # NetworkPresence
              ```
            - **Añadir al ADR:**
              > *"Solo se usan MACs unicast como identidad primaria. MACs multicast/broadcast se tratan como `NetworkPresence` (fallback a IP)."*

---

### **📌 D3 — Pseudonimización determinista**
**✅ APROBADO SIN CAMBIOS.**
- **`K_pseudo` por instalación** + **HMAC-SHA256** es **óptimo**.
- **Versionado de `anon-id`** (`K_pseudo_vN`) tras rotación es **elegante**.
- **Canal de rotación** (Jenkins → etcd → Vault local) es **seguro y escalable**.

---

### **📌 D4 — Paquete mensual por nodo**
**✅ APROBADO CON DETALLES ADICIONALES.**

#### **D4a — Clave de idempotencia**
- **✅ Correcto:** Usar `firma Ed25519(batch_content)` como `idempotency_key`.
- **Recomendación:**
    - **Incluir `period_start` y `period_end` en el cálculo de la firma** para evitar colisiones entre batches de distintos meses con el mismo contenido (improbable pero posible).
    - **Ejemplo:**
      ```json
      {
        "idempotency_key": "ed25519:sha256(period_start + period_end + batch_content)"
      }
      ```

#### **D4b — Schema Parquet candidato**
- **✅ Schema es técnicamente sólido.**
    - **`timestamp_utc_ns` (int64):** **Óptimo** (evita strings, zona horaria explícita en UTC).
    - **`anon_host_id`/`anon_flow_id` (utf8):** **Correcto** (HMAC en hex lowercase).
    - **Tipos de Arrow:** **Adecuados** (ej: `float32` para `confidence`).

- **Ajustes menores:**
    1. **`dst_port_class`:**
        - **Problema:** `well-known` (<1024), `registered` (1024-49151), `ephemeral` (49152-65535) es **correcto**, pero **`ephemeral` puede ser ambiguo** (algunos sistemas usan puertos efímeros en rangos distintos).
        - **Propuesta:**
            - Usar **`dynamic`** en lugar de `ephemeral` para mayor claridad.
            - **Schema actualizado:**
              ```json
              "dst_port_class": "well-known|registered|dynamic"
              ```
    2. **`alert_severity`:**
        - **Problema:** `0=none` puede ser redundante (si `event_type="normal"`, ¿por qué incluir `severity=0`?).
        - **Propuesta:**
            - **Eliminar `0=none`** y usar `NULL` para eventos sin severidad.
            - **Schema actualizado:**
              ```json
              "alert_severity": "low|medium|high|critical"  // NULL si no aplica
              ```

#### **D4c — Fragmentación de batches**
- **⚠ Riesgo no cubierto:** Si un batch supera **100 MB** (límite sugerido en el dictamen anterior), **¿cómo se fragmenta?**
    - **Propuesta:**
        - **Fragmentar por `event_type`:**
            - `ml-detector-YYYY-MM-{anon_node_id}-anomaly.parquet`
            - `ml-detector-YYYY-MM-{anon_node_id}-normal.parquet`
        - **O por rango temporal:**
            - `ml-detector-YYYY-MM-{anon_node_id}-part1.parquet` (días 1-15)
            - `ml-detector-YYYY-MM-{anon_node_id}-part2.parquet` (días 16-31)
        - **Añadir al ADR:**
          > *"Si el batch supera 100 MB, se fragmenta por `event_type` o rango temporal. Cada fragmento incluye los mismos metadatos JSON, con `fragment_index` y `total_fragments` para reconstrucción en el servidor central."*

---

### **📌 D5 — Modelo de grafo Neo4j**
**✅ APROBADO SIN CAMBIOS.**
- **Ontología mínima** es **suficiente** para el MVP.
- **Eliminación de `PRECEDES`** es **correcta** (el ordenamiento temporal se infiere de `Episode.period`).
- **`MERGE` idempotente** es **robusto**.

- **Recomendación (opcional):**
    - **Añadir índice en Neo4j** para `Host.id` y `Episode.period`:
      ```cypher
      CREATE INDEX FOR (h:Host) ON (h.id);
      CREATE INDEX FOR (e:Episode) ON (e.period);
      ```
    - Esto **acelera queries** de evolución histórica.

---

### **📌 D6 — Topología etcd**
**✅ APROBADO SIN CAMBIOS.**
- **Parametrización por tamaño** es **realista**.
- **Observer en servidor central** es **buena práctica**.

---

### **📌 D7 — Jerarquía de Vault**
**✅ APROBADO CON ACLARACIÓN.**
- **Procedimiento de recuperación** (D7) es **completo**, pero **falta detallar el *quórum* de recuperación**.
    - **Pregunta:** ¿Quién autoriza la recuperación de un Vault local? ¿Requiere **aprobación manual** de un administrador?
    - **Propuesta:**
        - **Añadir al ADR:**
          > *"La recuperación de Vault local requiere aprobación manual de un administrador autorizado (via Jenkins). El proceso se audita en el servidor central (log firmado con timestamp)."*

---

### **📌 D8 — Flujo de derecho al olvido**
**✅ APROBADO SIN CAMBIOS.**
- **Flujo es claro y alineado con GDPR.**
- **Recomendación:**
    - **Incluir un *timeout* para el borrado en Neo4j:**
        - Ej: Si el comando de borrado no se ejecuta en **7 días**, se revoca automáticamente (para evitar borrados accidentales).

---

---
---
## **❓ Respuesta a OQ-1: Conectividad intermitente**
**Pregunta:** *¿Cómo se comporta el batch ante conectividad intermitente? ¿Se acumula en cola local? ¿Cuánto tiempo? ¿Qué pasa si SQLite ha rotado esos datos?*

**Respuesta del Consejo:**

### **1. Mecanismo de cola local**
- **Solución propuesta:**
    - **Cola persistente en el nodo** (ej: **SQLite + tabla `pending_batches`**).
    - **Estructura de la tabla:**
      ```sql
      CREATE TABLE pending_batches (
          idempotency_key TEXT PRIMARY KEY,  -- Clave única (firma Ed25519)
          batch_blob BLOB NOT NULL,           -- Batch comprimido y firmado
          created_at INTEGER NOT NULL,        -- Timestamp UTC (epoch ns)
          attempts INTEGER DEFAULT 0,        -- Número de reintentos
          last_attempt INTEGER,              -- Último intento (epoch ns)
          status TEXT DEFAULT 'pending'     -- pending|sent|failed
      );
      ```
    - **Lógica de reintento:**
        - El nodo **intenta enviar el batch cada 24h** (configurable).
        - Si falla, **incrementa `attempts`** y actualiza `last_attempt`.
        - **Límite de reintentos:** 7 días (configurable).
        - Si se agota el límite, **el batch se marca como `failed`** y se notifica al operador (log + alerta).

### **2. Retención en SQLite local**
- **Problema:** Si la conectividad se interrumpe **más de 30 días** (horizonte de SQLite), los datos **ya no estarán disponibles** para generar el batch.
- **Solución:**
    - **Extender horizonte de SQLite a 45 días** (para cubrir ventanas de conectividad intermitente).
    - **O usar un buffer en disco** (ej: archivos Parquet temporales) para datos que superen los 30 días.
    - **Añadir al ADR:**
      > *"El nodo edge retendrá datos crudos en SQLite durante **45 días** (en lugar de 30) para cubrir ventanas de conectividad intermitente. Si un batch no puede enviarse en ese plazo, se descarta y se registra una alerta de pérdida de datos (auditable)."*

### **3. Priorización de batches**
- **Batches más antiguos primero** (FIFO) para evitar pérdida de datos históricos.
- **Añadir al ADR:**
  > *"Los batches pendientes se envían en orden cronológico (FIFO), priorizando los más antiguos para minimizar la pérdida de datos históricos."*

### **4. Notificación de fallos**
- **Alertas proactivas:**
    - Si un batch lleva **>3 días pendiente**, el nodo envía una **notificación al servidor central** (via ZeroMQ, si hay conectividad).
    - El servidor central **agrega estas alertas a un dashboard de salud** (ej: Grafana).

---
**Acción:**
Añadir una sección **"Manejo de Conectividad Intermitente"** al ADR con estos puntos.

---

---
---
## **📝 Cambios Requeridos en el ADR (Resumen)**

| Sección | Cambio | Prioridad |
|---------|--------|-----------|
| **D2** | Aclarar manejo de MACs multicast/broadcast (solo unicast como identidad primaria). | Alta |
| **D4b** | Ajustar `dst_port_class` (`ephemeral` → `dynamic`) y `alert_severity` (eliminar `0=none`). | Media |
| **D4b** | Añadir fragmentación de batches (>100 MB) por `event_type` o rango temporal. | Media |
| **D7** | Detallar *quórum* de recuperación de Vault local (aprobación manual). | Media |
| **Nueva** | Sección **"Manejo de Conectividad Intermitente"** (respuesta a OQ-1). | **Alta (bloqueante para despliegue)** |
| **Nueva** | Añadir índices recomendados en Neo4j (`Host.id`, `Episode.period`). | Baja |

---

---
---
## **🎯 Próximos Pasos (Priorizados)**
1. **✅ Resolver OQ-1** (Añadir sección de conectividad intermitente al ADR).
2. **✅ Ajustar schema Parquet** (D4b: `dst_port_class`, `alert_severity`).
3. **[DEBT-PARQUET-SCHEMA-001]** **Validar schema contra CSVs reales en Vagrant** (P0 bloqueante).
4. **Implementar PoC de pseudonimización + Parquet** (validar D2 + D3 + D4).
5. **Diseñar pipeline de ingesta en Neo4j** (validar D5).

---
---
## **📌 Veredicto Final**
**✅ APROBADO CON AJUSTES MENORES.**
La **v3 del ADR-0043** es **técnicamente robusta, legalmente alineada con GDPR, y lista para implementación**. Las modificaciones solicitadas son **menores y enfocadas en claridad y detalles operativos**.

**Para el Consejo:**
¿Estáis de acuerdo con **priorizar la respuesta a OQ-1 (conectividad intermitente)** como bloqueante para el primer despliegue? **Sí**, es crítico para garantizar **resiliencia en entornos reales**.