# ADR-048 — etcd HA con Raft nativo

- **Estado:** En revisión (DAY324): se implementa en el PR2 de DEBT-ETCD-HA-TLS-RAFT-001; ver «Revisión DAY324» al final
- **Fecha:** 2026-05-23
- **Autor:** Alonso Isidoro Román
- **Revisores:** Consejo de Sabios (pendiente votación formal)
- **Referencias:** ADR-047 (resiliencia en capas), ADR-046 (ventana de correlación)

---

## Contexto

etcd-server actualmente corre en modo single-node. Es un Single Point of Failure (SPOF) conocido y aceptado transitoriamente como deuda arquitectónica, con Falco + cron como mecanismo de resiliencia de primera línea mientras el quórum no esté implementado (ver ADR-047, Capa 1 transitoria).

La arquitectura objetivo elimina este SPOF mediante un cluster etcd en modo HA con consenso Raft.

---

## Decisión

### Modelo de cluster

Cluster etcd de **3 nodos** con Raft nativo sobre gRPC/HTTP2.

**Topología mínima:** 3 nodos toleran 1 fallo manteniendo quórum (mayoría = 2 de 3). 5 nodos tolerarían 2 fallos simultáneos pero es decisión post-FEDER.

### Lo que NO se usa

**Sin ZooKeeper.** ZooKeeper existe para dar consenso a sistemas que no lo tienen nativamente. etcd ya implementa Raft. Usar ZooKeeper con etcd sería redundante y añadiría complejidad operacional innecesaria en un entorno donde el número de componentes ya es significativo.

**Sin ZeroMQ para replicación entre nodos etcd.** ZeroMQ tiene su lugar en aRGus para la comunicación entre componentes del pipeline de detección. La replicación del cluster etcd es responsabilidad exclusiva del protocolo Raft interno de etcd. Introducir ZeroMQ en la capa de replicación competiría con el protocolo de consenso nativo y produciría comportamiento indefinido.

### Modelo de consistencia

Raft garantiza consistencia fuerte, no consistencia eventual. Una escritura no se confirma hasta que la mayoría de nodos la ha reconocido. El cliente recibe ACK solo cuando el quórum ha aceptado el cambio.

**Propiedad garantizada ante split-brain:** Con 3 nodos y una partición de red 1+1+1, ningún nodo forma quórum solo. El cluster se detiene antes de aceptar escrituras inconsistentes. Esto es una propiedad de seguridad garantizada por Raft, no un riesgo.

### Acceso desde el pipeline

Los componentes del pipeline aRGus se conectan a cualquier nodo del cluster. etcd redirige internamente al líder cuando es necesario. La reelección ante caída del líder ocurre en ~200ms, transparente para el pipeline.

---

## Lo que es código nuestro

Únicamente el bootstrap del cluster. Cada instancia etcd-server debe arrancar conociendo las direcciones de sus peers mediante los flags de cluster correspondientes. Es configuración de arranque, no implementación de algoritmo de consenso.

```
# Ejemplo conceptual de flags de arranque por nodo
--name=etcd-node-1
--initial-cluster=etcd-node-1=http://node1:2380,etcd-node-2=http://node2:2380,etcd-node-3=http://node3:2380
--initial-cluster-state=new
--listen-peer-urls=http://node1:2380
--listen-client-urls=http://node1:2379
```

La adaptación de `etcd-server` consiste en añadir soporte para arranque en modo cluster mediante estos flags, en lugar del modo single-node actual.

---

## Lo que NO es código nuestro

- El algoritmo de consenso Raft
- La replicación del log entre nodos
- La detección de fallo del líder
- El proceso de reelección
- La redirección de clientes al líder

Todo lo anterior es responsabilidad del binario etcd.

---

## Hardware objetivo

Según el plan de adquisición FEDER:

| Nodo | Hardware | Rol |
|------|----------|-----|
| etcd-node-1 | N100 miniPC (Intel i226-V NIC) | Nodo etcd |
| etcd-node-2 | RPi5 8GB | Nodo etcd |
| etcd-node-3 | RPi5 8GB | Nodo etcd |

Los tres nodos son funcionalmente idénticos en cuanto al rol etcd. Todos tienen la misma información operacional compartida. Si alguno se cae, la reelección es transparente porque todos los nodos activos tienen el mismo estado committed.

---

## Estado transitorio hasta implementación

Mientras el quórum no esté implementado, la resiliencia de etcd-server se basa en:

