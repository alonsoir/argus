#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_docs_day185.py — aRGus NDR — cierre documental DAY 185

Actualiza docs/BACKLOG.md y README.md con lo de DAY 185:
  - Hito B1-B3 (extracción libcorrelation_v1, byte-identidad probada) — NO cierra
    DEBT-LIBCORRELATION-V1-EXTRACT-001 (eso es B4); registra el progreso.
  - Hallazgo de locale: bronce histórico verificado en punto decimal (classic de
    facto). D-E es endurecimiento, NO bug-fix con breaking change.
  - 5 DEBT nuevas del Consejo (fuzzing, matriz locales, defensa newline, clave HMAC,
    formateo locale-agnóstico) + criterio de cierre de cada una.

IDEMPOTENTE: detecta marcadores ya presentes y no duplica. Si no encuentra un
ancla de inserción, AVISA y no toca el fichero (nunca adivina).

ALCANCE HONESTO: registra solo lo que DAY 185 estableció. No cierra deudas que
siguen abiertas ni declara B4 hecho (no lo está).

Uso:
    python3 update_docs_day185.py [--root /ruta/al/repo] [--dry-run]

--dry-run muestra qué cambiaría sin escribir. Corre primero con --dry-run.
"""

import argparse
import os
import sys
import datetime

# ── Bloques a insertar ───────────────────────────────────────────────────────

# Entrada nueva del BACKLOG (sección DAY 185). Se inserta tras la cabecera de
# criterio/política, antes de la primera sección "## 🆕 Entradas DAY 184".
BACKLOG_DAY185_SECTION = r"""## 🆕 Entradas DAY 185 — Extracción libcorrelation_v1 (B1-B3) + locale verificado + Consejo

> Origen: sesión DAY 185 (branch `feature/day183-kuzu-sink-unwind-flush`). Extracción de la
> capa de serialización del contrato bronce `correlation_v1` a una librería compartida,
> siguiendo Via Appia "por adición" (B1→B4). Hoy: B1-B3 hechos y verdes (réplica construida y
> PROBADA byte-idéntica); B4 (rewire + borrar `build_row`) queda para DAY 186 con cabeza fresca.
> Síntesis del Consejo (8/8) incorporada. Todo esto es "suelo que protege la medición".

### ✅ HITO DAY 185 — libcorrelation_v1 extraída y probada byte-idéntica (B1-B3)

- **Corte en tres capas** (frontera = `struct CorrelationV1Row`): `to_row()` [protobuf→Row,
  exclusivo de ml-detector] · `serialize()` [Row→bytes, LIB COMPARTIDA = notario único de los
  bytes] · `CorrelationWriter` [bytes→disco]. El viejo `build_row` fundía mapeo protobuf
  (exclusivo, se queda) + serialización CSV (común, extraída).
- **B1 — `to_row` por adición** (verde): `ml_defender::to_correlation_v1_row(event)` añadido a
  `correlation_writer.{hpp,cpp}` SIN tocar `build_row`. Tri-estado `Ok/Skip/Error`. ml-detector
  compila limpio bajo `-Werror`.
- **B2 — golden congelado** (27 vectores): `capture_golden` escribe por el path del ORÁCULO
  (`write_record`/`build_row`, nunca `serialize`) a `tests/data/correlation_v1_golden.tsv`.
  3 realistas + 24 rincón (comas, comillas, `\n`/`\r`/`\t` embebidos, NaN, Inf, negativos, alta
  precisión, UTF-8, vacíos, puertos/ts extremos, los 7 enums de `DetectorSource`, enum desconocido,
  `community_id` vacío→SKIP). Capturado forzando locale classic (asunción de producción).
  Resultado: `WRITTEN=26 SKIPPED=1 mismatches=0`.
- **B3 — test de oráculo** (verde, 27/27): `test_correlation_v1_oracle` prueba que
  `serialize(to_row(e))` es byte-idéntico contra el golden congelado Y contra `write_record` en
  vivo; vectores SKIPPED → `to_row` devuelve `Skip` exacto (sella D-F). Diagnóstico por byte en
  divergencia. **Este es el primer verde que prueba la corrección del refactor, no solo su
  colocación.**
- **Validador estructural** `validate_correlation_v1_scaffold.py` (rev B2): 46 OK · 0 FALTA.
- **Decisión de proceso (Via Appia):** B1-B3 se commitean como hito ANTES de B4. Separar
  "construí y probé la réplica" de "borré el original" — dos afirmaciones distintas.

