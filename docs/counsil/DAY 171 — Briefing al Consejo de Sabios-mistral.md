Aquí tienes una versión estructurada y clara para presentar al **Consejo de Sabios**, con énfasis en las decisiones críticas, el progreso técnico y las preguntas abiertas. He organizado el contenido para facilitar la revisión y la toma de decisiones, destacando los puntos de acción inmediata y las implicaciones estratégicas.

---


Resumen Ejecutivo — DAY 171


| **Área**               | **Estado**                          | **Próximos Pasos**                     |
|------------------------|-------------------------------------|----------------------------------------|
| **Objetivo**           | Validar paridad **operacional** del `community_id` (no solo especificación). | Replay en vivo (#1) + validación de bidireccionalidad (#2). |
| **Cross-check**        | Dry-run completado (Neris offline).   | Replay en vivo con tcpreplay a baja tasa. |
| **Verificador**        | Python (`community_id_crosscheck.py`). | Decidir lenguaje (P1) y umbral de anomalías (P2). |
| **Infraestructura**    | Logs y telemetría implementados.      | Confirmar `PromiscModePolicy=allow-all` (P3). |

---

---

## **1. Logros del Día (CERRADO)**
### ✅ **aRGus: Telemetría del `community_id`**
- **Implementación limpia**:
    - Helper `sniffer::flow::log_community_id_emission` (7 campos TSV: `cid`, 5-tupla, timestamp).
    - **Gateado por `ARGUS_CID_CROSSCHECK=1`** (coste cero en hot path).
    - **Fichero dedicado**: `/vagrant/logs/lab/cid-xcheck-argus.tsv` (mutex + fflush).
    - **Test TDH**: Validado contra la diana DAY 170 (TCP seed 0 → `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`).
    - **Compatibilidad**: Variant A (eBPF) y Variant B (libpcap).

- **Decisión clave**:
    - El log **no está en `compute_community_id`** (que es pura función de hash), sino en los *call-sites* de sellado (donde la 5-tupla está en scope).
    - **No se descarta ninguna discrepancia**: Las anomalías se guardan para análisis forense (posible evasión o edge case).

---

### ✅ **Verificador de Paridad**
- **Diseño**:
    - Compara `community_id` (no 5-tupla) entre los 3 sensores.
    - Categorías:
        - **agree**: Intersección de los 3 (objetivo).
        - **expected_diff**: Diferencias por diseño (ej. ICMP → `nullopt` en aRGus).
        - **anomaly**: Todo lo demás (se vuelca a `cid-xcheck-anomalies.tsv`).
    - **Guard N>0**: Evita falsos positivos si un sensor no captura tráfico.

- **Rutas de logs**:
    - Suricata: `/var/log/suricata/eve.json` (community_id raiz).
    - Zeek: `/vagrant/logs/lab/zeek/conn.log` (seed=0 persistente).
    - aRGus: `/vagrant/logs/lab/cid-xcheck-argus.tsv`.

- **Dry-run (Neris offline)**:
    - **Resultado**:
        - `agree = 2` (TCP + UDP/DNS).
        - `expected_diff = 76` (ICMP/IPv6-ICMP).
        - `anomaly = 14443` (artefacto por datos no homogéneos).
    - **Bugs detectados y corregidos**:
        - Escaping de `\t` en `vagrant ssh`.
        - Adaptador de Suricata leyendo `/var/log` (producción) en vez del pcap.

---

---

## **2. Pendientes para Mañana (PRIORIDAD)**
### 🔴 **Replay en Vivo (#1)**
- **Objetivo**: Validar paridad con tráfico real en `intnet ml_defender_gateway_lan`.
- **Requisitos**:
    1. **Orquestación**:
        - Arrancar aRGus (`ARGUS_CID_CROSSCHECK=1`), Suricata, Zeek en `eth1` (PROMISCUO).
        - Ejecutar `tcpreplay` del pcap Neris **a baja tasa** (evitar pérdidas).
        - Parar Zeek tras el replay (flushea al cierre TCP).
    2. **Validación**:
        - Correr `community_id_crosscheck.py` sin flags (rutas de producción).
        - Verificar que los 3 sensores ven **TODOS los paquetes** (no solo los suyos).

- **Riesgo**: Si `PromiscModePolicy` no es `allow-all` en el Vagrantfile, los sensores verán 0 paquetes → **falso verde** (el guard N>0 lo detecta, pero es mejor prevenir).

---

### 🟡 **Caso de IPs Invertidas (#2)**
- **Objetivo**: Probar bidireccionalidad canónica (mismo `community_id` para SYN y SYN-ACK).
- **Acción**:
    - Crear pcap mínimo con 2 paquetes (SYN + SYN-ACK invertido).
    - Validar que el `community_id` sea idéntico para ambos.

---
### 🟡 **Delta de Timestamps (#3)**
- **Objetivo**: Calibrar `source_wait_timeout` (aRGus: 5s, Suricata: 10s, Zeek: 20s) con datos reales.
- **Acción**:
    - Extender el parser para comparar `ts_emision_ns` entre sensores.

---

---
---
## **3. Preguntas Críticas al Consejo**
---

### **P1 — Lenguaje del Verificador: ¿Python o C++?**
**Contexto**:
- El verificador (`community_id_crosscheck.py`) es **andamiaje de host** (corre en macOS, una vez por replay, orquesta `vagrant ssh`).
- **No comparte runtime** con el pipeline C++ (sniffer/detector/firewall, 24/7, hot path).
- **Coherencia actual**: Las herramientas de host (ej. `parse_results.py`) ya son Python.

**Recomendación**:
❌ **NO migrar a C++** (coste de mantenimiento > beneficio).
✅ **Mantener en Python** y enfocar el debate en el **adaptador de ingesta real** (el que publicará `SecurityEvent` por ZeroMQ al correlation-engine).
- **Pregunta clave**:
  ¿Qué lenguaje/forma deben tener los adaptadores de ingesta (Suricata → ZeroMQ, Zeek → ZeroMQ)?
    - Opciones:
        - **C++**: Coherencia con el engine, pero complejidad para parsear JSON/redis/kafka.
        - **Python/Go**: Más ágil para fuentes externas, pero añade dependencias.

---

### **P2 — Umbral de Anomalías: ¿Cero o Porcentaje?**
**Contexto**:
- En el replay real, se espera que las anomalías colapsen a un número pequeño (ej. diferencias legítimas por reensamblado en Suricata vs. flujo en aRGus).
- **Riesgo**: Si se acepta un % de anomalías, podría enmascarar bugs o evasiones.

**Opciones**:
1. **Cero estricto**: Cualquier discrepancia en TCP/UDP = fallo.
    - ✅ Simple y seguro.
    - ❌ Puede ser demasiado estricto (diferencias legítimas por capa).
2. **Umbral porcentual** (ej. <0.1% de flujos TCP/UDP).
    - ✅ Flexible para diferencias legítimas.
    - ❌ Requiere justificar el umbral (¿cómo evitar racionalizar resultados?).

**Pregunta**:
¿Qué criterio de aceptación definimos **ANTES** del replay?

---
---
### **P3 — Promiscuidad del `intnet`: ¿Confirmar `allow-all`?**
**Contexto**:
- El replay usa MACs originales del pcap → **unknown-unicast**.
- VirtualBox solo inunda el tráfico a todos los puertos si `PromiscModePolicy=allow-all` está configurado en el Vagrantfile para `eth1` de las 3 VMs (Suricata, Zeek, aRGus).

**Riesgo**:
- Si falta, los sensores verán 0 paquetes → logs vacíos → **falso verde** (el guard N>0 lo detecta, pero es mejor evitarlo).

**Acción propuesta**:
✅ **Documentar y confirmar** `PromiscModePolicy=allow-all` en el Vagrantfile como invariante **antes** del replay.

---
---
---
## **4. Resumen de Decisiones Requeridas**
| **Pregunta**               | **Opciones**                          | **Impacto**                          |
|----------------------------|---------------------------------------|--------------------------------------|
| **P1: Lenguaje verificador** | Python (recomendado) / C++ (no)       | Mantenimiento vs. coherencia pipeline.|
| **P1b: Adaptadores ingesta** | C++ / Python/Go                       | Arquitectura a largo plazo.          |
| **P2: Umbral anomalías**     | Cero estricto / % (ej. <0.1%)         | Sensibilidad a evasiones vs. ruido.  |
| **P3: Promiscuidad**         | Confirmar `allow-all` en Vagrantfile. | Evitar falso verde.                  |

---
---
## **5. Próximos Pasos (Acciones Concretas)**
1. **Consejo decide**:
    - P1 (lenguaje verificador/adaptadores).
    - P2 (umbral de anomalías).
    - P3 (confirmar `allow-all`).
2. **Equipo ejecuta**:
    - Replay en vivo (#1) + validación de bidireccionalidad (#2).
    - Extender parser para delta de timestamps (#3).
3. **Documentación**:
    - Actualizar Vagrantfile con `PromiscModePolicy=allow-all`.
    - Definir criterio de aceptación (P2) en el ADR correspondiente.

---
---
**Observación final**:
El dry-run ya demostró que el **matching por `community_id` funciona end-to-end**. El replay en vivo es el último paso para validar la paridad **operacional** en condiciones reales. Las decisiones del Consejo sobre P1-P3 son críticas para evitar bloqueos o falsos positivos/negativos.

FIRMADO

MISTRAL