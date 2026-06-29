# Respuesta del Consejo de Sabios — Kimi

Alonso, gracias por el briefing. Leído con atención. A continuación mi veredicto como miembro del Consejo sobre las cuatro preguntas y algunas observaciones adicionales.

---

## Q1 — `rag-ingester` vs `AdapterSpec`: ¿Solapamiento o capas distintas?

**Veredicto: Son capas distintas. El diferimiento para FEDER es correcto, pero la razón no es solapamiento sino priorización de riesgo.**

Mi lectura:

| Dimensión | `AdapterSpec v1` | `rag-ingester` / `rag-security` |
|---|---|---|
| **Plano** | Correlación en tiempo real (crisis) | Conocimiento histórico/semántico (análisis) |
| **Latencia objetivo** | Milisegundos (path crítico) | Segundos/minutos (path analítico) |
| **Consumidor** | `correlation-engine` (decisión automática) | Operador humano o LLM de análisis post-incidente |
| **Persistencia** | Ventana temporal, evicción agresiva | Acumulativo, embedding, retrieval |
| **Semántica** | Estructurada, contrato rígido | Densa, vectorial, aproximada |

**Por qué no solapan:** `AdapterSpec` normaliza el *ingreso* de eventos al plano de correlación. `rag-ingester` normaliza el *almacenamiento* de eventos para recuperación semántica posterior. Un evento puede pasar por ambos (AdapterSpec → correlation-engine → rag-ingester como sink), por uno solo, o por ninguno. Son *pipes* en serie, no *taps* en paralelo sobre el mismo grifo.

**Riesgo real si los confundes:** Si intentas que `AdapterSpec` absorba la semántica RAG, le metes complejidad de embedding y retrieval a un path que debe ser O(1) en decisión. Si intentas que RAG absorba el contrato de crisis, pierdes la separación de planos que defiendes en 2.1.

**Recomendación:** Diferirlos para FEDER es acertado, pero documenta la distinción en el ADR de scoping (¿ADR-049? o nota en ADR-046 v4) para que no se vuelva a plantear. Post-FEDER, `rag-ingester` vuelve como plano de *knowledge*, no como reemplazo de AdapterSpec.

---

## Q2 — ¿Merece ADR-050 la frontera víctima→defender?

**Veredicto: Sí, y es de primer orden. Tu postura de seguridad es sólida, pero le falta un vector: el *bootstrap* de confianza.**

Los cuatro principios que propones (firma en origen + entrada no confiable + enforcement-nunca-bloqueado + silencio-como-señal) son correctos y defensibles ante tribunal. Sin embargo, hay un quinto elemento que no mencionas explícitamente:

**5. Bootstrap de identidad del agente:** ¿Cómo sabe `defender` que el agente que se acaba de levantar en `victim-debian` es *su* agente y no uno implantado por el atacante durante el provisioning? El agente firma con Ed25519, pero ¿de dónde saca la clave privada? Si está hardcodeada en la imagen/basebox, el atacante que compromete la imagen compromete la firma.

**Propuesta para ADR-050:**
- El agente genera par de claves en su primer arranque y hace un *attestation* inicial al `defender` vía un canal bootstrap (ej. Vagrant host-only, no routable desde el atacante).
- `defender` mantiene un `allowed_agents` registry (podría ser en `etcd`, coherente con ADR-048).
- Rotación de claves periódica, con ventana de gracia.
- El silencio-como-señal que mencionas se amplifica: si un agente *reaparece* con una clave distinta sin haber hecho rotación legítima, es compromiso confirmado (no solo "posible").

**Sobre el nombre:** ADR-050 es apropiado. El tema es "Entrega cross-frontera entre plano de enforcement y plano de detección". Es tan crítico como ADR-046 (correlación) y merece su propio documento.

---

## Q3 — Topología de víctimas: `victim-debian` + `victim-alpine`

**Veredicto: La dual-key es correcta. Alpine es riesgoso para Wazuh. Tengo alternativa.**

**Sobre Alpine:** Wazuh agente oficial no tiene build para musl libc. Hay un paquete `wazuh-agent` en Alpine testing, pero es community-maintained, suele ir varias versiones detrás, y el módulo de integridad de archivos (syscheck) a veces falla en sistemas de archivos que no son ext4/zfs. **No es confiable para FEDER.**

