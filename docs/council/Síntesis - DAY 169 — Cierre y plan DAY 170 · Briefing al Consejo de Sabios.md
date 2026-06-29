# Síntesis del feedback del Consejo — DAY 169 → DAY 170

**Proyecto:** aRGus++ (NDR-EDR Híbrido Distribuido)
**Fecha:** 2026-05-29 (cierre DAY 169)
**Redacta:** Claude (Anthropic), sobre las 8 respuestas del Consejo
**Objeto:** consolidar el feedback en algo accionable para DAY 170; corregir lo que no debe entrar al ADR; decidir qué vuelve al Consejo.

---

## 1. Veredicto general

**Ratificación unánime (8/8)** de las decisiones de la tarde (separación de planos, frontera víctima→defender, reasignación de componentes) y de las cuatro respuestas Q1–Q4. No hay disidencia. Lo que sigue son refinamientos aditivos + una aportación nueva de peso (bootstrap de identidad, Kimi) + correcciones al feedback.

---

## 2. Consolidación por pregunta

### Q1 — rag-ingester vs AdapterSpec → **planos distintos; diferir es correcto** (8/8)
- Solapan solo en la *superficie de ingesta*, no en función. Marco que adopta el Consejo (Kimi): son **pipes en serie**, no taps en paralelo — un evento puede fluir `AdapterSpec → correlation-engine → rag-ingester` (rag como *sink*), no son dos grifos sobre la misma fuente.
- **Acción:** documentar la distinción (detección determinista vs conocimiento semántico). **Corrección de numeración:** Mistral y Kimi sugieren "ADR-049" — **ese número está ocupado** (Vault HA + Shamir). La distinción cabe como nota en ADR-046 v4, o ADR nuevo con número libre. No reutilizar 049.

### Q2 — Frontera víctima→defender → **ADR-050, sí** (8/8). Lista de vectores consolidada:
1. **Firma en origen (Ed25519)** + **entrada no confiable** (`validate_or_abort`) + **enforcement nunca bloqueado por telemetría**. *(base)*
2. **Anti-replay** (consenso total): la firma cubre **contador monotónico + timestamp + nonce**; ventana de validez (Qwen: ±5 s, nonce 64-bit); rechazar viejo/desordenado/nonce repetido. Reutiliza el checkpoint monotónico de AdapterSpec.
3. **Bootstrap de identidad del agente (Kimi — la aportación nueva más importante):** si la clave de firma está horneada en la basebox, comprometer la imagen compromete la firma → toda la postura se cae. Fix: el agente **genera par de claves en primer arranque** y hace **attestation** a defender por **canal bootstrap = plano de gestión (eth0), no la intnet atacada (eth1)**; defender mantiene un registro `allowed_agents` (en **etcd**, coherente con ADR-048); rotación con ventana de gracia; un agente que **reaparece con clave distinta sin rotación legítima = compromiso CONFIRMADO** (no solo posible).
4. **Validación cruzada = testigo OFF-HOST.** Matiz importante: la validación mutua debe ser **plano de red (sensores, fuera del host) contra telemetría de host**, no dos fuentes on-host (firewall vs Wazuh, ambas comprometibles si el host cae). El atacante en el host no controla a Suricata/Zeek/aRGus; un host que reporta "todo en orden" mientras la red ve ataque hacia él es contradicción de alta señal.
5. **Espectro de degradación** (ChatGPT/Qwen): no solo alive/dead — distinguir `network_partition` / `agent_crash` / `host_compromise` por umbrales de latencia, caída abrupta de volumen, bursts imposibles, heartbeat sin payload útil, usando el estado de los *otros* sensores del mismo host.
6. **Rotación + revocación de claves** documentada (DeepSeek/Qwen/Kimi).

- **Corrección cripto (importante):** Mistral propone añadir **AES-256-GCM** (confidencialidad) y **HMAC-SHA256** (integridad). **Son redundantes** con el stack que ya tienes: **ChaCha20-Poly1305 es AEAD** (confidencialidad *y* integridad vía Poly1305) + Ed25519 (autenticidad de origen) + HKDF, sobre ZeroMQ. ADR-050 **no necesita cripto nueva**: necesita *aplicar* la existente a través de la nueva frontera + añadir anti-replay (2) + bootstrap (3). No reinventar el AEAD.
- **Nota de reproducibilidad:** las claves del agente son específicas del run (generadas en arranque); viven en la telemetría *en vivo*, no en el núcleo reproducible del dataset (como `ingested_at`). El replay lee envelopes grabados (artefacto B), no re-firma. No tratar las claves como núcleo reproducible.

### Q3 — Topología de víctimas → **Debian primaria; Alpine fuera del camino crítico** (8/8)
- `victim-debian` primaria dual-key: sin reservas. Wazuh-en-Alpine (musl) confirmado arriesgado por todos.
- **Fallback de consenso: Debian-minimal/slim** (mismo glibc, agente Wazuh de primera clase, footprint pequeño). Otros candidatos citados: Ubuntu minimal, Rocky (variedad RHEL), Void, OpenWrt+osquery, Fedora CoreOS — opcionales, no necesarios.
- Alpine → **degradar a "nodo de firma de red" (sin Wazuh)** si no entra en una tarde; refuerza la tesis de separación de planos (no todo nodo necesita EDR) y aún aporta variedad al dataset.
- **Perfil de servicios (lo que faltaba de ti) — consenso:** SSH (22, brute-force/hydra) + webapp HTTP (80/8080, nginx+php para sqlmap) + **un puerto bait** (3306/5432 para recon/nmap). Tres servicios bastan para una kill-chain completa.

