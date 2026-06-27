## DeepSeek — Respuesta al Informe DAY 108

Excelente consolidación. El `vagrant destroy && vagrant up` como gate de calidad es el estándar de oro de la reproducibilidad. Habéis pasado de un pipeline frágil a uno que sobrevive a un destroy limpio en dos ciclos. Eso es un hito.

Ahora, a las preguntas.

---

### Q1 — `std::terminate()` vs excepción en el invariant

**Recomendación:** **Mantener `std::terminate()` en producción, pero en desarrollo (`MLD_DEV_MODE=1`) emitir log `CRITICAL` y `exit(1)` (no `std::terminate`).** El `std::terminate()` dificulta el debugging porque no hay stack trace manejable. Un `exit(1)` con log claro es igual de fail-closed pero más depurable.

**Propuesta concreta:**

```cpp
if (config_.encryption_enabled && config_.component_config_path.empty()) {
    const char* dev_mode = std::getenv("MLD_DEV_MODE");
    if (dev_mode && std::string(dev_mode) == "1") {
        std::cerr << "CRITICAL: encryption_enabled requires component_config_path. Exiting." << std::endl;
        std::exit(1);
    } else {
        std::terminate();  // producción: fail-closed ruidoso
    }
}
```

**Argumento:** En desarrollo, quieres poder lanzar el componente bajo depurador y ver exactamente dónde falla. `std::terminate()` a veces impide eso (depende del depurador). `exit(1)` es igual de final pero más limpio. En producción, `std::terminate()` es aceptable porque el orquestador (systemd) reiniciará el componente.

**Decisión:** Cambiar a `exit(1)` en desarrollo; mantener `std::terminate()` en producción.

---

### Q2 — etcd-client: ¿cache o rebuild siempre?

**Recomendación:** **No cache por ahora. Es premature optimization.**

**Razonamiento:**
- `vagrant destroy` es un evento relativamente infrecuente en el flujo normal de desarrollo. La mayoría de las veces, `vagrant up` se ejecuta una vez por sesión, no varias veces al día.
- 2 minutos de rebuild en un ciclo de 10-15 minutos de provisionamiento total no es un cuello de botella significativo.
- Añadir cache (checksums, tarballs) introduce complejidad y posibles bugs de stale cache que son mucho más difíciles de depurar que la espera de 2 minutos.

**Cuándo reconsiderar:** Si el equipo crece y múltiples desarrolladores ejecutan `vagrant destroy` varias veces al día, se puede añadir un mecanismo de cache condicional (ej. `tools/provision.sh --skip-build`). Pero hoy, no.

**Decisión:** Mantener rebuild siempre. Documentar que es intencional para garantizar que la librería está siempre actualizada con el código fuente.

---

### Q3 — PHASE 2b en rag-ingester: riesgos específicos

**Recomendación:** **El plugin puede modificar `MessageContext` (incluyendo payload), pero NO debe tener acceso a las estructuras internas de FAISS o CSV. El plugin se invoca antes de la ingesta, y puede decidir early-return (rechazar el mensaje) modificando `result_code != 0`.**

**Riesgos específicos de rag-ingester:**
1. **Dual-pipeline FAISS + CSV:** El plugin no debe asumir que el mensaje va solo a uno de ellos. Debe tratarse como un flujo único de eventos.
2. **Payload grande:** Los mensajes cifrados pueden contener eventos de muchos flows. El plugin no debe asumir tamaños máximos.
3. **Integridad de la ingesta:** Si el plugin modifica el payload (ej. añadiendo metadatos), debe asegurarse de que el formato sigue siendo válido para el deserializador de eventos. Lo más seguro es que el plugin sea **solo lectura** (no modifique `payload`) y solo decida si el mensaje se procesa (`result_code=0`) o se descarta (`result_code != 0`).

**Propuesta de contrato para rag-ingester:**
- `direction` siempre `MLD_RX` (solo recibe, no envía).
- `payload` apunta a un buffer con uno o más eventos serializados (protobuf).
- El plugin puede leer el payload pero **no modificarlo**.
- Si `result_code != 0`, el mensaje se descarta silenciosamente (no se ingiere).
- Si se necesita modificar el payload, se requerirá un diseño específico (copiar a un nuevo buffer, etc.).

**Gate TEST-INTEG-4b:** Debe incluir un plugin de prueba que verifique que el mensaje no es modificable (o que si se modifica, el componente lo detecte y falle, como en D8 de ADR-023).

---

### Q4 — rag-security/config no existe en provision.sh

**Recomendación:** **Crear el directorio vacío en `provision.sh` y también el symlink, aunque el binario lo cree después.**

**Razonamiento:**
- El symlink JSON es necesario para que el componente encuentre su configuración. Si el directorio no existe, el symlink no se puede crear (o se crea roto).
- Crear el directorio vacío es inofensivo (el binario lo reutilizará).
- Esto unifica el comportamiento con el resto de componentes: todos los directorios de configuración existen después de `provision.sh`, incluso si el binario nunca se ha ejecutado.

**Acción:** En `provision.sh`, añadir después de `create_component_dir` para rag-security:

```bash
create_component_dir "rag-security"
# Crear symlink incluso si el directorio está vacío
ln -sf "/vagrant/rag-security/config/rag_security_config.json" \
      "/etc/ml-defender/rag-security/config.json"
```

**Nota:** El directorio `/vagrant/rag-security/config/` debe existir en el repositorio (o crearse en provision.sh). Si el binario crea el directorio al arrancar, el symlink puede apuntar a un destino inexistente temporalmente. Para evitarlo, asegura que el directorio de configuración del repositorio existe (puede estar vacío, pero debe existir).

---

### Resumen ejecutivo

| Q | Decisión | Acción |
|---|----------|--------|
| Q1 | `std::terminate()` en prod; `exit(1)` en `MLD_DEV_MODE` | Modificar el invariant con comprobación de variable de entorno |
| Q2 | No cache. Rebuild siempre. | Dejar como está. Documentar intencionalidad. |
| Q3 | Plugin en rag-ingester: solo lectura, puede descartar mensaje, no modificar payload | Especificar contrato en ADR-023 para rag-ingester. TEST-INTEG-4b con plugin de solo lectura. |
| Q4 | Crear directorio vacío y symlink en provision.sh | Añadir en `provision.sh` la creación del directorio y symlink para rag-security. |

---

### Comentario adicional

El gate `vagrant destroy && vagrant up` es el mejor test de integración que podéis tener. Habéis pasado de un pipeline que solo funcionaba en vuestra sesión manual a uno reproducible. Eso es un salto cualitativo. Enhorabuena.

El siguiente paso lógico es PHASE 2b en rag-ingester, siguiendo el patrón ya validado. Pero antes, aplicad los cambios de Q4 para que el symlink esté presente desde el primer momento.

— DeepSeek, miembro del Consejo de Sabios