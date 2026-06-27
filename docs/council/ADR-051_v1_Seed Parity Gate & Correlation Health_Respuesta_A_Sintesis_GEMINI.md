Excelente síntesis. El nivel de alineamiento y la madurez de las enmiendas aditivas confirman que el Consejo ha operado con una precisión quirúrgica. Las aportaciones no solo blindan la robustez teórica del ADR-051, sino que aceleran su **transición hacia tareas de ingeniería puramente accionables** para el backlog de aRGus++.

Como miembro del Consejo, valido al 100% esta síntesis y la hoja de ruta propuesta. No hay necesidad de una tercera ronda de debate conceptual; la v2 está lista para su redacción y posterior ratificación de fidelidad.

Para asegurar que el paso de la teoría a los *tickets* de desarrollo sea directo y sin fricciones, desgloso a continuación la **estructura de ejecución técnica** basada en tus consensos:

---

## 1. Plan de Ejecución por Fases (Despliegue de Deuda Técnica)

Para evitar el bloqueo que introduce `DEBT-ARGUSPP-COUNTER-DUMP-001` sobre las métricas de aRGus, el despliegue se desacopla en dos horizontes claros:

### Fase 1: Inmediata (Gate Total + Health-Check Parcial)

* **Gate de Arranque:** Implementación del **Community ID Parity Gate** (§3.1) con la batería de 4 vectores (TCP, UDP, IPv6, Invertido). **Bloqueante 8/8 para los 3 sensores.** El pipeline no arranca si Suricata, Zeek o aRGus divergen.
* **Runtime:** Se activa el cálculo de `orphan_rate` / `match_rate` **únicamente para la frontera Suricata $\leftrightarrow$ Zeek**.
* **Mitigación Temporal para aRGus:** Se implementa la métrica heurística provisional propuesta por DeepSeek: el motor de correlación analiza flujos compartidos por Suricata+Zeek que caen dentro del mapa de cobertura de aRGus; si tras el `source_wait_timeout` conservador (~120s) no hay rastro de aRGus, se genera un pre-alerta de sospecha.

### Fase 2: Integración Post-Dump

* Una vez cerrado `DEBT-ARGUSPP-COUNTER-DUMP-001`, se integra el contador nativo de aRGus en el core del health-check, convirtiendo el `orphan_rate` de aRGus en una métrica determinista de primer nivel.

---

## 2. Especificación de los Vectores del Gate (Batería Mínima)

Para la implementación de `DEBT-CID-PARITY-VECTORS-001`, la batería de prueba en la interfaz de captura (vía `tcpreplay` o inyección de sockets crudos en el segmento virtual) se estructurará formalmente de la siguiente manera:

| Vector | Tipo / Capa | Flujo Físico (Origen $\rightarrow$ Destino) | Payload / Config | Propósito del Test |
| --- | --- | --- | --- | --- |
| **V1 (Neris)** | TCP IPv4 | `147.32.84.165:1027 \rightarrow 74.125.232.195:80` | Flag: SYN | Validar regresión con DAY 171/172 (`1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`) |
| **V2 (mDNS)** | UDP IPv4 | `192.168.1.50:5353 \rightarrow 224.0.0.251:5353` | Standard Query | Validar canonicalización UDP y tratamiento de IPs Multicast |
| **V3 (IPv6)** | TCP IPv6 | `[2001:db8::1]:443 \rightarrow [2001:db8::2]:49152` | Flag: SYN-ACK | Verificar paridad en el ordenamiento de bytes (Endianness) en direcciones de 128 bits |
| **V4 (Inverso)** | TCP IPv4 | `74.125.232.195:80 \rightarrow 147.32.84.165:1027` | Flag: ACK | **Test de Canonicidad:** Exigir idéntico CID que V1 modificando la dirección del flujo |

---

## 3. Lógica del Oráculo de Dos Niveles y Quórum

Para dar cumplimiento a la enmienda de ChatGPT y Mistral, la lógica de validación interna del script del Gate (`make crosscheck-run` evolucionado) implementará el siguiente árbol de decisión:

```
                  [ ¿Coinciden los N sensores entre sí? ]
                                   / \
                                  /   \
                                SÍ     NO  --> [ FAIL-CLOSED ]
                                /              (Vuelco verbose + Diagnóstico)
                               /
     [ ¿Coinciden con pycommunityid? ]
                   / \
                  /   \
                SÍ     NO --> [ WARNING CRÍTICO: Quórum Isomórfico ]
                /             "Posible bug/desactualización del oráculo"
               /              (NO bloquea el arranque productivo)
       [ BOOT SUCCESS ]

```

---

## 4. Estructura de Datos para el Grafo de Confianza (Runtime Degradation)

Cuando el `orphan_rate` de un sensor supere el umbral crítico provisional (`>15%` sostenido durante 5 minutos) en producción, se activará el **aislamiento dinámico**. La tarea técnica asociada dictamina que el motor de correlación mutará el esquema de inserción en Neo4j:

* **Acción 1:** El nodo `Sensor` afectado cambia su propiedad `status` de `"HEALTHY"` a `"DEGRADED_DRIFT"`.
* **Acción 2:** Todo nuevo nodo `SecurityEvent` o relación de correlación (`CORRELATED_TO`) que dependa exclusivamente de la frontera de ese sensor mientras persista el estado degradado, inyectará los siguientes metadatos:
```json
{
  "correlation_confidence": "LOW",
  "degradation_source": "suricata-core-01",
  "evidence_orphan_rate": 0.22,
  "timestamp_monotonic": 86421.04
}

```



Esto evita que los analistas en el entorno hospitalario actúen ante falsos positivos provocados por el desalineamiento, manteniendo la visibilidad del tráfico intacta.

---

## 5. Próximos pasos inmediatos

Procedamos a consolidar este documento de síntesis en el repositorio. Por mi parte, doy el **visto bueno definitivo** para que redactes la **ADR-051 v2** bajo el título unificado de **"Community ID Parity Gate & Correlation Health"**.

La precisión de esta sesión de trabajo demuestra el valor real de este Consejo. Quedo a la espera de la v2 para la revisión final de fidelidad. ¡Excelente trabajo de arquitectura, Alonso!

FDO
GEMINI