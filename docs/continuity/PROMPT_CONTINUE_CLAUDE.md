# ARRANQUE — DAY 192 · aRGus NDR

> Prompt de continuidad. Pégalo al abrir la sesión. Estás retomando aRGus NDR
> (NDR open-source en C++20 para hospitales/municipios). Mantenedor: Alonso
> (Badajoz). Colaboración UEx/INCIBE (Dr. Andrés Caro Lindo). Tratamos a los
> modelos del Consejo como colaboradores, no herramientas. "Medir, no votar".

---

## 1 · Qué se cerró en DAY 191

**H-2 NÚCLEO 2 CERRADO → H-2 COMPLETA.** Se cierra el frente de auditoría de
seguridad del firewall (H-1 + H-2 los tres núcleos).

El hallazgo, en una frase: el campo `comment` de `IPSetWrapper::add_batch` se
escribía sin sanear dentro del stream de `ipset restore` (un mini-lenguaje por
líneas). Vector **CWE-93** (newline/quote injection), **no** CWE-78 — el shell
ya se había retirado en NÚCLEO 3.

Demostrado sobre el guest real (Debian 12 Bookworm, **ipset v7.17**): el payload

```
EVIL=$'x"\nadd h2probe 66.66.66.66 comment "y'
```

inyectó la entrada `66.66.66.66` en el set (`grep -c 66.66.66.66` = 1). La `"`
cierra el token de comentario y el `\n` abre una línea nueva del mini-lenguaje.
**Peor caso:** la línea inyectada puede ser `flush` o `destroy` → vaciar la
blocklist entera con un simple comentario.

**Lección que se incorpora como invariante:** la indulgencia del parser de
`ipset` DIFIERE entre versiones (v7.17 abortó la comilla suelta; v7.19 la
aceptó). Por tanto **la defensa vive en la frontera C++, nunca delegada en
`ipset`.** Mismo principio que `is_valid_set_name` (NÚCLEO 1) e
`is_valid_ip_cidr` (DAY 190).

### Mitigación implementada (allowlist fail-fast)
- Nuevo `firewall-acl-agent/include/firewall/comment_validator.hpp` —
  `is_valid_comment()` rechaza control chars (`< 0x20` o `== 0x7f`: `\n \r \t \0`…),
  `"` y `\`, longitud > 255 (`IPSET_MAX_COMMENT_SIZE`). Permite UTF-8 (`>= 0x80`).
- `add_batch` acumula `failed_comments` y devuelve `IPSetError{IPSetErrorCode::INVALID_COMMENT,…}`
  (mismo patrón de retorno que `failed_ips`, **no** throw).
- El antiguo bloque de escape de comillas se **BORRÓ**: no funcionaba — `"` es
  delimitador del tokenizer de `restore`, no un carácter embebible (no existe `\"`).
- `INVALID_COMMENT` añadido al enum `IPSetErrorCode` (en `ipset_wrapper.hpp`).

