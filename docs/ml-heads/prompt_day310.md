# Prompt de continuidad DAY310 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY307-DAY309) para crear el contexto. Base en el repo (`main`):
`docs/ml-heads/prompt_day310.md` (este), `docs/ml-heads/day309_diseno.md`, `docs/BACKLOG.md` (secciones "DAY309" y
"Cierre DAY309"). Claude puede leer el repo en GitHub en solo lectura; nunca hace commits, push ni PR: Alonso controla
lo que se sube.

## Estado al cerrar DAY309 (27-oct-2026)

- **`main` en `6605c296`** (PR #151, `feat/sniffer-flow-expiry`), etiqueta `pre-release-flow-expiry-0.0.8`.
  EMECAS+++ production verde sobre `69d8f207`: 28/28 hitos, los cinco E2E del lab con PASA, 2 h 05 min (las últimas
  corridas tardan ~2 h, no 4-5 h).
- Cerradas en esa rama: DEBT-SNIFFER-FLOW-EXPIRY-001, DEBT-SNIFFER-FLOWTABLE-CONFIG-001 y
  DEBT-SNIFFER-TESTS-NOT-REGISTERED-001.
- `make test-components PROFILE=production`: **cinco** líneas de resumen, flow_uid 9, sniffer **23**, ml-detector 15,
  autonomía 3, firewall 82 (total 132). Se comprueban las cinco, cada una con su número.
- Antes/después de la caducidad en ddos_v2 (`day309_diseno.md`): en ninguna corrida cambia una decisión por la
  caducidad. A (`lab-e2e-mitigacion`) PASA en los dos lados; B (batería ntp/dns/syn y benigna) decisiones iguales salvo
  0 frente a 8 positivos aislados en la benigna, explicados por la etapa 1 en el borde de K; C (ataque que vuelve tras
  330 s) `flow_packet_count` 2,080 → 1,027, decisiones iguales.

## Lo siguiente, en el orden decidido

1. **Rama del RAG Logger del ml-detector** (DEBT-RAG-LOGGER-BRANCH-001, con DEBT-DOCS-CSV-SCHEMA-V1-001). La deuda
   dice "decidir retirar o mantener con medida". Antes de proponer nada: inventario completo con `git grep` (sin
   truncar, volcado a fichero y contado) de todo lo que cuelga del RAG Logger (lista en la deuda), y leer enteros los
   ficheros que se vayan a tocar. Recordar de DAY285: el rag_logger debe salir del camino caliente; el cifrado, la
   compresión y el `correlation_writer` son imprescindibles; Alonso sospecha que algún proceso que lo alimenta no se
   puede deprecar: averiguarlo antes de retirar.
2. **Residuos del repo** (DEBT-REPO-RESIDUOS-001, ampliada DAY309: parcheadores de un solo uso ya aplicados en
   `scripts/flow_expiry/` y en la raíz, los `.v1.0` del PayloadAnalyzer, y un único envoltorio de corrida del lab en vez
   de las tres copias del esqueleto de `d302_mitigacion_e2e.sh`).
3. **REA**, al final.

En ramas propias, más adelante: DEBT-SNIFFER-LENHIST-UNBOUNDED-001 (vector de agotamiento de memoria y coste dominante
por evento), barrido de `idle_timeout_s`/`active_timeout_s` junto a DEBT-DDOS-V2-LONG-ATTACK-001,
DEBT-DDOS-V2-ETAPA2-FP-BENIGNOS-001 (la etapa 2 da p1 > 0,5 a tráfico legítimo; solo la etapa 1 lo frena) y
DEBT-SNIFFER-PAYLOAD-ANALYZER-001.

## Instrumentos de DAY309 (`scripts/flow_expiry/`)

- `d309_corrida_e2e.sh NOMBRE bateria FAM PPS | benigna` y `d309_hueco_e2e.sh NOMBRE` (Mac, raíz del repo): corrida del
  lab con el escritor del dataset encendido solo durante la prueba y trap que restaura JSON, receptor TCP, pipeline y
  relojes. Se niegan a escribir en un directorio de corrida que ya existe. Para usarlos igual en `main` y en una rama,
  se copian a `logs/lab/dayNNN/tools/` (ignorado por git).
- `d309_bateria_analisis.py`, `d309_hueco_analisis.py` y `d309_comparar.py`: análisis contra la predicción y
  comparación antes/después.
- `d309_p1_filas.cpp`: recalcula la etapa 2 de ddos_v2 fila a fila sobre el dataset con el mismo bosque del ml-detector
  (paridad con sklearn comprobada). Compilar en el defender:
  `g++ -std=c++20 -O2 -Wall -Wextra -Werror -I/vagrant/ml-detector/include /vagrant/scripts/flow_expiry/d309_p1_filas.cpp -o /tmp/d309_p1`
- El "antes" de una rama es `main`: `git switch --detach <hash>`, `make pipeline-build PROFILE=production`, medir,
  volver a la rama y recompilar (las rutas del Makefile están fijas en `/vagrant`).

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR, y si una corrida falla no se sigue
con el paso siguiente. Antes y después en cada paso. Comandos exactos y completos, en orden, diciendo dónde se ejecuta
cada uno (Mac / defender / client), con la salida a fichero + `; cat`. Ficheros generados como descarga con sha256 (se
guardan desde `~/Downloads` con `mv`). Parcheadores que validen TODO antes de escribir NADA (sha256 de partida y de
llegada, anclas únicas, "ya aplicado", `--check`/`--apply`), probados por Claude en una copia desechable antes de
entregarlos; los parcheadores de un solo uso no se commitean, los instrumentos de medida sí. `git grep`, nunca
`grep -rn .`; inventarios sin truncar, volcados a fichero y contados. awk con `LC_ALL=C`. El JSON es la ley: se lee
siempre; si un campo falta o está mal formado, defecto (igual al del JSON) + aviso, y el log dice por cada campo el
valor y si sale del JSON o del defecto. Leer el fichero entero antes de parchear. Compilar siempre el pipeline completo
en producción (`make pipeline-build PROFILE=production`); diagnósticos con `grep -E ':[0-9]+:[0-9]+: (warning|error):'`;
pruebas con `make test-components PROFILE=production` comprobando las cinco líneas de resumen. Las tareas del Makefile
que no estén duplicadas se quedan. No se mantiene código deprecado: se borra. Las secciones de un documento escritas
antes de medir no se reescriben: el resultado va aparte.

## Lecciones de DAY309

- **Antes de predecir lo que mide un test, leer el código que prueba**, no solo el test.
- **Un inventario se saca contra el fichero**, no se hereda de la lista de una deuda (eran 5 tests sin registrar, no 3).
- **`pgrep -f` / `pkill -f` se encuentran a sí mismos** cuando su línea de comandos contiene el patrón: un servicio se
  vigila por su puerto y se para por su PID.
- **Un comprobador se lee por su texto, no por su código de salida**: un fallo no capturado de Python sale con rc 1.
- **Un criterio relativo no sirve con base 0**: para positivos aislados se predice una cuenta absoluta.
- **Un análisis que agrupa por origen filtra también por protocolo** (el ping de fondo de "esperar ESTABLE" sale de .50).
- **Un `tail` corto puede cortar justo lo que importa**: el análisis va a fichero y se lee entero.
- **Una diferencia de decisiones se investiga con hipótesis escritas antes de mirar** y un instrumento que reproduzca
  la decisión fila a fila; así se separó "efecto de la rama" de "etapa 1 en el borde de K".
