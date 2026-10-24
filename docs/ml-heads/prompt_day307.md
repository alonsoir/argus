# Prompt de continuidad DAY307 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY305-DAY306) para crear el contexto. Base en el repo:
`docs/ml-heads/prompt_day307.md` (este), `docs/ml-heads/day306_retirar_ddos_v1.md`, `docs/BACKLOG.md`
(sección "Cierre DAY306").

## Estado al cerrar DAY306 (24-oct-2026)

- Rama `feat/ddos-v1-retire` (5 commits: `349a3a63`, `1195f91a`, `dfa5e0b1`, `76cecd17` y el de documentación).
  DEBT-DDOS-V1-RETIRE-001 cerrada en código: la cabeza DDoS v1 ya no existe en ml-detector, sniffer, proto (campos
  2, 3, 4, 6, 8, 9 y 10 reservados), configuración ni `ml-training`. Regresión ddos_v2 PASA en tres corridas.
- Pendiente: EMECAS+++ `PROFILE=production` desde cero, PR contra main y, tras el merge, etiqueta
  `pre-release-ddos-v1-retired-0.0.7`.
- Erratum conocido: el commit `dfa5e0b1` ("3/5") lleva también los 40 borrados; el `76cecd17` ("4/5") solo Makefile
  y `.gitignore`. Va explicado en la PR. La historia no se reescribe.

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR. Comandos exactos y completos,
en orden, diciendo dónde se ejecuta cada uno (Mac / defender / client), con la salida redirigida a fichero + `; cat`.
Ficheros generados como descarga con sha256. Parcheadores que validen TODO antes de escribir NADA (sha256 de cada
fichero de partida, anclas únicas, sha256 de los bloques que se borran, estado "ya aplicado", `--check`/`--apply`).
`git grep`, nunca `grep -rn .` en la raíz. awk con `LC_ALL=C`. En el Mac, `cat -vet` (no `cat -A`). El JSON es la
ley; ningún campo se lee en silencio. Compilar siempre en producción y el pipeline completo
(`make pipeline-build PROFILE=production`, y `make tools-build PROFILE=production` si se tocan herramientas).
Diagnósticos: `grep -E ':[0-9]+:[0-9]+: (warning|error):'`. Pruebas: `make test-components PROFILE=production`.
E2E: `make lab-e2e-protegidos LAB_E2E_DIA=dayNNN` (formato estricto dayNNN; si el directorio del día ya existe,
renombrarlo antes) o `make lab-e2e` (los cinco). `vagrant up` sin nombre solo levanta el defender:
`vagrant up client` y después `make lab-clock-step`. No se mantiene código deprecado: se borra.

## Lecciones de DAY306

- **Una regresión de replay se predice como rango, no como identidad.** `lab-e2e-protegidos` varía ±25 eventos entre
  corridas: FIN en [10 741, 10 787], alertas de .61 en [5369, 5393], identidad exacta.
- **`git rm` mete los borrados en el índice al momento.** Va justo antes del commit que debe llevarlos.
- **Leer el fichero entero antes de parchear.** Los dos sitios que habrían tumbado el ml-detector al quitar
  `ml.level2.ddos` (`config_loader` y `etcd_client`) no salían en los conteos; salieron leyendo los ficheros.
- **Inventario primero, por clase de fichero y con la lista de candidatos medida contra el paper y el código vivo.**

## Orden decidido por Alonso

1. **EMECAS+++ y merge de `feat/ddos-v1-retire`** (si no se cerró en DAY306).
2. **Caducidad de flujos** (DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001). Medir primero la RAM
   por flujo con la tabla llena, y la batería de la etapa 2 antes y después.
3. **Rama RAG Logger del ml-detector** (DEBT-RAG-LOGGER-BRANCH-001), con DEBT-DOCS-CSV-SCHEMA-V1-001.
4. **Residuos del repo** (DEBT-REPO-RESIDUOS-001, ampliada DAY305 y DAY306).
5. **REA, al final.**

Más adelante, en rama propia: DEBT-PROTO-CONTRACTS-SPLIT-001 (contratos protobuf sniffer→ml-detector y
ml-detector→firewall). Pendiente sin bloquear: DEBT-DDOS-V2-PINNED-ENV-001 y la medida de herramienta de
DEBT-ETCD-REMOTE-ADMIN-001.
