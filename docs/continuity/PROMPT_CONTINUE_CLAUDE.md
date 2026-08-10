# PROMPT DE CONTINUIDAD — aRGus NDR — ÚLTIMO PR (overhaul pipeline-start/status) → read-only

## Punto de entrada (mide, no asumas)
    git checkout main && git pull
    git log --oneline -4
    git tag --list 'pre-release-*'
Debes ver HEAD en `c94c18f6` (Merge #137, cara pública) y `pre-release-0.0.1` + `-0.0.2`.
La cara pública (paper v25 arXiv:2604.04952 + reproducibilidad) está CERRADA en main (DAY 254).
`main` PROTEGIDA (GH013): todo por PR. NUNCA push directo a main.
Rama de trabajo nueva off main, p.ej. `fix/pipeline-start-overhaul`.
Limpieza: `docs/readme-cierre` ya fusionada (borrable local+remota).

## Qué es este PR — el ÚLTIMO antes de read-only
Fontanería interna de `pipeline-start` / `pipeline-status`. NO cara pública.
Cuatro deudas, un PR. Al terminar: repo en modo LECTURA.
Regla del día: cada *-start exige binarios y VMs concretas — MEDIR las secciones
pipeline-start, pipeline-status y *-start del Makefile real ANTES de tocar.

## Las cuatro deudas (todas: medir → componer, no reimplementar)

1) DEBT-PIPELINE-START-DISABLE-RAG-001
   pipeline-start hoy encadena: test-provision-1 → etcd-server-start → rag-start →
   rag-ingester-start → ml-detector-start → firewall-start → sniffer-start.
   pipeline-status chequea rag-security y rag-ingester entre otros.
   CAMBIO: quitar rag-start + rag-ingester-start del arranque, y las dos líneas
   rag del status. SIN borrar targets ni binarios (rag-build/rag-ingester-build
   siguen; EMECAS los testea). Considerar flag opt-in (p.ej. WITH_RAG=1) para
   re-armarlos sin romper EMECAS/test-all.

2) DEBT-PIPELINE-START-BINARY-GUARD-001
   pipeline-start ASUME binarios compilados (como asumía reproduce-paper antes de
   reproduce-paper-deps). CAMBIO: guard que compile lo que falte con el MISMO
   $(PROFILE) antes de arrancar. Generaliza a pipeline-start lo que hoy hace
   reproduce-paper-deps. Medir qué binario exige cada *-start.

3) DEBT-STATUS-ALL-VMS-001
   pipeline-status solo mira defender (vagrant ssh -c → VM primaria). AMPLIAR a
   las 5 VMs: defender (aRGus), suricata (systemctl), zeek (zeekctl status),
   wazuh (manager/agent), client. Añadir: driver de tráfico de la última corrida
   (marker/STAMP en logs/lab), ruta de log por componente, y el comando
   `vagrant ssh <vm>` para llegar a cada uno.

4) DEBT-STATUS-LOGFILES-001
   Rutas de log estándar por componente en el status (logs/lab/*.log). Hermano
   de la #3; probablemente se resuelven juntas.

## Cierre
rama → commit → push → PR → merge → pull main. Committear en este PR el registro
de deuda técnica final. Opcional tag pre-release-0.0.3. DESPUÉS: repo en modo
lectura (branch protection dura / GitHub "Archive repository").

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO. Conjetura etiquetada o no se dice.
- Fidelidad de reuso: componer piezas existentes, no reimplementar.
- Alonso pilota; mide contra fichero y pega salida. NO str_replace: fichero completo.
- No `grep -rn` desde raíz: `git grep` o fichero concreto.
- No encadenar comandos de salida grande en el mismo bloque. sed BSD: `sed -i ''`.
  Recetas del Makefile con TAB. main PROTEGIDA: todo por PR.

## Hilos de memoria
[[cierre-paper]] (agenda de cierre; este PR anclado ahí como "el siguiente").
