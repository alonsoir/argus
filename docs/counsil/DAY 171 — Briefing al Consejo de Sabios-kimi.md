# Respuesta del Consejo de Sabios — DAY 171

Leído el briefing. El cierre de hoy es sólido: tenemos observabilidad pura del data-plane, un verificador con semántica correcta (paridad por valor de CID, no por tupla), y la decisión de no descartar anomalías es la correcta de seguridad. A continuación, el contraste pedido sobre las tres preguntas.

---

## Sobre el cierre de hoy

**`sniffer::flow::log_community_id_emission`** — La separación de concerns es correcta: `compute_community_id` permanece pura (función matemática), el log vive en el call-site donde la 5-tupla está en scope, y el gateo por `ARGUS_CID_CROSSCHECK` protege el hot path. El uso de mutex + fflush para el TSV es pragmático para un test tooling; no es el path de producción.

**Verificador por valor de CID** — Acertado. El community_id encapsula la canonicalización; comparar por tupla abierta reintroduciría el problema de nomenclatura (TCP/tcp/6) y perdería la propiedad que queremos validar: que los tres motores canonicalizan igual.

**Anomalías como señal, no como ruido** — Esta es la decisión de mayor peso de seguridad del día. El caso (c) EVASION es exactamente el threat model que justifica un NDR multi-sensor. Capturar el volcado forense con 5-tupla por sensor preserva evidencia admisible para el grafo de correlación (ADR-052). Mantenerlo.

**Dry-run** — Los artefactos del dry-run (2 bugs reales cazados, 14443 anomalías explicadas por muestra no homogénea) validan que el tooling funciona. El replay en vivo es el único paso que queda para demostrar paridad operacional real.

---

## P1 — Lenguaje del verificador: Python vs C++

**Recomendación del Consejo: Mantener Python para el verificador de host. Migrar a C++ solo el adaptador de ingesta del pipeline.**

Tu argumento es correcto y completo. Añado el contraste:

| Aspecto | Verificador de host (`community_id_crosscheck.py`) | Adaptador de ingesta (pipeline) |
|---|---|---|
| **Runtime** | macOS/host, una vez por experimento | VM, 24/7, acoplado al sniffer |
| **Coherencia** | Con `parse_results.py`, scripts de orquestación | Con sniffer/detector/firewall (C++) |
| **Criticidad** | Baja: falla → re-run del experimento | Alta: falla → pérdida de eventos |
| **Cambio frecuencia** | Alta: ajustes de formato, nuevos sensores | Baja: protocolo estable (SecurityEvent) |
| **Lenguaje óptimo** | Python (velocidad de iteración) | C++ (coherencia de runtime, -Werror, TSAN) |

**Sobre el adaptador de ingesta real**: Ese sí es la decisión de peso. El engine es C++ y las fuentes hablan JSON (Suricata), TSV (Zeek), y ZeroMQ interno (aRGus). La opción pragmática es:

- **Suricata**: Adaptador en C++ que lea `eve.json` vía `nlohmann/json` o similar, o que se suscriba al redis output de Suricata si ya está configurado. No reescribir Suricata.
- **Zeek**: Zeek tiene un framework de plugins nativos en C++. Un plugin Zeek en C++ que emita directamente por ZeroMQ al correlation-engine elimina el paso intermedio de parseo de `conn.log` y reduce latencia. Es más trabajo upfront pero mejor arquitectura.
- **aRGus**: Ya es C++ y habla ZeroMQ nativo; no necesita adaptador, solo el formalismo del `SecurityEvent` protobuf.

**Veredicto**: El verificador de host se queda en Python. El adaptador de ingesta del pipeline se diseña en C++ (con posible plugin nativo para Zeek). Son dos problemas distintos con diferentes restricciones de runtime.

---

## P2 — Umbral de anomalías: ¿cero o tolerancia?

**Recomendación del Consejo: Cero estricto para TCP/UDP sobre flujos completos (SYN → FIN/RST), con escape explícito para fragmentación/reensamblado documentado.**

Definamos el criterio de aceptación *antes* del replay, como pides:

### Criterio de aceptación propuesto

| Categoría | Criterio | Justificación |
|---|---|---|
| **agree** | > 95% de los flujos TCP/UDP completos | La canonicalización Corelight es determinista; si los tres motores ven la misma 5-tupla, deben coincidir. |
| **expected_diff** | ICMP, IPv6-ICMP, no-TCP/UDP → 100% permitido | Por diseño: `compute_community_id` devuelve `nullopt` para estos. |
| **anomaly** | **0% para flujos TCP/UDP completos** | Cualquier discrepancia en un flujo TCP/UDP donde los tres motores han visto los mismos paquetes (sin pérdida) es un bug o una señal de evasión. |

