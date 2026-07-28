# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 235

## Punto de entrada (mide, no asumas)
    git log --oneline -6 main
    vagrant status
Tras DAY 234: `mitre-start` corre E2E (fix de UN espacio en la línea 8 del script).
Titular reproducible = 14, VALIDADO (grafo == grep, dos métodos sin código común).
Commits del día: fix del script + entradas de BACKLOG (docs). Artefactos bajo
/vagrant/logs/day234-kuzu/ y /vagrant/logs/lab/ (ignorados).

## El estado que ordena el día
**Batalla A (mitre-start reproducible) mecánicamente GANADA, CONGELADA hasta que
entren Zeek+Wazuh.** Va de stack-arriba a aristas cross-sensor sin comandos
manuales; titular 14 honesto. Su promoción a TAREA EMECAS+++ (test de aceptación
destroy→up desde cero + gate auto-verify grafo-vs-grep) se hará CUANDO el script
esté completo con los cuatro sensores, no antes.
**Siguiente: Zeek al grafo.** Paso 2 del roadmap post-233.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- Identidad de flujo = hash(node_id ‖ community_id), SIN tiempo (Opción B, DAY 225).
  node_id = punto de observación, NO el host. Join SIEMPRE por community_id.
- Un día, una batalla. Via Appia (un criterio que no puede ponerse rojo no mide).
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes.
  `git add` explícito por fichero. macOS: nunca `sed -i` sin `-e ''` (Python3 heredoc).
  A horas malas, parar.

## Candidato de batalla DAY 235 — Zeek al grafo (Alonso decide el corte)
Adapter de Zeek: estándar de [[suricata-adapter]] + alcance N-ficheros (DAY 227,
"todo el jugo"). Corte MVP recomendado (espejo de Suricata DAY 226): SOLO conn.log.
1. `vagrant up zeek` (hoy not created) → EJERCITA POR PRIMERA VEZ el camino
   from-scratch del bloque ADAPTER_TOOLCHAIN (DAY 230). Ver los 6 paquetes
   INSTALARSE, no "ya presentes". Paga DEBT-VM-SENSOR-NO-TOOLCHAIN-001 de verdad.
2. Verificar community_id en conn.log CONTRA FICHERO, con la lección DAY 225:
   comparar mtime de site/local.zeek vs hora de arranque del proceso Zeek (la config
   correcta que el proceso vivo no ha leído). Diana seed 0: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=
3. Cobertura de campos de conn.log (tools/eval/eve_field_coverage.py o equivalente).
4. `scaffold_adapter.py --sensor zeek` → stub to_row.cpp que falla ruidoso →
   escribir el mapeo conn.log → 19 cols. Zeek es TELEMETRÍA (F1 0.042) →
   TelemetryEvent, cols de veredicto vacías (D6). flow_start de conn.log = ts (D4).
5. Criterio del día: N filas de Zeek en el bronce, TODAS pasando validate().
   NI oro NI Kuzu (eso es el día siguiente, como en la progresión de Suricata).
   Alternativas: ampliar a N ficheros (dns/http/ssl) = "todo el jugo", batalla posterior;
   o el paso 4 (paper).

## Deudas registradas DAY 234 (en docs/BACKLOG.md, sección 🆕 Entradas DAY 234)
- DEBT-MITRE-SURICATA-EVE-NOT-WINDOWED-001 (P3): adapter Suricata lee el eve.json
  entero → arrastre en caliente; neutralizado por destroy→up.
- DEBT-EVENT-ID-COLLISION-001 (P2): event_id colisiona bajo scan; puede tragarse
  una corroboración (titular_grafo ≤ intersección_grep).
- DEBT-DATASETS-FETCH-NOT-AUTOMATED-001 (P2): fetch de CTU-13/CICIDS para la ruta
  de eval del paper (mitre-start NO lo necesita).

## A medir (afecta al paper, no bloquea)
¿Está la Opción B (flow_uid sin tiempo, DAY 225) IMPLEMENTADA en código, o solo
decidida? Si sí, reencuadrar por qué DAY 233 dio 253 aristas de observación (el
self-join por community_id sobre múltiples TelemetryEvent por cid, no el window).
Si no, el window-sin-bucket sigue vivo. Medir antes de escribir la sección del grafo.

## Notas de fontanería DAY 234 (medidas, no re-medir)
- Fix del TOY_KEY: un espacio antes del `#` en la anotación gitleaks:allow (línea 8).
  Sin espacio, `VAR="..."# cmd` es asignación-prefijo → bash corre `cmd` y VAR no persiste.
- mitre-start crea Kuzu FRESCA por run: /vagrant/logs/day234-kuzu/mitre-<STAMP>.kuzu.
- La clave HMAC real sigue saliendo por curl HTTP en claro a :2379 (DEBT-HMAC-KEY-
  INSECURE-TRANSPORT-001, P1) — envuelta en el ALERT del script; NO es producción.
- community_id = col 5 del bronce (CSV). Método fiable de intersección: `grep -Fxf`
  con LC_ALL=C (inmune a locale), NO `comm` (dio números basura en DAY 233).
- ADAPTER_TOOLCHAIN ya está en el Vagrantfile para zeek+wazuh (DAY 230), pero el
  camino from-scratch (instalando) NUNCA se ha probado.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` al cerrar.