# ADR-034 — Deployment Topology Declarativa

**Status:** DRAFT — pendiente revisión Consejo de Sabios  
**Date:** 2026-04-15  
**Author:** Alonso Isidoro Roman  
**Feature destino:** `feature/bare-metal` (fase tardía)  
**Pre-requisitos:** ADR-026 XGBoost + ADR-029 bare-metal + topología multi-VM + Ansible

---

## Contexto

El despliegue actual de aRGus NDR asume una topología single-node (Vagrant, desarrollo).
En producción real — un hospital, un centro de salud, un ayuntamiento — la infraestructura
es multi-nodo y multi-planta. Cada planta tiene su propia red, sus propios switches, y sus
propios requisitos de aislamiento.

Sin una representación declarativa de la topología, el despliegue multi-nodo requiere
configuración manual por nodo, lo que no escala, introduce errores humanos, y hace imposible
garantizar la coherencia criptográfica entre componentes (seed_families, ADR-021).

Esta ADR define `deployment.yml` como Single Source of Truth (SSOT) de la topología física,
y Ansible + Jinja2 como motor de despliegue, con Jenkins como orquestador CI/CD.

---

## Decisión

### D1 — deployment.yml como SSOT

Un único fichero declarativo describe la topología completa de un despliegue:
plantas, nodos por planta, componentes por nodo, y parámetros de red.

```yaml
deployment:
  site: "Hospital Perpetuo Socorro"
  environment: production  # production | staging | dev

floors:
  - id: floor_0
    name: "Planta Baja — Urgencias"
    nodes: 1
    components:
      sniffer: 1
      ml-detector: 2
      firewall-acl-agent: 1
    seed_family: floor_0_seed   # ADR-021 multi-familia

  - id: floor_1
    name: "Planta 1 — Hospitalización"
    nodes: 10
    components:
      sniffer: 10
      ml-detector: 10
      firewall-acl-agent: 10
    seed_family: floor_1_seed

aggregation:
  rag-ingester: 30        # suma ml-detector + firewall de todas las plantas
  rag-security: 1         # único punto de consulta semántica
  etcd-server: 3          # cluster HA — ver ADR-035

network:
  zeromq_transport: tcp
  crypto: chacha20-poly1305   # ADR-013/020
  noise_p2p: enabled          # ADR-024, cuando esté implementado
```

### D2 — Tres capas de despliegue

1. **`deployment.yml`** — topología declarativa (plantas × nodos × componentes)
2. **Ansible + Jinja2** — motor de despliegue. Itera `deployment.yml` y genera:
    - Configuraciones JSON por nodo (`firewall.json`, `sniffer.json`, etc.)
    - Seeds por `seed_family` (invoca `provision.sh` por familia)
    - Systemd units por componente
    - Perfiles AppArmor por componente
3. **Jenkins** — orquestador CI/CD. Pipeline: lint → build → sign → deploy → verify

### D3 — seed_families por planta (ADR-021 multi-familia)

Cada planta tiene su propio `seed_family`. El blast radius de un compromiso
queda limitado a la planta afectada — los canales de otras plantas permanecen intactos.

`provision.sh` acepta `--family <floor_id>` para generar seeds por familia.

### D4 — Aggregation fanout

El fanout de N rag-ingesters → 1 rag-security se resuelve con:
- ZeroMQ PUSH/PULL (N productores, 1 consumidor)
- `trace_id` con origen `floor_id:node_id:component` para trazabilidad
- rag-security deduplica por `trace_id` — sin duplicados bajo reconexión

**Pregunta abierta OQ-1:** ¿Fanout > 50 requiere `rag-ingester-coordinator`
como componente intermedio, o ZeroMQ PUSH/PULL escala suficiente?
→ **Pendiente Consejo. Benchmark requerido antes de ACEPTADO.**

### D5 — Validación de topología pre-despliegue

`make validate-topology` verifica `deployment.yml` antes de cualquier despliegue:
- Coherencia de seed_families vs componentes declarados
- Ausencia de colisiones de puertos ZeroMQ entre nodos
- Presencia de binarios firmados para todos los componentes declarados

---

## Consecuencias

**Positivas:**
- Despliegue reproducible en cualquier topología hospitalaria con un único fichero
- Coherencia criptográfica garantizada por diseño (seed_families por planta)
- CI/CD completo desde `deployment.yml` hasta verificación de integridad post-despliegue
- Escalable: añadir una planta = añadir un bloque en el YAML

**Negativas / Trade-offs:**
- Introduce Ansible y Jenkins como dependencias de infraestructura
- `deployment.yml` se convierte en fichero crítico de seguridad — debe estar firmado
  y versionado. Compromiso de este fichero = compromiso de toda la topología.
- Fanout alto (OQ-1) puede requerir un componente adicional no planificado

---

## Preguntas abiertas para el Consejo

| ID | Pregunta | Opciones |
|----|----------|---------|
| OQ-1 | Fanout N rag-ingesters → 1 rag-security: ¿ZeroMQ PUSH/PULL es suficiente a >50 nodos? | A: PUSH/PULL nativo · B: rag-ingester-coordinator |
| OQ-2 | ¿Jenkins es la elección correcta para CI/CD, o preferimos GitHub Actions + self-hosted runner en el hospital? | A: Jenkins · B: GitHub Actions · C: Gitea Actions (air-gap) |
| OQ-3 | ¿`deployment.yml` debe firmarse con Ed25519 (mismo esquema ADR-025/032)? | Recomendación: sí, siempre |
| OQ-4 | ¿Ansible Galaxy (roles externos) o playbooks propios únicamente? Implicaciones de supply chain. | A: propios únicamente (más seguro) · B: roles auditados de Galaxy |

---

## Referencias

- ADR-021: INVARIANTE-SEED-001 + seed_families multi-nodo
- ADR-024: Noise_IKpsk3 (cifrado P2P entre nodos)
- ADR-025: Plugin Integrity — mismo esquema de firma para `deployment.yml`
- ADR-029: Variantes hardened — topología multi-VM es prerequisito
- ADR-035: etcd-server HA — depende de este ADR para describir el cluster