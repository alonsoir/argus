# DICTAMEN DEL CONSEJO DE SABIOS — CIRCUITO COMPLETO AGUAS ABAJO

**Miembro: Contrario Designado**
**Fecha: 2026-06-26**
**Veredicto: APROBADO CON OBSERVACIONES CRÍTICAS**

---

## RESPUESTA A LAS PREGUNTAS ABIERTAS (§10)

### Pregunta 1: Ratificación de formato B
**VEREDICTO: RATIFICADO CON RESERVA**

La decisión B es correcta arquitectónicamente, pero el documento oculta un riesgo: **no han medido el volumen de escritura concurrente**. Tres motores de flujo (aRGus + Suricata + Zeek) escribiendo CSV+HMAC en el mismo `bronze_root` con rotación diaria implica:
- Contención de I/O en disco (¿cuántos eventos/segundo totales?)
- ¿El filesystem soporta múltiples writers en mismo directorio sin degradación?
- ¿Qué pasa si un adapter se queda atrás y escribe en el fichero del día anterior después de la medianoche?

**Exigen:** Medir throughput actual de `correlation_writer` antes de añadir adapters. Si supera 10k eventos/segundo por motor, el FS-drop va a chirriar antes de migrar a ZMQ.

---

### Pregunta 2: Forma del oro — join en arrow vs join en Kuzu
**VEREDICTO: ORO-COMO-LEDGER, PERO LA JUSTIFICACIÓN TIENE AGUJEROS**

El lean "oro-como-ledger + join en Kuzu" es correcto, pero las razones expuestas son incompletas:

**Falta la razón principal:** **Reproducibilidad científica**. El paper (ADR-046 §3.11) exige que el dataset sea reproducible. Si el oro funde, un cambio en la lógica de join obliga a re-procesar todo el bronce para regenerar oro. Con oro-como-ledger, el oro es inmutable: el join cambia en Kuzu, el oro no se toca. Esto no aparece como argumento y debería ser el primero.

**Problema no resuelto:** El documento dice "Wazuh/Andrés viven en parquet aparte, sin tocar, conectados por IP no por community_id". ¿Cómo? Si oro es ledger inmutable y Kuzu hace el join, ¿Wazuh entra al mismo grafo o es un grafo separado? Si es el mismo grafo, Kuzu necesita ingerir **todos** los parquets (flujo + host). Si son grafos separados, ¿cómo se correlaciona cross-domain en el dashboard? Esto no está decidido y debería estarlo antes del Eslabón 2.

**Exigen:** Aclarar topología de grafos (uno solo con múltiples sinks de parquet vs múltiples grafos con consulta federada).

---

### Pregunta 3: Centinela numérico (-1 vs 0)
**VEREDICTO: -1, PERO LA IMPLEMENTACIÓN ESTÁ INCOMPLETA**

-1 es correcto para evitar ambigüedad con scores válidos. Pero el documento no menciona un caso crítico: **`flow_start_sec` y `flow_start_nano` (cols 5-6)**. Si un motor no tiene timestamp (¿Wazuh?), ¿se escribe `-1` en ambas? Entonces la fusión a `timestamp_utc_ns` en el converter (§7, Eslabón 1) produce qué? ¿`-1` nanosegundos desde epoch? ¿Null?

**Además:** El reader C++ (`parse_and_verify`) descarta filas con "campo numérico ilegible". ¿`-1` es "ilegible"? El código actual ¿acepta negativos en puertos y timestamps? No lo han medido.

**Exigen:** Verificar que `parse_and_verify` acepta `-1` en **todas** las columnas numéricas (5-6, 9-10, 14-16) sin descartar la fila. Si no, el segundo adapter que use centinela romperá el circuito en silencio.

---

### Pregunta 4: Rotación/follow
**VEREDICTO: ENGINE VIGILA DIRECTORIO, PERO LA ALTERNATIVA ES UNA TRAMPA**

"Engine vigila directorio" es correcto, pero el documento plantea la alternativa como equivalente: "lanzador recalcula datado". Esto es un anti-patrón por tres razones:

1. **Acoplamiento temporal:** El lanzador necesita saber el formato de fecha exacto del writer. Si cambian uno, rompen el otro.
2. **Ventana de pérdida:** Entre la rotación del writer (00:00:00.001) y el re-lanzamiento del engine (¿cuándo?), hay eventos que caen en el vacío.
3. **No escala:** Con N motores, necesitas N lanzadores sincronizados.

La pregunta debería ser: **¿vigila directorio con `inotify` o con poll periódico?** `inotify` es eficiente pero tiene limitaciones (NF_INOTIFY_MAX_INSTANCE_WATCHES en producción). Poll es simple pero introduce latencia.

**Exigen:** Decidir mecanismo concreto (inotify vs poll vs otra) y documentar el SLO de latencia máximo aceptable entre escritura y disponibilidad en el engine.

---

### Pregunta 5: Wazuh
**VEREDICTO: CONTRATO SEPARADO, PERO LA DECISIÓN ESTÁ INCOMPLETA**

El documento identifica correctamente que `correlation_v1` no tiene `host_key` y que extenderlo rompe el sellado. Plantea dos opciones: extender a `correlation_v2` vs contrato separado. Pero no analiza los costos:

