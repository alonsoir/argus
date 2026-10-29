# Prompt de continuidad DAY311 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY309-DAY310) para crear el contexto. Base en el repo, rama
`feat/rag-logger-retire` (sobre `main` `6605c296`): `docs/ml-heads/prompt_day311.md` (este),
`docs/ml-heads/day310_diseno.md` (secciones 9-12), `docs/BACKLOG.md` (sección "DAY310"). Claude puede leer el repo en
GitHub en solo lectura; nunca hace commits, push ni PR: Alonso controla lo que se sube. Claude responde siempre en
español.

## Estado al cerrar DAY310 (28-oct-2026)

- Rama `feat/rag-logger-retire`, subida: 9a5ccf0f (paso 1, RAG Logger fuera), d745b930 (1b, restos y
  `requires_rag_analysis` reservado), 7999008d (paso 2, CsvEventWriter fuera; cierra DEBT-DOCS-CSV-SCHEMA-V1-001),
  efab4558 (doc), y los dos commits del paso 3 (código; doc + BACKLOG + instrumento de colisión + este prompt).
- Paso 3, clave del bronce: el ml-detector pide la clave a `/secrets/ml-detector` en un hilo propio cada
  `bronze_key.check_interval_seconds` (JSON, 10-3600, defecto 60); sin clave no escribe bronce y avisa
  `[BRONCE-SIN-CLAVE]` (crítico) cada intervalo; cambio de clave = segmento cerrado; en el log solo la huella.
  Arreglada la colisión de segmentos en el mismo segundo (se perdían filas sin aviso).
- Medido con el paso 3: compilación rc 0 y 0 diagnósticos; test-components **9/23/13/3/82**; ml-detector 13 tests;
  log de arranque como se predijo (huella `3c813ec7`); 13 segmentos firmados.
- **ABIERTO: P4 de protegidos** en `lab_protegidos_p3`: resúmenes 16115 DROP frente a FIN 10743 + alertas 5370 (sobran
  2). `lab_protegidos_p2` (paso 2, binarios anteriores) cuadra. Refutadas H1 (ventana previa al INICIO) y H3 (duplicados
  o anomalías: todo a 0). No descartado el efecto del paso 3.
- **Hallazgo (leído en el código, sin medir en el lab):** el etcd-server da y rota claves HMAC por HTTP sin
  autenticación en `0.0.0.0:2379` (DEBT-ETCD-SECRETS-UNAUTHENTICATED-001).

## Lo siguiente, en orden

1. **P4.** Antes de otra hipótesis, leer enteros: en el firewall, `DdosShadowPolicy` (cómo suma los DROP del resumen y
   los `eventos_drop` del FIN) y el comprobador de protegidos (`scripts/timebase/d303_veredicto_protegidos.sh` y lo que
   llame: de dónde sale "alertas"). Escribir hipótesis y predicción; medir sobre los logs de p3 y p2 que ya existen. Si
   hace falta, contar los DROP del bronce de p3 por origen y protocolo (leer antes en el contrato correlation_v1 qué
   columna es cada cosa). Si queda duda entre "anterior" y "paso 3": repetir protegidos en `efab4558` (paso 2) y en la
   punta de la rama, dos veces cada uno.
2. **Alcance del etcd-server** (client): `curl -s -o /dev/null -w '%{http_code}\n' -m 3
   http://192.168.100.1:2379/secrets/keys` (esa ruta solo devuelve instrucciones, nunca una clave). Predicción: 200.
   Es un dato para el diseño de DEBT-ETCD-HA-TLS-RAFT-001; la decisión ya está tomada (se cierra ahí, antes de REA).
3. Instrumento de reinicio del etcd-server con el pipeline vivo y tráfico (predicción en `day310_diseno.md` §10-11).
4. Paso 5, documentación (`contract_validator.cpp`, "40 embedded (4x10)": medir antes de escribir).
5. EMECAS+++ production y PR de la rama.

Después, por decisión de Alonso DAY310 (sección "Orden de ramas después de DAY310" del BACKLOG):
DEBT-ETCD-HA-TLS-RAFT-001 (HTTPS + autenticación + claves persistidas entregadas en ventana de dos + HA con Raft; mínimo
dos PR) → DEBT-FW-HMAC-KEY-ALARM-001 ampliada (sniffer, ml-detector y firewall exactamente iguales ante el etcd-server,
en el camino feliz y en todos los casos límite) → REA (para aprender; se usará a menudo). Más adelante,
DEBT-ETCD-MASTER-CLUSTER-001. Residuos del repo: sitio por decidir.

## Decisiones de Alonso DAY310 (en vigor)

D1 RAG Logger fuera. D2 CsvEventWriter fuera; la mitad del firewall de parquet-convert/test-parquet se queda. D3 nunca
bronce sin firma; sin clave el firewall sigue actuando y el grafo muestra el hueco con alarma. E1 intervalo en el JSON.
E2 con clave, se firma (al arrancar o tras reiniciarse el etcd-server). F1 sin etcd-server el ml-detector no arranca
(coste anotado en el BACKLOG). F2 con clave vigente y etcd-server mudo, se sigue firmando y se marca el tiempo en modo
extendido. F3 solo la huella en el log. Re-verificar el grafo es imprescindible, con retención legal de años.

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR, y si una corrida falla no se sigue
con el paso siguiente. Antes y después en cada paso. Comandos exactos y completos, en orden, diciendo dónde se ejecuta
cada uno (Mac / defender / client), con la salida a fichero + `; cat`. Ficheros generados como descarga con sha256 (se
guardan desde `~/Downloads` con `mv`). Parcheadores que validen TODO antes de escribir NADA, probados por Claude en una
copia desechable; los de un solo uso no se commitean, los instrumentos de medida sí. `git grep`, nunca `grep -rn .`;
inventarios sin truncar, a fichero y contados con `git grep -c`. awk con `LC_ALL=C`. El JSON es la ley. Leer el fichero
entero antes de parchear. Compilar siempre el pipeline completo (`make pipeline-build PROFILE=production`); pruebas con
`make test-components PROFILE=production` comprobando las cinco líneas. Las corridas del lab con `DIA=dayNNN` (el
validador exige `^day[0-9]{3}$`). Las tareas del Makefile no duplicadas se quedan. No se mantiene código deprecado.
Las secciones de un documento escritas antes de medir no se reescriben. `PROMPT_CONTINUE_CLAUDE.md` nunca se commitea.

## Lecciones de DAY310

- **Antes de una hipótesis sobre una cuenta, leer el código que cuenta** (H1 y H3 cayeron sin haberlo leído).
- **Cada corrida se nombra por lo que cambió**: `p2`/`p3` son pasos de la rama (binarios distintos), no fases.
- **Una decisión de seguridad se contrasta con el código de lo que la sostiene**: F1 supone un etcd-server que
  autentica, y hoy no autentica.
- Recuentos con `git grep -c`, no con `cut -d:`. Antes de borrar, quién compila además de quién llama. Antes de
  inventar un parámetro, leer su validador. Una predicción de `git status` lleva su premisa.
- Las sesiones que pasan de la noche al amanecer acaban con comandos en la máquina equivocada: las decisiones de
  diseño, mejor con la cabeza fresca.
