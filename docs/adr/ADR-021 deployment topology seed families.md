# ADR-021 — Deployment Topology SSOT and Channel Seed Families

**Estado:** Aprobado (FASE 3 — post-arXiv)
**Fecha:** 2026-03-28 (DAY 100)
**Autores:** Alonso Isidoro Roman + Consejo de Sabios (Grok/xAI, Claude/Anthropic)
**Relacionado:** ADR-013 (seed distribution), ADR-022 (threat model), ADR-001 (deployment stack)

---

## Contexto

En DAY 98–99 se completó la migración completa a `CryptoTransport` (ADR-013 PHASE 2).
Los contextos HKDF son ahora simétricos por canal gracias a `contexts.hpp`.
El siguiente paso lógico es escalar a topologías distribuidas reales con múltiples
instancias de cada componente.

La pregunta es: ¿cómo se gestiona la distribución de seeds cuando hay N sniffers,
P ml-detectors, R firewalls en hosts distintos?

La solución de FASE 1 (seed único por componente en instancia única) no escala
a topologías multi-nodo. Se necesita un modelo de **familias de canal**.

---

## Decisión

### 1. deployment.yml como SSOT de topología

Se introduce `deployment.yml` como **única fuente de verdad** de la topología
distribuida de Argus. Define instancias, hosts, y pertenencia a familias de canal.

```yaml
topology:
  sniffer:
    instances: [sniffer1]
    host: 192.168.56.10
    seed_families: [family_A]
  ml-detector:
    instances: [ml-detector1, ml-detector2]
    hosts: [192.168.56.11, 192.168.56.12]
    seed_families: [family_A, family_B, family_C]
  firewall:
    instances: [firewall1]
    host: 192.168.56.13
    seed_families: [family_B, family_C]
  rag-ingester:
    instances: [rag-ingester1]
    host: 192.168.56.14
    seed_families: [family_C]
  rag-local:
    instances: [rag-local1]
    host: 192.168.56.15
    seed_families: []
```

### 2. Familias de canal (seed families)

Cada canal lógico tiene su propia familia de seeds. Un componente puede pertenecer
a varias familias y recibe un `seed.bin` distinto por familia, en paths separados.

| Familia | Canal lógico | Miembros |
|---------|-------------|----------|
| family_A | captura → detección | sniffer + ml-detector |
| family_B | detección → enforcement | ml-detector + firewall |
| family_C | artefactos → RAG | ml-detector + firewall + rag-ingester |

**Principio:** la clave HKDF derivada es compartida **solo** entre los miembros
de la misma familia. Un sniffer comprometido no puede derivar las claves del
canal RAG.

### 3. provision.sh refactorizado para leer deployment.yml

En FASE 3, `tools/provision.sh` leerá `deployment.yml` y:
1. Generará un `seed.bin` por familia
2. Distribuirá cada seed solo a los miembros de esa familia
3. Copiará vía SSH/Ansible a `/etc/ml-defender/{component}/seeds/{family}/seed.bin`

### 4. Versioning de contextos HKDF

Los strings de contexto en `contexts.hpp` ya incluyen sufijo de versión (`:v1`).
**Política de versioning:**

- Cambio de topología (nuevos nodos) → **no** requiere bump de versión de contexto
- Cambio de semántica del canal → bump a `:v2`
- Migración: ambas versiones coexisten durante un período de transición documentado

```cpp
// Ejemplo de coexistencia durante migración
constexpr const char* CTX_SNIFFER_TO_ML_V1 = "ml-defender:sniffer-to-ml-detector:v1";
constexpr const char* CTX_SNIFFER_TO_ML_V2 = "ml-defender:sniffer-to-ml-detector:v2";
```

---

## Consecuencias

**Positivas:**
- Topología completamente declarativa — el operador define quién habla con quién
- Principio de mínimo privilegio a nivel de canal criptográfico
- `provision.sh` se convierte en herramienta de infraestructura completa
- Compatible con Ansible (FASE 3 CI/CD)

**Negativas / restricciones:**
- Requiere que `deployment.yml` exista antes de provisionar
- Un componente en múltiples familias recibe múltiples seeds — la selección
  del seed correcto por canal es responsabilidad del componente
- Aumenta la superficie de gestión de secrets en despliegues grandes

---

## Estado de implementación

| Elemento | Estado |
|----------|--------|
| `contexts.hpp` — contextos v1 | ✅ DAY 99 |
| `deployment.yml` — schema y ejemplo | ⏳ FASE 3 |
| `provision.sh` — lectura de manifiesto | ⏳ FASE 3 |
| Multi-seed por componente | ⏳ FASE 3 |
| Vagrantfile multi-VM | ⏳ FASE 3 |

**Pre-requisito:** arXiv submission → milestone gate antes de FASE 3.

---

## Addendum DAY 116 — 13 Abril 2026

### Invariante criptográfico descubierto: seed_family compartido

**Contexto del hallazgo:**
Durante la implementación de `provision.sh --reset` (DEBT-ADR025-D11, DAY 116),
la primera versión de `reset_all_keys()` generó seeds independientes para cada
componente. Resultado: HKDF derivó claves distintas en cada extremo del canal →
MAC verification failed en todos los PUTs de configuración. Pipeline en fail-closed.

