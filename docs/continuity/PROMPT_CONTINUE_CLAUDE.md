## Estado de arranque (verificado al cierre de DAY 188)
- Rama `feature/day188-security-debt-audit` sobre `b6352fa9` (main actual; el prompt
  de DAY 188 decía 888ed69a pero main avanzó con el merge del PR #102, README).
- Dos commits limpios, separados por naturaleza:
  - `b3f4a3df` — seguridad: H-1 (Cypher injection) + H-2 movimiento 1 (IP injection).
  - `429e40ac` — infra: targets test-firewall por perfil + .gitignore (*_day188.py).
- H-1 (Cypher injection): CERRADA. Producción 100% parametrizada (ADR-057).
  `dialect_smoke.cpp` (huérfano que ejecutaba la salida interpolada) eliminado.
  Evidencia: test_cypher_prepared.cpp 7/7, incl. test de 2º orden (param-token como
  dato literal, no re-interpolación).
- H-2 movimiento 1 (IP injection): CERRADO. `is_valid_ip` endurecido contra bypass
  CIDR+`\n` (allowlist estricto + prefijo CIDR en rango). `is_valid_ip` movido a public.
  Evidencia: unit test_ipset_is_valid_ip 7/7 + e2e test_ipset_injection_integration 1/1
  (canario set_exists(evil)==false contra ipset real, requiere root).
- Build en /vagrant/firewall-acl-agent/build-$(PROFILE); profiles: debug, production, etc.

## INVARIANTE DE ARRANQUE — REGLA EMECAS (no negociable)
- main pasó EMECAS al cierre de DAY 187; la rama de hoy NO ha tocado el invariante de
  arranque. Mañana: confirmar verde en la RAMA antes de seguir:
  make build && make test-all   (perfil debug)
  make test-firewall            (no-root, debe ir verde)
  (Si no sale verde, NO se toca nada más hasta que lo esté.)
- PENDIENTE de decisión: pushear rama como backup esta noche. NO abrir PR-a-main hasta
  cerrar H-2 mov.2 (make audit no puede estar verde para H-2 hasta entonces).

## OBJETIVO DE HOY (DAY 189): H-2 movimiento 2 — cerrar H-2 del todo
MISMA rama `feature/day188-security-debt-audit` (H-1 + H-2 completa = un audit coherente).
Tesis: dejar `make audit` verde para H-2 retirando el shell y validando los campos
restantes que alimentan el fichero `ipset restore`.

### NÚCLEO
**1. set_name crudo al fichero restore** (firewall-acl-agent/src/core/ipset_wrapper.cpp:
~L329 add_batch, ~L416 delete_batch). Un `\n` en set_name inyecta línea restore igual
que lo hacía la IP. PRIMER PASO = DIAGNÓSTICO, no validar a ciegas:
- Mirar tests/unit/test_config_loader_setname.cpp y de dónde sale el validador que
  prueba. HIPÓTESIS: ya existe un validador de set_name reutilizable. NO duplicar.
- Si sirve, reusarlo. Si no, allowlist `[A-Za-z0-9_.:-]`, longitud ≤ IPSET_MAXNAMELEN,
  RECHAZAR `-` inicial (CWE-88 argument injection).
- Test que ataque: set_name = "x\nadd evil 6.6.6.6" y set_name = "-X".

**2. comment solo escapa `"`, no `\n`** (~L343). Sanear saltos antes del fichero restore.
Test: comment con `\n` no inyecta línea restore.

**3. Retirar popen/system de los ~13 métodos** → safe_exec/execvp (patrón ya probado,
ver tests/unit/test_safe_exec.cpp). create_set, destroy_set, flush_set,
set_exists_unlocked, test, rename_set, swap_sets, save, restore, list_sets, get_stats,
list_entries. Para los que leen stdout (list_sets, get_stats, list_entries): variante
que captura salida; el `| grep '^add'` de list_entries → a C++.

**4. make audit (semgrep) VERDE para H-2** — solo legítimo TRAS 1-3. Cualquier supresor
con justificación + test de ataque como prueba. NO contorsionar código para callar al
linter. Medir, no votar.

### RELLENO SI SOBRA SESIÓN
- Comentario huérfano `/// Validate IP address format` en ipset_wrapper.hpp (quedó tras
  mover la declaración a public). Borrar.

### FUERA DE ESTA RAMA (a propósito)
- Limpieza de huérfanos TRACKED: ipset_wrapper.hpp.old + 4 .py de merges previos
  (add_newline_guard_test.py, update_docs_day184/185.py, validate_correlation_v1_scaffold.py).
  Su propio commit/rama. Herramienta lista: cleanup_tracked_cruft_day188.py (--discover
  para ver la deuda TOTAL de backups en el árbol; era intuición de DAY 188, medirla).
- Enganchar test-firewall a test-all (toca el invariante EMECAS de arranque) → decisión
  separada, con calma.

## Cierre del día (DAY 189)
- make audit VERDE para H-1 Y H-2 + EMECAS verde.
- Commits separados por naturaleza. Marcar H-2 CERRADA en docs/BACKLOG.md (con día +
  evidencia: unit+e2e mov1, tests mov2, audit verde).
- AHORA SÍ: PR a main "DAY 188-189: cierre audit H-1/H-2". Unidad revisable.
- Continuity DAY 190 + post LinkedIn.

## Contacto / referencias
Dr. Andrés Caro Lindo (andresc@unex.es, UEx/INCIBE). Paper arXiv:2604.04952 Draft v18.
Consejo de Sabios (8 modelos) para revisión adversarial si mov.2 lo merece.