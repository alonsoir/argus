# ADR-035 — etcd-server Alta Disponibilidad

**Status:** CLOSED — ver ADR-0043 D6
**Date:** 2026-04-15  
**Author:** Alonso Isidoro Roman  
**Feature destino:** `feature/bare-metal` (fase tardía)  
**Pre-requisitos:** ADR-034 Deployment Topology Declarativa

---

## Contexto

En la arquitectura single-node actual, `etcd-server` es un SPOF (Single Point of Failure).
En una topología hospitalaria de 30+ nodos, un fallo de etcd implica:

- Pérdida de registro de componentes — ningún componente puede descubrir a los demás
- Pérdida de distribución de seeds — nuevos nodos no pueden arrancar con crypto
- Pérdida de configuración centralizada — cambios de ACL no se propagan

En infraestructura crítica (hospitales, centros de salud), esto no es aceptable.
Un ataque de denegación de servicio dirigido a etcd tumba el sistema de detección completo.

Esta ADR define la estrategia de Alta Disponibilidad para `etcd-server` usando
un cluster de 3 nodos con consenso Raft, integrado con `deployment.yml` (ADR-034).

---

## Decisión

### D1 — Cluster etcd de 3 nodos mínimo

El quorum de Raft requiere `(n/2)+1` nodos activos. Con 3 nodos:
- Tolerancia a fallos: 1 nodo puede caer sin pérdida de servicio
- Quorum: 2/3 nodos necesarios para escrituras

Con 5 nodos (topologías grandes):
- Tolerancia a fallos: 2 nodos pueden caer
- Recomendado para hospitales con >3 plantas

```yaml
# En deployment.yml (ADR-034)
etcd:
  cluster_size: 3          # mínimo recomendado
  nodes:
    - host: etcd-0         # nodo líder inicial
      ip: 192.168.10.10
    - host: etcd-1
      ip: 192.168.10.11
    - host: etcd-2
      ip: 192.168.10.12
  peer_port: 2380
  client_port: 2379
  data_dir: /var/lib/etcd
  auto_compaction_retention: "1h"
```

### D2 — TLS mutuo entre nodos del cluster

La comunicación peer-to-peer entre nodos etcd usa TLS mutuo (mTLS):
- CA propia del despliegue (generada por `provision.sh --etcd-ca`)
- Certificados por nodo firmados por la CA
- Rotación de certificados documentada en `docs/operations/etcd-cert-rotation.md`

La comunicación cliente→etcd también usa TLS. Los 6 componentes del pipeline
presentan certificados de cliente firmados por la misma CA.

**Pregunta abierta OQ-1:** ¿Usamos la CA de `provision.sh` (Ed25519, libsodium)
o una CA X.509 estándar (RSA/ECDSA) para compatibilidad con herramientas etcd nativas?
→ **Pendiente Consejo.**

### D3 — Integración con deployment.yml (ADR-034)

El cluster etcd se describe en `deployment.yml` junto con el resto de la topología.
Ansible genera la configuración de cada nodo etcd a partir del fichero declarativo.

`make validate-topology` (ADR-034 D5) verifica que el cluster etcd tiene quorum
antes de aprobar el despliegue.

### D4 — Estrategia de failover para los 6 componentes del pipeline

Los componentes del pipeline se conectan a etcd usando una lista de endpoints:

```json
{
  "etcd_endpoints": [
    "https://192.168.10.10:2379",
    "https://192.168.10.11:2379",
    "https://192.168.10.12:2379"
  ],
  "etcd_dial_timeout_ms": 5000
}
```

El cliente etcd en C++ (ya existente) se actualiza para intentar los endpoints
en orden, con retry exponencial. Si los 3 fallan → fail-closed (componente no arranca).

### D5 — Backup y recuperación del cluster etcd

`make etcd-snapshot` genera un snapshot de etcd en `/var/backups/etcd/`:
- Snapshot diario automatizado vía systemd timer
- Retención: 7 días
- Restauración documentada en `docs/operations/etcd-recovery.md`

**Integración con Recovery Contract (ADR-024 OQ-6):** el procedimiento de
rotación de seeds incluye un paso de snapshot etcd pre-rotación.

### D6 — Tamaño mínimo de cluster por topología hospitalaria

| Tamaño del hospital | Plantas | Nodos pipeline | Cluster etcd |
|---|---|---|---|
| Pequeño (centro de salud) | 1-2 | < 10 | 3 nodos |
| Mediano (hospital comarcal) | 3-5 | 10-30 | 3 nodos |
| Grande (hospital regional) | >5 | >30 | 5 nodos |

---

## Consecuencias

**Positivas:**
- Elimina el SPOF más crítico de la arquitectura multi-nodo
- Tolerancia a fallo de 1 nodo sin interrupción del servicio de detección
- Recuperación automática del cluster cuando el nodo caído vuelve (Raft)
- Backup automático con retención configurable

**Negativas / Trade-offs:**
- Requiere 3 nodos físicos o VMs dedicadas a etcd — coste de infraestructura real
- mTLS añade complejidad operativa: gestión de CA y certificados
- La CA de despliegue se convierte en un activo crítico — compromiso = compromiso total
- Para centros de salud muy pequeños (1 nodo), 3 nodos etcd puede ser desproporcionado

**Pregunta abierta OQ-2:** ¿Cómo manejamos despliegues en centros de salud
de 1-2 nodos donde un cluster etcd de 3 no es viable económicamente?
Opciones: A) etcd single-node con backup frecuente (acepta SPOF documentado)
B) etcd embebido en el pipeline como modo degradado
→ **Pendiente Consejo.**

---

## Preguntas abiertas para el Consejo

| ID | Pregunta | Opciones |
|----|----------|---------|
| OQ-1 | CA para mTLS etcd: ¿Ed25519/libsodium (coherente con ADR-025) o X.509 estándar? | A: Ed25519 · B: X.509 ECDSA P-256 |
| OQ-2 | Despliegues muy pequeños (1-2 nodos): ¿single-node etcd aceptable con SPOF documentado? | A: single-node aceptado · B: modo embedded |
| OQ-3 | ¿etcd v3 nativo o Kubernetes etcd (implica introducir k8s)? | Recomendación: etcd v3 nativo. Sin k8s. |
| OQ-4 | Monitorización del cluster: ¿integrar alertas etcd en rag-security, o herramienta externa (Prometheus)? | A: rag-security · B: Prometheus + Alertmanager |

---

## Referencias

- ADR-021: seed_families — etcd distribuye seeds, su HA es prerequisito
- ADR-024: Noise_IKpsk3 — los peers usan etcd para descubrimiento
- ADR-034: Deployment Topology — `deployment.yml` describe el cluster etcd
- docs/operations/Recovery Contract — snapshot etcd es paso previo a rotación de seeds
- etcd documentation: https://etcd.io/docs/v3.5/op-guide/clustering/