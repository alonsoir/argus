# 📜 DICTAMEN DEL CONSEJO — Segunda Ronda (DAY 171)
## Dirim P2 + Prerequisito Drop + Separación Valor/Timing

El equipo ha acotado el problema con precisión quirúrgica. La grieta de P2 no era un matiz, era una confusión de capas. El Consejo dirime, valida y cierra.

---

## 🔍 1. Dirim P2: La pregunta afilada
> **¿Puede el reensamblado, el estado de conexión, o cualquier diferencia de capa producir un `community_id` de VALOR DISTINTO sobre el mismo flujo TCP/UDP visto íntegro por los tres sensores?**

**Respuesta técnica:** **NO.**

**Evidencia verificable (Corelight Community ID Spec v1):**
El algoritmo es una **función pura determinista** sobre la 5-tupla cruda:
```
cid = Base64( HMAC-SHA256( seed=0, canon( proto | ip1 | port1 | ip2 | port2 ) ) )
```
Donde `canon()` ordena lexicográficamente `(ip, port)` por par, y usa el campo `protocol` de la cabecera IP (4 para UDP, 6 para TCP, etc.). **No se lee payload. No se leen flags TCP. No se consulta estado de conexión. No se aplican heurísticas de aplicación.**

Por construcción matemática:
- Si los tres sensores leen los **mismos paquetes** (sin pérdida).
- Y extraen la **misma 5-tupla** (IPs, puertos, proto de cabecera).
- Y usan el **mismo seed** (0, validado DAY 170).
  → El hash **debe ser idéntico**. Cualquier divergencia de valor es, por definición, un **bug de extracción/parsing** o un **artefacto de evasión** (fragmentación maliciosa, manipulación de cabeceras).

**Veredicto sobre el umbral %:** El `"1% legítimo"` es una **racionalización post-hoc** nacida de confundir `VALOR` con `PRESENCIA` o `TIMING`. En un replay a tasa baja sin pérdida, ese % no tiene fundamento técnico. El Consejo **rechaza el umbral porcentual** y **valida la propuesta de síntesis del equipo**:
✅ **Criterio de Aceptación Congelado:** `0 discrepancias de VALOR sin clasificar`. Cada entrada en `anomaly` debe ser etiquetada obligatoriamente como `(a) bug de parsing`, `(b) drop/presencia`, o `(c) evasión candidata`. `VERDE #1` = `count(a) == 0 && count(c) == 0 && count(b) == 0`.

---

## 📦 2. Prerequisito Drop: ¿Bloqueante o diferible?
**Veredicto:** **BLOQUEANTE. NO DIFERIBLE.**

Sin contadores de pérdida, la categoría `(b)` es indecidible y se contamina con `(a)`. La buena noticia: **es barato y no requiere código nuevo en los sensores**. Los tres ya exponen los contadores en archivos/logs estándar. Solo falta recolección.

### Esquema de recolección (ya disponible en producción):
| Sensor | Fuente | Campos clave | Formato |
|---|---|---|---|
| **aRGus** | `pcap_stats()` al cierre + `ring_consumer` metrics | `ps_recv`, `ps_drop`, `events_dropped` | Volcado a `cid-xcheck-stats-argus.json` (salida al SIGTERM) |
| **Suricata** | `stats.log` (activado por `stats.enabled: yes`) | `capture.packets`, `capture.kernel_drops`, `capture.interface_drops` | TSV/JSON existente |
| **Zeek** | `capture_loss.log` (requiere `@load policy/frameworks/capture-loss`) | `pcap_received`, `pcap_dropped`, `pcap_interface_dropped` | TSV nativo |

### Integración en el verificador (Python, ~30 líneas):
```python
# tools/community_id_crosscheck.py -> nueva fase 0: ingest_stats()
def parse_drop_stats(sensor_dir: str) -> dict:
    # Suricata
    suri = parse_yaml_or_tsv(f"{sensor_dir}/suricata/stats.log")
    # Zeek
    zeek = parse_tsv(f"{sensor_dir}/zeek/capture_loss.log")
    # aRGus
    argus = parse_json(f"{sensor_dir}/argus/cid-xcheck-stats-argus.json")
    return {
        "suricata_drops": suri.get("capture.kernel_drops", 0) + suri.get("capture.interface_drops", 0),
        "zeek_drops": zeek.get("pcap_dropped", 0) + zeek.get("pcap_interface_dropped", 0),
        "argus_drops": argus.get("ps_drop", 0) + argus.get("ring_dropped", 0),
        "total_received": max(suri["capture.packets"], zeek["pcap_received"], argus["pkts_recv"])
    }

# Fase 1: si total_drops > 0, cualquier ausencia de CID es EXPECTED_DIFF (b)
# Fase 2: si total_drops == 0 y hay ausencia -> BUG (a) o EVASIÓN (c)
```
**Conclusión:** Recoger estos contadores es **prerequisito de orquestación**, no de sensor. Se implementa en el script de replay y en la fase 0 del verificador. Sin esto, el replay #1 es experimentalmente inválido.