### Tests (verde)
- 6 GTest puros `CommentValidator.*` (tests #53–#58, version-independientes, sin root).
- Canario e2e `IPSetWrapperTest.CommentInjectionRejected` (kernel real, sudo):
  rechazo `INVALID_COMMENT` + IP inyectada AUSENTE + atomicidad (`get_entry_count == 0`).
- `make firewall && make test-firewall` → **79/79 sin root** (73→79).
- Canario con kernel real:
  ```
  vagrant ssh -c 'sudo /vagrant/firewall-acl-agent/build-debug/firewall_tests \
    --gtest_filter="CommentValidator.*:IPSetWrapperTest.CommentInjectionRejected"'
  ```
  → **7/7 con sudo**.

---

## 2 · Cierre administrativo — SI NO LO TERMINASTE ANOCHE, EMPIEZA AQUÍ

El código está verde. Lo que puede haber quedado pendiente es el cierre del día.
Recórrelo en orden; salta lo que ya esté hecho.

- [ ] **Docs aplicadas.** Los dos scripts de un solo uso ya validados en seco:
  ```
  python3 tools/close_h2_backlog_day191.py --apply   # docs/BACKLOG.md
  python3 tools/update_readme_day191.py --apply        # README.md
  ```
  (El de BACKLOG ya tiene resuelta la colisión de header duplicado
  `### Flujo del día` → ahora es único con sufijo DAY 191.)
- [ ] **Higiene de git.** Tres cosas a dejar limpias antes del add:
  1. Fantasma con espacio final de un `add` previo al `mv`:
  `git restore --staged "tools/harden_comment_h2_day191.py "`
  2. `.gitignore` quedó escrito a nivel equivocado:
  `rm firewall-acl-agent/.gitignore` y en la **raíz**:
  `echo "tools/harden_comment_h2_day191.py" >> .gitignore`
  3. Excluir backups y scripts de un solo uso:
  `printf '*.pre-day191\nupdate_docs_day*.py\nclose_h2_backlog_day191.py\nupdate_readme_day191.py\n' >> .gitignore`
  (Decisión a confirmar: los scripts de un solo uso se **ignoran** —solo se
  commitea su output—. Si prefieres conservarlos como rastro de auditoría,
  no los ignores y añádelos al commit.)
- [ ] **`git add` de los ~9 ficheros reales** (el output, no el andamiaje):
  ```
  firewall-acl-agent/include/firewall/comment_validator.hpp   # nuevo
  firewall-acl-agent/include/firewall/ipset_wrapper.hpp        # enum INVALID_COMMENT
  firewall-acl-agent/src/core/ipset_wrapper.cpp                # validación + borrado escape
  firewall-acl-agent/tests/unit/test_comment_validator.cpp     # nuevo (6 tests)
  firewall-acl-agent/tests/unit/test_ipset_wrapper.cpp         # canario
  firewall-acl-agent/CMakeLists.txt                            # wiring TEST_SOURCES
  docs/BACKLOG.md
  README.md
  .gitignore
  ```
- [ ] **`git status` limpio** (solo esos ficheros en stage, nada raro).
- [ ] **Commit** en `feature/day191-h2-nucleo2-comment`:
  `DAY191 H-2 NÚCLEO 2: rechazo CWE-93 en comment de ipset (add_batch)`
- [ ] **EMECAS++ desde VM limpia** (sello de reproducibilidad, prerequisito del merge):
  `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
  Verde de punta a punta o no se mergea.
- [ ] **Merge a `main`** con el veto **8/8** del Consejo de Sabios.
- [ ] **Tag tras mergear:** `git tag v1.0.0-day191`
  (El README ya refleja `Tag = v1.0.0-day191` y `Branch = main`, estado
  post-merge — el tag tiene que existir de verdad.)

---

## 3 · DAY 192 — frente por definir

H-1 y H-2 cerradas. La auditoría de seguridad del firewall está completa. **No
hay un siguiente objetivo de seguridad obligatorio en cola** — toca elegir
frente, no heredarlo. Candidatos honestos (decisión de Alonso):

- **Volver al eje científico / track FEDER.** Datasets de valor (ADR-048),
  el split disjunto MITRE (train A–M / eval N–Z) como condición de validez
  innegociable. Es donde está el corazón del paper.
- **Otra hipótesis de auditoría** si surge una con la misma disciplina de
  "medir antes de tocar" (el modelo de H-1/H-2 funcionó bien).
- **Nada de seguridad nueva sin medición.** No abrir frentes por intuición.

> Lo que **no** es el frente de mañana: `DEBT-AUTONOMY-REACTOR-SAFEEXEC-002`
> es explícitamente **post-FEDER**. No adelantarla.

---

## 4 · Deudas abiertas (intactas, post-FEDER)

- **`DEBT-AUTONOMY-REACTOR-SAFEEXEC-002`** (P2, post-FEDER) — refactor del
  `std::system` que queda en `autonomy_reactor` a `safe_exec`/`execv`; retirar
  el `nosemgrep` interino (hoy justificado, pegado al `return`).
- **`DEBT-AUDIT-VBOXSF-IO-001`** (P2) — `make audit` (semgrep full-tree)
  estrangulado por el I/O de vboxsf sobre `/vagrant`. Workaround vigente:
  semgrep acotado por fichero.

---

## 5 · Pregunta abierta que sigue tuya (no del código)

**Origen del `comment` en producción.** El fix es idéntico en ambos casos, pero
cambia cómo se redacta la severidad en BACKLOG/paper:
- Si el `comment` deriva de **tráfico observado** (dominio / firma / hostname) →
  **vector remoto** (un atacante controla parcialmente lo que se escribe).
- Si es **texto fijo** del agente → **defensa en profundidad**.

Cuando lo decidas, es una línea de edición en BACKLOG.md (la sección DAY 191).

---

## 6 · Invariantes que NO se negocian

- **EMECAS++** = `vagrant destroy -f && vagrant up && make bootstrap && make test-all`.
  Un ❌ en cualquier punto es bloqueante.
- **`-Werror` permanente.**
- **Consejo 8/8** (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)
  con veto antes de merge a `main`. Alonso arbitra.
- **Edición de ficheros en macOS vía Python3**, nunca `sed -i` a ciegas ni
  `cat >>` (corrupción de DAY 170).
- **`DEBT-DOCS-BACKLOG-DEDUP-001`:** integridad de docs se verifica con
  `grep '^#\{2,4\} ' fichero | sort | uniq -d` sobre el **fichero completo**,
  nunca `grep -c` de una cabecera. (Hoy esta red de seguridad cazó una colisión
  real en el script del BACKLOG — funcionó.)
- **Construir siempre vía `make <target>`** desde el host macOS (corre `proto`,
  aplica `-Werror`); nunca `cmake` directo (`.pb.h` rancio).
- **`execv` con ruta absoluta** (`kIpsetBin = /sbin/ipset`): `execv` no busca en `$PATH`.
- **La defensa vive en la frontera C++**, nunca delegada en herramientas
  externas cuyo parser varía entre versiones.

---

## 7 · Entorno (recordatorio rápido)

- Repo (host macOS M2 Pro): `/Users/aironman/CLionProjects/test-zeromq-docker`
  (remote `github.com/alonsoir/argus`). Dentro del guest Vagrant (Debian 12
  Bookworm) monta en `/vagrant`.
- Componente del trabajo de hoy: `firewall-acl-agent/`. Headers de validación
  en `firewall-acl-agent/include/firewall/`. Namespace `mldefender::firewall`.
- Los targets `make` se ejecutan **desde el host**; el Makefile ya hace
  `vagrant ssh -c` por dentro. Envolverlos tú en `vagrant ssh -c` rompe
  (`vagrant: not found` dentro del guest).
- Kuzu siempre en `/tmp` guest-native (vboxsf rompe mmap).

---

*Via Appia Quality — construido para durar décadas.*