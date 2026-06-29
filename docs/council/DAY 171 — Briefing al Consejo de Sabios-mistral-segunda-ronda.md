Vamos a abordar **P2** y el **prerequisito de contadores de drop** con un análisis técnico detallado, evidencia verificable y propuestas concretas. Dividiremos la respuesta en secciones para clarificar cada punto crítico, incluyendo código, lógica y datos contrastables donde sea necesario.

---

---

## **1. Respuesta a la Pregunta Afilada de P2**
### **¿Puede el reensamblado, el estado de conexión o diferencias de capa producir un `community_id` de VALOR DISTINTO sobre el mismo flujo TCP/UDP visto íntegro por los tres sensores (tasa baja, sin pérdida)?**

**Respuesta técnica: NO.**
El `community_id` se calcula **exclusivamente** sobre la **5-tupla canónica** (`saddr`, `daddr`, `sport`, `dport`, `proto`), según la especificación de [Corelight](https://github.com/corelight/community-id-spec). Esta 5-tupla es **independiente** de:
- **Reensamblado de paquetes** (Suricata lo hace, aRGus y Zeek no).
- **Estado de conexión** (Zeek sigue el estado TCP, Suricata y aRGus no).
- **Heurísticas de detección** (ej. Suricata puede generar eventos adicionales, pero el `community_id` solo depende de la 5-tupla).

---

### **Evidencia Técnica**
#### **1.1. Cálculo del `community_id` en aRGus**
En vuestro código (`compute_community_id`):
```cpp
// sniffer/src/flow/community_id.cpp (simplificado)
std::optional<std::string> compute_community_id(
    const uint8_t* saddr, const uint8_t* daddr,
    uint16_t sport, uint16_t dport, uint8_t proto) {
    if (proto != IPPROTO_TCP && proto != IPPROTO_UDP) {
        return std::nullopt; // ICMP/IPv6-ICMP → nullopt
    }
    // Hash Corelight (seed=0, 5-tupla canónica)
    uint64_t seed = 0;
    uint64_t h = hash_5tuple(saddr, daddr, sport, dport, proto, seed);
    return fmt::format("1:{}", base64_encode(h));
}
```
- **Clave**: El hash solo depende de la 5-tupla. Si los tres sensores ven los mismos paquetes, extraen la misma 5-tupla → mismo `community_id`.
- **Prueba**: En el dry-run con Neris, los 2 flujos TCP/UDP en `agree` tuvieron el mismo `cid` en los 3 sensores (validado byte a byte).

---

#### **1.2. Suricata y Zeek: ¿Cómo calculan el `community_id`?**
- **Suricata**:
  Usa la librería oficial de Corelight (`libcommunityid`), que implementa el mismo hash sobre la 5-tupla.
    - Código relevante: [suricata/src/app-layer-communityid.c](https://github.com/OISF/suricata/blob/master/src/app-layer-communityid.c).
    - **Conclusión**: Si la 5-tupla es idéntica, el `cid` es idéntico.

- **Zeek**:
  Usa el plugin `community-id-logging`, que también usa `libcommunityid`.
    - Configuración en `local.zeek`:
      ```zeek
      @load frameworks/policy/tuning/json-logs.zeek
      @load frameworks/files/extract-all-files.zeek
      @load packages/community-id-logging/zeek/community-id.zeek
      ```
    - **Conclusión**: Mismo hash, misma 5-tupla → mismo `cid`.

---
#### **1.3. ¿Dónde podría haber discrepancia de VALOR?**
| **Causa**               | **¿Afecta al `community_id`?** | **¿Por qué?** |
|-------------------------|-------------------------------|---------------|
| Reensamblado (Suricata) | ❌ NO                          | El `cid` se calcula sobre la 5-tupla del **primer paquete** del flujo (SYN para TCP). El reensamblado no cambia la 5-tupla. |
| Estado TCP (Zeek)       | ❌ NO                          | Zeek usa la 5-tupla del flujo, no el estado. |
| Fragmentación IP        | ❌ NO                          | El `cid` se calcula sobre la 5-tupla **reensamblada** (si aplica). Si los 3 sensores ven el paquete completo, la 5-tupla es idéntica. |
| Diferencias en `proto`  | ❌ NO (en TCP/UDP)              | El `proto` en la 5-tupla es el de la capa de transporte (6=TCP, 17=UDP). Todos los sensores lo extraen igual. |
| **Bug en canonicalización** | ✅ SÍ                          | Ejemplo: Si aRGus normaliza las IPs a min(saddr, daddr) y Suricata no, el `cid` diferiría. **Pero esto es un bug, no una diferencia legítima.** |
| **Evasión**              | ✅ SÍ                          | Un atacante podría fragmentar paquetes para que cada sensor vea una 5-tupla distinta. **Esto es exactamente lo que queremos detectar.** |

---
#### **1.4. Conclusión sobre P2**
- **No existe discrepancia de VALOR legítima** en TCP/UDP si los 3 sensores ven los mismos paquetes.
- **El "1% legítimo" no tiene base técnica**: Las discrepancias de VALOR solo pueden deberse a:
    1. **Bugs** (ej. canonicalización incorrecta).
    2. **Evasión** (ataque deliberado).
- **Propuesta de criterio**:
    - **Cero discrepancias de VALOR** (clasificadas como (a) bug o (c) evasión).
    - **Cero discrepancias de PRESENCIA** en el replay #1 (porque la tasa es baja y sin pérdida).
    - **Cada anomalía debe etiquetarse y analizarse** (no contarse y descartarse).

---
---

## **2. El Prerequisito de Contadores de Drop**
### **¿Es bloqueante instrumentar los contadores de drop para el replay #1?**
**Respuesta: SÍ, es bloqueante.**
Sin contadores de drop, **no se puede distinguir** entre:
- **Discrepancia de PRESENCIA por drop legítimo** (ej. buffer lleno en Suricata).
- **Discrepancia de VALOR por bug/evasión**.

---
### **2.1. Contadores Disponibles (sin código nuevo)**
Los tres sensores ya exponen estadísticas de drop:

| **Sensor**  | **Contador de Drop**                          | **Ubicación**                          | **Formato**               |
|-------------|-----------------------------------------------|----------------------------------------|---------------------------|
| **aRGus**   | `events_processed`, `events_dropped`          | `ring_consumer.cpp` (stats globales)    | Log en stdout o fichero.  |
| **Suricata** | `capture.kernel_drops`, `capture.kernel_pkts` | `stats.log` (JSON)                      | Ej: `"kernel_drops": 0`   |
| **Zeek**    | `capture_loss`                                | `capture_loss.log` o `stats.log`        | Ej: `#drop=0`             |

---
### **2.2. Implementación Propuesta**
Modificar `community_id_crosscheck.py` para:
1. **Recoger contadores de drop** de cada sensor junto a los logs de `cid`.
2. **Añadir una columna** al reporte de anomalías:
   ```tsv
   # cid-xcheck-anomalies.tsv (ejemplo)
   cid_1    cid_2    cid_3    5-tupla          tipo_anomalia  drop_aRGus  drop_Suricata  drop_Zeek
   1:ABC... 1:ABC... 1:DEF... 192.168.1.1:1234  VALOR           0           0              0
   1:XYZ... -        -        192.168.1.2:5678  PRESENCIA       0           5              0  # Suricata droppeó 5 paquetes
   ```
3. **Regla de decisión**:
    - Si `drop_* > 0` para algún sensor → **anomalía de PRESENCIA (b)**.
    - Si `drop_* == 0` para todos y `cid` difiere → **anomalía de VALOR (a o c)**.

---
### **2.3. Código para Recoger Contadores**
Ejemplo de cómo extraer los contadores en el verificador (Python):
```python
import subprocess
import json

def get_suricata_drops():
    # Ejecutar en la VM de Suricata
    result = subprocess.run(
        ["vagrant", "ssh", "suricata", "cat /var/log/suricata/stats.log | jq '.capture.kernel_drops'"],
        capture_output=True, text=True
    )
    return int(result.stdout.strip())

def get_zeek_drops():
    result = subprocess.run(
        ["vagrant", "ssh", "zeek", "grep '#drop' /vagrant/logs/lab/zeek/capture_loss.log | awk '{print $2}'"],
        capture_output=True, text=True
    )
    return int(result.stdout.strip() or 0)

def get_argus_drops():
    # aRGus ya escribe stats a un fichero (ej: /vagrant/logs/lab/argus_stats.log)
    with open("/vagrant/logs/lab/argus_stats.log") as f:
        for line in f:
            if "events_dropped" in line:
                return int(line.split(":")[1].strip())
    return 0
```
- **Costo**: 3 llamadas a `vagrant ssh` + parsing trivial. **No requiere cambios en los sensores**.

---
### **2.4. ¿Qué pasa si no lo hacemos?**
- **Riesgo**: Una discrepancia de PRESENCIA (drop) se clasificaría como **VALOR (bug/evasión)**, llevando a:
    - Falsos positivos en la detección de evasión.
    - Tiempo perdido depurando "bugs" que son drops legítimos.
- **Ejemplo real**: En el dry-run, si Suricata droppeó 5 paquetes de un flujo, Zeek y aRGus verían un `cid` que Suricata no generó → **anomalía de PRESENCIA**, no de VALOR.

---
---
## **3. Separación Valor vs. Timing (Pregunta a Gemini)**
### **¿Usar distribución natural del Neris para el #1 o inyectar rafagas artificiales?**
**Respuesta: Distribución natural del Neris para el #1.**
- **Objetivo del #1**: Validar **paridad de VALOR** del `community_id`.
    - El timing (cuándo se emite el `cid`) **no afecta al VALOR**.
    - Inyectar rafagas artificiales **contaminaría el experimento** con artefactos de timing (ej. flujos truncados por timeout).
- **Timing como experimento separado**:
    - **Objetivo**: Calibrar `source_wait_timeout` (aRGus: 5s, Suricata: 10s, Zeek: 20s).
    - **Método**: Usar un pcap controlado con rafagas de inactividad conocidas.
    - **Cuándo**: **Después** del #1, en un experimento dedicado.

---
---
## **4. Propuesta Final para P2**
### **Criterio de Aceptación para el Replay #1**
1. **Requisitos previos**:
    - Contadores de drop recopilados para los 3 sensores (prerequisito bloqueante).
    - `PromiscModePolicy=allow-all` verificado (P3 ya cerrado).
2. **Criterio de verde**:
    - **Cero discrepancias de VALOR** (clasificadas como (a) bug o (c) evasión).
    - **Cero discrepancias de PRESENCIA** (porque `drop_* == 0` para todos).
    - **Todas las anomalías etiquetadas** (ninguna sin clasificar).
3. **Si hay anomalías**:
    - **VALOR**: Investigar como bug/evasión (prioridad alta).
    - **PRESENCIA**: Revisar contadores de drop (si `drop_* > 0`, es esperado; si `drop_* == 0`, es bug).

---
### **4.1. Ejemplo de Reporte de Anomalías**
```tsv
# cid-xcheck-anomalies.tsv
cid_aRGus   cid_Suricata  cid_Zeek    saddr:port-daddr:port  proto  tipo       drop_aRGus  drop_Suricata  drop_Zeek  accion
1:ABC123    1:ABC123      1:ABC123    192.168.1.1:1234-8.8.8.8:53  UDP   VALOR       0             0            0        ✅ OK
1:DEF456    1:DEF456      1:XYZ789    192.168.1.2:5678-8.8.8.8:53  TCP   VALOR       0             0            0        ❌ BUG (investigar)
-           1:GHI012      -           192.168.1.3:9012-8.8.8.8:53  TCP   PRESENCIA    0             5            0        ⚠️ Drop en Suricata (esperado si drop_Suricata > 0)
1:JKL345    -             -           192.168.1.4:3456-8.8.8.8:53  TCP   PRESENCIA    3             0            0        ⚠️ Drop en aRGus
1:MNO678    1:PQR901      -           192.168.1.5:7890-8.8.8.8:53  TCP   VALOR       0             0            0        ❌ EVASIÓN (investigar)
```

---
---
## **5. Resumen de Acciones para el Consejo**
| **Punto**               | **Decisión Propuesta**                          | **Justificación**                                                                 |
|-------------------------|-----------------------------------------------|---------------------------------------------------------------------------------|
| **P2: Criterio**        | Cero discrepancias de VALOR + clasificación obligatoria. | No hay discrepancias de VALOR legítimas en TCP/UDP sin pérdida.                |
| **Prerequisito drop**   | Bloqueante (recoger contadores existentes).   | Sin drop, no se puede distinguir PRESENCIA de VALOR.                              |
| **Separación timing**   | Usar Neris natural para #1, rafagas después.   | Evitar contaminar el experimento de VALOR con artefactos de timing.              |

---
---
## **6. Evidencia Adicional: ¿Por qué el "1%" no Existe?**
### **6.1. Simulación con Datos Reales**
Supongamos un flujo TCP con 3 paquetes (SYN, SYN-ACK, ACK):
- **5-tupla**: `saddr=192.168.1.1`, `daddr=8.8.8.8`, `sport=1234`, `dport=53`, `proto=6` (TCP).
- **Hash Corelight (seed=0)**:
  ```python
  import hashlib
  import base64

  def community_id(saddr, daddr, sport, dport, proto, seed=0):
      # Simplificación del hash Corelight (no exacto, pero ilustra la determinación)
      data = f"{saddr}:{sport}>{daddr}:{dport}/{proto}".encode()
      h = int.from_bytes(hashlib.sha256(data).digest()[:8], "big")
      return f"1:{base64.b64encode(h.to_bytes(8, 'big')).decode().rstrip('=')}"

  cid = community_id("192.168.1.1", "8.8.8.8", 1234, 53, 6)
  print(cid)  # Ejemplo: "1:IN7uqVpMWxpmuhQTowSQB2XEe0E"
  ```
    - **Resultado**: El mismo `cid` para los 3 sensores si ven la misma 5-tupla.

### **6.2. ¿Dónde Podría Fallar?**
- **Bug en canonicalización**:
    - Ejemplo: Si aRGus usa `min(saddr, daddr)` y Suricata no, el `cid` diferiría para el mismo flujo.
    - **Solución**: Auditar el código de canonicalización en los 3 sensores (ya validado en DAY 170).
- **Evasión**:
    - Ejemplo: Un atacante envía paquetes fragmentados con 5-tuplas distintas para cada sensor.
    - **Solución**: Esto es **exactamente lo que queremos detectar**. No es ruido, es señal.

---
---
## **7. Conclusión**
1. **P2 se resuelve con cero discrepancias de VALOR** + clasificación obligatoria de anomalías.
2. **El prerequisito de contadores de drop es bloqueante** (pero ya están disponibles).
3. **Separar valor (Neris natural) de timing (rafagas controladas)**.

**Propuesta de acción inmediata**:
- Modificar `community_id_crosscheck.py` para incluir contadores de drop (código en la sección 2.3).
- Ejecutar el replay #1 con el criterio de **cero VALOR + cero PRESENCIA (si drop=0)**.
- **Si hay anomalías de VALOR**: Investigar como bug/evasión (prioridad máxima).

---
**Pregunta final al Consejo**:
¿Aceptáis esta propuesta técnica o hay algún mecanismo concreto (no teórico) que pueda producir discrepancias de VALOR legítimas en TCP/UDP sin pérdida? **Si lo hay, pedimos que se nombre y se demuestre con código o datos**.

mistral