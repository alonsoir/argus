# etcd-server

Fachada HTTPS del plano de control de aRGus. Los componentes del pipeline (sniffer, ml-detector,
firewall-acl-agent, bronze-to-gold-converter…) hablan con él por **mTLS**: se registran, mandan su latido, leen y
publican su configuración y piden su clave HMAC. El etcd-server guarda el registro en **etcd** y las claves HMAC en
**Vault**, y sirve el **manifiesto firmado de rangos protegidos** (ADR-060) a los firewalls.

El registro y las claves HMAC del bronce solo los toca el etcd-server, con su propio certificado: los componentes
los piden por su API, no a etcd ni a Vault.

## Dónde corre

En la VM `etcd` del laboratorio (192.168.100.20), como servicio systemd `ml-defender-etcd-server.service`, junto a
etcd y Vault, que escuchan solo en 127.0.0.1 (etcd en el 2381 por HTTPS, Vault en el 8200 por HTTPS).

| Qué | Dónde |
|---|---|
| Binario | `/opt/argus/etcd-server/bin/etcd-server` (librerías propias en `/opt/argus/etcd-server/lib`) |
| Configuración | `/etc/ml-defender/etcd-server/etcd-server.json` (la escribe Ansible, ver Despliegue) |
| Identidad (semilla, claves Ed25519) | `/etc/ml-defender/etcd-server/` (ADR-013: la crea `provision.sh`) |
| Certificados | `/etc/argus-pki/{ca.crt,etcd-server.crt,etcd-server.key}` |
| Puerto | 2379, HTTPS con certificado de cliente obligatorio |
| Log | journal: `journalctl -u ml-defender-etcd-server` |

La VM etcd no tiene compilador (ADR-039): el binario se compila en el defender y se copia.

## Qué hace

### 1. mTLS y autorización (`tls`, `authz`)

- `tls.modo=mtls`: solo se acepta un cliente con certificado firmado por la CA de `tls.ca_file`.
- Identidad del cliente: el certificado lleva exactamente un **CN** (la instancia, p. ej. `sniffer`) y un **OU** (el
  rol), los dos con forma `[a-z0-9-]{1,63}`.
- **Denegar por defecto**: una petición que no casa con ninguna regla de `authz.reglas` es 403 y
  `[ETCD-AUTHZ-DENEGADO]`. Cada regla: método, ruta (con como mucho un segmento variable `{c}`) y a quién se
  permite: `propio` (CN == `{c}`), `ou:<rol>` o `cualquiera` (cualquier certificado de la CA).
- Una regla mal formada invalida la tabla entera: se avisa de cada error y se usa la tabla por defecto.

Las rutas de la configuración de este repositorio:

| Método y ruta | Quién | Para qué |
|---|---|---|
| `GET /health` | cualquiera | salud |
| `POST /register`, `POST /unregister` | cualquiera | alta y baja en el registro |
| `POST /v1/heartbeat/{c}` | propio | latido |
| `GET`/`PUT /config/{c}`, `PUT /v1/config/{c}` | propio | configuración del componente |
| `GET /secrets/{c}` | propio | clave HMAC del componente (ventana de dos) |
| `GET /secrets/valid/{c}` | propio, `ou:bronze-to-gold-converter` | claves válidas para verificar el bronce |
| `POST /secrets/rotate/{c}` | `ou:admin` | rotar la clave HMAC |
| `GET /components`, `/validate`, `/info` | `ou:admin` | operación |
| `GET /v1/protegidos` | `ou:firewall-acl-agent`, `ou:argus-infra` | manifiesto vigente |
| `PUT /v1/protegidos` | `ou:argus-infra` | publicar un manifiesto firmado |
| `GET /v1/protegidos/v/{c}` | `ou:argus-infra` | una versión del histórico (diff, deshacer) |

Los dos roles de administración están separados a propósito (ADR-060, D9 bis): `admin` opera cada día y no puede
publicar el manifiesto; `argus-infra` solo puede publicar el manifiesto.

### 2. Registro y latidos en etcd (`almacen`, `heartbeat`)

- Claves en etcd, bajo el `prefijo` del despliegue (uno por despliegue, p. ej. `/argus/<hospital>/<planta>/`):
  `<prefijo>registro/<CN>`, `<prefijo>latido/<CN>`, `<prefijo>epoca`.
- El etcd-server entra en etcd por gRPC con TLS; el CN de su certificado es su usuario RBAC (rol `argus-rw`, solo
  lectura y escritura bajo `/argus/`).
- Un componente sin latido durante `heartbeat.interval_seconds × timeout_multiplier` se marca muerto (no se borra);
  su siguiente latido lo revive.
