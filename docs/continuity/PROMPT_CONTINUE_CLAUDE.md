# PROMPT DE CONTINUIDAD — DAY 207 (continúa DAY 205-206)
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
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection — push directo rechazado, confirmado DAY 206).
- **Consejo de Sabios** (9 modelos: Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh defender -c` para comandos del VM (defender = VM de desarrollo principal, lleva todo el peso; hay más VMs en el mismo Vagrantfile) · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.
- `.PHONY` en Makefile: lista separada por ESPACIOS, nunca comas (lección DAY 205).
- **Lección nueva DAY 206:** al comitear y hacer push a una rama de trabajo, verificar SIEMPRE con `git log --oneline -3 <rama>` y `git log --oneline -3 origin/<rama>` que el commit realmente llegó antes de abrir el PR — un desfase silencioso entre "commit hecho" y "push hecho" dejó fuera del PR #117 el registro de dos deudas en BACKLOG.md, que hubo que corregir con un PR #118 separado.

## Estado al cierre de DAY 206 — Eslabón 1 (Flujo A): converter desbloqueado, mergeado a main

### Resumen de lo cerrado hoy
1. **Converter desbloqueado.** El bloqueo de DAY 205 (clave HMAC efímera en memoria)
   se resolvió sin tocar código: `SecretsManager` ya expone un endpoint HTTP de
   depuración (`GET http://0.0.0.0:2379/secrets/<componente>`) que devuelve la
   clave activa en claro. Capturada la clave de `ml-detector`
   (`e95b13b86323d57c10a2f574470b9ab2645cc39eff37f76af5c0808b5f4682cc`, 32 bytes,
   generada `2026-07-04T03:24:36Z`), exportada como `ARGUS_BRONZE_HMAC_KEY_HEX`.
2. **`bronze_to_gold_converter.cpp` compilado y ejecutado con éxito** contra fila
   fresca (`logs/correlation/argus/2026-07-04-032653.csv`, generada por
   `make pipeline-start` completo, NO contra el CSV del 2 de julio, ya irrecuperable).
   24/24 filas convertidas, 0 descartadas. Compila limpio con `-Werror -Wall -Wextra`
   sin ningún warning — mejor de lo esperado para un primer intento.
   Libs de link: `avro-c arrow parquet` (vía pkg-config) + `-lsodium -lcrypto`
   (esta última no estaba en el smoke test, hace falta para el HMAC real de
   `correlation_reader.cpp`).
3. **Aviso pendiente sin resolver (no bloqueante):** el converter imprime un
   recordatorio de "verificar bit a bit el flow_uid recomputado contra el ya
   materializado en Kuzu" — pero **Kuzu no está corriendo ni tiene base de datos
   creada en este pipeline mínimo** (`ps aux | grep kuzu` vacío, `find -iname
   "*.kuzu"` vacío). No es un fallo del converter: el circuito bronce→Kuzu
   (`test_bronze_to_kuzu_circuit.cpp`, verificado en EMECAS+++) es un componente
   distinto que no se activó en esta sesión. **Conectar la salida de este
   converter con Kuzu por primera vez es una pieza de diseño nueva, deliberadamente
   diferida — no forma parte del alcance ya ratificado del converter** (ver cabecera
   del propio `.cpp`: "FUERA DE ALCANCE HOY"). Decisión de Alonso DAY 206: no
   improvisarlo a mitad de sesión, evaluar diseño mínimo en sesión propia.
4. **Prueba de reproducibilidad total del Vagrantfile — PASADA.**
   `vagrant destroy -f && vagrant up defender` desde cero (incluye reinstalación de
   Kuzu v0.11.3, avro-c, Arrow/Parquet 24.0.0-1 pinneados, snappy — SHA256 verificado
   en cada paso). `make eslabon1-smoke-test` → 12/12 verdes sin ningún
   `apt-get install` manual previo. Evidencia completa guardada en
   `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/evidence/
   day206-vagrant-destroy-up-defender.md`.
5. **Mejora de ergonomía (no estaba en el plan, salió de una observación de Alonso):**
   `eslabon1-smoke-build` y `eslabon1-smoke-test` ahora son invocables directamente
   desde el HOST (antes requerían estar ya dentro de `vagrant ssh defender`). Los
   targets ahora envuelven `vagrant ssh defender -c "..."` internamente, mismo
   patrón que `etcd-server-start` y el resto de targets del pipeline. Cuidado
   real de escapado verificado: `\$$(pkg-config ...)` (doble escape: uno para
   Make, uno para que la shell remota expanda pkg-config, no la local).
6. **Dos deudas P1 registradas en `docs/BACKLOG.md`** (texto completo ya en el
   fichero, no repetir aquí):
    - `DEBT-SECRETS-MANAGER-PERSISTENCE-001` — claves HMAC deben persistir en Vault
      (`ICryptoProvider`/`VaultProvider`, ADR-045), no en memoria pura.
    - `DEBT-PROD-ANTI-PTRACE-HARDENING-001` — mitigación en 5 capas (blocklist LotL,
      `CapabilityBoundingSet=~CAP_SYS_PTRACE`, AppArmor `deny ptrace`, Yama LSM
      `ptrace_scope=2/3`, regla Falco) contra lectura de `/proc/<pid>/mem`.
7. **EMECAS+++ verde** — circuito bronce→Kuzu verificado (dentro de test-all).
8. **Mergeado a `main` en dos PRs:**
    - PR #117 — código completo (diseño, converter, Vagrantfile, Makefile, smoke test).
    - PR #118 — corrección: registro de las dos deudas en BACKLOG.md, que por un
      desfase de push/commit no llegó a tiempo al PR #117.

## Rama
Todo el trabajo de DAY 205-206 ya vive en `main` (commit `7da6994f` al cierre de
DAY 206). No hay rama de trabajo abierta pendiente. `day205/eslabon1-avro-parquet-design`
y `day206/backlog-debts-registro` pueden borrarse (ya mergeadas, sin cambios sueltos).

## Acciones DAY 207 (en orden, según lo diferido del plan original de DAY 206)

1. **Retomar la acción 2 completa del converter:** test de equivalencia parcial
   contra el predicado §3.1 (ADR-058) — comparar Camino 0 vs Flujo A+B para
   verificar que producen el mismo conjunto de columnas D (cols 0-21) para las
   mismas filas de entrada. Esto es distinto e independiente del punto de Kuzu
   (ver abajo).
2. **Decidir el diseño mínimo de conexión bronce→Kuzu para ESTE converter
   específico** (deliberadamente diferido de DAY 206, no improvisado a mitad de
   sesión). Preguntas a resolver antes de escribir código:
    - ¿El converter mismo escribe a Kuzu (amplía su responsabilidad, cambiaría
      la cabecera del `.cpp` que hoy dice "fuera de alcance"), o se usa
      `kuzu_graph_sink.hpp` (ya existente) como componente separado que lee el
      Parquet/AVRO ya generado?
    - ¿Hace falta pasar esta decisión por el Consejo de Sabios (probablemente sí,
      si implica una decisión de arquitectura sobre cómo se conecta un componente
      nuevo con el grafo existente — no es puramente mecánico como capturar una
      clave HMAC)?
    - Antes de decidir nada: levantar Kuzu en el pipeline mínimo y confirmar que
      `test_bronze_to_kuzu_circuit.cpp` (el que ya pasa en EMECAS+++) usa un
      converter distinto o el mismo camino — medir, no asumir.
3. **Decisión pendiente sobre el destino de `bronze_to_gold_converter.cpp`:**
   ¿se queda como prototipo de diseño en `docs/design/.../converter-prototype/`,
   o "gradúa" a código de producción real (p.ej. `correlation-engine/tools/` o
   un componente nuevo)? Decisión explícita, no implícita — pendiente desde el
   plan original de DAY 206, acción 3.
4. **Opcional / evaluar con Alonso si hay margen:** iniciar el diseño de
   `DEBT-SECRETS-MANAGER-PERSISTENCE-001` (persistencia de claves HMAC en Vault) —
   es la deuda P1 más grande abierta hoy, con estimación propia de 2-3 sesiones.
   No forma parte estricta de Eslabón 1, pero está directamente motivada por él.

## Punteros
- `docs/design/eslabon-1-flujo-a-avro-parquet/eslabon-1-flujo-a-avro-parquet.md` —
  diseño ratificado, fuente de verdad del esquema.
- `docs/design/eslabon-1-flujo-a-avro-parquet/smoke/` — verificado 12/12 dos veces
  (incluyendo reproducibilidad completa desde `vagrant destroy`), no tocar salvo
  para revalidar en cambio de versión de Arrow.
- `docs/design/eslabon-1-flujo-a-avro-parquet/converter-prototype/` —
  `bronze_to_gold_converter.cpp` VERIFICADO (24/24 filas, `-Werror` limpio),
  `README.md` actualizado, `evidence/` con la prueba de reproducibilidad completa.
- `etcd-server/src/secrets_manager.cpp` — `SecretsManager`, in-memory puro, sin
  persistencia. Endpoint de depuración útil: `GET /secrets/<componente>` en el
  puerto 2379, devuelve la clave activa en claro (útil para testing, pero es
  precisamente la superficie que `DEBT-SECRETS-MANAGER-PERSISTENCE-001` busca
  endurecer a más largo plazo).
- `docs/BACKLOG.md` — las dos deudas P1 de DAY 205 ya registradas al final del
  fichero (líneas ~4827 en adelante al cierre de DAY 206).
- `Makefile` línea ~3034 — `eslabon1-smoke-build`/`eslabon1-smoke-test`, ahora
  invocables desde el host (envuelven `vagrant ssh defender -c` internamente).

*Via Appia Quality — Un escudo que aprende de su propia sombra.*