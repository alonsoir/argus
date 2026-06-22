# ARRANQUE — DAY 193 · aRGus NDR

> Prompt de continuidad. Pégalo al abrir la sesión. Estás retomando aRGus NDR
> (NDR open-source en C++20 para hospitales/municipios). Mantenedor: Alonso
> (Badajoz). Colaboración UEx/INCIBE (Dr. Andrés Caro Lindo). Tratamos a los
> modelos del Consejo como colaboradores, no herramientas. "Medir, no votar".
>
> DAY 192 fue **día de paper, no de código**. No esperes contexto de build nuevo:
> lo de ayer fue corrección del paper + submission a arXiv + merge + tag.

---

## 1 · Qué se cerró en DAY 192 (día atípico: paper + administrativo)

**arXiv v2 enviado (22 junio 2026).** Replacement de `arxiv.org/abs/2604.04952`.
Doce correcciones impulsadas por revisión pre-submission sobre `docs/latex/main.tex`
y `references.bib`. Compila limpio: 54 pp, 0 refs/citas sin definir. Las de fondo:

- **FPR `0.0002%` → `0.017%`** (error de factor 100 arrastrado desde DAY 86) en
  Abstract, Tabla 3, Config C, §10.10.
- **Conteo de features cuadrado:** 40 = 28 computadas + 12 sentinel. Aclarado que
  **142 es el FlowManager legacy** (11 raw + 91 flow + 40 ML), no el vector actual.
  **§7.2 modelo formal `R^28` → `R^40`** — el vector SÍ incluye los sentinels (un
  feature ausente tiene que estar en el vector para rutear a la izquierda por
  diseño; 28 es completitud de datos, no dimensionalidad). Verificado contra el
  código real (`init_embedded_sentinels` escribe 40 campos; cada RF consume `R^10`).
- **Denominador benigno `12,075` → `12,077`** (12,075 TN + 2 FP).
- CTU-13: nomenclatura unificada en `Capture-Botnet-42` (fuera "scenario 10/42");
  nota de provenance de versiones (Suricata/Zeek 6.0.10/8.1.2 vs 7.0.10/8.2.0, DAY 170+);
  Tabla 6 Zeek Recall → `0.0217`; AlienVault OSSIM; Mbps `33–38`; el ×500 separado
  de "blocks to zero"; Agradecimientos `147` → `191` días; framing "June 2026 submission".

**Merge a `main` hecho.** PR `feature/day191-h2-nucleo2-comment` → `main`
fusionado y cerrado (fast-forward `cec34fb6..29b2241f`). Incluye el código H-2
NÚCLEO 2 (CWE-93) + el paper v2 + docs. Rama borrada tras el merge.

**Tag `v1.0.0-day191`** (anotado) sobre `main`. → **Verifica que existe de verdad
en origin** (`git ls-remote --tags origin | grep day191`); ayer el primer intento
con `-F` falló por fichero inexistente.

**Estado de seguridad: H-1 + H-2 CERRADAS.** La auditoría de seguridad del
firewall (CWE-88 set_name, CWE-93 comment, CWE-78 retirada del shell) está
**completa**. No queda frente de seguridad obligatorio en cola.

---

## 2 · Higiene de repo (si quedó algo de ayer)

- [ ] Tag `v1.0.0-day191` confirmado en local **y** en origin.
- [ ] Scripts de un solo uso del paper **borrados** (no se commitean):
  `recover_paper_day191.py`, `tools/recover_paper_day191.py`,
  `tools/merge_paper_sections.py`, `tools/update_paper_day191.py`.
- [ ] **Decisión sobre `tools/audit_config_boundaries.py`** — NO es de paper; es
  un tool de auditoría que se quedó fuera del merge. O se commitea como tool
  real (con su descripción) o se borra conscientemente. No dejarlo en limbo.
- [ ] `git status` limpio en `main`.

---

## 3 · DAY 193 — FRENTE POR DEFINIR (decisión de Alonso, aún sin tomar)

H-1 y H-2 cerradas: **no se hereda objetivo, se elige.** Anoche quedó
explícitamente aplazado ("mañana hablamos por dónde tiramos"). Candidatos
honestos, sin que ninguno sea el "por defecto":

