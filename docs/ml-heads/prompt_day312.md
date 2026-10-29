# Prompt de continuidad DAY312 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY310-DAY311) para crear el contexto. Base en el repo, rama
`feat/rag-logger-retire` (sobre `main` `6605c296`): `docs/ml-heads/prompt_day312.md` (este),
`docs/ml-heads/day310_diseno.md` (secciones 13 y 14), `docs/BACKLOG.md` (sección "DAY311"). Claude puede leer el repo
en GitHub en solo lectura; nunca hace commits, push ni PR: Alonso controla lo que se sube. Claude responde siempre en
español.

## Estado al cerrar DAY311 (29-oct-2026)

- Rama `feat/rag-logger-retire`, pasos 1-5 hechos. Commits DAY311: 4d152671 (AISLADO: el firewall no pierde DROP en
  silencio; P4 de protegidos cerrado) y 7ae4c93c: paso 5 (resumen del contrato desde el descriptor) + arreglo de
  test_kuzu_graph_sink (string_view colgante) + instrumento de reinicio del etcd-server.
- Medido: compilación rc 0 y 0 diagnósticos; test-components 9/23/13/3/82; protegidos p4 PASA (16116 = 10746 + 5370
  + 0 + 0); reinicio del etcd-server R1-R6 como se predijo, R7 explicado (ver §14).
- **EMECAS+++ production PASA** sobre 7ae4c93c (punta de código): rc 0, 5/5 E2E del lab con RESULTADO PASA,
  9/23/13/3/82. Protegidos con aislados 4 = primera ventana del ataque con < m DROP (mecanismo de DAY300), ver §14.

## Lo siguiente, en orden

1. Commit de documentación DAY311 si no se hizo (§14 de day310_diseno.md, sección DAY311 del BACKLOG, este prompt).
2. PR de `feat/rag-logger-retire` a `main` (descripción: D1-D4, E1-E4, F1-F3, AISLADO, paso 5, test de Kuzu, datos
   medidos del etcd-server), merge y etiqueta.
3. Después, por decisión de Alonso: DEBT-ETCD-HA-TLS-RAFT-001 (HTTPS + autenticación + claves persistidas en ventana
   de dos + HA Raft; mínimo dos PR), con los hallazgos medidos DAY311: bronce no re-verificable tras reinicio,
   registro vacío tras reinicio, latidos rechazados invisibles, log que dice 200 cuando responde 404, etcd alcanzable
   sin autenticación desde el client. Antes de diseñar: inventario con git grep de todo lo que habla con el
   etcd-server (rutas, quién, cuándo) y lectura entera de etcd_server.cpp, secrets_manager.cpp y component_registry.cpp.

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR, y si una corrida falla no se sigue
con el paso siguiente. Antes y después en cada paso. Comandos exactos y completos, en orden, diciendo dónde se ejecuta
cada uno (Mac / defender / client), con la salida a fichero + `; cat`. `hostname` antes de medir en una VM. Ficheros
generados como descarga con sha256 (se guardan desde `~/Downloads` con `mv`). Parcheadores que validen TODO antes de
escribir NADA, probados por Claude en una copia desechable; instrumentos de medida probados en simulador antes de
entregarlos; los parcheadores de un solo uso no se commitean, los instrumentos sí. `git grep`, nunca `grep -rn .`;
inventarios sin truncar, a fichero y contados. awk con `LC_ALL=C`. El JSON es la ley. Leer el fichero entero antes de
parchear. Compilar siempre el pipeline completo (`make pipeline-build PROFILE=production`); pruebas con
`make test-components PROFILE=production` comprobando las cinco líneas. Las tareas del Makefile no duplicadas se quedan.
No se mantiene código deprecado. Las secciones de un documento escritas antes de medir no se reescriben.
`PROMPT_CONTINUE_CLAUDE.md` nunca se commitea. Las claves HMAC nunca salen por el terminal: solo la huella.

## Lecciones de DAY311

- Un recuento por víctima no se compara con uno global sin preguntar qué otras víctimas hay.
- Un instrumento débil (una foto cada 10 s) no refuta nada; una columna que depende de una función apagada no
  discrimina.
- Antes de medir un servicio, comprobar que está en marcha (la corrida de protegidos termina con pipeline-stop).
- El prompt `vagrant@…` no dice en qué máquina se está: `hostname` primero.
- Antes de predecir el texto de un log, leer la función que lo escribe, no solo la que la llama.
- Un fallo intermitente se reproduce en las condiciones en que falló: aislarlo cambia la memoria que lo provoca.
- Un log puede mentir (el etcd-server escribe 200 y responde 404).
- `pkill -f` se encuentra a sí mismo también en las pruebas del propio Claude: parar por PID.
- `ls -dt` no encuentra la última corrida si se reutiliza el directorio; EMECAS escribe en `logs/lab/day303/`.
