# PROMPT DE CONTINUIDAD — DAY 206 (continúa DAY 205)
# Instrucciones generales para Claude:

1. Piensa antes de codificar
   Expón tus suposiciones. Pregunta cuando no estés seguro. Nunca adivines.

2. Simplicidad primero
   Escribe el código mínimo que resuelva el problema.
   Sin abstracciones que nadie pidió.

3. Cambios quirúrgicos
   No toques código no relacionado con la solicitud.
   Cada línea cambiada debe rastrearse hasta lo que se pidió.

4. Ejecución orientada a metas
   Convierte instrucciones vagas en criterios de éxito verificables
   antes de escribir una sola línea.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio**.
- **Consejo de Sabios** (9 modelos: Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh -c` para comandos del VM (multi-VM: nombrar máquina, p.ej. `vagrant ssh defender -c`) · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.
- `.PHONY` en Makefile: lista separada por ESPACIOS, nunca comas (lección DAY 205).

## Estado al cierre de DAY 205 — Eslabón 1 (Flujo A): diseño RATIFICADO, converter BLOQUEADO

**DAY 205 cerró la acción 1 (diseño) completa y avanzó parcialmente la acción 2
(converter mínimo), topando con un bloqueo real no trivial: la clave HMAC de
producción es efímera en memoria, sin persistencia.**

### 1. Diseño Eslabón 1 (Flujo A) — RATIFICADO 9/9 por el Consejo de Sabios

- **Documento:** `docs/design/eslabon-1-flujo-a-avro-parquet/eslabon-1-flujo-a-avro-parquet.md`
- **Decisión de proceso:** NO es ADR numerado — documento de apoyo referenciado desde
  ADR-058 (8/9 del Consejo; Grok fue el único disidente, proponía ADR-059). Evita
  colisión de numeración (lección DAY 175/199).
- **Lenguaje:** C++20 puro. Cero Python en el camino crítico — cierra
  `DEBT-CIRCUIT-PARSER-CROSSLANG-001` **por diseño** (un solo runtime, sin frontera
  de lenguaje que cruzar en el parseo texto→double).
- **Librerías:** `avro-c` 1.11.1 (I/O AVRO, API C wrapeada desde C++20, mismo patrón
  que OpenSSL en `CorrelationWriter`) + Arrow/Parquet C++ **pinneados a `24.0.0-1`**
  (regla de proceso adoptada del Consejo: se pinnea la primera versión que supera la
  batería de validación reproducible; toda actualización posterior exige revalidación
  completa). Separación de responsabilidades: `avro-c` nunca toca Arrow, Arrow nunca
  toca AVRO — dos librerías, una responsabilidad cada una.
- **Esquema `correlation_gold_v1`:** 24 campos — bloque bronce (cols 0-18, copiado
  verbatim, nunca recalculado) + bloque oro (cols 19-23: `flow_start_window`,
  `seq_in_window`, `flow_uid` materializados — clase D; `ingested_at`,
  `temporal_anomaly` — clase E, pendientes de decisión de jerarquía WAL).
- **Partición:** solo por fecha (`date=YYYY-MM-DD/`), sin partición por `node_id`
  todavía (ADR-058 §8, evitar gold-plating especulativo).
- **Puertos en AVRO (cols 9-10):** `int` signed 32-bit + campo `doc` documentando la
  asimetría con `uint32_t` del proto. Unanimidad 9/9, sin deuda nueva.

### 2. Infraestructura cableada — Vagrantfile + Makefile (rama `day205/...`)

- **`Vagrantfile`:** bloque nuevo dentro de `all-dependencies` (`DEPENDENCIES_EOF`),
  justo tras Kuzu. Instala `libavro-dev` + añade repo oficial Apache Arrow
  (`apache-arrow-apt-source-latest-bookworm.deb`) + `libarrow-dev=24.0.0-1
  libparquet-dev=24.0.0-1` pinneados con `apt-mark hold`. Idempotente.
- **`Makefile`:** targets `eslabon1-smoke-build` / `eslabon1-smoke-test` (línea
  ~3027). **Bug corregido DAY 205:** `.PHONY:a,b` (coma) → `.PHONY: a b` (espacios) —
  la coma es inválida en GNU Make y hacía que el phony-target no emparejara los
  nombres reales.
- **PENDIENTE DE VERIFICAR MAÑANA:** todo esto se cableó y se probó en el estado
  ACTUAL de `defender` (con `libavro-dev`/Arrow ya instalados a mano en sesiones de
  exploración previas). **NUNCA se ha probado un `vagrant destroy -f && vagrant up`
  completo desde cero con este Vagrantfile** — es la única prueba real de que el
  provisioning reproduce el entorno. Explícitamente diferida a hoy por Alonso
  ("cuando tengamos que hacer el merge to main con emecas+++").

### 3. Smoke test — VERIFICADO 12/12, dos veces

- **Ruta:** `docs/design/eslabon-1-flujo-a-avro-parquet/smoke/eslabon1_smoke.cpp` +
  `correlation_smoke.avsc`.
- Verificado en sandbox (Ubuntu 24.04) y en `defender` (Debian 12 real) vía
  `make eslabon1-smoke-test`. 12/12 checks verdes en ambos, `-Werror -Wall -Wextra`
  limpio.
- **Hallazgo real capturado:** `parquet::arrow::OpenFile` y `FileReader::ReadTable`
  cambiaron de API (output-parameter → `arrow::Result<T>`) en Arrow 24.0.0. Cualquier
  código futuro basado en ejemplos de versiones <24 no habría compilado — ya
  corregido en el smoke test con la API `Result`-based.

### 4. Converter mínimo — ESCRITO, **NO COMPILADO, NO VERIFICADO**

- **Ruta:** `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/bronze_to_gold_converter.cpp`
   + `README.md` de estado (creado DAY 205, léelo antes de tocar el `.cpp`).
- Escrito reusando código real del repo (`parse_and_verify`, `CorrelationRecord`,
  `compute_flow_uid`/`window_micros` de `flow_uid.hpp`) contra los headers exactos
  verificados — NO adivinado.
- **Hallazgo real DAY 205:** `CorrelationRecord` NO almacena el HMAC (col 18) —
  `parse_and_verify` lo valida y lo descarta. El converter lo extrae por su cuenta
  con la misma técnica que usa `correlation_reader.cpp` internamente
  (`line.rfind(',')`) — necesario para `DEBT-GOLD-INTEGRITY-HMAC-001`.

### 5. BLOQUEO REAL — SecretsManager es 100% in-memory, sin persistencia

**Este es el hallazgo más importante de DAY 205, con implicaciones más allá del
converter.** Medido (no supuesto) contra `etcd-server/src/secrets_manager.cpp`:

- `SecretsManager::generate_hmac_key()` genera con `openssl rand` puro
  (no-determinista) y llama `store_key(key)` → `keys_storage_` (mapa en memoria,
  protegido por `storage_mutex_`). **Cero persistencia a disco.**
- Confirmado por ausencia: `sudo find / -iname "*hmac*"` en toda la VM no devuelve
  ningún fichero de secretos fuera de headers de librerías del sistema (OpenSSL,
  libsodium, Crypto++, Python `hmac.py`).
- **Consecuencia:** las claves que firmaron `logs/correlation/argus/2026-07-02-*.csv`
  (y todos los segmentos de bronce existentes) murieron con el proceso `etcd-server`
  de aquella sesión. Son **irrecuperables**. No es un bug del converter — es
  comportamiento real y hasta hoy no documentado del `SecretsManager` actual.
- **Candidato de deuda nueva (sin registrar aún — decisión de Alonso):**
  `DEBT-SECRETS-MANAGER-PERSISTENCE-001`. Un reinicio del proceso `etcd-server`
  invalida silenciosamente TODAS las filas de bronce ya firmadas, sin relación con
  `grace_period_seconds`/`min_rotation_interval_seconds` de ADR-004 (esa lógica
  protege rotación *voluntaria*, no muerte de proceso). Severidad a discutir —
  probablemente P1: toca la inmutabilidad del ledger "Via Appia" si llega a
  producción sin resolver. **NO decidido si es bloqueante de Eslabón 1** — el
  converter puede probarse con una fila fresca sin resolver la deuda de fondo hoy.

## Rama

`day205/eslabon1-avro-parquet-design`, push hecho. **NO mergeada a main todavía.**
`vagrant-ssh-config` excluido del repo vía `.gitignore` (contiene rutas de claves
privadas SSH locales — nunca debe trackearse).

## Acciones DAY 206 (en orden)

1. **Desbloquear el converter — generar una fila de bronce fresca con clave HMAC viva.**
   - Levantar pipeline mínimo: `etcd-server` + `ml-detector` (no todo EMECAS++
     necesariamente — evaluar si basta con estos dos para que se dispare al menos
     una fila de correlación, o si hace falta también `sniffer` + tráfico real/sintético).
   - `main.cpp:442` solo loguea la LONGITUD de la clave
     (`log->info("✅ [csv] HMAC key retrieved ({} chars)", key.size())`), no el valor
     — hay que decidir cómo capturarla: ¿log temporal adicional? ¿leer
     `keys_storage_` con un endpoint de depuración si `etcd-server` expone alguno?
     ¿instrumentar `main.cpp` de ml-detector temporalmente y revertir después?
     Decidir con el Consejo si aporta valor, o resolverlo Alonso solo por ser
     puramente mecánico.
   - Exportar `ARGUS_BRONZE_HMAC_KEY_HEX` con la clave capturada.
2. **Compilar y ejecutar `bronze_to_gold_converter.cpp`** contra la fila fresca (NO
   contra `2026-07-02-*.csv`, ya no verificable). Comando de compilación en el
   `README.md` de `converter-prototype/` — sin `-Werror` en el primer intento
   (ver qué warnings aparecen al integrar con código real del repo antes de exigir
   cero warnings).
3. **Si compila y corre limpio:** limpiar warnings, activar `-Werror`, decidir si
   `bronze_to_gold_converter.cpp` se queda como prototipo de diseño o "gradúa" a
   código de producción real (p.ej. `correlation-engine/tools/` o un componente
   nuevo) — decisión explícita, no implícita.
4. **Prueba de reproducibilidad total del Vagrantfile:** `vagrant destroy -f &&
   vagrant up defender` desde cero, confirmar que `make eslabon1-smoke-test` sigue
   dando 12/12 SIN ningún `apt-get install` manual previo. Esta es la única
   verificación real de que el provisioning cableado DAY 205 funciona — todo lo
   probado hasta ahora fue sobre un `defender` con dependencias ya instaladas a mano.
5. **Registrar (o descartar con justificación) `DEBT-SECRETS-MANAGER-PERSISTENCE-001`**
   en `docs/BACKLOG.md` — decisión de Alonso sobre severidad y si bloquea producción.
6. **Merge de `day205/eslabon1-avro-parquet-design` a `main`** vía EMECAS++, una vez
   3-4 estén verdes.
7. **Tras el merge, retomar la acción 2 original de DAY 205** (converter completo,
   con test de equivalencia parcial contra el predicado §3.1) si queda margen de
   sesión — o abrir DAY 207 limpio para ello.

## Punteros

- `docs/design/eslabon-1-flujo-a-avro-parquet/eslabon-1-flujo-a-avro-parquet.md` —
  diseño ratificado, fuente de verdad del esquema.
- `docs/design/eslabon-1-flujo-a-avro-parquet/smoke/` — verificado, no tocar salvo
  para revalidar en cambio de versión de Arrow.
- `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/` — NO verificado,
  bloqueado por HMAC key. Leer `README.md` antes de continuar.
- `etcd-server/src/secrets_manager.cpp` — `SecretsManager`, in-memory puro, sin
  persistencia (hallazgo DAY 205).
- `ml-detector/src/main.cpp:432-479` — construcción de `hmac_key_hex` vía
  `etcd_client->get_hmac_key()`, punto de instrumentación si se decide capturar la
  clave por log.
- `docs/council/DISEÑO — Eslabón 1, Flujo A (bronce → AVRO → Parquet oro)*.md` —
  transcripción completa de la ratificación 9/9.

*Via Appia Quality — Un escudo que aprende de su propia sombra.*