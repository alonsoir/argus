# Prompt de continuidad — DAY315 (tras DAY314, domingo 2026-11-01)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama
`feat/etcd-mtls-vault`. Responde siempre en español. Lee `docs/ml-heads/day312_diseno.md` (diseño de 4b y las
secciones «Resultados DAY313» y «Resultados DAY314») y el final de `docs/BACKLOG.md` (sección DAY312–314).

## Hecho y commiteado

| commit | qué |
|---|---|
| f4658796 | 4b.2: HTTPS + mTLS, autorización por (OU, CN), `tls.modo` mtls\|http, registro y latido en proceso |
| a29942fc | 4b.3: registro en el etcd real (gRPC + TLS); muerto se marca y no se borra; etcd caído = copia y escrituras 503 |
| **0ddfe530** | **4b.4: claves HMAC en Vault** (kv v2 con `cas_required`), ventana de dos, CAS; Vault caído = copia, sin copia 503 |

Medido DAY314 en el laboratorio, todo a la primera: ctest 9/23/13/**7**/82; `d313_registro_medir.sh` 28/28;
`d314_claves_medir.sh` 29/29; VM etcd rehecha (`vagrant destroy -f etcd && vagrant up etcd`) con la sonda
`✅ argus-hmac/ con cas_required=true`; despliegue PASA. Defender en modo memoria: `[ETCD-CLAVES-MEMORIA]`, ninguna
línea `ETCD-VAULT`, `[BRONCE-CLAVE]` con huella.

4b.4 en una línea: bloque `almacen_claves` del JSON (`vault_addrs` y certificados SIN defecto: ausentes, mal formados o
ilegibles = `[ETCD-VAULT-FATAL]`, no arranca); cada dirección con reintentos y espera creciente, luego la siguiente;
agotada la lista, `[ETCD-VAULT-NO-DISPONIBLE]` con el error de cada una y sondeo cada `sondeo_s`. `<CN>/<huella8>`
inmutable con CAS 0; `<CN>/ventana` con CAS = versión. Enfriamiento desde la creación de la activa (guardada en Vault).

## Decisiones de Alonso DAY314

- V1 cliente de Vault propio (httplib); V2 `cas_required` en el montaje; V3 defender en modo memoria hasta el paso 6;
  V4 buscar claves antiguas por huella fuera (va con DEBT-BRONZE-KEY-ID-001).
- Direcciones remotas sin defecto: solo en dev se puede suponer algo en localhost.
- `almacen.endpoints` y `almacen.prefijo` los rellena **Jenkins/Ansible desde el inventario** del entorno: dev (lab, un
  miembro elegido a mano) o preproducción/producción (lista completa de miembros del clúster del despliegue y su
  prefijo). La lista lleva TODOS los miembros: el líder lo elige Raft, nunca Jenkins; cualquier miembro reenvía las
  escrituras al líder. Prefijo por despliegue (p. ej. `/argus/<hospital>/<planta>/`): si dos plantas comparten clúster
  sin prefijo propio, sus registros se pisarían en silencio (los CN son los mismos).
- Un clúster etcd por despliegue (al menos por hospital); el admin decide en la plantilla si dos plantas comparten.
- Marcador de despliegue en etcd: DESCARTADO («menos es más»). Control fuerte futuro: una CA por despliegue.
- Arrancar sin etcd-server: sigue siendo un dilema («arrancar desprotegido es muy peligroso si un atacante ha entrado
  en la DMZ»). Medido: el cifrado ZMQ sale de `seed.bin` local, no de Vault ni del etcd-server. Pregunta para el PR2.

## Medido DAY314: el camino Ansible/Jenkins NO funciona (DEBT-ANSIBLE-DEPLOY-CONFIGS-001)

- Defender: ansible-core 2.14.18, Jenkins `active`. `ansible-playbook -i ansible/inventory/dev.yml
  ansible/playbooks/deploy_configs.yml --check --diff` → FALLA: `'argus_config_base' is undefined`.
- Causa (reproducida con 2.14.18 en una copia): Ansible solo carga `group_vars/` junto al inventario o junto al
  playbook; el repo las tiene en `ansible/group_vars/`. Con ellas en `ansible/inventory/group_vars/`, vale `/vagrant`.
  `dev.yml`/`prod.yml` son copias exactas de `argus_dev.yml`/`argus_prod.yml` y no existe grupo `dev` ni `prod`.