**Alternativas minimalistas que sí funcionan con Wazuh:**
- **Debian Slim** (`debian:12-slim`): ~30 MB base, glibc, Wazuh agente oficial estable. Pierdes "minimalismo extremo" pero ganas reproducibilidad.
- **Ubuntu Minimal** (`ubuntu:24.04-minimal`): Similar a Debian Slim, soporte Wazuh garantizado.
- **Rocky Linux Minimal** (`rockylinux:9-minimal`): Si quieres variedad de familia (RHEL vs Debian), Wazuh tiene builds oficiales.

**Mi recomendación:** Usa `victim-debian` como primaria dual-key (Wazuh + firewall-acl-agent). Usa `victim-alpine` **solo** como nodo de red/firewall (sin Wazuh), o reemplázalo por `victim-rocky` si quieres variedad de SO. Si insistes en Alpine, documenta explícitamente: "Wazuh no soportado; este nodo es sensor de red puro, no endpoint EDR". Eso refuerza la tesis de separación de planos: no todo nodo necesita EDR.

**Perfil de servicios (pendiente de ti):** Para FEDER, necesitas al menos:
- SSH (22) para brute-force.
- HTTP (80/8080) para webapp + sqlmap.
- Un puerto "bait" (ej. 3306 MySQL o 5432 PostgreSQL) para nmap/recon.

Tres servicios son suficientes para demostrar kill-chain completa sin saturar el escenario.

---

## Q4 — Reparto de componentes en `defender`

**Veredicto: Sano, pero con una reserva.**

`defender` = `sniffer` + `ml-detector` + `correlation-engine` es correcto. Son el plano de detección/correlación y deben co-locarse por latencia.

**Reserva:** El `correlation-engine` de ADR-046 v4 menciona "log de crisis". ¿Dónde se materializa ese log? Si es local en `defender`, es correcto. Si esperas que ese log sea consumido por `rag-ingester` (post-FEDER), entonces el log de crisis es la *frontera* que ADR-050 debe definir: ¿es un archivo que `rag-ingester` lee por polling, o un stream que emite por el mismo canal víctima→defender pero en dirección inversa? Mi recomendación: el log de crisis es **local inmutable** en `defender`; `rag-ingester` (cuando exista) lo lee como *lector pasivo*, nunca como consumidor prioritario. El correlation-engine no debe depender de que RAG esté vivo para registrar una crisis.

**Nada más debería salir de `defender`.** El `firewall-acl-agent` y `agente Wazuh` están correctamente en la víctima.

---

## Observaciones adicionales (no preguntadas, pero relevantes)

### Sobre el arnés de ataque (DAY 170, punto 4)
Tu formato de ground-truth es excelente. Sugiero añadir un campo: `network_segment` (ej. `intnet`, `nat`). En una arquitectura P2P/heterogénea, saber si el ataque cruzó segmento es relevante para el grafo temporal.

### Sobre picos de RSS (DAY 170, punto 5)
El `memcap` de Suricata es trampa: si lo fijas en 2 GB y el tráfico excede el buffer, Suricata *droppa* paquetes silenciosamente. Para FEDER, documenta: "memcap configurado como límite duro con alerta de drop; no como objetivo de uso". La medición de pico real es más valiosa con `tcpreplay` a velocidad de línea (1 Gbps) que a velocidad "cómoda".

### Sobre `community_id` (DAY 170, punto 6)
Asegúrate de que el `community_id` que generas en `sniffer` sea idéntico al que generaría Zeek/Suricata para el mismo 5-tupla. Si difieren en canonicalización (ej. tú usas `proto` como string "tcp" vs ellos como número 6), el join en el correlation-engine falla. Ese es el gate real de `DEBT-ARGUSPP-COMMUNITY-ID-001`.

---

## Resumen ejecutivo para Alonso

| Pregunta | Veredicto Kimi |
|---|---|
| Q1 | Capas distintas. Diferir es correcto, pero documenta la distinción. |
| Q2 | Sí, ADR-050. Añade bootstrap de identidad al agente. |
| Q3 | Debian primaria. Alpine sin Wazuh (sensor puro) o reemplazar por Rocky. Tres servicios: 22, 80/8080, bait. |
| Q4 | Sano. Log de crisis local inmutable; RAG lector pasivo post-FEDER. |

Piano, piano. DAY 170 tiene buena estructura. El riesgo mayor es Alpine+Wazuh; mitígalo temprano mañana para no perder tiempo en debugging de libc.

---
FIRMADO
*Kimi, Consejo de Sabios. DAY 169, cierre de sesión.*