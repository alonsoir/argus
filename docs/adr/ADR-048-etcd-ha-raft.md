# ADR-048 — etcd HA con Raft nativo

- **Estado:** En preparación (implementación post-FEDER)
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