### 🔬 HALLAZGO DAY 185 — locale de producción verificado (a favor)

Verificado por inspección directa del bronce histórico en `/vagrant/logs/correlation/argus/`:
los scores se escribieron con **punto decimal** (`0.038306`, no `0,038306`), a pesar de que el
shell de login corre `es_ES.UTF-8`. Causa: no hay unit systemd; el pipeline arranca vía
`vagrant ssh -c` con entorno vacío → locale **C de facto**. Consecuencias:
- **D-E (`imbue(classic)` en `serialize`) es ENDURECIMIENTO, no corrección de bug.** El golden
  capturado en classic casa con el histórico real. NO hay breaking change.
- El escenario catastrófico que 3 modelos dieron por plausible (bronce histórico corrupto con
  comas) queda **descartado con evidencia**.
- Pero el classic actual es **por accidente** (entorno vacío), no por diseño: una unit systemd con
  `LANG=es_ES`, o un arranque desde sesión interactiva, habría producido comas. El refactor blinda
  ese futuro por construcción → ver `DEBT-CORRELATION-V1-LOCALE-MATRIX-001`.

### 🧭 Síntesis del Consejo (8/8) — DAY 185

Brief retrospectivo (B1-B3) + prospectivo (plan B4). Veredicto agregado: **nadie bloquea B4;
piden cinco endurecimientos baratos antes.** Señal de oro (hallazgos que el brief NO teleó):
(a) el HMAC rompe la promesa "mismos bytes" entre productores — lo común es cols 0-17, la 18 es
integridad por-productor (DeepSeek); (b) el golden bajo classic forzado solo es fiel si producción
era classic — VERIFICADO a favor hoy (Kimi/DeepSeek/Qwen); (c) shadow mode de B4 = el fuzzing
pre-B4 de F1 (Gemini/ChatGPT/DeepSeek convergen); (d) formateo numérico locale-agnóstico por
construcción (Kimi/Qwen). Ruido descartado: binario viejo en Docker, semana de doble escritura en
staging (production-readiness, fuera de alcance), matriz de 5+ locales (4 bastan).

### DEBT-CORRELATION-V1-EXTRACT-B4-REWIRE-001 — Rewire write_record→serialize + borrar build_row
**Severidad:** 🟡 P1 — cierra DEBT-LIBCORRELATION-V1-EXTRACT-001
**Estado:** ABIERTO — DAY 185 (B1-B3 hechos; B4 para DAY 186, cabeza fresca)
**Componente:** `ml-detector/src/correlation_writer.cpp` + `.hpp`
`write_record` pasa a llamar `to_correlation_v1_row(event)` → si `Ok`, `serialize(row, hmac_key)`
→ escribe la línea; si `Skip`, cuenta skip. Se BORRAN `build_row` y `compute_hmac` de
`CorrelationWriter` (su lógica ya vive en la lib). Tras B4 el guard "vs oráculo en vivo" se vuelve
tautológico (serialize vs sí mismo); solo sobrevive "vs golden" (por eso se congeló antes).
**Pre-B4 obligatorio (Consejo):** (1) fuzz `serialize` vs `write_record` en vivo, N millones de
eventos, mientras el oráculo aún existe = shadow mode de F1; (2) decidir camino de fallo de clave
HMAC mal formada — excepción en constructor (hoy) vs error tipado en `serialize` (dos caminos para
la misma condición); (3) `grep -r build_row` para dependencias ocultas antes de borrar.
**Test de cierre:** `test_correlation_v1_oracle` y `test_correlation_roundtrip` siguen verdes tras
el rewire; `grep -rn build_row ml-detector/` = 0 (o solo comentarios); fuzzer pre-B4 sin divergencias.
**Estimación:** 1 sesión (DAY 186).

### DEBT-CORRELATION-V1-FUZZ-PROPERTY-001 — Red permanente de byte-identidad (fuzzing)
**Severidad:** 🟡 P1 — el golden de 27 vectores no basta como única red permanente
**Estado:** ABIERTO — DAY 185 (Consejo 8/8 — F1)
**Componente:** `libs/correlation-v1/tests/` + `ml-detector/tests/integration/`
27 vectores enumerados son una instantánea, no una propiedad (D-B: acotado, no probado). Dos
patas que se reconcilian: (a) ANTES de B4, fuzz `serialize(to_row(e))` vs `write_record` en vivo
sobre N millones de eventos aleatorios — congela divergencias mientras el oráculo existe (parte de
B4-REWIRE); (b) DESPUÉS de B4, fuzzing de propiedad sobre `CorrelationV1Row` (determinismo, reglas
de escape CSV, HMAC correcto sobre cols 0-17) como red permanente sin oráculo de bytes.
**Test de cierre:** fuzzer (a) sin divergencias sobre N≥1M eventos pre-B4; fuzzer (b) de propiedad
integrado en `make correlation-v1-test`, dispara sobre structs aleatorios.
**Estimación:** 1-2 sesiones.