1. **Falco** monitorizando el proceso etcd-server
2. **cron** intentando recuperación automática ante caída detectada
3. **Discord** notificando al administrador si las capas anteriores no resuelven el fallo

Este mecanismo transitorio está especificado en ADR-047 (Capa 1 transitoria y Capa 2).

---

## Consecuencias

- La implementación del quórum es trabajo post-FEDER pero la decisión arquitectónica está comprometida desde este ADR.
- El código de `etcd-server` debe diseñarse desde ahora con la separación clara entre lógica de negocio y modo de arranque (single vs cluster), para que la migración sea un cambio de configuración, no de arquitectura.
- Las pruebas de caos de DAY 161 se ejecutan sobre single-node transitorio. Los resultados establecen la línea base de comportamiento con la que comparar cuando llegue el HA.
- Los componentes del pipeline no deben asumir single-node en su código de conexión a etcd. El endpoint debe ser configurable para apuntar a cualquier nodo del cluster en el futuro.

---

## Revisión DAY324 (decisiones de Alonso; PR2 de DEBT-ETCD-HA-TLS-RAFT-001)

El PR1 (DAY312-DAY323, PR #153) cambió la arquitectura sobre la que se escribió este ADR. Donde esta revisión
contradiga a las secciones anteriores, manda la revisión.

### Qué se mantiene

- Tres miembros etcd con el Raft de etcd: un fallo tolerado (quórum 2 de 3). Sin ZooKeeper y sin ZeroMQ en la
  replicación. Consistencia fuerte; una partición 1+1+1 se detiene antes de aceptar escrituras inconsistentes.
- Lo que es código nuestro es arranque y configuración, no consenso.

### Qué cambia

1. **Los componentes no hablan con etcd.** Hablan por mTLS con el etcd-server (`etcd-server/README.md`). Solo el
   etcd-server habla con etcd, con su certificado (su CN es su usuario RBAC). El «Acceso desde el pipeline» queda así:
   cada componente lleva en su JSON `etcd.endpoints` (de 1 a 7; el etcd-client ya usa la primera que responde y
   conmuta) con **los tres etcd-server**, y cada etcd-server lleva en `almacen.endpoints` **los tres miembros etcd**.
2. **Un etcd-server por VM**, junto a su miembro etcd y su nodo Vault (ADR-049, revisión DAY324). Laboratorio: tres
   VMs idénticas con Debian mínimo (la box de la VM etcd): la de hoy (192.168.100.20) y dos nuevas (.21 y .22; nombres
   a fijar en el Vagrantfile). Perder una VM es perder a la vez un miembro etcd, un nodo Vault y un etcd-server.
3. **La reelección en «~200 ms» no está medida**, y con los valores por defecto de etcd (`heartbeat-interval` 100 ms,
   `election-timeout` 1000 ms) no es posible: tras caer el líder, los seguidores esperan al menos un
   `election-timeout`. Se sustituye por una medida (abajo). Los dos tiempos van en la plantilla de `etcd.conf.yml`,
   con rango y defecto documentados.
4. **Configuración por inventario.** El número de miembros y sus direcciones salen del inventario de Ansible;
   `etcd.conf.yml` se genera con una plantilla Jinja2, igual que `make deploy-configs` genera el JSON del etcd-server.
   Nada se escribe a mano en cada VM.
5. **Los miembros son infraestructura** (ADR-060). Cada IP nueva entra en la categoría `infraestructura` de la
   plantilla del manifiesto (/32, con su interfaz y su MAC fija) antes del primer EMECAS. El DAY317 (NTP de la VM
   etcd) y el DAY323 (NTP de los sensores) midieron lo que pasa si no: el tráfico del plano de control dentro de un
   episodio DDoS.
6. **Red.** Hoy etcd escucha solo en 127.0.0.1. Con tres VMs, peers (2382) y clientes (2381) escuchan también en la IP
   de la LAN, aceptados solo desde los otros dos miembros (nftables), con mTLS y certificados con la IP de cada nodo
   en el SAN. El 2379 del etcd-server, como hoy, solo desde el defender.
7. **Hardware.** El plan de adquisición FEDER (N100, RPi5) ya no aplica. Laboratorio: VMs de VirtualBox en el Mac.
   Producción: sin decidir.
8. **«Estado transitorio».** Lo que hay hoy, medido el DAY324 (abajo): systemd relanza etcd (`Restart=on-failure`) y
   el etcd-server (`Restart=always`, sin límite), y tras un corte de luz todo volvió sin intervención.

### Medido DAY324 (línea base: un nodo)

- El Mac se apagó a las 23:09 del DAY323 con las VMs encendidas (VirtualBox: `Caught signal: Terminated: 15`); las
  seis VMs quedaron `aborted`. `vagrant up etcd --no-provision`: etcd, Vault (desellado solo) y el etcd-server
  volvieron sin intervención, y `make etcd-vm-estado` dio SANO a la primera (etcd term 5, índice 1781, retraso 0;
  Vault 200; manifiesto v5).
- etcd 3.6.16: base de 1,6 MB (cuota 2,1 GB). Vault 2.2.1: raft, HA activo, Shamir 1 de 1, índice 707.
- VM etcd (1463 MB útiles): 390 MB usados en reposo. Pico por servicio desde el arranque (`memory.peak` del cgroup):
  vault 234 MB, falco 121, etcd 64, wazuh-agent 58, etcd-server 30; el resto, menos de 20 MB cada uno. Presión de
  memoria (PSI) 0.
- Disco: 3,1 GB por VM (sin `linked_clone`); el Mac tiene 206 GB libres.
- Mac con solo la VM etcd levantada: 85 % de memoria libre.

### Tamaño de cada VM

Los picos de los servicios suman ~510 MB, más el kernel y la base del sistema. 768 MB quedan en el límite y la VM no
tiene swap: un pico de más es el OOM matando un proceso. Las tres VMs empiezan con **1024 MB**; se mide el pico del
aprovisionamiento desde cero y de un EMECAS+++ (`memory.peak` por servicio, PSI, OOM en `dmesg`) y el tamaño final
sale de esa medida. Presupuesto del laboratorio: hoy 18 944 MB asignados; con 3 × 1024 en lugar de la VM de 1536,
20 480 MB (+1536); con 3 × 768, 19 712 MB (+768). CPU: dos vCPU por VM, como hoy (20 vCPU sobre 16 hilos del Mac);
etcd es sensible a la latencia, así que se cuentan los cambios de líder durante un EMECAS+++.

### Qué se mide en el PR2

Cada medida con su predicción escrita antes y su criterio fijado por Alonso.

- Caída del líder y de un seguidor: tiempo hasta el líder nuevo y hasta que el pipeline vuelve a tener latidos y
  `/secrets` con 200.
- Un miembro que vuelve: tiempo hasta retraso 0 (`etcd_vm_estado.sh`).
- Apagar los tres y encenderlos uno a uno: con uno, sin quórum (qué responde el etcd-server: lecturas de su copia en
  memoria y escrituras 503); con dos, quórum de nuevo.
- Cambios de líder durante un EMECAS+++ completo sin caídas provocadas (se espera ninguno).
- Publicación concurrente del manifiesto en dos etcd-server (abajo).

### Código que el HA obliga a cambiar

- `PUT /v1/protegidos` lee la versión vigente, comprueba y escribe `v/<N>` y `vigente` bajo un mutex del proceso. Con
  un etcd-server es correcto; con varios, dos publicaciones simultáneas pueden dejar `vigente` en una versión anterior
  a la última del histórico (los firewalls no retroceden, porque rechazan toda versión ≤ la aplicada, pero el
  etcd-server serviría un vigente viejo). Se hace con una transacción de etcd: `v/<N>` solo si no existe y `vigente`
  solo si no ha cambiado desde que se leyó. `IRegistryStore` gana esa operación, con un test que reproduce la carrera.
- Toda escritura del etcd-server que lee antes de escribir se revisa igual. Registro y latidos: gana la última,
  correcto. Ventana de claves en Vault: ya va con CAS; se mide la carrera de dos etcd-server creando la primera clave
  del mismo CN.

### Plan en PRs pequeños

1. PR2a: medida y diseño (esta revisión y la de ADR-049).
2. PR2b: tres VMs y etcd en clúster: inventario, plantilla de `etcd.conf.yml`, PKI con la IP de cada nodo, nftables,
   plantilla del manifiesto y vigilancia (Falco, Wazuh, argus-disco) en las VMs nuevas.
3. PR2c: Vault en clúster (ADR-049) y su Ansible.
4. PR2d: un etcd-server por VM, las direcciones en los JSON por Ansible y la transacción del manifiesto.
5. PR2e: las medidas de caída y EMECAS+++ desde cero.
