# DAY312 — Diseño del PR1 de DEBT-ETCD-HA-TLS-RAFT-001 (etcd-server en un nodo, HTTPS + mTLS, claves en Vault)

Base: `main` `cabac77` (merge PR #152, `pre-release-rag-logger-retire-0.0.9`). Inventario previo:
`day312_inventario_etcd.md`. Este documento se escribe ANTES de medir; los resultados van en secciones aparte.

## 1. Decisiones de Alonso (DAY312)

- **D1 = A.** El etcd real como almacén (Raft y TLS nativos) y nuestro etcd-server como fachada HTTPS sin estado
  propio, hablando con etcd por etcd-cpp-apiv3. Las claves HMAC no van a etcd: van a **Vault**, y el etcd-server las
  recupera de Vault cuando hacen falta.
- **D2.** mTLS: un certificado de cliente por componente; CA generada en el portátil, Jenkins orquesta y verifica
  (igual que la semilla de ChaCha20). Autorización por ruta según la identidad del certificado.
- **D3.** PR1 = un nodo (este documento). PR2 = HA con Raft. El re-registro tras 404 y el comportamiento idéntico de los
  tres componentes van en la rama siguiente (DEBT-FW-HMAC-KEY-ALARM-001).
- **D4.** El etcd-server sale del defender. HA real fuera del defender; el reparto de nodos del PR2 se decide con la
  RAM medida (ver §6).
- **V1.** Vault en modo servidor ya, con persistencia. Desellado **c** (clave de desellado en disco de la propia VM):
  solo para el laboratorio, aRGus sigue sin estar sellado para producción. En producción se decidirá entre a (manual,
  Shamir) y b (auto-unseal).
- **V2.** Vault sale del defender y se va con el etcd-server a la VM nueva.
- **V3.** En este PR solo las claves HMAC pasan al Vault en modo servidor. El resto de secretos (`secret/argus/crypto`,
  `vendor-key`, token enterprise) en otro PR (deuda nueva DEBT-VAULT-REST-SECRETS-001).

## 2. Medidas ya hechas (antes)

- **M0 (DAY312, Mac → client).** Predicción: rc 0, HTTP 200, `initialized:true`, `sealed:false`.
  Resultado: `hostname` = ml-client; `http=200`; `rc=0`; `initialized:true`, `sealed:false`, `version:2.2.1`.
  **PASA.** Vault dev del defender se alcanza sin token desde la posición del atacante (192.168.100.1:8200), igual que
  el 2379 (DAY311). Nueva deuda: DEBT-VAULT-DEV-EXPOSED-001 (se cierra con este PR al sacar Vault del defender).
- DAY311 (instrumento `scripts/bronze_key/d311_reinicio_etcd.sh`): tras reiniciar el etcd-server, claves nuevas (bronce
  anterior no re-verificable), registro vacío, latidos 404 invisibles, log 200 frente a 404. Es el "antes" del paso 7.

## 3. Arquitectura del PR1

```
 defender (192.168.100.1)                          VM nueva "etcd" (propuesta 192.168.100.20)
 ┌───────────────────────────┐   HTTPS + mTLS     ┌────────────────────────────────────────────┐
 │ sniffer / ml-detector /   │ ─────────────────► │ etcd-server (fachada, :2379)               │
 │ firewall (libetcd_client) │                    │   ├─ registro/config/época ─► etcd :2381   │
 └───────────────────────────┘                    │   │        (TLS, solo 127.0.0.1)           │
 Mac: mitre/ctu/custom_start                      │   └─ claves HMAC ─► Vault :8200            │
   (curl con cert de admin)                       │            (TLS, auth por certificado,     │
                                                  │             almacenamiento raft, 1 nodo)   │
                                                  │ nftables: 2379 solo desde .1 .10 .11 .12   │
                                                  └────────────────────────────────────────────┘
```

- etcd y Vault solo los usa el etcd-server: escuchan en 127.0.0.1 de la VM nueva. Nada del pipeline les habla
  directamente.
- Puerto del etcd real distinto de 2379 (que sigue siendo el de la fachada, para no tocar los JSON de los componentes
  más que en el host): propuesta 2381 cliente / 2382 peer. En el JSON del etcd-server.
- **Claves HMAC en Vault KV v2**, una entrada inmutable por clave (`argus-hmac/<componente>/<huella8>`) más un
  puntero (`argus-hmac/<componente>/ventana` = {activa, anterior, expira_anterior}). Nunca se borra una clave: el
  grafo debe poder re-verificarse años después (DAY310). Esto deja preparado DEBT-BRONZE-KEY-ID-001 sin hacerlo aquí.
- Autorización por ruta (identidad = CN del certificado de cliente):

  | Ruta | Quién |
  |---|---|
  | POST /register, /unregister, /v1/heartbeat/{c}, PUT /v1/config/{c}, GET/PUT /config/{c} | solo el CN = {c} |
  | GET /secrets/{c}, GET /secrets/valid/{c} | CN = {c}, y el conversor/verificador (CN propio) en lectura |
  | POST /secrets/rotate/{c}, PUT /v1/epoch, GET /components, /validate, /info | solo CN admin |
  | GET /health | cualquiera con certificado de la CA |
  | GET /seed, GET /secrets/keys | se borran (muertas: ver inventario) |

  Sin certificado válido: el TLS no llega a establecerse. Con certificado válido y ruta no permitida: 403 y línea
  `[ETCD-AUTHZ-DENEGADO]` con CN, método y ruta.
- Fuera en este PR (código muerto o peligroso): `auto_restart` + `system()`, `get_encryption_seed/key`,
  `rotate_encryption_key`, `/seed`, `/secrets/keys`, el `HttpEtcdRegistrar` del etcd-server hacia sí mismo si el
  registro deja de hacer falta (a comprobar), `etcd_client_base.cpp`, `etcd_client_manual.cpp`, `*.day54_*`
  (DEBT-ETCD-CLIENT-DEAD-VARIANTS-001), etcd-cpp-api opcional del ml-detector (ningún fuente lo usa).
- El JSON es la ley: `server.*`, `secrets.*`, `heartbeat.*`, rutas de certificados, direcciones de etcd y Vault, todo
  leído por campo con `[CONFIG]`/`[CONFIG-DEFAULT]` (cierra DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001). Campos que hoy
  no hacen nada y no se implementan aquí (`auto_restart`, `worker_threads` si no se cablea): `[CONFIG-OBSOLETO]` y
  fuera del JSON.
- Versiones fijadas: Vault (hoy sin fijar, se instaló 2.2.1), etcd, cpp-httplib (hoy `git clone` sin etiqueta).
  `CPPHTTPLIB_OPENSSL_SUPPORT` igual en todo lo que enlace `libetcd_client.so` (riesgo ODR, ver inventario §3.10).
- Vault no responde o sellado: el etcd-server sigue entregando la clave vigente que tenga en memoria, marca
  `[ETCD-VAULT-NO-DISPONIBLE]` periódica (intervalo en el JSON) y no rota. Sin clave en memoria (arranque con Vault
  caído): no entrega clave; el ml-detector ya da `[BRONCE-SIN-CLAVE]` y el firewall sigue actuando (D3 de DAY310).

## 4. Pasos, con su predicción

Cada paso: antes/después, compilación completa en producción, `make test-components PROFILE=production` con las
cinco líneas, y PARAR si algo no da lo predicho.

| # | Paso | Predicción escrita antes |
|---|---|---|
| 0 | Material: CA + certificados (etcd-server, sniffer, ml-detector, firewall, conversor, admin), script en el Mac, claves privadas fuera de git | `openssl verify -CAfile ca.pem` OK en los 6; ningún `.key` aparece en `git status` |
| 1 | VM "etcd" en el Vagrantfile (bookworm 12.20240905.1, RAM según §6), nftables | `vagrant up etcd` rc 0; desde el client, `curl` a :2379 → conexión rechazada o timeout; desde el defender, abierto |
| 2 | Vault en modo servidor en la VM: listener TLS, almacenamiento raft (1 nodo), init 1/1, desellado c por systemd, auth cert, política solo-etcd-server | `vault status` → sealed false tras `vagrant reload etcd` sin intervención; escribir clave → reiniciar Vault → misma huella; desde el client :8200 no alcanzable |
| 3 | etcd 1 nodo en la VM, TLS, solo 127.0.0.1 | `etcdctl endpoint health` (TLS) OK; put/get sobrevive a reinicio de etcd |
| 4 | etcd-server: JSON leído, HTTPS+mTLS, autorización, registro/config/época en etcd, claves en Vault con ventana de dos, log con el estado real, mutex/sin carrera, fuera el código muerto | tests nuevos del etcd-server en verde; sin cert → TLS falla; cert de sniffer pidiendo /secrets/ml-detector → 403; latido de no registrado → log con 404 |
| 5 | libetcd_client con TLS + certificado de cliente; JSON de los componentes apuntando a 192.168.100.20; scripts del lab con cert de admin | pipeline-start: los 3 componentes registrados (GET /components con cert admin → 4 con el etcd-server); ml-detector `[BRONCE-CLAVE]` con huella |
| 6 | Vault y etcd-server fuera del defender | en el defender, nada escucha en 2379 ni 8200 |
| 7 | Repetir el instrumento de reinicio de DAY311 (adaptado a la VM nueva) | tras reiniciar el etcd-server: misma huella de clave, bronce anterior verificable, registro conservado, latidos 200 |
| 8 | EMECAS+++ production | rc 0, 5/5 E2E con PASA, cinco líneas de test-components |

## 5. Preguntas abiertas para Alonso

- P1. Nombre e IP de la VM nueva (propuesta: `etcd`, 192.168.100.20, libre en el Vagrantfile).
- P2. Dónde viven en el Mac la CA y las claves privadas del lab (propuesta: directorio fuera del repo, p. ej.
  `~/argus-pki/`, copiado a las VMs en el aprovisionamiento) y si Jenkins ya entra en este PR o en el de producción.
- P3. ¿El conversor bronce→oro y la verificación del grafo entran como CN propio con lectura de `/secrets/valid/{c}`?

## 6. RAM (para decidir el reparto del PR2)

Hoy, con todo levantado: defender 8192 + client 1024 + suricata 2048 + zeek 2048 + wazuh 4096 = 17408 MB asignados.
La VM nueva del PR1 suma lo que se mida (propuesta inicial 1024 MB). Para el PR2 hay dos caminos, a decidir con la RAM
del Mac medida:
- tres nodos en VMs pequeñas (si bookworm + etcd + Vault caben en ~512 MB; medir);
- tres nodos en una sola VM, cada uno en su espacio de red (`ip netns`): Raft, caída de nodo y particiones medibles
  de verdad; la caída de la VM entera no.

## Resultados DAY312 (medidos; se añaden aparte, sin reescribir las secciones de diseño escritas antes de medir)

Rama `feat/etcd-mtls-vault` (sobre `main` `cabac77`). Commits: `e7309db2` (Vault dev en loopback + diseño + PKI),
`a3ad992d` (paso 1, VM etcd), `7df8914e` (paso 2, Vault en modo servidor).

### R0. Exposición del Vault dev del defender

- M0 (client → 192.168.100.1:8200/v1/sys/health): predicción 200, `sealed:false`. Resultado: `ml-client`, 200,
  `initialized:true`, `sealed:false`, 2.2.1. **PASA**. El Vault dev se alcanzaba sin token desde la posición del
  atacante, con el token root `argus-dev-token` escrito en el repo público.
- M0-b, ¿algo de fuera del defender usa el 8200? Primera captura (180 s): `syn_total=0`, **no válida**: la ventana se
  cerró antes de que `pipeline-start` llegara al `vault status` (diario: 07:56:41–07:59:41 CET; el arranque terminó
  hacia las 08:00:30). Control positivo (30 s + `vault status`): 1 SYN desde 127.0.0.1, el instrumento ve loopback.
  Repetición (600 s, parada + arranque + ~6 min): 1 SYN, desde 127.0.0.1 (el `vault status` del final). **PASA**:
  0 SYN no-loopback. Además, el etcd-server no habla con Vault en la compilación actual (0 conexiones en su arranque
  ni en su vigilancia cada 5 s). `git grep` coincide: todo lo que usa 127.0.0.1:8200 corre dentro del defender.
- Cambio (camino a, decisión de Alonso): Vault dev solo en 127.0.0.1 (Vagrantfile y Makefile), fuera el
  forwarded_port 8200. Resultado tras `vagrant reload defender`: escucha solo `127.0.0.1:8200`; defender 200; client
  `http=000` rc=7; Mac `http=000` rc=7; pipeline 4/4 RUNNING y `vault: RUNNING [dev]`. **PASA**.
  DEBT-VAULT-DEV-EXPOSED-001 cerrada para el Vault dev; el resto de secretos del Vault dev sigue en el defender
  hasta DEBT-VAULT-REST-SECRETS-001.

### R1. Paso 1, VM etcd

- `vagrant up etcd` rc=0; `etcd-base OK`, hora de 192.168.100.1, nftables `argus_etcd` cargada.
- Primera medida del cortafuegos: defender rc=7 (rechazo), predicho 200. **PARADA**. Hipótesis escritas antes de
  mirar: H1 ventana de 120 s cerrada; H2 servidor de prueba muerto; H3 regla `reject`. Diario: servidor de prueba
  07:54:06–07:56:06 UTC, `status=124` → H1. El rechazo prueba que el paquete del defender sí cruzaba nftables.
- Repetición (600 s): defender `http=200` rc=0; client `http=000` rc=28 (descartado). **PASA**.

### R2. Paso 2, Vault en modo servidor en la VM etcd

- Versión medida en el defender: `2.2.1-1` (predicho). Fijada en `VAULT_INSTALL`, compartido por defender y etcd.
- Primer `vagrant provision etcd`: rc=1 sin ejecutar nada (`File provisioner: The following settings shouldn't
  exist: name`). Corregido (`provision "pki-…", type: "file"`). Segundo: rc=0, Vault 2.2.1 (0e7c41b9, el mismo build
  que el defender) instalado y fijado, inicializado 1/1, root revocado, `sealed=False storage=raft`.
- `d312_vault_medir.sh`: M1-M6 **PASA** (login CN=etcd-server; escribir y releer; borrar 403; fuera de argus-hmac/
  403; certificado de sniffer 400; sin certificado sin TLS, curl rc 55/56; escucha solo 127.0.0.1:8200; unseal.key
  600 root). 8200 de la VM etcd desde defender y client: rc=28.
- Tras `vagrant reload etcd`, sin intervención: desellado, y `argus-hmac/d312/prueba` sigue con `d312abcd`
  (**persiste**). La entrada de prueba no se puede borrar (política): queda como rastro de la medida.
- Defender: `vault-install` → `✅ Vault 2.2.1-1 ya instalado y fijado` (el cambio de sitio no altera nada).
- Residuo anotado: el paquete genera un certificado autofirmado en `/opt/vault/tls` que no se usa.

### Lecciones DAY312

- La predicción del hostname se saca del Vagrantfile: el defender no tiene `vm.hostname` y se llama `bookworm`.
- Un instrumento que puede no ver nada no refuta nada: control positivo antes de interpretar un 0.
- Las ventanas de medida, con margen amplio y la hora UTC en cada línea: 120 s no alcanzan a ritmo humano con
  `vagrant ssh` (~15 s cada uno).
- Un parcheador se prueba sin los ficheros de trabajo de quien lo escribe (uno leía `/home/claude/work/…`).
- Una validación que pasa sobre una entrada vacía no vale: control negativo (nft sobre un fichero vacío daba OK).
- El aprovisionador `file` de Vagrant no admite `name:`; el nombre va como primer argumento con `type: "file"`.
- Un `grep` que busca un secreto lleva el secreto en sus argumentos: no se comprueba así.

## Diseño del paso 4b (código del etcd-server) — DAY312, escrito ANTES de tocar código

Base: rama `feat/etcd-mtls-vault` en `b5227f85` (4a: el etcd-server actual corre en la VM etcd). Lo que sigue es la
propuesta; las decisiones abiertas están en 4b.0 y nada se escribe hasta tenerlas.

### Medido para este diseño

- etcd-cpp-apiv3 v0.15.3 (la que fija el Vagrantfile): `SyncClient(url, ca, cert, privkey, target_name_override)`
  con TLS y certificado de cliente; `url` admite varios endpoints separados por coma (sirve para el PR2). Sus
  dependencias de ejecución son todas paquetes Debian (gRPC 1.51, protobuf 32, cpprest 2.10, abseil): la herramienta
  de despliegue de 4a las resuelve con `dpkg -S` sin cambios.
- La pasarela JSON de etcd 3.6.16 rechaza toda petición con certificado de cliente ("CommonName … will be ignored"):
  con RBAC por CN, el etcd-server habla con etcd solo por gRPC.
- `common/vault_client` es específico de la semilla de familia (token, libcurl, `fetch_seed`): no sirve tal cual
  para KV v2 con auth por certificado.

### 4b.0 Decisiones abiertas para Alonso

- **B1. Cliente de Vault.** (a) clase pequeña nueva en el etcd-server sobre cpp-httplib `SSLClient` (ya enlazado,
  sin dependencias nuevas): login por certificado + KV v2 leer/escribir; (b) extender `common/vault_transport`
  (libcurl) con una interfaz nueva. Propuesta: a.
- **B2. Tabla de autorización por ruta en el JSON** (el JSON es la ley; defectos iguales en el código; cada fila
  registrada en el log al arrancar con `[CONFIG]`/`[CONFIG-DEFAULT]`) frente a fija en el código. Propuesta: JSON.
- **B3. Instancias del registro.** Hoy el nombre con que se registra cada componente está fijo en su `main.cpp`. En
  4b el etcd-server toma la identidad del certificado (CN = instancia, OU = rol) y **rechaza** un registro cuyo nombre
  no coincida con el CN (403). Los componentes no cambian (CN = nombre actual). Propuesta: así.
- **B4. Clave HMAC del firewall** pasa a `/secrets/firewall-acl-agent` (P4). Antes de cambiarlo: `git grep` de
  quién verifica hoy el CSV del firewall con `/secrets/firewall`.

### 4b.1 Configuración: el JSON es la ley

`etcd-server.json` pasa a tener, con rango y formato documentados en el propio JSON (`_doc`), y leído campo a campo:

| Bloque | Campos |
|---|---|
| `server` | `listen_host` (IPv4), `port` (1-65535) |
| `tls` | `ca_file`, `cert_file`, `key_file` (rutas que deben existir) |
| `authz` | tabla ruta → identidades permitidas (CN propio, OU, `admin`) |
| `etcd` | `endpoints` (lista https://…), `ca_file`, `cert_file`, `key_file`, `prefix` (`/argus/`), `timeout_ms` |
| `vault` | `addr`, `ca_file`, `cert_file`, `key_file`, `kv_mount` (`argus-hmac`), `cert_role` (`etcd-server`), `aviso_intervalo_s` |
| `secrets` | los de hoy (`grace_period_seconds`, `rotation_interval_hours`, `default_key_length_bytes`, `min_rotation_interval_seconds`) |
| `heartbeat` | `interval_seconds`, `timeout_multiplier`, `check_interval_seconds` |

Campo ausente o mal formado → defecto (igual al del JSON) + aviso con campo, formato y límites; el log de arranque
recoge la configuración efectiva completa y de dónde sale cada valor. Campos que no hacen nada (`auto_restart.*`,
`security.*`, `server.worker_threads`, `secrets.storage`, `secrets.keys`) → `[CONFIG-OBSOLETO]` y fuera del JSON.
Cierra DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001. `--check-config` local: lee, valida, imprime la configuración
efectiva y sale (rc 0 / 1).

### 4b.2 Arranque

Orden corregido: `/run/argus` antes del `AutonomyPublisher` (medido 4a). Sin Vault ni etcd alcanzables el proceso
arranca igual y sirve lo que tenga (ver 4b.5), con aviso periódico; sin certificados TLS válidos no arranca
(no hay forma segura de servir).

### 4b.3 HTTPS + mTLS y autorización

- `httplib::SSLServer` con la CA del lab y verificación del certificado de cliente obligatoria. Sin certificado
  válido no hay TLS (no llega a ninguna ruta).
- Un único punto de autorización antes del enrutado (`set_pre_routing_handler`): CN y OU del certificado del par →
  tabla `authz`. Denegado → 403 y `[ETCD-AUTHZ-DENEGADO] cn=… ou=… metodo=… ruta=…`.
- Rutas que se borran: `/seed`, `/secrets/keys` (sin uso; medido en el inventario).
- `log_request` registra el estado REAL, después de decidir (DEBT-ETCD-HEARTBEAT-LOG-STATUS-001).

### 4b.4 Registro, configuración y época en etcd

`ComponentRegistry` deja de guardar en un `unordered_map` sin mutex: interfaz `IRegistryStore` con dos
implementaciones, `EtcdRegistryStore` (gRPC, prefijo `/argus/`) y `MemoriaRegistryStore` (solo tests). Claves:
`/argus/registro/<CN>`, `/argus/config/<CN>`, `/argus/latido/<CN>`, `/argus/epoca`. El registro sobrevive a un
reinicio del etcd-server (medido DAY311: hoy vuelve vacío).

### 4b.5 Claves HMAC en Vault (ventana de dos)

- Una entrada inmutable por clave: `argus-hmac/<CN>/<huella8>` = {clave, creada}; un puntero
  `argus-hmac/<CN>/ventana` = {activa, anterior, expira_anterior}. Nunca se borra una clave (la política no lo
  permite: medido M2d).
- Leer-o-crear bajo UN solo bloqueo (la carrera de DAY311: dos primeras peticiones podían crear dos claves).
- Caché en memoria de la ventana. Vault no disponible: se sirve la ventana en caché, `[ETCD-VAULT-NO-DISPONIBLE]`
  cada `aviso_intervalo_s`, no se rota. Sin caché (arranque con Vault caído): no se sirve clave; el ml-detector ya da
  `[BRONCE-SIN-CLAVE]` y el firewall sigue actuando.
- En el log, solo la huella (8 hex del SHA-256), nunca la clave.

### 4b.6 Fuera (código muerto o peligroso)

`auto_restart` + `system("systemctl restart …")`, `get_encryption_seed/key`, `rotate_encryption_key`,
`set_compression_mode/set_encryption_mode` sin uso, el `HttpEtcdRegistrar` del etcd-server hacia sí mismo si deja de
hacer falta (comprobar con `git grep` quién lee `/v1/epoch` aparte de él), `etcd_client_base.cpp`,
`etcd_client_manual.cpp`, `*.day54_*` (DEBT-ETCD-CLIENT-DEAD-VARIANTS-001).

### 4b.7 Pruebas y predicciones

- Tests unitarios nuevos del etcd-server (sin red): lectura del JSON (campo bueno, ausente, mal formado, fuera de
  rango), tabla de autorización, ventana de dos con almacén falso (crear, rotar, expirar, Vault caído). Línea nueva
  en `make test-components PROFILE=production`; las cinco de hoy (9/23/13/3/82) no cambian.
- En la VM etcd (instrumento nuevo `d312_es_medir.sh`): sin certificado → TLS falla; sniffer pide
  `/secrets/ml-detector` → 403; ml-detector pide `/secrets/ml-detector` → 200 y huella; latido de no registrado →
  log con 404; reinicio del etcd-server → misma huella y registro conservado.
- Compilación completa en producción con 0 diagnósticos.

## Resultados DAY313 — paso 4b.2 (medidos; sección aparte, sin reescribir el diseño de 4b escrito antes de medir)

Rama `feat/etcd-mtls-vault` sobre `7a666174`. Parcheador de un solo uso `d313_4b2_parche.py` v2 (sha256
`b12e5e25…e170f`, no se commitea): 11 ficheros. Instrumentos nuevos: `scripts/etcd_ha/d313_es_vm.sh` (arrancar/parar
en la VM etcd, con `--check-config` previo y tiempo de parada) y `scripts/etcd_ha/d313_es_medir.sh` (20 medidas desde
el defender; nunca imprime una clave).

### Decisiones de Alonso (DAY313, antes de escribir código)

- **T1 = modo `http` explícito para la transición.** `tls.modo` en el JSON: `mtls` (defecto) o `http`. El JSON del
  repo (defender, cuyos clientes siguen en HTTP hasta el paso 5) lleva `http` con aviso `[ETCD-TLS-DESACTIVADO]` al
  arrancar y cada `tls.aviso_http_intervalo_s`. La VM etcd usa `etcd-server.etcd-vm.json` (`mtls`, mismo contenido
  salvo `tls.modo`: lo comprueba un test). Un modo ausente o mal escrito va a `mtls`: una errata nunca rebaja a HTTP.
  Con `mtls` y certificados ilegibles o inválidos el proceso no arranca (`[ETCD-TLS-FATAL]`, §4b.2). El modo `http`
  se borra en el paso 6.
- **T3 = registro en proceso.** `git grep`: `HttpEtcdRegistrar` solo lo usaba en producción el propio etcd-server
  contra sí mismo (registro, latido cada 30 s, sondeo de `/v1/epoch` cada 2 s; el callback de época solo escribía en el
  log). Fuera `HttpEtcdRegistrar` y `CryptoEpochCoordinator` del etcd-server (adelanta parte de 4b.6); se registra y
  late directamente en su `ComponentRegistry`. `PUT`/`GET /v1/epoch` siguen como rutas.

### Lo que hace 4b.2

- `httplib::SSLServer` con la CA del lab como CA de cliente (certificado de cliente obligatorio).
- Autorización en `set_pre_routing_handler` con la tabla `authz` del JSON (15 reglas; defecto idéntico en
  `etcd_server_authz.hpp`, comprobado por test): plantillas por segmentos (`/secrets/{c}`, `{c}` = un segmento
  `[a-z0-9-]{1,63}`), `permitir` = `propio` | `ou:<rol>` | `cualquiera`; denegar por defecto; una regla mal formada
  invalida la tabla entera (defecto + aviso de cada error). Identidad: exactamente un CN y un OU con forma de nombre.
- `[ETCD←]` desde `set_logger`, después de responder: status real, CN y OU (DEBT-ETCD-HEARTBEAT-LOG-STATUS-001).
- Servidor como miembro: `stop()` llama a `server_->stop()` (antes `listen()` no volvía nunca).
- Fuera `/seed` y `/secrets/keys` (sin regla: 403 con mTLS, 404 en http). Resumen `[CONFIG-DEFAULT]` con la ruta real
  y el total de todos los bloques. `next_heartbeat_expected` desde `heartbeat.interval_seconds`. JSON de error de
  `PUT /config` bien formado.
- Test nuevo `test_etcd_server_authz` (17 casos; tres mutaciones del código hacen fallar los suyos).

### Medido

- M0 (defender): cpp-httplib **0.63.0** (clonado sin etiqueta). El código se probó con 0.12, 0.18, 0.26, 0.63 y 0.64.
- Primer `pipeline-start` tras el parche: `ETCD-TLS-DESACTIVADO` 0 veces, predicho ≥ 1. **PARADA.** Medido: el binario
  no contenía la cadena (H1) y el JSON no tenía `tls`: el `--apply` no se había ejecutado (`--check`: 11 pendientes).
- Compilación con el parche v1: **FALLA** en `etcd_server_authz.hpp:312:70`, `-Werror=stringop-overflow=` de GCC 12 con
  LTO. **PARADA.** Reproducido en un Debian 12 real (debootstrap; GCC 12.2.0, fmt 9.1, spdlog 1.10, libsodium 1.0.19,
  httplib 0.63.0) con las opciones de production del Makefile; el original compila (control). Causa: falso positivo con
  el temporal `const char* + std::string`; reescrito con dos `+=`. Parcheador v2: acepta la rama limpia o la v1
  aplicada (solo reescribe ese fichero); probado en clones limpios (rama limpia, v1 aplicada, v1 + otro fichero
  alterado → rechaza sin escribir).
- `make pipeline-build PROFILE=production`: compila. `make test-components PROFILE=production`: 9 / 23 / 13 / **5** / 82,
  todo verde (el etcd-server pasa de 4 a 5; la predicción «total 83» era errónea: 82 es otro componente y no cambia).
- Defender en modo `http`: `pipeline-start` 6/6 RUNNING, `/health` 200, 3 líneas `ETCD-TLS-DESACTIVADO`. **PASA.**
- Despliegue: `d312_etcd_vm_deploy.sh` **FALLA** (`vagrant ssh-config`): la VM etcd estaba `aborted`. **PARADA.**
  `VBox.log.1`: abierto 2026-10-30T08:47:32Z, cierre ordenado (`DESTROYING → TERMINATED`) a las 4 h 10 min 30 s =
  12:58Z; `pmset`: el Mac arrancó a las 14:07:25 (13:07Z) con Setup Assistant = reinicio por actualización de macOS. El
  resto de VMs se levantó con `make up`, que no incluye la VM etcd. Tras `vagrant up etcd`: Vault `Sealed false` sin
  intervención, 2379 libre, despliegue `RESULTADO PASA` (6 de 6 ficheros, manifiesto OK, binario `e22cfcc1f31fe7b9`).
- VM etcd con `etcd-server.etcd-vm.json`: `--check-config` OK (`tls.modo=mtls`, 0 ficheros TLS ilegibles), escucha en
  0.0.0.0:2379, 15 reglas, registrado en proceso.
- `d313_es_medir.sh` desde el defender contra `https://192.168.100.20:2379`: **20/20 PASA.**
  - Sin TLS válido no hay respuesta HTTP: sin certificado (rc 56), certificado de otra CA (rc 56), `vault.crt` con solo
    `serverAuth` (rc 56), HTTP en claro (rc 52).
  - admin `/health` y `/components` 200; sniffer `/health` 200; sniffer `/secrets/sniffer` 200 y `/secrets/ml-detector`
    403; latido de ml-detector sin registrar 404; admin `/seed` y `/secrets/keys` 403; sniffer rotar 403 y
    `/components` 403; `/secrets/sniffer%2Fx` y `/secrets/sniffer/` 403; sniffer-2 (OU sniffer) `/secrets/sniffer` 403;
    converter `/secrets/valid/ml-detector` 200 y `/secrets/ml-detector` 403; `/components` incluye `etcd-server`.
- Log de la VM etcd: 9 `[ETCD-AUTHZ-DENEGADO]` (predicho 9); el latido aparece como `status=404 | cn=ml-detector |
  ou=ml-detector`; 0 cadenas de 64 hex. **PASA.**
- Parada: 5,2 s tras SIGTERM, sin SIGKILL. Predicción inicial «< 2 s» **errónea**: el monitor de latidos duerme
  `heartbeat.check_interval_seconds` (10 s) antes de salir; corregida a ≤ 11 s antes de medir en el laboratorio
  (medido en el entorno de prueba 2,3–10,4 s). Se arregla al reescribir `ComponentRegistry` (4b.3).

### Lecciones DAY313

- Probar lo que se va a compilar en el mismo sistema y con las mismas opciones: Debian 12, GCC 12 y production
  (`-O3 -march=native -flto -Werror`). Un GCC 13 sin LTO no ve el falso `-Wstringop-overflow` de GCC 12.
- Un parcheador no se da por aplicado hasta que `--check` diga «ya aplicado (11/11)».
- Etiquetar el sitio de cada comando no basta: `bookworm` es el defender. Para la VM etcd, comandos del Mac con
  `vagrant ssh etcd -c`.
- `ssh -F <(vagrant ssh-config …)` dentro de una tubería falla en zsh interactivo (`/dev/fd/12: Bad file
  descriptor`); en bash, dentro de un script, funciona. En la terminal: fichero con `mktemp` y `rm` al terminar.
- Una VM nueva que no levanta `make up` puede quedarse caída sin que nadie lo vea (reinicio del Mac por actualización).

### Deudas y pendientes nuevos

- Fijar cpp-httplib en `v0.63.0` en el Vagrantfile.
- `make up` debe levantar también la VM etcd (antes del paso 8).
- `test_autonomy_integration` falló una vez en el bookworm de prueba (0,00 s) y no se repitió en 10 vueltas; el
  `LastTest.log` se sobrescribió. Vigilar.
- `tar` desde el Mac: `COPYFILE_DISABLE=1 tar --no-xattrs` (atributos `com.apple.provenance`).

## Resultados DAY314 — 4b.3 medido en el laboratorio y paso 4b.4 (sección aparte, sin reescribir lo anterior)

### 4b.3 en el laboratorio (commit `a29942f`)

- `--check` 16 listos, `--apply`, `--check` ya aplicado. `make pipeline-build PROFILE=production` y
  `make test-components PROFILE=production`: 9 / 23 / 13 / **6** / 82, todo verde (predicho).
- Defender (`almacen.modo=memoria`): `[ETCD-ALMACEN-MEMORIA]` y `[ETCD-REGISTRO] registrado` para sniffer, ml-detector y
  firewall-acl-agent. **PASA.** El log del etcd-server no lleva hora: el grep mezcla arranques (dos `registrado` por
  componente y tres avisos de memoria) y no se puede saber cuál es de este. Deuda nueva
  **DEBT-ETCD-SERVER-LOG-TIMESTAMP-001** (decisión de Alonso: parcheador aparte): 143 `std::cout/cerr` sin hora en
  `src/` e `include/`; pasar a un logger con la hora como primer campo y el patrón en el JSON.
- `d312_etcd_vm_deploy.sh production`: **PASA**, 5 librerías propias (+ `libetcd-cpp-api.so`) y 26 paquetes (gRPC 1.51,
  protobuf 32, cpprest 2.10, abseil), binario `d6a20d782cf750bb`.
- `d313_registro_medir.sh`: **28/28 PASA**. Etcd de vuelta: primer latido 200 en 0,7 s. Parada 0,07–0,12 s.

### Decisiones de Alonso (DAY314, antes de escribir código de 4b.4)

- **V1** cliente de Vault propio en el etcd-server (httplib::SSLClient; `common/vault_client` hace otra cosa: semilla,
  token, solo lectura, curl, y lo usan otros componentes).
- **V2** `cas_required=true` en el montaje `argus-hmac/` además del CAS en el código. La VM etcd se inicializó en DAY312
  sin él y con el root revocado: se rehace (`vagrant destroy -f etcd && vagrant up etcd`); hoy solo guarda
  `argus-hmac/d312/prueba`.
- **V3** `almacen_claves.modo = "memoria"` en el defender hasta el paso 6 (como `almacen.modo` y `tls.modo`).
- **V4** buscar una clave antigua por huella (re-verificar el grafo años después) queda fuera; va con
  DEBT-BRONZE-KEY-ID-001 («es una feature que pedirán los usuarios tras años en producción»).
- **JSON es la ley también para las direcciones**, pero sin defecto: solo en dev se puede suponer algo escuchando en
  localhost. En modo vault, `vault_addrs` (o una ruta de certificado) ausente, mal formada o ilegible =
  `[ETCD-VAULT-FATAL]` y no se arranca (`--check-config` lo detecta antes). Con la configuración bien y Vault sin
  responder: reintentos por dirección con espera creciente, luego la siguiente de la lista, luego aviso claro con el
  error de cada una; el etcd-server arranca (el registro sirve) y sigue sondeando.
- Arrancar sin etcd-server: sigue siendo un dilema para Alonso («arrancar desprotegido es muy peligroso si un atacante ha
  entrado en la DMZ»). Medido en el código: el cifrado ZMQ sale de `seed.bin` local, no de Vault ni del etcd-server; lo
  que depende del etcd-server es el registro y la clave HMAC del bronce (y el conversor, que necesita
  `/secrets/valid`). Pregunta abierta para el PR2; no toca 4b.4.

### Lo que hace 4b.4

- `etcd_server_claves.hpp`: bloque `almacen_claves` del JSON (modo, `vault_addrs` 1–7 sin repetir, `ca_file`,
  `cert_file`, `key_file`, `montaje`, `rol_login`, `timeout_ms`, `reintentos_por_direccion`, `espera_inicial_ms`,
  `espera_max_ms` ≥ inicial, `sondeo_s`, `aviso_intervalo_s`), cada campo con su origen en `[ETCD-CLAVES]`; interfaz
  `ISecretStore` (leer con versión, escribir con CAS; Ok, NoEncontrado, NoDisponible, Conflicto) y `MemoriaSecretStore`.
- `vault_secret_store.cpp`: kv v2 por HTTPS con certificado de cliente; login `auth/cert` (token renovado a mitad de su
  vida o ante un 403); lista de direcciones con reintentos; tras agotar la lista falla rápido, sin red, hasta que el
  sondeo encuentra una (`[ETCD-VAULT-CAMBIO]` si cambia de dirección).
- `SecretsManager` reescrito: `<CN>/<huella8>` = {clave, creada} escrita con CAS 0 y nunca borrada; `<CN>/ventana` =
  {activa, anterior, expira_anterior} con CAS = versión leída. Un solo mutex para leer-o-crear y rotar (la carrera de
  DAY311); entre instancias decide el CAS (se relee y se usa lo del otro: `[ETCD-CLAVES-CONCURRENTE]`; una rotación
  concurrente da 409). Enfriamiento medido desde la creación de la activa, guardada en Vault (vale tras un reinicio y
  entre instancias). Con el almacén caído: la última ventana conocida con sus dos claves (`desde_copia`), sin ella 503 y
  ninguna clave generada; rotar 503. Fechas en UTC con `timegm` (antes `mktime`, hora local). La huella se calcula como
  `CorrelationWriter::fingerprint` del ml-detector. En el log solo huellas.
- Rutas `/secrets/{c}`, `/secrets/valid/{c}`, `/secrets/rotate/{c}`: mismo formato (el ml-detector y el firewall leen
  `key`), más `huella` y `desde_copia`; `expires_at` vacío en la activa (antes, `time_point::max` mal formateado).
- Vagrantfile `[VAULT-CAS-D314]`: `cas_required=true` al inicializar y sonda en cada aprovisionamiento (escribir sin CAS
  con el certificado del etcd-server debe dar 400; si no, falla con el remedio).
- Tests: `test_almacen_claves` nuevo (22 casos); `test_secrets_manager_simple` y `test_hmac_integration` reescritos a la
  API nueva con reloj inyectado (el primero pasa de 9 s de `sleep` a 0,01 s). Instrumento nuevo
  `scripts/etcd_ha/d314_claves_medir.sh` (29 medidas, modo lab desde el Mac y local para el banco);
  `d313_es_vm.sh` muestra también `[ETCD-CLAVES]`/`[ETCD-VAULT…]`.

### Medido en el banco (debootstrap bookworm, GCC 12.2.0, opciones de production, Vault 2.2.1 con TLS, mTLS y auth cert como la VM, más `cas_required`)

- Control (4b.3 sin tocar): compila, ctest 6/6. Con 4b.4: compila con 0 diagnósticos del compilador (solo las notas de
  `lto-wrapper` y el aviso de `ld` de libsodium .26/.23, iguales que el control), ctest **7/7**.
- kv v2 con `cas_required` y la política del etcd-server, medido con curl antes de escribir código (predicho todo): sin
  `cas` 400; `cas=0` en ruta nueva 200; `cas=0` otra vez 400; `cas=1` 200 (versión 2); `cas=1` otra vez 400; DELETE 403;
  ruta inexistente 404.
- Mutaciones: sin copia, CAS al rotar, sin enfriamiento, sin comprobar la huella, sin caducidad → cada una hace fallar su
  test. «Generar con el almacén caído» resulta equivalente (la escritura de la clave también falla): el diseño ya lo
  impide.
- `d314_claves_medir.sh` local: 1ª pasada 29/29. **PARADA** en la 2ª (C10: `/secrets/valid` con Vault parado daba 503).
  Causa: tras reiniciar, la copia tenía la ventana y la activa pero no la anterior. Test que lo reproduce escrito antes
  del arreglo (falla), arreglo (al leer una ventana se cargan sus dos claves), test en verde. 3ª y 4ª: 28/29, C10 da 2
  claves y la predicción decía 1: **predicción errónea** (solo vale con Vault vacío; en la pasada anterior se rotó hace
  menos de 300 s). Corregida para predecir lo que había justo antes de parar Vault. 5ª y 6ª pasadas: **29/29**; 7ª sobre
  un Vault limpio: **29/29**. Copia servida con Vault parado en 0,09–0,10 s; Vault de vuelta, 200 en 1,7–1,8 s; parada
  0,17 s.
- Lista de direcciones (JSON modificado, predicho todo): sin `vault_addrs`, `--check-config` rc 1 y arranque rc 1 con
  `[ETCD-VAULT-FATAL]`; primera dirección que rechaza → `[ETCD-VAULT-CAMBIO]` y 200; primera que no responde (timeout
  500 ms) → escucha en 1,02 s y GET 200 en 0,06 s; ninguna → arranca, 503, y `[ETCD-VAULT-NO-DISPONIBLE]` con el error
  de cada dirección.
- Sonda del Vagrantfile: contra un Vault sin `cas_required` (como la VM de hoy) ❌ con el remedio; contra uno nuevo ✅.
- Regresión `d313_es_medir.sh` contra el binario nuevo: 20/20.
- En el banco no hay etcd: se usó el JSON de la VM con `almacen.modo=memoria` (el registro lo midió 4b.3).

### Lecciones DAY314

- Un instrumento se pasa al menos dos veces seguidas: la primera pasada parte de un estado limpio y esconde lo que
  depende de lo anterior (aquí, la clave anterior en la copia).
- Una predicción que depende del estado se escribe en función del estado medido justo antes, no como número fijo.

### Deudas y pendientes nuevos

- DEBT-ETCD-SERVER-LOG-TIMESTAMP-001 (arriba).
- `almacen.endpoints` (etcd) aún tiene defecto `https://127.0.0.1:2381`; por la regla de hoy («direcciones sin
  defecto») debería ser fatal en modo etcd. Decisión de Alonso pendiente.
- La pregunta de arrancar sin etcd-server (modo sin registro, con el cifrado ZMQ intacto) para el PR2.
- Rehacer la VM etcd para `cas_required` (V2) y volver a desplegar el etcd-server.

## Resultados DAY315 — DEBT-ANSIBLE-DEPLOY-CONFIGS-001 pasos 1-3 y 4b.6 (sección aparte, sin reescribir lo anterior)

Rama `feat/etcd-mtls-vault`. Commits: `fbd42be4` (paso 1), `58cb72ac` (pasos 2a-2c: `[DEPLOY-SSH-D315]`,
`[ETCD-CONFIG-ENTORNO-D315]`, `[INVENTARIO-FUERA-D315]`), `23c2e4f8` (paso 3: `[ETCD-ALMACEN-FATAL-D315]`) y `68ebbdaa`
(4b.6: `[ETCD-B4-D315]`). Instrumentos nuevos en `scripts/etcd_ha/`: `d315_ansible_paso1.sh`, `d315_ansible_paso2a.sh`,
`d315_ansible_paso2b.sh`, `d315_ansible_paso2c.sh`, `d315_paso3_codigo.sh`, `d315_paso3_medir.sh`, `d315_4b6.sh` y
`d315_b4_medir.sh`. Todo a la primera salvo lo que se indica.

### Decisiones de Alonso (DAY315)

- `deploy_configs.yml` conserva el nombre (lo llaman el Makefile y Jenkins); las variables de `group_vars` que solo
  leían las plantillas viejas se borran.
- Clave de despliegue propia generada en el defender (modelo de producción: Jenkins con su clave hacia los nodos), no
  la de Vagrant ni desde el Mac. `etcd-server.json` sale del tar de `d312`: ese fichero solo lo escribe Ansible.
- El repo es público: los inventarios reales viven fuera (operador o Jenkins) y dentro solo queda un ejemplo con datos
  ficticios. Un inventario sin máquinas del etcd-server es un fallo con mensaje claro, nunca un éxito vacío.
- En modo etcd son fatales `almacen.endpoints`, `almacen.prefijo`, `ca_file`, `cert_file` y `key_file` (como
  `vault_addrs`); endpoints repetidos cuentan como mal formado.
- `crypto_token` fuera de los dos lados. `HttpEtcdRegistrar` y `CryptoEpochCoordinator` (common/, ADR-045): ningún
  binario los usa y `/v1/epoch` no tiene consumidor; se decide en el paso 5.
- Preproducción de laboratorio como prueba FINAL (BACKLOG: fusionada en DEBT-LAB-PREPROD-TOPOLOGIAS-001).
- Cada commit marca con precisión lo que hace (un commit por cambio lógico).

### Paso 1 (`fbd42be4`)

- Fuera `ansible/templates/sniffer.json.j2` y `ml_detector_config.json.j2`, sus tareas y los `group_vars` duplicados;
  `group_vars` pasa junto al inventario (`ansible/inventory/group_vars/`). Variables huérfanas borradas.
- Medido antes de cambiar: `make deploy-configs` SÍ cargaba variables (`-e @group_vars`) y habría sobrescrito los JSON
  del repo.

### Pasos 2a-2c (`58cb72ac`)

- **2a, clave de despliegue.** Provisioner `deploy-key` en el defender (`/root/.ssh/argus_deploy_ed25519`: Jenkins
  corre como root) y `deploy-access` en la VM etcd (usuario `argus-deploy`, sudo sin contraseña SOLO en el lab, huella
  publicada en `/vagrant/dist/deploy/known_hosts_etcd`).
  **Cazado**: `ansible.cfg` lleva `host_key_checking = False` y Ansible antepone `StrictHostKeyChecking=no`; con una
  huella falsa en `known_hosts` conectaba igual. Arreglo: `ansible_host_key_checking: true` en el inventario.
- **2b, config del etcd-server por entorno.** Play sobre `etcd_servers`: JSON del repo + `almacen.endpoints` y
  `almacen.prefijo` del inventario (`etcd_almacen_endpoints`, `argus_prefijo`, sin defecto), escrito en
  `/etc/ml-defender/etcd-server/etcd-server.json` con `validate: etcd-server --check-config` y `follow: false` (el
  destino era un enlace a un JSON del repo). `d312` ya no copia `etcd-server.json`; `d313_es_vm.sh` lee por defecto el
  desplegado.
- **2c, inventarios fuera.** Ejemplo en `ansible/inventory/ejemplo-preprod/` con direcciones RFC 5737; fuera
  `prod.yml`; `make deploy-configs-prod INVENTARIO=<ruta>` obligatorio; `ARGUS_INVENTARIO` obligatorio en main
  (`Jenkinsfile.prod`); un inventario sin `etcd_servers` falla con `[ETCD-CONFIG-ENTORNO]`. `d312` con
  `DPkg::Lock::Timeout=600` (medido: `unattended-upgrades` tenía dpkg justo tras arrancar la VM).

### Paso 3 (`23c2e4f8`)

En modo etcd, `endpoints`, `prefijo`, `ca_file`, `cert_file` y `key_file` ausentes o mal formados (y endpoints
repetidos) = `[ETCD-ALMACEN-FATAL]` y no arranca; `--check-config` imprime `almacen_fatales=N`. En modo memoria solo
avisa. Arranque sin endpoints medido: se niega en 0,04 s. Cierra la pendiente de DAY314 («`almacen.endpoints` aún
tiene defecto `https://127.0.0.1:2381`»).

### 4b.6 y B4 (`68ebbdaa`)

- Antes, `/register` cortaba el nombre en el primer guion: `firewall-acl-agent` → `/secrets/firewall` → 403 con mTLS
  (sin clave HMAC para su CSV). Ahora `/secrets/<CN>` y `/config/<CN>`. En el defender el firewall pasa de
  `key_path=/secrets/firewall` a `/secrets/firewall-acl-agent` (32 bytes).
- `crypto_token` fuera del servidor y de `ServicePaths::is_valid()` de etcd-client (no existe ninguna ruta `/crypto`).
- Borradas `etcd_client_base.cpp`, `etcd_client_manual.cpp`, `etcd_client.hpp.day54_hmac_only` y
  `etcd_client.cpp.day54_broken` (cierra DEBT-ETCD-CLIENT-DEAD-VARIANTS-001).
- Un `grep -r` del parcheador de 4b.6 se dejó engañar por 9 `*.backup*` ignorados en `etcd-client/` y `etcd-server/`:
  búsquedas siempre con `git grep`.

### Medido al final de DAY315

- `make test-components PROFILE=production`: 9 / 23 / 13 / 7 / 82, todo verde.
- `d313_registro_medir.sh` 28/28; `d314_claves_medir.sh` 29/29; `d315_paso3_medir.sh` 15/15 dos veces seguidas;
  `d315_b4_medir.sh` 10/10 dos veces seguidas.
- `d312_etcd_vm_deploy.sh` PASA (binario `6d837186`); `make deploy-configs` en dev: `etcd ok=7 changed=0`.
- JSON desplegado en la VM etcd = `etcd-server.etcd-vm.json` del repo (sha256 `3fedf9ad…`).

### Medido: Jenkins no puede hacer preproducción hoy

- `Jenkinsfile.dev`: los stages «Build .deb» (línea 96) y «Deploy Vagrant Test» (101) son solo un `echo` de
  DEBT-PACKAGE-DEB-001 y DEBT-DEPLOY-VAGRANT-001 («deferred, skipping»).
- `Jenkinsfile.prod`: `agent { label 'argus-server' }` (línea 14), un agente que no existe, y lanza `vagrant destroy -f
  && vagrant up` (líneas 40 y 123).
- El único componente con despliegue de binarios es el etcd-server (`d312_etcd_vm_deploy.sh`), y se lanza desde el Mac.
- DEBT-DEPLOY-VAGRANT-001 no tiene entrada propia en el BACKLOG: solo aparece en la lista de deudas de DAY167.

### Lecciones DAY315

- Una comprobación de huella que nadie ha visto fallar no comprueba nada: `ansible.cfg` la desactivaba en silencio.
  Control negativo (huella falsa) antes de darla por buena.
- Antes de ejecutar un target que «solo despliega configuración», medir adónde escribe: el de DAY161 habría escrito
  sobre los JSON del repo.
- Una VM recién arrancada puede tener dpkg cogido por `unattended-upgrades`: se espera el bloqueo, no se falla.
- Ficheros ignorados por git engañan a `grep -r`; `git grep` solo ve lo trackeado.
- El mensaje del commit del paso 1 (`fbd42be4`, «d315_ansible_paso1...») no dice qué hace. La historia no se
  reescribe: queda descrito aquí y en el BACKLOG.

### Pendientes

- RBAC de etcd por prefijo en producción: en el lab el rol del etcd-server cubre `readwrite /argus/`; con prefijos por
  despliegue (`/argus/<hospital>/<planta>/`) el rol tiene que cubrirlos.
- `d312`: 25 paquetes Debian hoy frente a 26 medidos DAY314; sin explicar.
- `make up` no levanta la VM etcd (añadirla antes del paso 8); tras parar el Mac queda `aborted`: `vagrant up etcd`
  (etcd y Vault vuelven solos; `argus-vault-unseal` desella). Para mirar Vault hace falta `sudo` y certificado de cliente.
- DEBT-ETCD-SERVER-LOG-TIMESTAMP-001; cpp-httplib sin fijar a `v0.63.0` en el Vagrantfile; `test_autonomy_integration`
  (falló una vez DAY313); DEBT-CONFIG-JINJA2-PIPELINE-001 (mismo patrón para sniffer y ml-detector).
- Siguiente: paso 5 (libetcd_client con TLS y lista de endpoints para sniffer, ml-detector y firewall), empezando por
  medir qué cliente usa cada uno; dentro, `get_encryption_seed()` contra `/seed` (borrada en 4b.2), los
  `crypto_token_path` de sus JSON y la decisión sobre el ADR-045. Después pasos 6, 7 y 8.

## Diseño del paso 5 (libetcd_client con TLS y lista de endpoints) — DAY316, escrito ANTES de tocar código

Base: rama `feat/etcd-mtls-vault` en `0de22545` (docs de DAY315; el código es el de `68ebbdaa`). Todo lo de «Medido» sale
de `git grep` y de leer los ficheros en esa base. Las decisiones abiertas están en 5.0 y no se escribe código hasta
tenerlas.

### Medido para este diseño

- **M1. Un solo cliente.** Sniffer (`sniffer/src/userspace/etcd_client.cpp`), ml-detector (`ml-detector/src/etcd_client.cpp`)
  y firewall (`firewall-acl-agent/src/core/etcd_client.cpp`) tienen cada uno su envoltorio (unas 215 líneas, casi
  idénticos), todos sobre `etcd_client::EtcdClient` de `libetcd_client.so`. La librería habla con `httplib::Client` en
  claro (`etcd-client/src/http_client.cpp` 38, 84, 130 y 180); `Config` solo tiene `host` y `port`
  (`etcd_client.hpp` 36-39).
- **M2. `endpoints[0]`.** Sniffer `main.cpp:334`, ml-detector `main.cpp:148`, firewall `main.cpp:403`. El envoltorio quita
  `http://` y corta en el primer `:`: una URL `https://` no se puede parsear. Los cuatro JSON traen hoy `localhost:2379`
  (el etcd-server del defender, en `tls.modo=http`).
- **M3. `etcd.endpoints` ausente**, tres comportamientos: sniffer pone `localhost:2379` sin avisar
  (`config_manager.cpp:454`); ml-detector, fatal (`get_required`, `config_loader.cpp:191`, como los otros 11 campos del
  bloque, 190-200); firewall, vector vacío y después `endpoints[0]`: comportamiento indefinido (`config_loader.cpp:594`,
  `main.cpp:403`). `enabled` tiene defecto `true` en el sniffer, es obligatorio en el ml-detector y vale `false` por
  defecto en el firewall.
- **M4. Leídos y nunca aplicados**: `connection_timeout_ms`, `retry_attempts` y `retry_interval_ms` (los tres JSON traen
  5000 / 3 / 1000; ningún envoltorio los pasa a la librería, que usa su `timeout_seconds = 5` y 3 reintentos);
  `config_sync_path`, `required_for_encryption`, `service_registration_path`, `fallback_mode` y
  `heartbeat_interval_seconds` del bloque `etcd` (se guardan y nadie los lee; la librería late con su
  `heartbeat_interval_seconds = 30` del código; `encryption.fallback_mode` del transporte es otro campo y no entra aquí);
  `crypto_token_path` (sniffer con defecto, ml-detector obligatorio, el firewall ya no lo lee pero sigue en su JSON).
- **M5. Nadie llama a `/seed`.** El sniffer lee `seed.bin` en local (`etcd_client.cpp:201`), pero su `main.cpp:704`
  escribe «Encryption seed obtained from etcd-server» (falso). El `get_encryption_seed()` del ml-detector no tiene
  ninguna llamada y acaba en `get_encryption_key()` de la librería, que devuelve `""` desde DAY98
  (`etcd-client/src/etcd_client.cpp:711`). El único `"/seed"` del árbol es `common/vault_transport.cpp:50` (Vault, la
  semilla de familia, no el etcd-server).
- **M6.** En el ml-detector, `encryption_enabled = (el endpoint no empieza por "http://")`: con `https://` se activaría por
  casualidad.
- **M7. ADR-045.** `http_etcd_registrar.cpp` y `crypto_epoch_coordinator.cpp` se compilan dentro de `libcrypto_provider.so`
  (`common/CMakeLists.txt` 57-62; cabeceras instaladas 143-145), que enlazan el etcd-server y el firewall. Ningún binario
  usa esas clases. `IEtcdRegistrar` y `StubEtcdRegistrar` (`common/etcd_registrar.h/.cpp`) NO son ADR-045: los usa
  `vault_client.cpp` y se quedan. Tests: `test_crypto_epoch_coordinator` solo prueba el coordinador;
  `test_e2e_rotation` tiene 6 pruebas y solo T1 (`test_handle_reloads_on_epoch_change`) y T4
  (`test_coordinator_epoch_id_propagates_to_wire`) usan el coordinador; T2, T3, T5 y T6 (ida y vuelta por el cable en
  épocas 1 y 2, ventana de dos claves, centinela `0xFFFF` rechazado antes de descifrar, DEBT-CRYPTO-NEGATIVE-TEST-001) son
  la única cobertura de la época en el cable (`test_wire_protocol` no la tiene). `common/tests/test_http_etcd_registrar.cpp`
  es huérfano: ningún CMake lo compila.
- **M8. `/v1/epoch`** solo lo consumía el coordinador: rutas en `etcd_server.cpp` 489 y 498, dos reglas en
  `etcd_server_authz.hpp` 175 y 185 y en los dos JSON del etcd-server, y una aserción en `test_etcd_server_authz.cpp:202`.
- **M9. ODR.** `libetcd_client` se compila sin `CPPHTTPLIB_OPENSSL_SUPPORT`; `crypto_provider` lo exporta `PUBLIC`
  (`common/CMakeLists.txt:107`) y el firewall enlaza las dos. En producción solo dos ficheros incluyen `httplib.h`:
  `etcd-client/src/http_client.cpp` y `common/http_etcd_registrar.cpp` (este se borra con ADR-045). El etcd-server es otro
  binario, con su propia definición `PRIVATE`.
- **M10. Otros consumidores de la librería.** `tools/synthetic_sniffer_injector.cpp` y `synthetic_ml_output_injector.cpp`
  (los usan los E2E del Makefile, 1424-1457) construyen `etcd_client::Config` a mano con `host`/`port`, defecto
  `localhost:2379`, y solo hacen `connect()` + `register_component()` con los nombres `cpp_evolutionary_sniffer` y
  `synthetic-ml-output`. Ningún E2E comprueba ese registro, y `cpp_evolutionary_sniffer` es un nombre que el etcd-server
  ya rechaza (`test_registro_componentes.cpp:72`). Tests con servidor falso en HTTP: `etcd-client/tests` (6 ejecutables)
  y `ml-detector/tests/integration/test_etcd_client_hmac.cpp` (`http://127.0.0.1:<puerto>`).
- **M11. Certificados en el defender.** El Vagrantfile solo reparte la PKI (`ARGUS_PKI_DIR`, defecto `~/argus-pki`) a la VM
  etcd (`/etc/argus-pki/`, líneas 1554-1577); al defender no le llega ningún certificado de componente.
- **M12. Scripts del lab.** `mitre_start.sh:32`, `ctu_start.sh:38` y `custom_start.sh.template:31` sacan la clave HMAC del
  ml-detector con `curl -s http://localhost:2379/secrets/ml-detector` (para el conversor). Con mTLS, `/secrets/ml-detector`
  solo lo puede leer el CN `ml-detector`; el conversor tiene `/secrets/valid/{c}`.

### Decisiones de Alonso (DAY316)

- **C1.** TLS y lista de endpoints en la librería, no en los tres envoltorios.
- **C2.** Los envoltorios pasan la lista completa del JSON (fuera el parseo de `host:port`).
- **C3.** Fuera `get_encryption_seed()` del ml-detector, `get_encryption_key()` de la librería y `crypto_token_path`
  (JSON y cargadores). En el sniffer la función que lee `seed.bin` deja de llamarse «del etcd-server» y su log no lo dice.
- **C4.** Fuera `HttpEtcdRegistrar` y `CryptoEpochCoordinator` (ADR-045), con lo medido en M7: se queda `IEtcdRegistrar`;
  de `test_e2e_rotation` se van T1 y T4 y se quedan T2, T3, T5 y T6.
- **D1.** En los componentes, `etcd.endpoints`, `ca_file`, `cert_file` y `key_file` ausentes o mal formados son fatales,
  como el almacén del etcd-server (los rellena Jenkins desde el inventario): mensaje con campo, formato y límites, y el
  proceso no arranca. El resto del bloque lleva defecto, aviso en el log y origen de cada valor.
- **D2.** Fuera `etcd.enabled` (sin etcd-server el pipeline no arranca, DAY310).
- **D3.** Fuera `GET` y `PUT /v1/epoch` y sus dos reglas de autorización.
- Regla general (DAY291/300/308, recordada DAY316): el JSON es la ley; ausente o mal formado → defecto validado + aviso
  claro + el proceso sigue; la única excepción son las direcciones y credenciales que rellena el aprovisionamiento.

### 5.0 Decisiones abiertas para Alonso

- **E1. Inyectores sintéticos (M10).** (a) Quitarles etcd entero (`connect` + `register` y el enlace a la librería): no
  firman nada, nadie comprueba su registro y con mTLS necesitarían un certificado falso. (b) Certificado propio y regla
  de autorización. Propuesta: a, con la predicción de que los E2E sintéticos siguen dando PASA.
- **E2. Tests con servidor falso.** (a) CA desechable generada por el propio test con `openssl` en un directorio
  temporal (nada en el repo ni en `/vagrant`), servidor `httplib::SSLServer`; (b) material de prueba fijo en el repo.
  Propuesta: a (el repo es público y no debe llevar claves, ni de prueba).
- **E3. Campos del bloque `etcd` sin efecto (M4).** Propuesta: `heartbeat_interval_seconds` se APLICA (pasa a la
  librería: 5-300, defecto 30, aviso y origen en el log); `config_sync_path`, `required_for_encryption`,
  `service_registration_path` y `fallback_mode` del bloque `etcd`, fuera, como `crypto_token_path`.
- **E4. Certificados en el defender (M11).** Propuesta: aprovisionador en el Vagrantfile, igual que el de la VM etcd,
  desde `ARGUS_PKI_DIR` a `/etc/argus-pki/<componente>.{crt,key}` (`.key` 0600 root; los tres corren como root) más
  `ca.crt`. Antes, medir en el Mac qué CN tiene el certificado del firewall (`firewall` o `firewall-acl-agent`).
- **E5. Scripts del lab (M12).** Propuesta: entran en el paso 5. Leen con el certificado del conversor
  (`bronze-to-gold-converter`) por `GET /secrets/valid/ml-detector` en `https://192.168.100.20:2379`. Antes, medir el
  formato de esa respuesta (lista de claves con su huella) y cuál usa hoy el conversor.

### 5a. Librería (`etcd-client/`)

- `Config`: fuera `host` y `port`; dentro `endpoints` (lista de `https://<host>:<puerto>`, 1-7, sin repetir),
  `ca_file`, `cert_file`, `key_file`, `connection_timeout_ms`, `retry_attempts`, `retry_interval_ms` y (con E3)
  `heartbeat_interval_seconds`.
- Transporte `httplib::SSLClient` con la CA del lab, certificado de cliente y verificación del certificado del servidor
  (nombre incluido). Recorre la lista: `retry_attempts` intentos por dirección separados `retry_interval_ms`, luego la
  siguiente. `[ETCD-CLIENTE-CAMBIO]` al cambiar de dirección y `[ETCD-CLIENTE-NO-DISPONIBLE]` con el error de cada una al
  agotar la lista. Un `http://` en la lista es mal formado (D1): no hay vuelta a HTTP.
- Fuera `get_encryption_key()`. `CPPHTTPLIB_OPENSSL_SUPPORT` y OpenSSL en el CMake de la librería.
- Comportamiento si el etcd-server cae después de arrancar: el de hoy, sin cambios en este paso (lo homogeneiza
  DEBT-FW-HMAC-KEY-ALARM-001). Al arrancar, si no se alcanza ninguna dirección, el componente no arranca (DAY314).

### 5b. Envoltorios y configuración (sniffer, ml-detector, firewall)

- Los tres envoltorios construyen `Config` con la lista y las rutas del JSON; sin parseo propio de la URL.
- Bloque `etcd` de los cuatro JSON (`sniffer.json`, `sniffer-libpcap.json`, `ml_detector_config.json`, `firewall.json`):
  `endpoints` = `["https://192.168.100.20:2379"]` y `ca_file`/`cert_file`/`key_file` (D1, fatales);
  `connection_timeout_ms` 100-60000 (defecto 5000), `retry_attempts` 1-10 (3), `retry_interval_ms` 100-60000 (1000),
  con defecto + aviso y el origen de cada valor en el log de arranque; rango y formato documentados en el propio JSON.
  Fuera `enabled` (D2), `crypto_token_path` (C3) y, si se aprueba E3, los cuatro sin efecto; `heartbeat_interval_seconds`
  pasa a aplicarse.
- En los tres `main.cpp`, fuera `endpoints[0]` y el `if (etcd.enabled)`.
- El etcd-server del defender (`localhost:2379`, http) se queda sin clientes del pipeline; se borra en el paso 6.

### 5c. Fuera (C3, C4, D3)

`get_encryption_seed()` del ml-detector (cabecera y fuente); `get_encryption_key()` de la librería;
`common/http_etcd_registrar.{h,cpp}`, `common/crypto_epoch_coordinator.{h,cpp}`, sus líneas en `CRYPTO_PROVIDER_SOURCES`
y en la lista de cabeceras instaladas, y `CPPHTTPLIB_OPENSSL_SUPPORT PUBLIC` de `crypto_provider` (nadie más lo
necesita, M9); `test_crypto_epoch_coordinator` (fuente y CMake), `test_http_etcd_registrar.cpp`, T1 y T4 de
`test_e2e_rotation` (y su servidor falso si ya no lo usa nadie); en el etcd-server, `GET`/`PUT /v1/epoch`, sus dos reglas
en `etcd_server_authz.hpp` y en los dos JSON, y la aserción de `test_etcd_server_authz.cpp:202`. Con E1 = a, el etcd de
los dos inyectores.

### 5d. Pruebas y predicciones

- Antes de tocar nada, medir en el defender el número de tests de `common` (`make vault-client-test`) y de `etcd-client`
  (su ctest): son la base de las predicciones de abajo.
- Banco (Debian 12, GCC 12, opciones de production): compila con 0 diagnósticos; control con la rama sin el parche.
- `make test-components PROFILE=production`: 9 / 23 / 13 / 7 / 82 (no cambian: el etcd-server pierde una aserción, no un
  test; el de HMAC del ml-detector se reescribe a TLS). `common`: uno menos que la base (`test_crypto_epoch_coordinator`).
  `etcd-client`: los mismos más uno nuevo (lista de direcciones y TLS: primera dirección que no responde → segunda;
  ninguna → error con todas; `http://` → mal formado; certificado de servidor de otra CA → falla).
- Mutaciones: sin verificar el certificado del servidor, sin pasar a la siguiente dirección, aceptando `http://` → cada una
  hace fallar su test.
- Laboratorio, tras `pipeline-start`, desde el defender con el certificado de admin contra la VM etcd:
  `GET /components` → `etcd-server`, `sniffer`, `ml-detector`, `firewall-acl-agent`, los cuatro vivos. ml-detector
  `[BRONCE-CLAVE]` con huella; firewall con `key_path=/secrets/firewall-acl-agent`. En el log del etcd-server, 0
  `[ETCD-AUTHZ-DENEGADO]` de los tres.
- Control negativo en el laboratorio: JSON del ml-detector con el certificado del sniffer → registro 403 y no arranca;
  sin `ca_file` → no arranca y el mensaje dice campo y formato; primera dirección falsa en la lista →
  `[ETCD-CLIENTE-CAMBIO]` y registro correcto.
- E2E sintéticos (con E1 = a) y `mitre-start` (con E5) siguen dando PASA.
- Cada instrumento, dos veces seguidas.

## Resultados DAY316 — paso 5: decisiones, C4+D3 y E4 medidos, estado deseado (sección aparte, sin reescribir el diseño)

### Decisiones de Alonso (DAY316, después del diseño)

- **E1 = c** (cambia la propuesta a). Los inyectores sintéticos son imprescindibles en EMECAS (`emecas` → `test-e2e-synthetic`;
  `emecas++` → `-full` y `-firewall`): no se desactivan. Cada inyector se presenta con el certificado del componente al que
  sustituye (el de sniffer con CN `sniffer`, el de ml-output con CN `ml-detector`) y lee endpoints y rutas TLS del bloque
  `etcd` del JSON de ese componente. Medido: el Makefile para el componente real antes de lanzar su sustituto (líneas 1418 y
  1450-1452), así que no hay dos registros con el mismo CN. Fuera los nombres falsos (`cpp_evolutionary_sniffer`,
  `synthetic-ml-output`) y el `localhost:2379` escrito en el código.
- **E2.** Tests unitarios (ctest, sin VMs): CA desechable en un directorio temporal, borrada al terminar. Integración y E2E en
  el laboratorio: los certificados reales del lab, repartidos por el mismo camino que usan los componentes (E4); ninguna CA
  de pruebas en ningún sitio. La CA no vive en Vault: Vault guarda solo las claves HMAC (PR1). Re-verificar el grafo años
  después necesita las claves HMAC (inmutables en Vault), no la CA.
- **E3, E4, E5:** como se propusieron en 5.0. En E4 entra también `bronze-to-gold-converter` (el conversor corre en el
  defender y E5 lo necesita); `admin` no va al defender.
- **F1.** La librería lee y valida el bloque `etcd` del JSON en un solo sitio (defectos con aviso, fatales, origen de cada
  campo en el log); sniffer, ml-detector y firewall solo le pasan el bloque tal cual (hoy jsoncpp en dos, nlohmann en uno, y
  tres comportamientos distintos).
- **F2.** Fuera `Config::from_json`/`from_json_file`, el constructor `EtcdClient(ruta_json)` y
  `etcd-client/config/etcd_client_config.json`: nadie los usa (`git grep`).
- **F3.** La lista de endpoints pasa a la siguiente dirección solo si no hay respuesta o hay un 5xx; un 4xx (403, 404) se
  devuelve enseguida, sin reintentar (hoy se reintenta toda respuesta que no sea 2xx).

### Estado deseado (Alonso, DAY316) y lo que cambia de lo decidido

El pipeline arranca aunque no responda ninguna de las direcciones del etcd-server (p. ej. un fallo físico). Lo peor que
ocurre es que no se puede firmar con la clave HMAC: es el precio a pagar, porque lo más importante es que el hospital no
quede desprotegido. En el grafo esos momentos deben verse como periodos en que el etcd HA/Raft de esa instalación tuvo
problemas, analizables por el administrador (que todo el etcd caiga durante un ataque es, como mínimo, motivo para
investigar). Cuando algún etcd-server vuelva a dar servicio, los componentes se dan de alta, hacen el handshake, obtienen
su clave HMAC y operan con normalidad. Si un servidor cae, entra otro; el estado se comparte: el etcd-server lee el estado
compartido del etcd real, y los etcd del Raft se sincronizan entre sí (incluida la configuración JSON de los componentes)
por un canal interno cifrado y de confianza comprobada, para que un proceso etcd pirata no pueda colarse.

Cambia:
- **D1:** un bloque `etcd` mal formado ya no para el proceso: ese componente queda sin etcd, con `[ETCD-CLIENTE-FATAL]`
  periódico (campo, formato y límites), y sigue protegiendo (regla DAY291: el pipeline no se queda parado).
- **5a:** «si no se alcanza ninguna dirección, el componente no arranca» pasa a «arranca, avisa y reintenta».
- **DAY314:** el dilema de arrancar sin etcd-server queda resuelto: se arranca. El cifrado de ZMQ no depende del
  etcd-server (sale de `seed.bin` local).

### Medido contra el estado deseado

- Hoy, sin etcd-server al arrancar: el sniffer sale («etcd integration is REQUIRED… seed must be obtained from
  etcd-server», motivo falso: la lee de `seed.bin`), el ml-detector sale («REQUIRED for ml-detector»), el firewall sigue
  sin etcd.
- Ya existe (DAY310): el ml-detector pide la clave del bronce cada `bronze_key.check_interval_seconds`, no escribe nunca
  bronce sin firma (`records_sin_clave`), firma con la vigente en modo extendido si el etcd-server cae y aplica en caliente
  la que llega tarde (`[BRONCE-CLAVE-RECUPERADA]`).
- `GET /secrets/{CN}` no exige registro, solo el certificado con ese CN: se puede firmar aunque el registro tarde.
- El firewall pide su clave una sola vez, al arrancar (`zmq_subscriber.cpp:88`); sin clave no escribe su CSV y no la
  vuelve a pedir.
- etcd real: TLS mutuo entre pares (`peer-transport-security`, `client-cert-auth: true`) y RBAC para el etcd-server; un
  miembro nuevo entra solo con `member add`. Hueco: la misma CA firma los certificados de los componentes.
- Vault es de un nodo: con varios etcd-server las claves HMAC solo se comparten si Vault también es HA.
- El hueco por falta de clave solo se ve en el log (`[BRONCE-SIN-CLAVE]`, contador); al grafo no llega como evento.

### Plan revisado

- **Commit A (paso 5):** TLS + lista de endpoints + lector único en la librería (F1-F3, C3, E3, E1 = c); ningún componente
  sale por el etcd-server; la librería reconecta sola en cada llamada si no estaba conectada, así el sondeo de clave del
  ml-detector la recoge cuando vuelve un etcd-server.
- **Commit B (DEBT-FW-HMAC-KEY-ALARM-001):** re-registro en segundo plano en la librería, el firewall pide su clave cada
  cierto tiempo como el ml-detector, aviso periódico mientras no haya etcd; los tres iguales.
- **PR2:** varios nodos etcd + etcd-server, Vault HA (raft integrado), `peer-cert-allowed-cn` y una CA por despliegue.

### C4 + D3 medidos (commit `1e75d0618`, 17 ficheros, +16/-1131)

- Alcance mayor que M8: detrás de `/v1/epoch` había gestión de época entera en el etcd-server (`EpochInfo`,
  `set_epoch`/`get_epoch`, `guardar_epoca`/`leer_epoca` del registro y su test). Fuera todo; también OpenSSL y
  `CPPHTTPLIB_OPENSSL_SUPPORT PUBLIC` de `crypto_provider` (solo los usaba el registrador).
- Corrección de M9: `crypto_provider` lo enlazan el etcd-server y el firewall por la ruta del `.so`, no como objetivo de
  CMake, así que la definición `PUBLIC` no les llegaba. El riesgo ODR del firewall estaba en el `.so`: llevaba httplib
  compilado con OpenSSL (el registrador) junto a `libetcd_client.so` sin OpenSSL. Desaparece con el registrador.
- Banco (Debian 12, GCC 12.2.0, cadena del Makefile, etcd-server en production): control y parche con los mismos avisos
  (8 notas de `lto-wrapper` + 1 `ld` libsodium .26/.23); common 13 → 12, etcd-client 4, etcd-server 7, dos pasadas; con
  `ARGUS_VAULT_ENABLED=ON` 15 → 14 (rojo `test_ntp_health_check` en los dos: sin NTP en el banco). Primera pasada
  **PARADA**: `test_etcd_server_authz` 16/17, el test esperaba el texto de log `regla 1/15`; corregido a `1/13`. Los tests
  nuevos contra el código viejo: 3 de 17 fallan.
- Laboratorio: parcheador 31/31; `pipeline-build` production rc 0; `test-components` 9 / 23 / 13 / 7 / 82; common 12/12.
  Despliegue **PARADA**: la VM etcd estaba `aborted` (`make up` no la levanta); tras `vagrant up etcd`: PASA, binario
  `86d52cd93200ed60`, 25 paquetes; `deploy-configs` `etcd ok=7 changed=1`; registro 28/28 y claves 29/29, dos veces.

### E4 medido (commit `59d0fc592`, +52/-1)

- Banco con una PKI de juguete (`d312_pki.sh`): primera pasada y repetición 4 ✅; seis negativos (clave cruzada, falta una
  clave, certificado de otra CA, CN equivocado, clave 0644, sin `ca.crt`) fallan cada uno con su mensaje. Cazado en el
  control positivo: OpenSSL 3 antepone `subject=` al sujeto. `ruby -c` del Vagrantfile: `Syntax OK`.
- Laboratorio: aprovisionamiento rc 0, 4 ✅, repetición rc 0; huellas iguales a las del Mac (sniffer `2af48d66`,
  ml-detector `a5a2bc4c`, firewall-acl-agent `d2fa1409`, converter `1bfd79af`); `/etc/argus-pki` 0700 root, `.key` 0600 root,
  entrada borrada. Certificado del firewall medido en el Mac: `CN=OU=firewall-acl-agent` (coincide con B4).

### Deudas y pendientes nuevos (DAY316)

- **DEBT-PKI-AT-REST-001:** `ca.key` en el Mac y las `.key` de los componentes en claro en disco (0600 root). En producción
  la CA, fuera de línea y lejos del despliegue; para las claves de cliente: pedirlas a Vault al arrancar y tenerlas en
  memoria, o TPM/HSM.
- **DEBT-GRAPH-HUECO-SIN-CLAVE-001:** que el periodo sin clave HMAC se vea en el grafo como evento (p. ej. una fila firmada
  de tipo hueco al recuperar la clave, con inicio, fin y filas perdidas). Toca correlation_v1: diseño propio.
- Vault del lab: `d314_claves_medir.sh` rota con `force` la clave del CN real `ml-detector` y cada pasada deja claves
  inmutables para siempre (medido: `c10f19d3` → `60768287`), además de `argus-hmac/d312/prueba`. Propuesta: CN de prueba
  propio para los instrumentos y rehacer la VM etcd antes del paso 8.
- DEBT-REPO-RESIDUOS-001: cuatro parcheadores viejos sin trackear en `scripts/` (`d313_4b2_parche.py`, `d313_4b3_parche.py`,
  `d314_4b4_parche.py`, `d314_docs_parche.py`).
- Tests manuales de etcd-client que nunca entran en ctest y necesitan un etcd-server en HTTP (`test_hmac_integration_client`,
  `test_put_config_integration`, `test_service_discovery`): se actualizan en el commit A o se borran; decide Alonso.

### Lecciones DAY316

- Contar todas las apariciones de un número antes de cambiarlo: el test guardaba el 15 también dentro de un texto de log.
- Un control positivo hace falta también en los scripts de aprovisionamiento (OpenSSL 3 y `subject=`).
- `vault status` en la VM etcd necesita `sudo` y certificado de cliente: un `grep` vacío no prueba nada.
- Sin emojis en los comandos que se pegan en la terminal: zsh calcula mal el ancho y la línea se ve corrida.