- PELIGRO medido: con las variables arregladas, las plantillas de DAY161 sobrescriben los JSON: `sniffer.json` -502/+8
  de 561 líneas, `ml_detector_config.json` -371/+9 de 423; y en dev `argus_config_base` = `/vagrant`, o sea, los JSON
  DEL REPO. Hoy no rompe nada solo porque falla antes de escribir.

## Plan DAY315 (aprobado por Alonso)

1. **Borrar** `ansible/templates/sniffer.json.j2`, `ansible/templates/ml_detector_config.json.j2`, sus tareas en
   `deploy_configs.yml` y los duplicados `ansible/group_vars/dev.yml` y `prod.yml`; **después** mover `group_vars`
   junto al inventario. En ese orden, para que nunca pueda correr la versión que destruye los JSON.
2. **Configuración del etcd-server por entorno**: una tarea que lee el JSON del repo y sustituye SOLO
   `almacen.endpoints` y `almacen.prefijo` con variables del inventario (nombres propuestos: `etcd_almacen_endpoints`,
   `argus_prefijo`; ojo: `etcd_endpoints` ya existe y es otra cosa, componentes → etcd-server en 2379), escribe en
   `/etc/ml-defender/etcd-server/etcd-server.json` de la VM etcd (nunca en `/vagrant`) y comprueba `--check-config`
   antes de darlo por desplegado.
   - dev: un target del Makefile la lanza con el inventario dev (lab: `["https://127.0.0.1:2381"]`, elegido a mano);
     la VM etcd entra en `ansible/inventory/dev.yml`; `d313_es_vm.sh` y el despliegue pasan a leer ese JSON.
   - pseudo-distribuido: Jenkins con el inventario de preproducción o producción y su lista y prefijo. Hoy no existe
     inventario de preproducción: crearlo.
3. **Código**: `almacen.endpoints` en modo etcd SIN defecto → `[ETCD-ALMACEN-FATAL]` y no arranca (como `vault_addrs`).
   Tests como los de `almacen_claves`; `--check-config` lo cuenta.
- Antes de entregar: Ansible 2.14.18 contra copias aquí y el banco bookworm (GCC 12, production) para el código.
- Predicciones a escribir antes de medir: ctest 9/23/13/7/82 (el test del almacén crece, no aparece uno nuevo),
  `d313_registro_medir.sh` 28/28 y `d314_claves_medir.sh` 29/29 con el JSON generado.

## Deuda (punto 4, no para mañana)

- DEBT-CONFIG-JINJA2-PIPELINE-001: el mismo patrón («JSON del repo + campos sustituidos desde el inventario», sin
  plantillas completas que se desfasan) para sniffer y ml-detector.

## Pendientes anotados

- DEBT-ETCD-SERVER-LOG-TIMESTAMP-001: el log del etcd-server no lleva hora (143 `cout/cerr`); parcheador aparte.
- `make up` no levanta la VM etcd: añadirla antes del paso 8. Comprobar `vagrant status etcd` al empezar.
- Fijar cpp-httplib en `v0.63.0` en el Vagrantfile (hoy se clona sin etiqueta).
- `test_autonomy_integration`: falló una vez en el banco DAY313, no se repitió.
- `scripts/timebase/__pycache__/` en el .gitignore (DEBT-REPO-RESIDUOS-001).
- Siguientes de 4b: 4b.6 (B4 `/secrets/firewall-acl-agent`, variantes muertas de etcd-client), paso 5 (libetcd_client
  con TLS y lista de endpoints: hoy sniffer, ml-detector y firewall solo usan `endpoints[0]`), paso 6 (Vault y
  etcd-server fuera del defender; borrar `tls.modo=http` y los modos memoria), 7, 8 (EMECAS+++).

## Reglas

Medir, no votar; predicción escrita antes; si algo no da lo esperado, parar. Todo lo que se compile, probarlo antes en
bookworm con las opciones de production, y cada instrumento al menos dos veces seguidas. Ficheros entregados con su
sha256. Comandos exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd con
`vagrant ssh etcd -c`; `bookworm` es el defender). Desde zsh, nada de `ssh -F <(…)`: `mktemp`. El repo es de solo
lectura para Claude.