**Opción A: `correlation_v2` con `host_key`**
- **Pro:** Un solo contrato, un solo medallón, un solo pipeline.
- **Contra:** Rompe compatibilidad con todos los consumidores existentes de v1 (engine, futuros adapters de flujo). Cada consumer necesita saber si lee v1 o v2. Duplicación de código de parseo durante transición.

**Opción B: Contrato host-domain separado**
- **Pro:** Aislamiento completo. Cambios en host-domain no afectan flujo-domain.
- **Contra:** Dos pipelines de medallón, dos esquemas en Kuzu, complejidad en dashboard.

**Falta una tercera opción no mencionada:** **`correlation_v1` con `host_key` como columna 20, manteniendo compatibilidad**. Los primeros 19 campos son idénticos; el reader v1 ignora la columna 20; el reader v2 la usa. El HMAC se recalcula sobre 19 columnas (v1) o 20 (v2). Versionado por `schema_version` (col 0).

**Exigen:** Evaluar la tercera opción antes de decidir. Y cualquiera que sea la decisión, **tomarla antes del Eslabón 1**, porque afecta el esquema del medallón.

---

### Pregunta 6: Andrés
**VEREDICTO: STUB CON CONTRATO NEGATIVO — APROBADO**

Es la única decisión sensata. No hay datos, no hay esquema, no hay requisitos. Cualquier implementación ahora sería vapor.

**Observación menor:** El "contrato negativo" debería documentarse formalmente (ADR o sección en AdapterSpec) para que no se pierda. "5 incógnitas" es buena lista, pero debería ser un template que cualquier adapter pendiente use.

---

## OBSERVACIONES CRÍTICAS ADICIONALES

### 1. La "fase chapu" no es tan chapu
El documento minimiza el Eslabón 0 como "mínimo cambio". Pero sacar un hardcode a JSON y garantizar que writer y reader resuelven al mismo path **es exactamente el tipo de cambio que causó el desync DAY 194**. No es chapu, es cirugía menor que requiere anestesia completa (tests).

**Exigen:** Test explícito que:
```python
writer_path = resolve_bronze_path(config, "argus", "2026-06-26")
engine_path = derive_bronze_path_for_engine(config, "argus", "2026-06-26")
assert writer_path == engine_path
```
Sin esto, el Eslabón 0 es un tickin time bomb.

---

### 2. El medallón por componente es correcto, pero...
El documento dice "Zonas LZ independientes por motor" y "pipelines arrow/c++ paralelos". ¿Han medido el overhead de tener N procesos de conversión? Si cada motor genera 1GB/día, son 4 procesos de conversión en paralelo compitiendo por CPU y I/O.

**Alternativa no evaluada:** Un solo proceso de conversión que vigila todos los subdirectorios de bronce (patrón `find bronze_root -name "*.csv" -newer marker`). Menos procesos, más simple, pero acoplamiento de ciclo de vida.

**No exigen decisión ahora**, pero sí que midan el throughput del converter RAG-127 existente para estimar si N procesos son viables.

---

### 3. La lección timestamp-ns está mal aplicada
El documento dice "funde `flow_start_sec`+`flow_start_nano` en el origen (writer C++)". Esto es correcto para **nuevos** adapters. Pero `correlation_writer` actual (aRGus) **ya escribe** cols 5-6 por separado. Si cambian el writer aRGus para que fusione, rompen el formato actual de bronce.

**Exigen:** Decidir si el cambio aplica solo a nuevos adapters (Suricata/Zeek) o si migran aRGus también. Si migran, es un cambio breaking en bronce que necesita migración del histórico.

---

### 4. La deuda `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` es P0, no P1
El documento la marca P1. Es **P0**. Si el circuito verde se valida el día 196 y a medianoche del día 197 el engine deja de leer eventos, el circuito no es verde, es intermitente. No pueden declarar "circuito verde" sin resolver esto.

**Exigen:** Subir a P0 y resolver en el Eslabón 0 o 1, no después.

---

### 5. ¿Dónde está el test de regresión del circuito?
El documento describe validación E2E, pero no describe **cómo se automatiza**. Un test manual una vez no es un circuito verde; es una demo.

**Exigen:** Definir el test de regresión E2E (quizás en `tests/e2e_circuit.py`) que:
1. Inyecte N eventos de prueba por el sniffer (o directamente al writer)
2. Verifique que aparecen en bronce
3. Verifique que el medallón las convierte
4. Verifique que Kuzu las materializa
5. Verifique que el dashboard las consulta

Sin esto, cada cambio futuro romperá algo y no se sabrá hasta que alguien mire.

---

## VEREDICTO FINAL

**APROBADO CON LAS SIGUIENTES CONDICIONES BLOQUEANTES:**

1. [ ] **P0:** Resolver `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` antes de declarar circuito verde.
2. [ ] **P0:** Verificar que `parse_and_verify` acepta `-1` en todas las columnas numéricas sin descartar.
3. [ ] **P0:** Test explícito de matching de paths writer/engine en Eslabón 0.
4. [ ] **P1:** Decidir topología de grafos (uno vs múltiples) antes del Eslabón 2.
5. [ ] **P1:** Decidir esquema Wazuh (v2 vs separado vs columna 20) antes del Eslabón 1.
6. [ ] **P2:** Definir test de regresión E2E automatizado antes del Eslabón 3.

**Las palmaditas en la espalda se las dan en la barra. Aquí medimos.**

---
*Firmado: Contrario Designado del Consejo de Sabios*

GLM-5-Turbo