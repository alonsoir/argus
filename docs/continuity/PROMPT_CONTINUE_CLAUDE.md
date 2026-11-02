# Prompt de continuidad — DAY316 (tras DAY315, lunes 2026-11-02)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama
`feat/etcd-mtls-vault`. Responde siempre en español. Lee `docs/ml-heads/day312_diseno.md` (diseño de 4b y las
secciones de resultados DAY313 y DAY314) y el final de `docs/BACKLOG.md` (sección DAY312–314). DAY315 todavía NO está
documentado ahí: está en este prompt.

## Hecho y commiteado DAY315 (todo medido en el laboratorio, todo a la primera salvo lo indicado)

| commit | qué |
|---|---|
| (DAY315, antes de 2a) | paso 1: fuera las plantillas Jinja de sniffer/ml-detector y los group_vars duplicados; group_vars junto al inventario |
| 58cb72ac | pasos 2a–2c de DEBT-ANSIBLE-DEPLOY-CONFIGS-001 (`[DEPLOY-SSH-D315]`, `[ETCD-CONFIG-ENTORNO-D315]`, `[INVENTARIO-FUERA-D315]`) |
| 23c2e4f8 | paso 3: campos del almacén fatales en modo etcd (`[ETCD-ALMACEN-FATAL-D315]`) |
| 68ebbdaa | 4b.6: `/register` con el CN completo, fuera `crypto_token` y las variantes muertas de etcd-client (`[ETCD-B4-D315]`) |

Medido al final: ctest 9/23/13/7/82; `d313_registro_medir.sh` 28/28; `d314_claves_medir.sh` 29/29;
`d315_paso3_medir.sh` 15/15 (x2); `d315_b4_medir.sh` 10/10 (x2); `d312_etcd_vm_deploy.sh` PASA (binario `6d837186`);
`make deploy-configs` dev `etcd ok=7 changed=0`; JSON desplegado en la VM etcd = `etcd-server.etcd-vm.json` del repo
(sha256 `3fedf9ad…`). En el defender el firewall pasó de `key_path=/secrets/firewall` a `/secrets/firewall-acl-agent`.

### Qué hace cada parte

- **Paso 1**: `deploy_configs.yml` conserva el nombre (Makefile y Jenkins lo llaman); variables huérfanas borradas.
  Medido antes: `make deploy-configs` SÍ cargaba variables (`-e @group_vars`) y habría sobrescrito los JSON del repo.
- **2a** clave de despliegue: provisioner `deploy-key` en el defender (`/root/.ssh/argus_deploy_ed25519`, Jenkins es
  root), `deploy-access` en la VM etcd (usuario `argus-deploy`, sudo sin contraseña SOLO lab, huella publicada en
  `/vagrant/dist/deploy/known_hosts_etcd`). **Cazado**: `ansible.cfg` lleva `host_key_checking = False` y Ansible
  antepone `StrictHostKeyChecking=no`: con huella falsa conectaba igual. Arreglo: `ansible_host_key_checking: true`.
- **2b**: play sobre `etcd_servers`: JSON del repo + `almacen.endpoints`/`almacen.prefijo` del inventario
  (`etcd_almacen_endpoints`, `argus_prefijo`, sin defecto), escrito en `/etc/ml-defender/etcd-server/etcd-server.json`
  con `validate: etcd-server --check-config` y `follow: false` (el destino era un enlace a un JSON del repo). `d312` ya
  no copia `etcd-server.json`; `d313_es_vm.sh` lee por defecto el desplegado.
- **2c**: inventarios reales FUERA del repo (es público); `ansible/inventory/ejemplo-preprod/` con RFC 5737; fuera
  `prod.yml`; `make deploy-configs-prod INVENTARIO=<ruta>` obligatorio; `ARGUS_INVENTARIO` obligatorio en main
  (Jenkinsfile.prod); un inventario sin `etcd_servers` falla con `[ETCD-CONFIG-ENTORNO]`; `d312` con
  `DPkg::Lock::Timeout=600` (medido: `unattended-upgrades` tenía dpkg tras arrancar la VM).
- **Paso 3**: en modo etcd, `endpoints`, `prefijo`, `ca_file`, `cert_file`, `key_file` ausentes o mal formados (y
  endpoints repetidos) = `[ETCD-ALMACEN-FATAL]`, no arranca; `--check-config` imprime `almacen_fatales=N`. En modo
  memoria solo avisa. Arranque sin endpoints medido: se niega en 0,04 s.
- **4b.6/B4**: antes `/register` cortaba en el primer guion: `firewall-acl-agent` → `/secrets/firewall` → 403 con mTLS
  (sin clave HMAC para su CSV). Ahora `/secrets/<CN>` y `/config/<CN>`. `crypto_token` fuera (no existe ruta `/crypto`).

