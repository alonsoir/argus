# DAY 169 — Cierre y plan DAY 170 · Briefing al Consejo de Sabios

**Proyecto:** aRGus NDR → aRGus++ (NDR-EDR Híbrido Distribuido)
**Fecha cierre:** 2026-05-29 (DAY 169)
**Para:** Consejo de Sabios (Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen) y archivo de Alonso
**Propósito:** registrar lo hecho hoy, fijar el plan de DAY 170, y recoger feedback del Consejo antes de continuar.

---

## 1. Lo cerrado hoy (DAY 169)

- **Deliberación del Consejo completa (4 pasadas).** Integración multi-motor resuelta: modelo dual de claves, grafo temporal heterogéneo asimétrico, fuentes esperadas dinámicas + ventanas separadas, evicción en 3 capas con cuota anti-pinning, horizonte de reorden, inmutabilidad + event-sourcing, reproducibilidad vía `config_hash`, artefacto autoritativo (B) + pcap de verificación.
- **ADR-046 v4** redactado y aceptado (sustituye a v3). **`AdapterSpec v1`** redactado como documento normativo aparte.
- **D5 resuelto por Alonso:** el entregable FEDER es el pipeline vivo ejecutando MITRE ATT&CK + captura inmutable + replay determinista → dataset reproducible para demostrar la **plausibilidad del entrenamiento distribuido federado**.
- **Pipeline arriba:** `vagrant up defender suricata zeek wazuh` — los cuatro corriendo, **`defender` incluido** (era el bloqueo de DAY 168).
- **RSS en reposo medido** (asignado/usado interno): defender 8 GB/871 MB · suricata 2 GB/780 MB · zeek 2 GB/244 MB · wazuh 4 GB/674 MB. **Veredicto:** el time-slice server↔pipeline cabe en 32 GB con holgura; el hardware externo (N100/Pi) **probablemente no es necesario para FEDER** (queda como upgrade post-FEDER que refuerza la tesis federada por mérito propio). Falta medir **picos bajo carga**.
- **`client` listo:** tcpreplay + nmap + atomic-red-team operativos. (metasploit no es paquete apt; queda fuera, no es crítico — atomic-red-team es el framework MITRE.)

---

## 2. Decisiones de arquitectura de la tarde (a ratificar)

**2.1 Separación de planos (principio rector, defendible ante tribunal).** El plano de detección/correlación **no** se coloca sobre el activo a proteger. En el activo solo vive el mínimo que tiene que actuar localmente: **agente firewall** (actúa sobre el firewall físico local) y **agente Wazuh** (un HIDS es host-based por definición). Sensores + ml-detector + correlation-engine viven fuera, en defender.

**2.2 Reasignación de componentes.**
- **defender** (plano de detección): `sniffer`, `ml-detector` (+ correlation-engine y log de crisis de ADR-046 v4, núcleo del plano — a confirmar co-locación).
- **victim-debian** (activo a proteger, primario dual-key): `agente Wazuh` + `firewall-acl-agent`.
- **victim-alpine** (nodo mínimo/edge, variedad de dataset): igual, **pendiente de validar** que el agente Wazuh corre sobre Alpine/musl; si no, se elige otro SO minimalista donde sí entre.
- **`rag-ingester` + `rag-security`: DIFERIDOS** por probable solapamiento con `AdapterSpec v1`. (Ver pregunta Q1 — no dado por resuelto.)

**2.3 Nueva frontera de entrega: víctima → defender.** Lo que antes era co-locación cómoda (salida de firewall == entrada de rag-ingester) pasa a ser un canal **cross-máquina y cross-frontera-de-confianza** (el agente vive en un activo potencialmente comprometido). Implicaciones:
- Mismo contrato que AdapterSpec: **at-least-once + idempotencia (dedup) + buffer durable acotado + backpressure que nunca bloquea**.
- **Desacople enforcement/telemetría (ADR-047):** el firewall **sigue bloqueando localmente y bufferiza** aunque el canal a defender caiga; el enforcement nunca se bloquea por la entrega de telemetría.
- **Confianza:** el agente **firma en origen (Ed25519)**; rag-ingester/defender tratan el stream como **entrada no confiable** (valida, acota, rate-limita; nunca a ciegas), misma disciplina que `validate_or_abort()` antes de `dlopen`.
- **El silencio del agente es señal:** un agente que deja de latir en un host bajo ataque es evento de correlación (posible compromiso), no "fallo de entrega" — el correlation-engine ya sabe tratar una fuente armada que enmudece.
- **HA (ml-detector↔rag-ingester):** apoyarse en **etcd/Raft (ADR-048)** + idempotencia; "una canónica, las demás segregadas, nunca mezcladas".