### DEBT-CORRELATION-V1-LOCALE-MATRIX-001 — Matriz de locales hostiles como gate de inmunidad
**Severidad:** 🟡 P1 — inmunidad de locale verificada en UN solo locale (es_ES)
**Estado:** ABIERTO — DAY 185 (Consejo 8/8 — F2; locale de producción ya verificado a favor)
**Componente:** `libs/correlation-v1/tests/test_correlation_v1.cpp`
El contrato bronce debe ser **locale-invariante por diseño** (mismo `0.910000` en Badajoz, Tokio o
São Paulo). `serialize` fuerza classic; el test P0b prueba inmunidad ante UN locale hostil
(es_ES). Falta MATRIZ como gate: parametrizar P0b sobre {es_ES (coma decimal), de_DE (millares),
ar_SA (dígitos no latinos), C}. No es "soportar" locales, es **comprobar inmunidad**. NOTA: el
locale de producción ya se verificó a favor en DAY 185 (bronce histórico en punto decimal, classic
de facto) — esta deuda es blindaje del futuro (una unit systemd con LANG podría reintroducir el
riesgo), no investigación de corrupción activa.
**Test de cierre:** P0b corre los 4 locales; bajo cada uno la salida de `serialize` es byte-idéntica.
Un solo byte distinto = fallo de aislamiento.
**Estimación:** 0.5 sesión (parametrizar el test existente).

### DEBT-BRONZE-EMBEDDED-NEWLINE-001 — Saltos de línea embebidos rompen reader getline
**Severidad:** 🟡 P1 (defensa barata YA) / arreglo de formato post-FEDER
**Estado:** ABIERTO — DAY 185 (Consejo 8/8 — F4; destapado por vector rincon_04)
**Componente:** `libs/correlation-v1/` (validate/to_row) + `correlation-engine` (parse_and_verify)
Un campo string con `\n`/`\r` embebido → `csv_string` lo entrecomilla pero mantiene el byte literal
→ la "fila" bronce ocupa varias líneas físicas → un reader basado en `getline` (probablemente
`parse_and_verify`) parte el registro y el HMAC no valida. Es debilidad del FORMATO, no del
refactor (el golden lo captura leyendo el fichero entero). Distinción del Consejo: diferir el
ARREGLO del reader es legítimo (post-FEDER); diferir la DETECCIÓN no. Defensa barata YA: `validate`
(o `to_row`) rechaza con error ruidoso cualquier campo con `\n`/`\r` embebido. NOTA: añadir esa
defensa hace que `rincon_04` deje de producir bytes → su entrada en el golden pasa de WRITTEN a
rechazada y hay que regenerarla.
**Investigación pre-cierre:** ¿`parse_and_verify` usa `getline` o un parser CSV RFC 4180? Si
`getline` y hay `\n` en bronce histórico → corrupción activa (poco probable: ningún productor
actual mete `\n`).
**Test de cierre:** `validate` rechaza campo con `\n`/`\r` embebido (error tipado, no silencioso);
golden regenerado; decisión de formato (escapar vs prohibir vs parser RFC 4180) documentada para v2.
**Estimación:** 0.5 sesión (defensa) + decisión de formato post-FEDER.

### DEBT-BRONZE-HMAC-KEY-POLICY-001 — La col 18 (HMAC) no es "mismos bytes" entre productores
**Severidad:** 🟢 P2 — precisión del claim del contrato, no bloqueante de B4
**Estado:** ABIERTO — DAY 185 (Consejo 8/8 — F6 no listado, DeepSeek)
**Componente:** contrato bronce `correlation_v1` (especificación) + adaptadores futuros
El contrato exige "mismos bytes para el mismo dato lógico", pero la col 18 es HMAC-SHA256 con clave
de fuera. Si cada adaptador firma con su clave, dos filas con cols 0-17 idénticas tienen col 18
distinta → NO son los mismos bytes en la 18. Reencuadre correcto: lo común entre productores son
las **columnas 0-17**; la 18 es integridad por-productor, no identidad. NO bloquea B4 (B4 no toca
la semántica HMAC; DeepSeek exageró ahí). Sí obliga a precisar el claim del contrato cuando entren
adaptadores reales y a decidir política de claves (clave de contrato compartida vs HMAC como
apéndice externo a las cols 0-17). Liga con DEBT-BRONZE-KEY-PROVISIONING-001 (ya existente).
**Test de cierre:** especificación del contrato declara explícitamente que la identidad cross-productor
cubre cols 0-17; política de clave HMAC para multi-productor decidida y documentada.
**Estimación:** 0.5 sesión (decisión + doc) cuando entre el primer adaptador no-aRGus.

