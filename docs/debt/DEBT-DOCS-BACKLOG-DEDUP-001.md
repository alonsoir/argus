# DEBT-DOCS-BACKLOG-DEDUP-001 — docs/BACKLOG.md tiene el cuerpo duplicado

**Estado:** CERRADO — DAY 170 (commit caaebf32: 5336->2839 lineas, cabeceras 2->1, nudo final eliminado, nota DAY 149 reparada). Causa raiz: operacion manual en sesion DAY 158 (cat fichero >> mismo fichero), NO el update-day158-docs.sh (que tiene guard correcto).
**Severidad:** P1 docs (no bloquea código; corrompe la memoria operativa)
**Origen:** detectado DAY 170 al ir a indexar KALMAN + ZMQ-LIMITS

## Diagnóstico (cerrado)
- `grep -c "aRGus NDR — BACKLOG" docs/BACKLOG.md` = 2. wc -l = 5336 (~2x).
- La duplicacion entro en commit `297e4133` (DAY 158). Ultimo commit sano: `b5f1e420` (DAY 157).
- Los 12 commits DAY 158-169 editaron copias indistintas -> NO se puede restaurar b5f1e420 (perderia DAY 158-169).
- Mitad A (lineas 1-2733, cabecera DAY 169) es la base COMPLETA: contiene todo DAY 167-169
  (NTP cerrado, CI-enterprise, community-id Suricata, ADR-046 v4, AdapterSpec). Verificado.
- Mitad B (2734-5336) es el duplicado viejo. Solo 3 secciones son contenido UNICO a rescatar de B:
  1. "## ADR-046 v3 — aRGus++ Multi-Source Pipeline (DAY 158)" (tabla maestra DEBT-ARGUSPP-* completa)
  2. "### DEBT-HARDWARE-STORAGE-001 — NVMe obligatorio" (DAY 160)
  3. "## Notas del Consejo de Sabios — DAY 148 (8/8)"
  El resto de B es duplicado estricto (p.ej. BOOTSTRAP-...-CONSUMERS-001 ya esta 3x en A).

## Plan de cierre (ejecutar con luz, no de madrugada)
1. Base = mitad A integra (head -n 2733 del HEAD actual).
2. Reinjertar las 3 secciones unicas de B en su lugar cronologico/tematico correcto.
3. Anadir las 3 entradas pendientes: BACKLOG-RESEARCH-KALMAN-001, BACKLOG-RESILIENCE-ZMQ-LIMITS-001,
   DEBT-ZEEK-COMMUNITY-ID-PROVISION-001.
4. Verificar: grep -c "aRGus NDR — BACKLOG" = 1 ; wc -l ~2800 ; las 3 secciones rescatadas presentes.
5. Commit unico: "fix(docs): de-duplicate BACKLOG.md (corrupcion DAY 158) + index KALMAN/ZMQ/ZEEK".
6. Trabajar en /tmp, cp sobre el original solo al verificar. Reversible.

## Entradas pendientes de indexar (su contenido ya existe en su .md propio)
- docs/experiments/BACKLOG-RESEARCH-KALMAN-001.md (RESEARCH, prereq: 4 fuentes+Neo4j integrados)
- docs/BACKLOG-RESILIENCE-ZMQ-LIMITS-001.md (BACKLOG, bloqueado por ADR-048 etcd HA)
- DEBT-ZEEK-COMMUNITY-ID-PROVISION-001 (NUEVO DAY 170): persistir @load community-id-logging +
  redef CommunityID::seed=0 en provision del Vagrantfile zeek (experiments/zeek-comparative/Vagrantfile).
  Sin esto, community_id en Zeek no sobrevive a destroy/up y el join cross-tool falla en silencio.