> Esta frontera probablemente merezca **ADR nuevo (¿ADR-050?)** — "Entrega entre plano de enforcement y plano de detección" — por su decisión de seguridad de primer orden. No redactado aún.

---

## 3. Plan DAY 170 (orden de ataque)

1. **Decidir perfil de servicios de la víctima** (SSH solo, o SSH + webapp para sqlmap, + puerto extra para nmap). *Pendiente de Alonso.*
2. **Escribir bloque `victim-debian`** en el Vagrantfile (agente Wazuh → manager .12; firewall-acl-agent; chrony contra el mismo origen NTP; servicios; en `eth1`/intnet). Reglas: nada de `set -e` en provisions, DNS-fix tras chrony, `printf` en vez de heredoc anidado, `autostart: false`.
3. **Validar agente Wazuh sobre `victim-alpine`.** Si no entra limpio: elegir SO minimalista alternativo, o degradar Alpine a "nodo de firma de red" y documentarlo.
4. **Arnés de ataque en `client`:** scenario runner + formato de etiqueta ground-truth (`{scenario_id, step_index, technique_id, tactic, tool, attacker_ip, target_host_key, expected_domain, start_unix_ns, end_unix_ns, config_hash}`) + captura. Primer **kill-chain dual-dominio** (recon→brute-force→persistencia host→exfil).
5. **Capturar picos de RSS bajo carga** (estrés con tcpreplay) — cierra con evidencia la cuenta de los 32 GB; vigilar el `memcap` de Suricata.
6. **(Dev, prioridad 2 real de DAY 169, en paralelo):** `community_id` en sniffer + `network_security.proto`, `-Werror`, EMECAS++. Gate del test de coherencia y de `DEBT-ARGUSPP-COMMUNITY-ID-001`.
7. **Housekeeping:** quitar del provision de `client` la línea `apt install metasploit-framework` (deja de escupir el `E:` rojo).

---

## 4. Preguntas al Consejo (feedback antes de continuar)

**Q1 — ¿`rag-ingester` solapa con `AdapterSpec`, o son planos distintos?** Hipótesis de Alonso: solapamiento (de ahí el diferimiento). Contrahipótesis: son capas distintas — AdapterSpec alimenta el **correlation-engine** (crisis en tiempo real), rag-ingester alimenta la **capa de conocimiento RAG** (recuperación semántica para análisis). Si son distintos, rag vuelve post-FEDER en su propio plano; si solapan de verdad, es una simplificación. En cualquier caso, **diferirlos para el empuje FEDER es buen scoping.** ¿Veredicto?

**Q2 — La frontera víctima→defender, ¿merece ADR-050?** ¿Es correcta la postura de seguridad (firma en origen + entrada no confiable + enforcement-nunca-bloqueado + silencio-como-señal), o falta algún vector?

**Q3 — Topología de víctimas.** `victim-debian` (primaria dual-key) + `victim-alpine` (edge, variedad). ¿Objeciones al riesgo Wazuh-en-Alpine? ¿Mejor SO minimalista candidato si Alpine falla?

**Q4 — Reparto de componentes.** defender = sniffer + ml-detector (+ correlation-engine). ¿Sano, o algo más debería salir de defender hacia su plano correcto?

---

## 5. Deudas y pendientes vivos

- `DEBT-ARGUSPP-COMMUNITY-ID-001` — verificar `community_id` en outputs reales (gate: dev de prioridad 2).
- `DEBT-ARGUSPP-CLOCK-ADVERSARIAL-001` — reloj adversarial (post-FEDER).
- **Número físico pendiente:** picos de RSS bajo carga (Suricata) + footprint del server a solas.
- **Pasada 4** (cuando toque): contrato del dataset federado (Parquet, etiquetado MITRE por fase, particionado, walk-forward).
- Posible **ADR-050**: entrega enforcement↔detección.

---

*DAY 169 cerrado. Descanso. Mañana: víctima, arnés de ataque, y feedback del Consejo. Piano, piano.*