Evaluación directa. El estado del sistema es sólido; los cambios atacan causas raíz (no síntomas) y el gate reproducible tiene valor real. Respuestas a las preguntas:

---

# Q1 — `std::terminate()` vs excepción en invariant

**Decisión recomendada: mantener `std::terminate()` en producción, degradar en dev.**

Tu intuición es correcta: este invariant es **de seguridad**, no de lógica de negocio. Un arranque sin cifrado efectivo es peor que un crash.

**Política concreta:**

```cpp
if (config_.encryption_enabled && config.component_config_path.empty()) {
#ifdef MLD_DEV_MODE
    std::cerr << "[FATAL][DEV] encryption_enabled=true pero component_config_path vacío\n";
    return false;  // o lanzar excepción controlada
#else
    std::terminate();
#endif
}
```

**Matiz importante:**

* En dev → quieres iterar
* En prod → quieres garantías

👉 No mezclar ambos mundos. Esto encaja con D10 (MLD_DEV_MODE ya existente).

---

# Q2 — build de etcd-client en `provision.sh`

**Respuesta: NO optimizar todavía. Mantener build desde cero.**

Razón:

* Estás en fase de **validación de reproducibilidad**
* Cache introduce:

    * estados ocultos
    * problemas de invalidación
    * bugs difíciles de reproducir

El coste actual (~2 min) es aceptable frente al beneficio:

> certeza de que el sistema se construye limpio siempre

**Cuándo optimizar:**

* cuando tengas CI real
* cuando el build supere ~5–10 min
* cuando haya múltiples developers

**Si quieres dejar preparado el terreno:**

* añade checksum del source (sin usarlo aún)
* documenta el punto de hook

---

# Q3 — plugins en `rag-ingester` (riesgo real)

Aquí sí hay diferencia importante respecto a firewall.

## Problema

`rag-ingester` no es solo pipeline → es **sistema de persistencia semántica (FAISS)**

Si permites que el plugin modifique el `MessageContext`:

👉 estás permitiendo que modifique lo que se indexa

---

## Riesgo crítico

* poisoning del vector store
* corrupción semántica persistente
* ataques de largo plazo (no visibles inmediatamente)

---

## Recomendación clara

**Modo por defecto: READ-ONLY para plugins en rag-ingester**

```text
plugin puede:
  - leer payload
  - decidir aceptar/rechazar (early return)

plugin NO puede:
  - modificar payload antes de FAISS
```

---

## Si necesitas modificación (futuro)

Hazlo explícito:

```text
capability: MODIFY_BEFORE_INGEST
```

Y:

* desactivado por defecto
* auditado
* probablemente firmado con key distinta (D12 futuro)

---

## Flujo recomendado

```text
payload → plugin (read-only)
        → decision (OK / DROP / FLAG)
        → FAISS ingest (solo si OK)
```

👉 Esto protege tu memoria a largo plazo.

---

# Q4 — `rag-security/config` no existe en provisioning

**Decisión recomendada: crear el directorio en provision.sh.**

Razón:

* consistencia del sistema de archivos
* elimina estados implícitos
* simplifica reasoning

---

## Regla general

> provision.sh define el estado base del sistema
> los binarios no deben crear estructura crítica

---

## Implementación

```bash
mkdir -p /vagrant/rag-security/config
chown vagrant:vagrant ...
chmod 755 ...
```

Y luego:

* crear symlink en provisioning (no en runtime)

---

## Por qué importa

Evita:

* condiciones de carrera en arranque
* diferencias entre entornos
* bugs “solo ocurre en limpio”

---

# Observaciones adicionales (importantes)

---

## 1. El invariant que añadiste es clave

Este cambio:

```cpp
if (config_.encryption_enabled && config.component_config_path.empty())
```

Es de alto valor porque:

> convierte un fallo silencioso en fallo explícito

👉 Esto es exactamente lo que diferencia sistemas robustos de sistemas frágiles.

---

## 2. provision.sh ahora es parte del TCB

Antes no lo era. Ahora sí.

Implica:

* debe versionarse con cuidado
* necesita tests (aunque sean bash)
* cualquier cambio puede romper todo

👉 Considera:

```text
TEST-PROVISION-1: vagrant destroy → up → pipeline-start → status == 6/6
```

como gate formal.

---

## 3. ADR-027 (CTX swap) bien justificado

Tu validación empírica es correcta:

* sin swap → MAC failure
* con swap → OK

Y la explicación HKDF es coherente.

👉 Esto ya no es hipótesis, es comportamiento demostrado.

---

# Conclusión del Consejo

## Decisiones

* Q1: `terminate` en prod, degradar en dev → ✅
* Q2: no optimizar build aún → ✅
* Q3: plugins en rag-ingester read-only por defecto → ⚠️ CRÍTICO
* Q4: crear config en provisioning → ✅

---

## Riesgo principal identificado ahora

> Integridad del RAG (FAISS) frente a plugins

Esto es nuevo y relevante. Merece probablemente:

👉 **ADR-028: RAG Ingestion Trust Model**

---

## Insight final

Estás entrando en una fase distinta del proyecto:

* antes: que funcione
* ahora: que sea **imposible que falle silenciosamente**

Los cambios de DAY 108 van exactamente en esa dirección.