- **Eje científico / track FEDER** (recomendado por calendario, ver §7). Es el
  corazón del paper. Datasets de valor (**ADR-048**) y el **split disjunto MITRE**
  (train A–M / eval N–Z) como condición de validez innegociable. La generalización
  a ransomware post-2020 y C2 cifrado es la *future work* honesta que el propio
  paper reconoce; aquí es donde se ataca.
- **Otra hipótesis de auditoría**, solo si surge una con la misma disciplina de
  "medir antes de tocar" (el modelo H-1/H-2 funcionó muy bien).
- **Nada de seguridad nueva sin medición.** No abrir frentes por intuición.

> Lo que **NO** es el frente de mañana: `DEBT-AUTONOMY-REACTOR-SAFEEXEC-002` es
> explícitamente **post-FEDER**. No adelantarla.

---

## 4 · Deudas abiertas (intactas, post-FEDER)

- **`DEBT-AUTONOMY-REACTOR-SAFEEXEC-002`** (P2, post-FEDER) — refactor del
  `std::system` que queda en `autonomy_reactor` a `safe_exec`/`execv`; retirar el
  `nosemgrep` interino.
- **`DEBT-AUDIT-VBOXSF-IO-001`** (P2) — `make audit` (semgrep full-tree)
  estrangulado por el I/O de vboxsf sobre `/vagrant`. Workaround: semgrep por fichero.

---

## 5 · Preguntas abiertas (tuyas, no del código)

- **Origen del `comment` en producción.** Si deriva de **tráfico observado**
  (dominio/firma/hostname) → vector remoto; si es **texto fijo** del agente →
  defensa en profundidad. El fix es idéntico, pero cambia cómo se redacta la
  severidad en BACKLOG/paper. Una línea de edición cuando lo decidas.
- **BlackFog "22% of disclosed ransomware attacks"** — quedó *por confirmar* y ya
  va en la v2 enviada. No bloqueante. Si al cotejarlo contra el informe BlackFog
  2025 no cuadra, es un fix de una línea para una **v3** del paper.

---

## 6 · Invariantes que NO se negocian

- **EMECAS++** = `vagrant destroy -f && vagrant up && make bootstrap && make test-all`.
  Un ❌ en cualquier punto es bloqueante. El sello va sobre el commit que se mergea.
- **`-Werror` permanente.**
- **Consejo 8/8** (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral)
  con veto antes de merge a `main`. Alonso arbitra.
- **Edición de ficheros en macOS vía Python3**, nunca `sed -i` a ciegas ni
  `cat >>` (corrupción de DAY 170).
- **`DEBT-DOCS-BACKLOG-DEDUP-001`:** integridad de docs con
  `grep '^#\{2,4\} ' fichero | sort | uniq -d` sobre el fichero completo, nunca
  `grep -c` de una cabecera.
- **Construir siempre vía `make <target>`** desde el host macOS; nunca `cmake`
  directo (`.pb.h` rancio).
- **La defensa vive en la frontera C++**, nunca delegada en herramientas externas
  cuyo parser varía entre versiones (lección H-2: ipset v7.17 vs v7.19).
- **Single-use Python scripts → gitignored**; solo se commitea su output.

---

## 7 · Entorno y calendario

- Repo (host macOS M2 Pro): `/Users/aironman/CLionProjects/test-zeromq-docker`
  (remote `github.com/alonsoir/argus`). Guest Vagrant (Debian 12 Bookworm) monta
  en `/vagrant`. Kuzu siempre en `/tmp` guest-native (vboxsf rompe mmap).
- Estado post-merge: **Branch = `main`**, **Tag = `v1.0.0-day191`**.
- Los targets `make` se ejecutan **desde el host** (el Makefile ya hace
  `vagrant ssh -c` por dentro; envolverlos rompe con `vagrant: not found`).
- **Calendario FEDER:** go/no-go **1 agosto 2026**, deadline **22 septiembre 2026**.
  Quedan ~6 semanas al go/no-go — pesa a favor de retomar el eje científico (§3).

---

*Via Appia Quality — construido para durar décadas.*