## Decisiones de Alonso DAY315

- Playbook con el mismo nombre; variables huérfanas borradas; clave propia de despliegue (modelo producción);
  `etcd-server.json` fuera del tar; inventarios fuera del repo con ejemplo dentro; inventario vacío = fallo.
- Fatales del almacén: endpoints, prefijo y las tres rutas; endpoints sin repetir (como `vault_addrs`).
- `crypto_token` fuera de los dos lados. **HttpEtcdRegistrar y CryptoEpochCoordinator (common/, ADR-045)**: ningún
  binario los usa y `/v1/epoch` no tiene consumidor; **se decide en el paso 5**.
- **DEBT-PREPROD-LAB-001** (nueva, prueba FINAL): preproducción de lab con objetivo Alpine diminuto (128–256 MB),
  client = atacante, DDoS y ransomware SIMULADO (Atomic Red Team / mitre-start), solo funcional (no capacidad: Mac 2019).
  Solo cuando todas las cabezas estén certificadas (hoy solo DDoS). Antes, medir RAM. Después del paso 6.
- Commits: cada uno marca con precisión lo que hace (separar por cambio lógico).

## Plan DAY316

1. **Documentar DAY315** (parcheador de docs, commit aparte): sección «Resultados DAY315» en `day312_diseno.md`
   (sin reescribir lo anterior) y sección DAY315 en el BACKLOG: cerradas DEBT-ANSIBLE-DEPLOY-CONFIGS-001 y
   DEBT-ETCD-CLIENT-DEAD-VARIANTS-001; nueva DEBT-PREPROD-LAB-001; medido que **Jenkins NO puede hacer preproducción**
   (Jenkinsfile.dev: «Build .deb» y «Deploy Vagrant Test» son eco de DEBT-PACKAGE-DEB-001/DEBT-DEPLOY-VAGRANT-001;
   Jenkinsfile.prod pide un agente `argus-server` que no existe y lanza `vagrant up`; solo el etcd-server tiene
   despliegue de binarios, `d312`, desde el Mac). Pendientes de abajo.
2. **Paso 5**: libetcd_client con TLS y lista de endpoints para sniffer, ml-detector y firewall (hoy solo usan
   `endpoints[0]`). Empezar MIDIENDO qué cliente usa cada uno (sniffer y ml-detector tienen su propio `etcd_client.cpp`;
   el firewall usa la librería `etcd-client`). Dentro del paso 5: sus llamadas a `get_encryption_seed()` contra `/seed`
   (borrada en 4b.2), los `crypto_token_path` de sus JSON, y la decisión sobre el ADR-045.

## Pendientes anotados

- RBAC de etcd por prefijo en producción: en el lab el rol del etcd-server cubre `readwrite /argus/`; con prefijos por
  despliegue (`/argus/<hospital>/<planta>/`) el rol tiene que cubrirlos.
- `d312`: 25 paquetes Debian hoy frente a 26 medidos DAY314; sin explicar.
- DEBT-REPO-RESIDUOS-001: 9 `*.backup*` ignorados en `etcd-client/` y `etcd-server/` (engañaron a un `grep -r` del
  parcheador de 4b.6: usar siempre `git grep`); binario `firewall-acl-agent/fuzz/fuzz_validate_chain` trackeado;
  `scripts/timebase/__pycache__/`.
- `make up` no levanta la VM etcd (añadirla antes del paso 8); tras parar el Mac la VM queda `aborted`: `vagrant up etcd`
  (etcd y Vault vuelven solos; `argus-vault-unseal` desella). Para mirar Vault hace falta `sudo` y certificado de cliente.
- DEBT-ETCD-SERVER-LOG-TIMESTAMP-001, cpp-httplib sin fijar a `v0.63.0` en el Vagrantfile, `test_autonomy_integration`
  (falló una vez DAY313), DEBT-CONFIG-JINJA2-PIPELINE-001 (mismo patrón para sniffer y ml-detector).
- Siguientes de DEBT-ETCD-HA-TLS-RAFT-001: paso 5, paso 6 (Vault y etcd-server fuera del defender; borrar `tls.modo=http`
  y los modos memoria), 7, 8 (EMECAS+++).

## Reglas

Medir, no votar; predicción escrita antes; si algo no da lo esperado, parar. Todo lo que se compile, probarlo antes en
el banco con las opciones de production (g++-12, `-O3 -march=native -DNDEBUG -flto`), y cada instrumento al menos dos
veces seguidas y también contra el comportamiento viejo (tiene que fallar). Ficheros entregados con su sha256 y como
bloque `cat > f <<'EOF'`. Comandos exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM
etcd con `vagrant ssh etcd -c`). Búsquedas con `git grep`, nunca `grep -r`. El repo es de solo lectura para Claude.