**Root cause:** el invariante "todos los componentes comparten el mismo seed_family
en despliegue single-node" estaba implícito en el código desde DAY 95, nunca
documentado explícitamente.

**Fix aplicado (commit 3c0a214f):** `reset_all_keys()` genera UN seed aleatorio
y lo distribuye a los 6 componentes antes de regenerar los keypairs Ed25519.

### Invariante explícito

> **INVARIANTE-SEED-001:** En un despliegue single-node, todos los componentes
> del pipeline DEBEN compartir el mismo `seed.bin` (seed_family). HKDF deriva
> subkeys distintos por canal mediante el contexto (CTX_ETCD_TX/RX, etc.), pero
> el material raíz es común. Cualquier operación que regenere seeds DEBE
> distribuir el mismo valor a los 6 componentes.

**Test de validación:** TEST-INVARIANT-SEED — verifica que post-reset todos los
`seed.bin` de los 6 componentes son byte-a-byte idénticos.

### Regresión respecto al modelo multi-familia original

El diseño original de este ADR (DAY 100) definía seed_families distintas por canal:
- family_A: sniffer ↔ ml-detector
- family_B: ml-detector ↔ firewall
- family_C: ml-detector ↔ firewall ↔ rag-ingester

Este modelo es arquitecturalmente superior: un componente comprometido solo expone
los seeds de los canales en que participa. El blast radius queda contenido.

La simplificación a seed único fue una decisión pragmática para el despliegue
single-node actual (un solo Vagrantfile, 6 componentes en el mismo host). En esta
topología, la separación por familias no aporta protección real porque un atacante
con acceso al host tiene acceso a todos los seed.bin igualmente.

**Implicación para producción multi-nodo:** el modelo de familias DEBE reimplementarse
cuando los componentes estén en hosts separados. La separación por familia limita
el blast radius de un host comprometido — el atacante solo obtiene los seeds de
los canales que pasan por ese host, no el seed raíz global.

### Amenaza de inspección de RAM (nueva — DAY 116)

**Amenaza identificada:** un atacante con capacidad de RAM forensics en cualquier
componente puede extraer el seed_family de memoria, comprometiendo la raíz de
confianza criptográfica de todo el pipeline.

**Mitigación aplicable (sin hardware):**
El seed solo se necesita durante la derivación HKDF. El flujo correcto es:
seed.bin → load → HKDF derive(tx_key, rx_key) → explicit_bzero(seed) → mlock(tx_key, rx_key)

Post-derivación, el seed no debe permanecer en RAM. Los subkeys derivados deben
estar protegidos con mlock() para evitar swap a disco.

Un atacante que obtiene los subkeys de un canal comprometido NO puede reconstruir
el seed ni los subkeys de otros canales.

**Deuda técnica:** DEBT-CRYPTO-003a — implementar mlock() + explicit_bzero(seed)
post-derivación en seed_client.cpp. Ya estaba en backlog; ahora tiene contexto
de amenaza explícito.

**Mitigación definitiva (hardware):** ADR-033 (TPM 2.0 Measured Boot) — el seed
nunca entra en userspace; la derivación HKDF ocurre dentro del TPM. Post-PHASE 4.

### Estado de implementación actualizado

| Elemento | Estado |
|---|---|
| contexts.hpp — contextos v1 | ✅ DAY 99 |
| seed_family single-node compartido | ✅ DAY 116 (INVARIANTE-SEED-001) |
| explicit_bzero(seed) post-derivación | ⏳ DEBT-CRYPTO-003a |
| mlock() subkeys derivados | ⏳ DEBT-CRYPTO-003a |
| deployment.yml — schema multi-familia | ⏳ producción multi-nodo |
| provision.sh — multi-seed por familia | ⏳ producción multi-nodo |
| TPM derivación hardware | ⏳ ADR-033 post-PHASE 4 |

*Addendum — DAY 116 — 13 Abril 2026*

### Addendum DAY 117 — 14 Abril 2026

#### INVARIANTE-SEED-001 — Validación en producción

TEST-INVARIANT-SEED implementado y ejecutado:
- 3 resets consecutivos (`provision.sh --reset`) → 6 seeds idénticos en cada reset
- `make test-invariant-seed` integrado en `make test-all` como CI gate
- Hashes únicos post-reset: 1/1 (PASSED)

#### Regresión vs multi-familia

INVARIANTE-SEED-001 aplica exclusivamente a deployments single-node (PHASE 3).
En producción multi-nodo, cada familia tendrá su propio seed distinto — el test
deberá parametrizarse por familia. Esta extensión corresponde a la fase de
`deployment.yml` multi-familia (columna ⏳ en tabla de implementación).

#### Backup policy operacional

`cleanup_old_backups()` implementada en `provision.sh`:
- Máximo 2 backups por componente/dir
- Llamada automática en: `reprovision_component`, `reset_all_keys`,
  `reset_plugin_signing_keypair`
- Test: 3 resets → 14 backups (2 × 7 targets: 6 componentes + plugins signing)
- Backups más antiguos eliminados automáticamente al superar el límite

*Addendum — DAY 117 — 14 Abril 2026*