### DEBT-CORRELATION-V1-NUMERIC-FORMAT-AGNOSTIC-001 — Formateo numérico locale-agnóstico por construcción
**Severidad:** 🟢 P2 — endurecimiento, no urgente
**Estado:** ABIERTO — DAY 185 (Consejo — Kimi/Qwen)
**Componente:** `libs/correlation-v1/src/correlation_v1.cpp` (`fmt_double`)
`serialize` fuerza `imbue(classic)`, correcto pero frágil: cualquier código futuro que use
`std::to_string`/`printf`/`fmt::format` sin locale explícito rompería la invariante. Encapsular el
formateo numérico en una función interna que NUNCA dependa de `operator<<`+`imbue` sino de
`std::to_chars` (C++17) o `snprintf("%.6f")` — inmunidad por construcción, no por disciplina.
**Test de cierre:** `fmt_double` usa formateo locale-agnóstico nativo; el test de matriz de locales
(DEBT-CORRELATION-V1-LOCALE-MATRIX-001) pasa sin depender de `imbue`.
**Estimación:** 0.5 sesión.

### DEBT-DD-ENUM-GUARD-COL17-001 — Guard de símbolo de enum desconocido en col 17 (diferido legítimo)
**Severidad:** 🟢 P2 — endurecimiento, sin regresión
**Estado:** ABIERTO — DAY 185 (Consejo 8/8 — F3; D-D diferido)
**Componente:** `libs/correlation-v1/` (validate) + `to_row`
El `write_record` actual emite `""` en col 17 para un enum desconocido (lleva así desde siempre);
el refactor lo preserva byte a byte (`rincon_16` en el golden). Diferir el guard NO introduce
regresión — es endurecimiento (rechazar en vez de aceptar silenciosamente), no corrección. Por eso
NO bloquea el merge. Criterio de cierre (convergencia Claude/DeepSeek/Gemini): **cerrar cuando el
primer adaptador no-aRGus (Suricata) entre al pipeline** — ahí un productor que no usa
`DetectorSource_Name` podría meter un símbolo arbitrario y el guard deja de ser cosmético. Atado a
evento real, no a fecha. Nota de breaking change (DeepSeek): productores que hoy emiten `""`
empezarían a ser rechazados → coordinar.
**Test de cierre:** `validate` rechaza (error tipado) un símbolo de col 17 fuera del conjunto legal;
test positivo (7 símbolos válidos) + negativo (símbolo inválido). Activar al integrar Suricata.
**Estimación:** 0.5 sesión (al integrar el primer adaptador).

