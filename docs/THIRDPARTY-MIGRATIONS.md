# aRGus NDR — Third-Party API Migrations

Registro de APIs de terceros deprecated actualmente suprimidas en CMake.
Cada supresión requiere entrada en este fichero con plan de migración y criterio de cierre.

**Política (Consejo DAY 140, 8/8):**
- Código de terceros con API deprecated → suprimir por fichero en CMake + entrada aquí
- Criterio de cierre: API upstream estable O CVE (→ upgrade inmediato)
- Nunca suprimir warnings de código propio

---

## llama.cpp — `llama_new_context_with_model` → `llama_init_from_model`

**Estado:** SUPRIMIDO temporalmente
**Fichero afectado:** `rag/src/llama_integration_real.cpp:29`
**Supresión CMake:** `rag/CMakeLists.txt` — `-Wno-deprecated-declarations`
**DEBT asociada:** `docs/adr/DEBT-LLAMA-API-UPGRADE-001.md`
**Fecha de registro:** 2026-05-03 (DAY 140)

### Descripción

llama.cpp deprecó `llama_new_context_with_model` en favor de `llama_init_from_model`.
El cambio puede implicar diferencias semánticas en lifecycle de contexto y gestión
de memoria. No se actualiza antes de FEDER para evitar riesgo de regresión en un
componente sin test robusto.

### Criterio de cierre

- llama.cpp publica release estable con `llama_init_from_model` sin breaking changes, O
- Aparece CVE en la API deprecated (→ upgrade inmediato, sin esperar FEDER)

### Plan de migración

1. Verificar changelog de llama.cpp cuando llegue a release estable
2. Actualizar llamada en `llama_integration_real.cpp`
3. Eliminar supresión en `rag/CMakeLists.txt`
4. Verificar `make all 2>&1 | grep -c warning:` = 0 sin supresión
5. Cerrar `DEBT-LLAMA-API-UPGRADE-001`

---

## protobuf — `network_security.pb.cc`

**Estado:** SUPRIMIDO permanente (código generado)
**Fichero afectado:** `sniffer/build-debug/proto/network_security.pb.cc`
**Supresión CMake:** múltiples CMakeLists — `-Wno-sign-conversion`
**Fecha de registro:** DAY 139

### Descripción

Código generado automáticamente por `protoc`. Los warnings de conversión
signed/unsigned son inherentes al código generado y no son mantenibles.
La supresión es permanente para código generado — no es deuda técnica.

### Criterio de revisión

Si se actualiza `protoc` a una nueva versión mayor, verificar que las supresiones
siguen siendo correctas ejecutando `make all 2>&1 | grep -c warning:` tras regenerar.

---

## XGBoost trees — `internal_detector.cpp`

**Estado:** SUPRIMIDO permanente (código generado)
**Fichero afectado:** `ml-detector/src/ddos/traffic/internal_detector.cpp`
**Supresión CMake:** `ml-detector/CMakeLists.txt` — `-Wno-sign-conversion`
**Fecha de registro:** DAY 139

### Descripción

Código generado por el exportador C++ de XGBoost. Contiene cientos de miles
de líneas de comparaciones de árboles de decisión con conversiones implícitas.
No es mantenible — supresión permanente para código generado.

### Criterio de revisión

Si se regenera el modelo y se exporta con una nueva versión de XGBoost,
verificar `make all 2>&1 | grep -c warning:` tras la regeneración.

---

## FAISS + libtool — build warnings de ml-defender

**Estado:** DOCUMENTADO (no suprimido en CMake — build externo)
**Ficheros afectados:**
- `/tmp/faiss/faiss/utils/hamming_distance/generic-inl.h:312` — `-Wswitch-unreachable` (×7)
- libtool: `'-version-info/-version-number' is ignored for convenience libraries` (×8)
  **Supresión CMake:** no aplicable (FAISS se compila como proyecto externo en `/tmp/`)
  **Fecha de registro:** 2026-05-04 (DAY 141)

### Descripción

Warnings de build de FAISS y libtool que aparecen durante la compilación de
ml-defender. Son 100% third-party — fuera del scope de `-Werror`. No contaminan
nuestro código propio. Aparecen prefijados con `defender:` en el output de EMECAS.

### Workaround EMECAS

Filtrar del grep de verificación:
```bash
grep 'warning:' output.md | grep -v 'defender:'
```

### Criterio de revisión

Si se actualiza FAISS a una nueva versión, verificar si los warnings desaparecen.
En ese caso, eliminar esta entrada.

### Seguimiento

`docs/adr/BACKLOG-BUILD-WARNING-CLASSIFIER-001.md` — clasificación automática
de warnings de build via RAG pipeline (post-FEDER).

---

*Última actualización: DAY 141 — 4 Mayo 2026*