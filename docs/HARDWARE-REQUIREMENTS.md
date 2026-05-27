# aRGus NDR — Hardware Requirements
<!-- DEBT-PROD-COMPAT-BASELINE-001 — DAY 132 -->

This document defines the minimum and recommended hardware specifications for
deploying **aRGus-production** (ADR-030 Variant A: x86-64 + AppArmor + eBPF/XDP).

For the research variant (ADR-031 seL4/Genode) see the `aRGus-seL4` branch.
For the development environment see the root `Vagrantfile`.

---

## Target Organizations

Hospitals, schools, and municipalities that cannot afford commercial NDR solutions.
The reference deployment costs approximately **150–200 USD** in bare-metal hardware.

---

## Minimum Specification (Variant A — x86-64)

| Component | Minimum | Notes |
|-----------|---------|-------|
| **CPU** | x86-64, 4 cores @ 2.0 GHz | eBPF/XDP requires kernel ≥ 5.8 |
| **RAM** | 4 GB DDR4 | Pipeline stable at ~1.28 GB under load |
| **Storage** | 32 GB SSD | OS + pipeline + FAISS index |
| **NIC 1** | 1 Gbps (monitored) | eBPF/XDP hook; must support XDP driver mode |
| **NIC 2** | 100 Mbps (management) | SSH, etcd, RAG queries |
| **OS** | Debian 13 (Trixie) or Ubuntu 24.04 LTS | Linux kernel 6.x |

> **Throughput note:** The pipeline processes ~33–38 Mbps in the virtualized
> reference environment (VirtualBox NIC ceiling). Bare-metal throughput on a
> 1 Gbps NIC is expected to be significantly higher; characterization is
> tracked as DEBT-BAREMETAL-THROUGHPUT-001.

---

## Recommended Specification

| Component | Recommended | Notes |
|-----------|-------------|-------|
| **CPU** | x86-64, 8 cores @ 3.0 GHz | ml-detector uses ~3.2 cores at peak |
| **RAM** | 8 GB DDR4 | Headroom for FAISS growth + TinyLlama |
| **Storage** | 64 GB SSD (NVMe preferred) | Fast FAISS index writes |
| **NIC 1** | 1 Gbps (monitored) | XDP native driver mode preferred |
| **NIC 2** | 1 Gbps (management) | |
| **OS** | Debian 13 + Linux 6.12 LTS | Long-term support kernel |

---

## Reference Commodity Hardware (~150–200 USD)

The following single-board and mini-PC platforms have been evaluated as
cost-effective deployment targets:

| Platform | CPU | RAM | Price (approx.) | Notes |
|----------|-----|-----|-----------------|-------|
| Intel N100 mini-PC | x86-64, 4C @ 3.4 GHz | 8–16 GB | ~120–180 USD | Recommended — dual NIC models available |
| Beelink EQ12 | Intel N100 | 8 GB | ~150 USD | Dual NIC, fanless |
| Raspberry Pi 5 | ARM64, 4C @ 2.4 GHz | 8 GB | ~80 USD + case | Variant B (ARM64) — see ADR-030 |
| Raspberry Pi 4 | ARM64, 4C @ 1.8 GHz | 4–8 GB | ~60 USD + case | Variant B (ARM64) minimum |

> **ARM64 note:** Raspberry Pi 4/5 are covered by Variant B (ADR-030 ARM64 +
> AppArmor + libpcap). eBPF/XDP support on RPi depends on NIC driver;
> libpcap fallback is the safe default. Variant B Vagrantfile:
> `vagrant/hardened-arm64/Vagrantfile` (pending).

---

## NIC Compatibility (eBPF/XDP)

XDP native driver mode provides the highest performance. XDP generic mode
(skb) is a fallback supported by all NICs but with higher CPU overhead.

| NIC driver | XDP native | Notes |
|------------|-----------|-------|
| `igb` (Intel 1G) | ✅ | Recommended |
| `ixgbe` (Intel 10G) | ✅ | Overkill for target orgs, works |
| `virtio_net` | ✅ (generic) | VirtualBox/QEMU — used in dev |
| Realtek `r8169` | ⚠️ generic only | Common on cheap mini-PCs; functional |
| USB NIC | ❌ | Not supported for monitored interface |

Verify XDP support before deployment:
```bash
ip link set dev <NIC> xdp obj /vagrant/sniffer/bpf/xdp_sniffer.o sec xdp
# If this fails, the NIC requires generic XDP mode (set in sniffer.json)
```

---

## Software Requirements (Production VM — no compiler)

The production VM must **not** contain any C/C++ compiler or build toolchain.
This is enforced by `make check-prod-no-compiler` (ADR-039 BSR axiom).

| Package | Version | Purpose |
|---------|---------|---------|
| Linux kernel | ≥ 6.x | eBPF/XDP support |
| AppArmor | ≥ 3.x | Mandatory access control (ADR-030) |
| libsodium | 1.0.19 | ChaCha20-Poly1305 + Ed25519 |
| libzmq | 4.3.x | ZeroMQ transport |
| libprotobuf | 3.x | Protocol Buffers serialization |
| onnxruntime | 1.17.x | Internal threats classifier |
| ipset / iptables | any | Firewall ACL agent |
| etcd | 3.5.x | Config + seed distribution |

**Not installed in production:**
`gcc`, `g++`, `clang`, `cmake`, `make`, `build-essential`, `libsodium-dev`,
`libzmq3-dev`, `protobuf-compiler` — verified by `make check-prod-no-compiler`.

---

## Deployment Topology

```
Internet / External Threats
         │
    ┌────▼─────────────────┐
    │  aRGus Primary Node  │  150–200 USD bare-metal
    │  NIC 1 (monitored)   │◄── hospital / school network segment
    │  NIC 2 (management)  │◄── admin network
    │  6/6 pipeline        │
    │  AppArmor enforcing  │
    └──────────────────────┘
         │ heartbeat (optional)
    ┌────▼─────────────────┐
    │  aRGus Warm Standby  │  150–200 USD (optional HA)
    └──────────────────────┘
```

Single-node deployment is the baseline. Warm-standby HA is recommended for
hospitals; etcd HA (3-node Raft) is tracked as a future milestone (ADR-035).

---

## Not Supported

- GPU acceleration (not required; RF inference: 0.24–1.06 µs, XGBoost: 1.986 µs)
- Cloud offload (deliberate — no live network metadata leaves the deployment site)
- Windows host OS
- USB NICs on the monitored interface

---

## Related ADRs

| ADR | Title |
|-----|-------|
| ADR-030 | aRGus-AppArmor-Hardened (Variant A x86 + Variant B ARM64) |
| ADR-031 | aRGus-seL4-Genode (research branch) |
| ADR-039 | Build/Runtime Separation — no compiler in production |
| ADR-025 | Plugin Integrity — Ed25519 + TOCTOU-safe dlopen |

---

*DAY 132 — 26 April 2026 · feature/adr030-variant-a · Via Appia Quality*