### El escape: fragmentación y reensamblado

El único caso legítimo de discrepancia no-evasión es cuando los motores operan en **capas diferentes**:

- **Suricata** reensambla IP (defragmentación) y TCP (stream reassembly). Su community_id se calcula sobre la 5-tupla del flujo reensamblado.
- **Zeek** sigue el estado TCP (handshake, cierre) y puede agrupar/fragmentar eventos de conexión.
- **aRGus** captura por flujo a nivel de pcap/libpcap; si no hay reensamblado explícito, ve los paquetes crudos.

**Para el replay #1**: usamos el pcap Neris a **tasa baja** (sin pérdida, sin fragmentación). En estas condiciones, los tres motores deben ver los mismos paquetes en el mismo orden. **Anomalía = 0** es el criterio correcto.

**Para el caso #5 (RSS bajo carga)**: ahí permitiremos discrepancias por pérdida de paquetes (un sensor ve el SYN, otro no), pero ese es un experimento *deliberadamente opuesto* y separado. No confundir los criterios.

**Veredicto**: Para el replay #1, el criterio es **anomalía = 0 sobre flujos TCP/UDP**. Si aparece una anomalía, se investiga como bug o evasión antes de declarar verde. No aceptamos un porcentaje de "ruido legítimo" sin clasificarlo primero.

---

## P3 — Promiscuidad del intnet: ¿Invariante documentado?

**Recomendación del Consejo: Sí. PromiscModePolicy=allow-all en eth1 de las tres VMs es un invariante de arquitectura documentado en el Vagrantfile y en ADR-046.**

Tu guard `N>0` es correcto (mata el falso verde de logs vacíos), pero es un **fail-safe**, no un **fail-operational**. Preferimos que el experimento nunca llegue a la condición de fallo.

### Acción concreta

1. **Vagrantfile**: Añadir/verificar en la definición de `eth1` (o el adapter del intnet `ml_defender_gateway_lan`):
   ```ruby
   node.vm.network "private_network", 
     virtualbox__intnet: "ml_defender_gateway_lan",
     virtualbox__promiscuous_mode: "allow-all"  # o equivalente en Vagrant/VirtualBox
   ```
   Para las tres VMs: `suricata`, `zeek`, `defender` (aRGus).

2. **Documentación**: Añadir una nota en ADR-046 v4 §3.10 (o ADR-051/052 si allí vive la topología de red):
   > "El intnet `ml_defender_gateway_lan` opera en promiscuous mode `allow-all` en todas las VMs del sensor array. Esto es requisito para que el tráfico de replay (unknown-unicast con MACs originales del pcap) llegue a los tres sensores simultáneamente. Cualquier cambio en esta política invalida los experimentos de paridad operacional."

3. **Check de precondición**: En el script de orquestación del replay #1, añadir un check que valide `ip link show eth1` o equivalente para confirmar PROMISC antes de lanzar `tcpreplay`. Si no está en PROMISC, abortar con error explícito antes de gastar el replay.

### Riesgo adicional: MACs originales del pcap

El pcap Neris tiene MACs de la captura original. En el intnet de VirtualBox, el switch virtual es un hub/broadcast domain si está en promiscuous mode. Si no lo está, el switch aprende MACs y envía unicast solo al puerto destino. Como las VMs no tienen las MACs del pcap, el tráfico se dropa silenciosamente en el switch virtual.

**Veredicto**: Confirmar `allow-all` como invariante documentado. Añadir check de precondición en el script de orquestación. El guard `N>0` se mantiene como última línea de defensa, pero no como estrategia principal.

---

## Resumen de acciones para mañana (DAY 172)

1. **Replay en vivo (#1)**: Orquestar aRGus + Suricata + Zeek en `eth1` promiscuo, un solo `tcpreplay` del Neris a tasa baja. Criterio de aceptación: **anomalía = 0** sobre flujos TCP/UDP.
2. **Caso de IPs invertidas**: Preparar pcap de 2 paquetes (SYN + SYN-ACK) para validar bidireccionalidad canónica. Puede hacerse en el mismo replay #1 si el Neris ya lo trae, o como sub-experimento inmediato después.
3. **Delta de timestamps**: El `.tsv` ya captura `ts_emision_ns`. El parser de comparación puede esperar al día siguiente; no es bloqueante para el criterio de paridad.
4. **Vagrantfile**: Verificar/documentar promiscuous mode antes del replay.
5. **Adaptador de ingesta**: Iniciar diseño de C++ para Suricata (JSON/redis) y Zeek (plugin nativo C++), separado del verificador Python.

El cimiento del AdapterSpec §10 está bien apoyado. A cerrar el replay.

— Consejo de Sabios, DAY 171.

FIRMADO
KIMI