"""

# Claim honesto para el README (reemplaza/añade en la tabla de resultados o como nota).
README_CLAIM_NOTE = r"""
> **Nota DAY 185 — claim honesto de la extracción `libcorrelation_v1`:** Extracción de la capa de
> serialización del contrato `correlation_v1` a librería compartida, **verificada byte-idéntica**
> contra el oráculo `build_row` sobre **27 vectores enumerados y bajo locale classic** (3 tests
> verdes: lib P0-P3, oracle 27/27, scaffold 46 OK). Salvedades: (a) equivalencia general **acotada
> por enumeración, no probada** (D-B); (b) golden capturado en classic — locale de producción
> **verificado a favor** (bronce histórico en punto decimal, classic de facto), luego D-E es
> endurecimiento, no breaking change; (c) `\n` embebido rompe readers `getline`
> (DEBT-BRONZE-EMBEDDED-NEWLINE-001); (d) guard de enum desconocido (D-D) diferido sin regresión;
> (e) la identidad cross-productor cubre cols 0-17, la col 18 (HMAC) depende de política de claves.
> B4 (rewire + borrar `build_row`) pendiente DAY 186.
"""


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def update_backlog(text, dry_run):
    notes = []
    changed = False

    # 1) Insertar la sección DAY 185 antes de "## 🆕 Entradas DAY 184"
    if "Entradas DAY 185" in text:
        notes.append("  [skip] Sección 'Entradas DAY 185' ya presente — no se duplica.")
    else:
        anchor = "## 🆕 Entradas DAY 184"
        idx = text.find(anchor)
        if idx < 0:
            notes.append("  [AVISO] No encuentro ancla '## 🆕 Entradas DAY 184'. "
                         "Sección DAY 185 NO insertada — revísalo a mano.")
        else:
            text = text[:idx] + BACKLOG_DAY185_SECTION + "\n" + text[idx:]
            notes.append("  [ok] Sección 'Entradas DAY 185' insertada antes de DAY 184.")
            changed = True

    # 2) Actualizar la fecha de cabecera
    import re
    new_date = datetime.date.today().isoformat()
    m = re.search(r"\*Última actualización: DAY \d+ — \d{4}-\d{2}-\d{2}\*", text)
    new_header = f"*Última actualización: DAY 185 — {new_date}*"
    if m:
        if m.group(0) == new_header:
            notes.append("  [skip] Cabecera de fecha ya en DAY 185.")
        else:
            text = text[:m.start()] + new_header + text[m.end():]
            notes.append(f"  [ok] Cabecera de fecha → DAY 185 ({new_date}).")
            changed = True
    else:
        notes.append("  [AVISO] No encuentro la línea '*Última actualización...*' — no tocada.")

    return text, changed, notes


def update_readme(text, dry_run):
    notes = []
    changed = False

    # 1) Nota de claim DAY 185 tras el bloque <!-- /DAY-STATUS -->
    if "claim honesto de la extracción `libcorrelation_v1`" in text:
        notes.append("  [skip] Nota de claim DAY 185 ya presente — no se duplica.")
    else:
        anchor = "<!-- /DAY-STATUS -->"
        idx = text.find(anchor)
        if idx < 0:
            notes.append("  [AVISO] No encuentro '<!-- /DAY-STATUS -->'. "
                         "Nota de claim NO insertada — revísalo a mano.")
        else:
            insert_at = idx + len(anchor)
            text = text[:insert_at] + "\n" + README_CLAIM_NOTE + text[insert_at:]
            notes.append("  [ok] Nota de claim DAY 185 insertada tras DAY-STATUS.")
            changed = True

    return text, changed, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    backlog_path = os.path.join(args.root, "docs", "BACKLOG.md")
    readme_path = os.path.join(args.root, "README.md")

    for p in (backlog_path, readme_path):
        if not os.path.isfile(p):
            print(f"❌ No existe: {p}")
            print("   Corre desde la raíz del repo o usa --root.")
            sys.exit(2)

    print("=" * 64)
    print(f"  Cierre documental DAY 185  {'(DRY-RUN)' if args.dry_run else ''}")
    print("=" * 64)

    # BACKLOG
    print("\ndocs/BACKLOG.md:")
    btext = read(backlog_path)
    btext, bchanged, bnotes = update_backlog(btext, args.dry_run)
    for n in bnotes:
        print(n)

    # README
    print("\nREADME.md:")
    rtext = read(readme_path)
    rtext, rchanged, rnotes = update_readme(rtext, args.dry_run)
    for n in rnotes:
        print(n)

    if args.dry_run:
        print("\n(DRY-RUN — no se escribió nada. Quita --dry-run para aplicar.)")
        sys.exit(0)

    if bchanged:
        write(backlog_path, btext)
        print(f"\n✅ Escrito: {backlog_path}")
    else:
        print(f"\n(- sin cambios en {backlog_path})")
    if rchanged:
        write(readme_path, rtext)
        print(f"✅ Escrito: {readme_path}")
    else:
        print(f"(- sin cambios en {readme_path})")

    print("\nSiguiente paso sugerido (NO automático):")
    print("  git add docs/BACKLOG.md README.md")
    print("  git commit -m 'docs(day185): hito B1-B3 libcorrelation_v1 + locale verificado + 7 DEBT del Consejo'")
    print("\nPENDIENTE DAY 186 (no cerrado hoy, para el prompt de continuidad):")
    print("  - B4: rewire write_record→serialize + borrar build_row (DEBT-...-B4-REWIRE-001)")
    print("  - Pre-B4: fuzz serialize vs oráculo vivo + grep -r build_row + decidir fallo clave HMAC")
    print("  - Commitear el golden (tests/data/correlation_v1_golden.tsv) en su commit de datos")
    print("  - Defensa anti-\\n embebido en validate + regenerar rincon_04 del golden")
    print("  - Publicación en inglés del hito (pendiente)")


if __name__ == "__main__":
    main()