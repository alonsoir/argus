# BACKLOG-BENCHMARK-CAPACITY-001 — Empirical Capacity Benchmark: eBPF vs libpcap vs ARM64

**Estado:** BACKLOG  
**Prioridad:** P1 — FEDER Year 1 Deliverable obligatorio  
**Bloqueado por:** ADR-029 Variant A estable + ADR-029 Variant B estable  
**Estimación:** 3–5 días de sesión  
**Responsable:** Alonso (PI) + Consejo de Sabios (revisión de protocolo y resultados)  
**Fecha de registro:** 2026-05-01 (DAY 137)

---

## Motivación

aRGus NDR está diseñado para proteger infraestructura crítica —hospitales, escuelas, municipios— que no puede permitirse soluciones enterprise. Esto genera una tensión real y éticamente relevante:

- Las organizaciones con más recursos usarán hardware x86-64 con NICs que soportan XDP nativo → `EbpfBackend` multihilo → máximo rendimiento.
- Las organizaciones con menos recursos usarán hardware ARM64 (Raspberry Pi, SBCs equivalentes) donde XDP nativo no está disponible en el driver de red integrado (`genet`) → `PcapBackend` monohilo → rendimiento inferior por diseño.

**Esto significa, en primera instancia, que quienes menos tienen pueden recibir menos protección técnica.**

El objetivo de este benchmark es cuantificar ese gap con rigor científico:
1. Saber exactamente cuánto es la diferencia real en condiciones hospitalarias típicas.
2. Explorar si configuraciones multi-SBC ARM64 pueden cerrar ese gap.
3. Publicar los resultados honestamente. Lo que tenga que ser, será.

---

## Las tres configuraciones bajo prueba

| ID   | Label                         | Arquitectura | Hardware objetivo                      | Backend        | Threading       | NIC XDP   |
|------|-------------------------------|--------------|----------------------------------------|----------------|-----------------|-----------|
| BM-A | x86-64 eBPF/XDP high-end      | x86-64       | Servidor / workstation, NIC XDP-native | `EbpfBackend`  | Multihilo (RSS) | ✓ nativo  |
| BM-B | x86-64 libpcap high-end       | x86-64       | Mismo hardware que BM-A                | `PcapBackend`  | Monohilo        | —         |
| BM-C | ARM64 libpcap low-power       | ARM64        | Raspberry Pi 5 (BCM2712, `genet`)      | `PcapBackend`  | Monohilo        | ✗         |
| BM-D | x86-64 eBPF/XDP low-power     | x86-64       | Intel N100 board (i226-V / i225)       | `EbpfBackend`  | Multihilo (RSS) | ✓ nativo  |

> **BM-B es el control crítico.** Aisla el coste de libpcap vs eBPF en hardware idéntico.  
> **BM-C vs BM-D** es la comparación justa: precio y consumo equivalente, arquitecturas distintas.  
> **BM-D vs BM-A** mide el coste de miniaturizar x86-64: ¿escala bien XDP hacia abajo?  
> **BM-D vs BM-C** responde la pregunta práctica para hospitales: ¿merece pagar 50–100€ más por un N100 frente a una RPi5?

### Coste aproximado del banco de pruebas completo

| Hardware              | Precio aprox. | Cantidad |
|-----------------------|---------------|----------|
| Servidor / workstation| existente     | 1        |
| Raspberry Pi 5 (8 GB) | ~80€          | 1–3      |
| Intel N100 mini board | ~100–180€     | 1        |
| Switch gestionable    | ~50–150€      | 1        |
| Cables / NICs         | variable      | —        |

> Hardware a adquirir antes de Fase 2. Fase 1 (virtualizado) no requiere ninguna compra.

---

## Generador de tráfico: pcap relay controlado

```
tcpreplay (máquina x86 dedicada, no bajo prueba)
    │
    ├── tasa: 100 Mbps / 500 Mbps / 1 Gbps / 2 Gbps
    ├── pcap: tráfico mixto realista (CIC-IDS-2017 u equivalente)
    │
    ▼
[red de test aislada]
    │
    ▼
sniffer bajo prueba (BM-A / BM-B / BM-C)
    │
    ▼
pipeline ZeroMQ → métricas
```

**Requisitos del generador:**
- NIC capaz de línea completa a la tasa objetivo (no limitado por el generador).
- pcap de entrada con distribución de tamaños de paquete realista (no solo jumbo frames).
- Reproducibilidad: mismo pcap, misma semilla, misma tasa → mismo resultado.

---

## Métricas a capturar

### Por configuración y tasa de inyección:

