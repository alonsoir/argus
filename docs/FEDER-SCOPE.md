# FEDER-SCOPE.md — Scope Mínimo Viable para Presentación FEDER
# ML Defender (aRGus NDR) — BACKLOG-FEDER-001
# Deadline: 22 septiembre 2026
# Go/no-go técnico: 1 agosto 2026

## Argumento Central

Un investigador solo + 8 AIs en 1 año ha construido un NDR de grado productivo
para infraestructura crítica que no puede permitirse soluciones comerciales.
Las fases 5 y 6 requieren financiación para escalar más allá de los límites
físicos de un investigador individual.

---

## Scope Mínimo Viable (Demo FEDER)

### Lo que SÍ se necesita
- NDR standalone funcional: pipeline 6/6 (sniffer → ml-detector → firewall-acl-agent)
- 2 nodos Vagrant simulados en la misma máquina (Variant A: Debian+AppArmor+eBPF/XDP)
- Detección en tiempo real sobre tráfico pcap reproducible (CIC-IDS-2017)
- XGBoost plugin (ADR-026) con F1≥0.9978 — IN-DISTRIBUTION, firmado Ed25519
- AppArmor enforce mode en los 6 componentes
- Métricas observables: latencia detección, throughput, tasa falsos positivos
- Reproducibilidad completa: `vagrant up && make bootstrap && make pipeline-start`

### Lo que NO se necesita para la demo
- ADR-038 completo (ACRL federado)
- Federación real entre nodos físicos distintos
- Privacidad diferencial (Year 2-3)
- seL4/Genode (ADR-031 — rama research, nunca a main)
- Despliegue en producción real (requiere DPIA/LOPD)
- ADR-035 etcd HA 3 nodos (suficiente 1 nodo para demo)
- ADR-034 Ansible/Jenkins completo

---

## Prerequisitos Técnicos (go/no-go 1 agosto 2026)

| Prerequisito | Estado | Owner |
|---|---|---|
| ADR-026 merged a main (XGBoost plugin estable) | 🔴 PENDIENTE | DAY 129+ |
| ADR-029 Variants A/B estables (benchmark reproducible) | 🔴 PENDIENTE | BACKLOG |
| Vagrantfile demo reproducible (pcap → detección) | 🔴 PENDIENTE | BACKLOG |
| Pipeline 6/6 RUNNING en VM limpia | ✅ DAY 129 | — |
| AppArmor 6/6 enforce mode | ✅ v0.4.0 | — |
| XGBoost F1≥0.9978 IN-DISTRIBUTION | ✅ DAY 122 | — |
| paper arXiv:2604.04952 activo | ✅ DAY 111 | — |

---

## Milestone Go/No-Go: 1 agosto 2026

Criterio de paso:
1. `vagrant destroy && vagrant up && make bootstrap` completa sin errores
2. `make pipeline-start && make pipeline-status` → 6/6 RUNNING
3. Script demo ejecuta pcap CIC-IDS-2017 → detección visible en logs
4. `make test-all` → ALL TESTS COMPLETE
5. XGBoost plugin cargado y firmado verificado en pipeline live

Si el go/no-go pasa → contactar a Andrés Caro Lindo (UEx/INCIBE) para fijar fecha presentación antes del 22 septiembre 2026.

---

## Script Demo (estructura — implementación en BACKLOG)

```bash
# scripts/feder-demo.sh — Demo NDR para presentación FEDER
# Ejecutar en máquina con Vagrant + VirtualBox instalados

set -euo pipefail

echo "=== aRGus NDR — Demo FEDER ==="
echo "=== Nodo 1: Sensor + ML Detector ==="
vagrant up
make bootstrap
make pipeline-start
sleep 30
make pipeline-status   # debe mostrar 6/6 RUNNING

echo "=== Reproduciendo tráfico CIC-IDS-2017 ==="
# TODO: implementar replay pcap contra interfaz virtual
# make pcap-replay PCAP=data/wednesday_attack.pcap

echo "=== Verificando detecciones XGBoost ==="
# TODO: make pipeline-log-tail COMPONENT=ml-detector | grep ATTACK

echo "=== Go/No-Go check ==="
make test-all
echo "DEMO COMPLETA — aRGus NDR operativo"
```

---

## Prerequisitos para Contactar a Andrés Caro Lindo

1. Go/no-go técnico superado (1 agosto 2026)
2. Draft v17+ paper arXiv con §5 actualizado (property testing + safe_path taxonomy)
3. Deck de 10 slides: problema → solución → resultados → financiación solicitada
4. Presupuesto estimado Fase 5+6 (hardware ARM64, equipo, infraestructura)
5. Carta de motivación FEDER con argumento open-source para infraestructura crítica pública

---

## Fases que Requieren Financiación

- **Fase 5**: Despliegue piloto real en hospital/municipio (hardware, soporte, DPIA)
- **Fase 6**: Federación multi-nodo, privacidad diferencial, certificación

*BACKLOG-FEDER-001 — deadline 22 septiembre 2026*
*Consejo D5 DAY 128: Demo = NDR standalone + 2 nodos simulados. Go/no-go: 1 agosto 2026.*