- El propio etcd-server se registra y manda su latido en proceso, sin pasar por la red.
- `almacen.endpoints` admite de 1 a 7 miembros etcd (`https://IPv4:puerto`); hoy el laboratorio tiene uno.

### 3. Claves HMAC del bronce en Vault (`almacen_claves`, `secrets`)

- Vault kv v2 por HTTPS, con login por certificado (`auth cert`, rol `rol_login`) en el montaje `montaje`
  (`argus-hmac`), con `cas_required=true`.
- Cada clave `<CN>/<huella8>` se escribe una vez y nunca se borra. La ventana de dos (`<CN>/ventana`: activa,
  anterior y cuándo expira la anterior) se cambia con CAS. Así, al rotar, el bronce firmado con la clave anterior
  sigue verificándose durante `secrets.grace_period_seconds`.
- `vault_addrs` admite de 1 a 7 direcciones; con varias, agotados los reintentos de una se pasa a la siguiente.

### 4. Manifiesto firmado de rangos protegidos (`protegidos`, ADR-060)

- `PUT /v1/protegidos` (solo OU `argus-infra`): antes de guardarlo, el etcd-server verifica la firma Ed25519 con la
  clave pública **compilada** en el binario (la misma que el firewall-acl-agent), el formato, los límites, que el
  `hospital_id` sea el suyo y que la versión sea mayor que la vigente. Si cuadra, lo guarda en etcd en
  `protegidos/vigente` y `protegidos/v/<N>`.
- `GET /v1/protegidos` da el sobre vigente; `GET /v1/protegidos/v/{n}`, la versión `n` del histórico (404 si no
  existe).
- Sin `protegidos.hospital_id` válido no hay valor sano por defecto: las dos rutas responden 503.
- Al arrancar se escribe en el log `[PROTEGIDOS-CLAVE]` con la huella de las dos ranuras compiladas (actual y
  siguiente) y el hospital.

## Configuración

El JSON es la ley. Cada campo documenta en su `_doc` el formato, el rango y los límites.

- Un campo de `server`, `heartbeat` o `secrets` (y también de `tls` y `authz`) que falta, tiene otro tipo o está
  fuera de rango: aviso `[CONFIG-DEFAULT]` y se usa el defecto, que es el mismo valor que trae
  `config/etcd-server.json`. El proceso arranca.
- Campos que ya no se usan: aviso `[CONFIG-OBSOLETO]`.
- **Sin defecto, no arranca**: en `tls.modo=mtls`, un certificado ilegible (`[ETCD-TLS-FATAL]`); en
  `almacen.modo=etcd`, `endpoints`, `prefijo` o los certificados ausentes o mal formados (`[ETCD-ALMACEN-FATAL]`);
  en `almacen_claves.modo=vault`, las direcciones o los certificados de Vault (`[ETCD-VAULT-FATAL]`). Son errores de
  despliegue, no fallos pasajeros.
- Un `modo` ausente o mal escrito va siempre al modo seguro (`mtls`, `etcd`, `vault`): una errata nunca rebaja la
  seguridad.

Comprobar sin arrancar (rc 0 sin defectos, 1 con alguno):

```bash
/opt/argus/etcd-server/bin/etcd-server -c /etc/ml-defender/etcd-server/etcd-server.json --check-config
```

### Ficheros de este directorio

- `config/etcd-server.json`: la configuración de la VM etcd. `almacen.endpoints`, `almacen.prefijo` y
  `protegidos.hospital_id` los sustituye Ansible desde el inventario (`make deploy-configs`).
- `config/etcd-server.smoke-enterprise.json`: **solo** para los actos I y III de emecas++ (`test-e2e-vault`,
  `vault-fault-inject`). HTTP en claro en 127.0.0.1, registro y claves en memoria (DEBT-VAULT-ENTERPRISE-SMOKE-VM-001).
  Avisa al arrancar y periódicamente (`[ETCD-TLS-DESACTIVADO]`, `[ETCD-ALMACEN-MEMORIA]`, `[ETCD-CLAVES-MEMORIA]`)
  para que nadie lo deje encendido.

## Despliegue

Desde el Mac, en la raíz del repositorio, con el defender y la VM etcd levantadas:

```bash
make pipeline-build PROFILE=production
make etcd-vm-deploy PROFILE=production
```

`etcd-vm-deploy` hace, en orden:

1. `scripts/etcd_ha/d312_etcd_vm_deploy.sh`: copia el binario compilado en el defender y sus librerías de
   `/usr/local/lib` con un manifiesto sha256, e instala en la VM etcd los paquetes Debian de las demás (sacados de
   `ldd` y `dpkg -S`, sin listas a mano). Pasa la identidad de `/etc/ml-defender/etcd-server/` del defender a la VM
   etcd por un tubo ssh, sin tocar el disco del Mac ni `/vagrant`, y la comprueba fichero a fichero con sha256.
   Instala en `/opt/argus/etcd-server/`, verifica el manifiesto y que no haya librerías sin resolver.