| Métrica                        | Unidad          | Notas                                       |
|-------------------------------|-----------------|---------------------------------------------|
| Packets captured              | pps             | Conteo en el sniffer                        |
| Packets dropped               | pps / %         | Kernel drop counter (libpcap stats / eBPF)  |
| CPU utilization per core      | %               | Por core durante captura sostenida          |
| ZeroMQ message latency P50    | µs              | Desde captura hasta entrega al pipeline     |
| ZeroMQ message latency P95    | µs              |                                             |
| ZeroMQ message latency P99    | µs              |                                             |
| Saturation point ("cliff")    | Mbps / pps      | Tasa a la que drop rate supera el 1%        |
| Memory footprint              | MB RSS          | Durante captura sostenida                   |

### Métricas derivadas (post-análisis):

- **Delta eBPF vs libpcap** (BM-A vs BM-B): coste del backend, hardware constante.
- **Delta ARM64 vs x86-64 libpcap** (BM-C vs BM-B): coste de arquitectura, backend constante.
- **Punto de operación seguro** para volúmenes hospitalarios típicos (100–500 Mbps).

---

## Hipótesis de trabajo

1. **BM-A vs BM-B:** eBPF/XDP ofrecerá ventaja significativa a partir de ~1 Gbps sostenido. Por debajo de 500 Mbps, la diferencia puede ser tolerable.

2. **BM-C vs BM-B:** ARM64 mostrará degradación adicional respecto a x86-64 libpcap, pero dentro de un rango aceptable para hospitales con tráfico real de 100–500 Mbps.

3. **Hipótesis multi-SBC:** N unidades RPi5 capturando segmentos de red distintos (por VLAN / switch port) pueden alcanzar agregado equivalente a BM-A. Por explorar.

> Las hipótesis son falsables. Si los datos las contradicen, se publica la contradicción.

---

## Experimento adicional: configuración multi-SBC ARM64

Si BM-C muestra gap inaceptable, explorar:

```
Switch gestionable
    ├── VLAN 1 → RPi5 #1 (PcapBackend) ──┐
    ├── VLAN 2 → RPi5 #2 (PcapBackend) ──┼──► ZeroMQ → servidor central
    └── VLAN N → RPi5 #N (PcapBackend) ──┘
```

- ¿Cuántos RPi5 se necesitan para alcanzar la capacidad de BM-A?
- ¿Cuál es el coste económico de esa configuración vs una NIC x86 con XDP?
- ¿Tiene sentido como arquitectura de despliegue para hospitales con poco presupuesto?

---

## Prerequisitos técnicos antes de ejecutar

- [ ] **BACKLOG-ZMQ-TUNING-001 concluido** — este benchmark debe correr sobre la configuración ZMQ optimizada, no sobre la configuración accidental original. De lo contrario los resultados medirían una mezcla de rendimiento real del backend y penalización artificial del tuning ZeroMQ.
- [ ] ADR-029 Variant A (`EbpfBackend`) estable y mergeada a main
- [ ] ADR-029 Variant B (`PcapBackend` / `sniffer-libpcap`) estable y mergeada a main
- [ ] DEBT-CAPTURE-BACKEND-ISP-001 resuelto (ISP violation en `CaptureBackend`)
- [ ] Vagrantfile ARM64 operativo y reproducible
- [ ] Protocolo EMECAS validado para las 3 configuraciones
- [ ] pcap de tráfico mixto preparado y versionado en el repositorio

---

## Relevancia para FEDER

Este benchmark es el **empirical capacity benchmark** identificado como deliverable de Year 1 en el prospecto FEDER (prospecto_argus_ndr_v3.docx). Justifica directamente la frase central del prospecto:

> *"We need a server to know what server we need in production."*

Los resultados determinarán las recomendaciones de hardware mínimo por tipología de despliegue (hospital pequeño, mediano, con recursos) que se incluirán en la documentación técnica y, potencialmente, en una publicación derivada del arXiv paper (arXiv:2604.04952).

---

## Notas éticas

Este benchmark nace de una preocupación real: que la arquitectura técnica pueda reproducir desigualdades económicas en la calidad de protección. El compromiso es medir sin sesgo y publicar sin filtrar resultados incómodos. Si ARM64 libpcap es suficiente para proteger un hospital de 200 camas, los datos lo dirán. Si no lo es, también.

---

## Referencias

- **BACKLOG-ZMQ-TUNING-001** — prerequisito directo de este benchmark
- ADR-029: Capture Backend Architecture (Variants A/B/C)
- DEBT-CAPTURE-BACKEND-ISP-001: ISP violation en `CaptureBackend`
- arXiv:2604.04952 (Draft v18) — números del abstract a corregir post-experimentación
- prospecto_argus_ndr_v3.docx — FEDER Extremadura 2026
- FEDER deadline: 22 septiembre 2026