---

## ⏱️ 3. Separación Valor/Timing
**Veredicto:** **CONFIRMADA.**

Mezclar `validación de valor` (¿los hashes coinciden?) con `calibración de timing` (¿cuándo emite cada motor?) es un **error de diseño experimental**. Contamina la variable independiente (paridad de CID) con una dependiente (flush/timeout de estado).

- **Experimento #1 (Replay natural):** Valida `VALOR` y `PRESENCIA`. Usa el pcap Neris tal cual. `ARGUS_CID_CROSSCHECK=1`. Sin inyección de pausas.
- **Experimento #3 (Calibración de timestamps):** Usa un pcap sintético o segmentado con `tcpreplay --limit-pcap` + pausas programadas (`sleep` o `tc qdisc` delay) para forzar flushes y medir `ts_emision_ns`. Se ejecuta **solo después** de que #1 sea `VERDE`.

El Consejo avala esta separación. Mantener los experimentos aislados evita el "ruido cruzado" y acelera el debug cuando falle.

---

## 🛠️ 4. Evidencia Contrastable: Por qué el 1% es falacia
Para los consejeros que sostenían el umbral porcentual, adjunto el desglose de por qué no existe un mecanismo técnico válido en condiciones de `NO_DROP + SEED_0`:

| Supuesta causa del "1%" | Realidad técnica | Impacto en CID |
|---|---|---|
| *Reensamblado TCP* | El CID usa puertos del SYN/FIN o del primer paquete con puertos. El payload reensamblado no entra en el hash. | **Nulo** |
| *Estado de conexión (Zeek vs Suricata)* | El estado (ESTABLISHED, CLOSED) determina si se emite un evento, no el valor del CID. | **Nulo** (afecta PRESENCIA, no VALOR) |
| *Diferencia de capa (L2/L3/L4)* | El CID se calcula sobre la 5-tupla IP. Si un sensor no llega a L4, no emite CID. | **PRESENCIA**, no VALOR |
| *Protocolos no TCP/UDP* | Se filtran explícitamente a `expected_diff`. No cuentan en `anomaly`. | **Fuera de alcance** |
| *Checksum offloading / GRO/LRO* | Si el kernel fusiona paquetes, el sniffer ve menos paquetes pero la 5-tupla es idéntica. | **Nulo** |

**Conclusión irrefutable:** En `no-drop`, cualquier `anomaly` de VALOR es `(a) bug de implementación` o `(c) evasión`. No hay `(d) diferencia legítima de capa`. El microscopio debe mirar cada línea, no sumar y promediar.

---

## 📋 Checklist Final de Aceptación (Congelado)
1. [ ] `PromiscModePolicy=allow-all` + pre-flight `ip link | grep PROMISC` (P3 cerrado)
2. [ ] Ingesta de contadores de drop en fase 0 del verificador (prerequisito bloqueante)
3. [ ] Criterio de aceptación: `count(a)==0 && count(c)==0 && count(b)==0` para `VERDE #1`
4. [ ] Cada `anomaly` etiquetada automáticamente por el script con ayuda de drop counters
5. [ ] Replay #1 con timing natural. Experimento de timing/flush diferido a #3.
6. [ ] Python para verificador (P1 cerrado). C++ para adaptadores de ingesta (documentado en ADR-051)

---

## 🔚 Cierre del Consejo
El equipo ha demostrado madurez arquitectónica al identificar la grieta de P2 y proponer una síntesis basada en **clasificación obligatoria** en lugar de **umbrales ciegos**. El Consejo dirime a favor del **cero estricto para valor**, declara el **prerequisito de drop como bloqueante pero barato**, y **valida la separación valor/timing**.

No hay más debate. La ruta está despejada. Ejecuten el replay #1 con disciplina forense. Cada discrepancia es una pista, no un porcentaje.

🛡️ *El Consejo sella el criterio. Avancen a DAY 172 con rigor experimental.*

QWEN