2. `make deploy-configs`: Ansible escribe `etcd-server.json` con los valores del inventario (el JSON no viaja con
   el paso 1).
3. Reinicia la unidad y exige que quede sana (`make etcd-vm-check`).

La unidad systemd la instala el Vagrantfile (aprovisionador `etcd-server-unit`, `run: always`). Hasta el primer
despliegue queda habilitada pero sin arrancar (`ConditionPathExists` sobre el binario y el JSON), así que un
`vagrant up` desde cero no falla. Arranca después de etcd, Vault y su desellado. `Restart=always`,
`StartLimitIntervalSec=0`: nunca se rinde.

### Operación

| Tarea (Mac) | Qué hace |
|---|---|
| `make etcd-vm-estado` | informe de etcd-server, miembros etcd y Vault (rc 0 siempre) |
| `make etcd-vm-check` | estricto: rc 1 si algo no está sano tras `ETCD_VM_ESPERA_S` (lo usa EMECAS) |
| `make etcd-server-start` / `make etcd-server-stop` | arranca (y comprueba) o para el servicio |

## Qué pasa si algo cae

| Cae | Qué hace el etcd-server |
|---|---|
| **etcd** | etcd es la única verdad. Las lecturas del registro salen de la última copia en memoria y las escrituras dan 503, con aviso `[ETCD-ALMACEN-NO-DISPONIBLE]` cada `aviso_intervalo_s`. Vuelve a conectar sin reiniciar: abre un canal gRPC nuevo, como mucho uno cada `reconexion_max_ms`. Si no pudo registrarse al arrancar, lo reintenta con cada latido. |
| **Vault** | Reintenta cada dirección `reintentos_por_direccion` veces con espera creciente (de `espera_inicial_ms` a `espera_max_ms`) y pasa a la siguiente. Agotada la lista: `[ETCD-VAULT-NO-DISPONIBLE]` con el error de cada una, sirve la **última ventana conocida** (sin ella, `/secrets` da 503 y no se genera ninguna clave), rotar da 503, y vuelve a probar cada `sondeo_s`. |
| **El propio etcd-server** | systemd lo relanza cada 5 s, sin límite. Mientras tanto, los componentes del pipeline arrancan y protegen, pero sin clave HMAC no firman bronce ni CSV hasta que vuelvan etcd-server, etcd y Vault (`make etcd-vm-aviso` lo dice en `pipeline-start`). |
| **Un certificado o la configuración** | Ver Configuración: los que no tienen defecto paran el arranque con su etiqueta `*-FATAL`. |

## Tests

En el defender, con el resto de componentes: `make test-components PROFILE=<perfil>` (ctest en
`etcd-server/build-<perfil>`). Cubren configuración (`test_etcd_server_config`), autorización
(`test_etcd_server_authz`), registro y latidos (`test_registro_componentes`, `test_latido_datos`), claves y ventana de
dos (`test_almacen_claves`, `SecretsManagerGracePeriod`, `test_secrets_manager_simple`, `test_hmac_integration`),
manifiesto de protegidos (`test_protegidos_servidor`) y autonomía (`test_autonomy_integration`).

De punta a punta lo prueba EMECAS+++, entre otras: `lab-e2e-reinicio-etcd` (para el etcd-server con el pipeline
vivo: misma huella de clave, ningún registro nuevo, latidos 200 al volver y todo el bronce del intervalo verificable)
y `lab-e2e-protegidos` (el manifiesto aplicado en el firewall).

## Límites actuales

- **Un solo nodo** de etcd y de Vault en el laboratorio. La configuración ya admite varios
  (`almacen.endpoints` y `almacen_claves.vault_addrs`, de 1 a 7), pero la alta disponibilidad (Raft con ≥ 3 nodos,
  Vault en HA) es el PR2 de DEBT-ETCD-HA-TLS-RAFT-001 y todavía no está medida.
- En el laboratorio, `argus-infra` vive en la VM etcd, que hace de máquina del administrador (no hay RAM para otra
  VM; ADR-060, D11). En un despliegue real va en la máquina del administrador.

## Referencias

- ADR-060: manifiesto firmado de rangos protegidos (`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md`).
- Diseño del PR1 (mTLS, registro en etcd, claves en Vault, servicio en la VM etcd): `docs/ml-heads/day312_diseno.md`.
- Deuda: DEBT-ETCD-HA-TLS-RAFT-001 en `docs/BACKLOG.md`.