### Q4 — Reparto en defender → **sano, con aislamiento** (8/8)
- `sniffer + ml-detector + correlation-engine` co-locados = correcto para FEDER.
- **Aislamiento AHORA, no cuando el estrés lo revele** (Qwen/Mistral/Gemini): `cgroups v2` con límites diferenciados (Suricata CPU-alta + memoria capada ~2.5 G; ml-detector CPU-shares menor, memoria ~4 G; correlation-engine memoria reservada, I/O throttled). Suricata: `memcap 2048mb`, `max-pending-packets 8192`, `prealloc-sessions 16384`; monitorizar `kernel_packets` vs `kernel_drops`.
- **Log de crisis = local inmutable en defender** (Kimi); rag-ingester (post-FEDER) lo lee como **lector pasivo**, nunca consumidor prioritario; el correlation-engine no depende de que RAG esté vivo.
- Segregación fase-2 (post-FEDER): correlation-engine como servicio stateful propio, ml-detector como cluster de inferencia, sniffer como edge collectors. Diferido.

---

## 3. Catches técnicos a NO perder

- **`community_id` — el gate real de `DEBT-ARGUSPP-COMMUNITY-ID-001` (Kimi):** el ID que genere el sniffer DEBE ser idéntico al de Zeek/Suricata para la misma 5-tupla. Si la canonicalización difiere (p. ej. `proto` como string `"tcp"` vs número `6`, u orden de endpoints), el join falla **en silencio**. Es exactamente el bug de orden de bytes que cazamos en la Pasada 1. Test de coherencia obligatorio antes del primer dataset.
- **`memcap` es trampa (Kimi/Mistral/Qwen):** si el tráfico excede el buffer, Suricata **dropea en silencio**. Documentar memcap como **límite duro con alerta de drop**, no como objetivo de uso. Medir el pico real a **velocidad de línea**, no "cómoda".
- **Test de reproducibilidad (DeepSeek):** ejecutar **dos kill-chains idénticas con minutos de diferencia** y comprobar que el artefacto B + `config_hash` reproducen bit-a-bit. Evidencia de alto valor para el tribunal.
- **`config_hash` extendido (Qwen):** debe incluir **versión de atomic-red-team + seed de aleatoriedad**, no solo los parámetros del engine.
- **Ground-truth (Kimi):** añadir campo `network_segment` (`intnet`/`nat`) a la etiqueta.
- **RSS bajo carga (DeepSeek/Gemini):** la cuenta de los 32 GB es *en reposo*; el tribunal querrá p50/p95/máximo bajo ataque representativo.

---

## 4. Orden de ejecución DAY 170 (síntesis de los ocho)

Hay tensión entre "ADR-050 primero" (Mistral) y "víctima+RSS primero" (Qwen). Resolución: **ADR-050 no bloquea levantar la víctima ni medir RSS ni el dev de community_id** — gobierna el *cableado* de telemetría firewall→defender, que es aguas abajo. Se redacta en paralelo.

1. **RSS bajo carga — ya, hoy mismo si quieres.** No necesita víctima: pipeline + client + tcpreplay (escalonar 10/50/100% de línea). Cierra la cuenta de hardware con evidencia. Es lo más barato y desbloquea el debate N100.
2. **Perfil de servicios decidido** (SSH + nginx+php + bait DB) → **bloque `victim-debian`** en Vagrantfile (tus reglas: sin `set -e`, chrony→DNS-fix, `printf`, `autostart:false`); validar registro del agente Wazuh con el manager .12.
3. **cgroups en el provision de defender** (no esperar al estrés).
4. **`community_id` en sniffer + proto + `-Werror`** (dev en paralelo; gate del dataset; ojo a la canonicalización proto-número).
5. **Arnés de ataque + ground-truth** (con `network_segment`, `config_hash` con versión ART).
6. **ADR-050 en paralelo** (no bloquea 1–5; gatea el cableado firewall→defender).
7. **Housekeeping:** quitar `metasploit-framework` del provision.
8. **Validación Alpine** con caja de tiempo corta; fallback Debian-minimal si no entra.

---

## 5. ¿Qué vuelve al Consejo?

**Nada como pasada-de-preguntas ahora** — Q1–Q4 están cerradas 8/8. Lo que volverá al Consejo, cuando exista, es:
- El **borrador de ADR-050** (como se hizo con ADR-046): incorpora los 6 vectores de §2-Q2, con el bootstrap de Kimi como sección propia y la corrección cripto.
- La **Pasada 4** (contrato del dataset federado) cuando toque. *(Corrección de numeración: Mistral lo llama "ADR-051"; el número lo asignas tú al redactarlo, evitando colisiones.)*

---

*Síntesis cerrada. DAY 170: medir, materializar, no explorar. Piano, piano.*