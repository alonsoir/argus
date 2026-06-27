# 📜 Dictamen del Consejo — DAY 171

## ✅ Validación del avance
El enfoque es **quirúrgicamente correcto**. Mantener `compute_community_id` pura, gatear la telemetría por `ARGUS_CID_CROSSCHECK=1`, volcar a fichero dedicado con mutex/fflush y tratar las discrepancias como evidencia forense (no como ruido) son decisiones de arquitectura que evitan deuda técnica inmediata. El dry-run ya demostró su valor: atrapó dos bugs de integración y validó el matching end-to-end. El camino a replay en vivo está despejado.

A continuación, respuestas directas a las preguntas y directrices para DAY 172.

---

## 🔍 Respuestas a Preguntas

### P1 — Lenguaje del verificador vs Adaptadores de ingesta
**Dictamen:**
- **Verificador (`community_id_crosscheck.py`): NO migrar a C++.** Queda en Python. Es herramienta de host, corre en macOS, orquesta `vagrant ssh`, y su ciclo de vida es de iteración rápida. Su coherencia es con `parse_results.py`, no con el hot-path. Forzar C++ aquí solo añadirá fricción de build/toolchain sin beneficio operacional.
- **Adaptadores de ingesta (AdapterSpec):** Aquí sí el lenguaje pesa. Recomendamos **C++ nativo** para los adaptadores que publican al `correlation-engine` vía ZeroMQ/Redis, por tres razones:
    1. **Cohesión de runtime:** mismo ciclo de vida, mismo `-Werror`/TSAN, misma gestión de memoria y backpressure que el sniffer.
    2. **Rendimiento en hot-path de ingesta:** `eve.json` y `conn.log` pueden crecer a MB/s; parsers como `simdjson` + cliente ZeroMQ/Redis en C++ evitan GC pauses o overhead de FFI.
    3. **Frontera clara:** el verificador es `host/orchestration`; los adaptadores son `vm/data-plane`. No se mezclan.
- **Acción:** Documentar esta frontera en **ADR-051 §4.2** (Polyglot Boundary). Si Zeek/Suricata exponen plugins nativos o brokers intermedios (Kafka/Redis Stream), evaluar Go/Rust solo si el transporte lo exige; caso contrario, C++.

### P2 — Umbral de anomalías y criterio de aceptación
**Dictamen:** Rechazamos el `"cero estricto"` y también el `"%" arbitrario`. Definimos un **Criterio de Aceptación Dual** que se congela **antes del replay**:

| Categoría | Criterio | Consecuencia |
|---|---|---|
| **Suite Canónica** (SYN, SYN-ACK, DNS/UDP, HTTP GET/TCP, seed=0) | `0 anomalías` sobre los flujos de prueba | Si `>0` → `FAIL` inmediato. Pausa replay. |
| **Tráfico Bulk (TCP/UDP)** | `anomaly ≤ 1.0%` del total de flujos válidos | Si `>1%` → replay se detiene, se genera `cid-xcheck-anomalies.tsv`, se clasifica por causa (retransmisión, fragmentación, timeout de estado, capa 2/3 mismatch). |
| **Expected Diff** | Ilimitado, pero **debe coincidir 100%** con el filtro por proto/ICMP | Si un ICMP/IPv6 cae en `anomaly` → bug de filtrado. |

- **Razón:** Las diferencias de capa (Suricata reensambla, Zeek mantiene estado TCP, aRGus opera por flujo capturado) generan divergencias legítimas en flujos fragmentados, con retransmisiones o con timeouts asimétricos. Un NDR no busca perfección sintáctica, sino **detección de evasión**. El umbral del 1% actúa como red de seguridad contra regresiones masivas sin cegar ante señales reales.
- **Acción:** Congelar este criterio en `tools/acceptance_criteria.md` antes de ejecutar el replay. El script `community_id_crosscheck.py` debe leerlo y fallar exitosamente (`exit 2` para threshold breach, `exit 1` para canonical fail).

### P3 — Promiscuidad del intnet y riesgo de falso verde
**Dictamen:** **MANDATORIO.** Confirmar y auditar `PromiscModePolicy=allow-all` en `eth1` de las tres VMs. Sin esto, el replay es una lotería de broadcasting.

- **Vagrantfile (invariante documentado):**
  ```ruby
  config.vm.provider "virtualbox" do |vb|
    vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
  end
  ```
  *(Aplicar a suricata, zeek, defender)*
- **Pre-flight check (script de orquestación):**
  Antes de iniciar `tcpreplay`, ejecutar en cada VM:
  ```bash
  ip link show eth1 | grep -q "PROMISC" || exit 1
  # Opcional: ethtool -k eth1 | grep "rx-promisc" para confirmación kernel
  ```
- Si el guard `N>0` salta, el replay se aborta y se registra como `FAIL: VISIBILITY_INVARIANT_BROKEN`. No se intenta racionalizar post-hoc.

---

## 📋 Checklist para DAY 172 (Replay en Vivo)

1. [ ] Aplicar `allow-all` en Vagrantfile + reiniciar redes de VMs.
2. [ ] Implementar pre-flight check de promiscuidad en script de orquestación.
3. [ ] Congelar `acceptance_criteria.md` (Criterio Dual P2).
4. [ ] Preparar pcap de 2 paquetes (SYN + SYN-ACK invertido) para prueba de bidireccionalidad canónica.
5. [ ] Configurar `tcpreplay` a tasa baja (`--pps=500` o `--mbps=10`), interfaz `eth1` en `client`, sin pérdida confirmada.
6. [ ] Arrancar secuencia: aRGus (`ARGUS_CID_CROSSCHECK=1`) → Suricata → Zeek → tcpreplay → espera de cierre TCP → volcado de logs → ejecución de `community_id_crosscheck.py`.
7. [ ] Capturar `ts_emision_ns` en `.tsv` y ejecutar parser de delta de timestamps (calibración de `source_wait_timeout`).
8. [ ] Si `anomaly > 1%` o `canonical != 0` → HALT, volcar `cid-xcheck-anomalies.tsv`, iniciar triage. Si pasa → merge a `feature/day171-live-replay` y cerrar paridad operacional.

---

## 🔚 Cierre del Consejo
El DAY 171 demuestra madurez en validación empírica y manejo forense de discrepancias. La separación entre **verificador de paridad** (Python/host) y **adaptadores de ingesta** (C++/VM) es arquitectónicamente sana. El criterio de aceptación dual y la invariante de promiscuidad eliminan riesgos de racionalización post-hoc y falsos verdes.

**Próximo hito:** Replay en vivo con criterios congelados. El Consejo queda a la espera de los resultados de `cid-xcheck-argus.tsv` vs `eve.json` vs `conn.log` bajo tráfico sincronizado.

🛡️ *El Consejo valida el rumbo. Ejecuten DAY 172 con disciplina de aceptación.*

FIRMADO 
QWEN