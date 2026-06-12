Recibido todo. Resuelvo el punto que te dejó en fuera de juego antes de sintetizar, porque importa para la síntesis:

**Lo de Gemini.** Gemini propuso *partir* el gate en dos: gate estricto **solo para aRGus** (que es código nuestro, podemos hacer que entre en pánico si su propio seed ≠ 0) y, para Zeek/Suricata (que son binarios de terceros), **no** un gate que lea sus configs, sino solo un "canario" pasivo — observar si la correlación cae a cero y alertar entonces. Su razonamiento: como Zeek/Suricata son externos, un gate que dependa de inspeccionar sus ficheros es frágil ante cambios de versión.

Pero tu decisión en el punto 1 **supera y unifica** la propuesta de Gemini, y por eso te chirriaba. Tú no distingues "aRGus interno vs. externos". Dices: el gate mide **el community_id que cada componente emite en runtime** sobre un flujo de referencia, y comprueba que coinciden. Eso trata a los tres por igual —no lee ningún fichero, ni el de aRGus ni el yaml de Suricata ni el local.zeek— y elimina justo la fragilidad que preocupaba a Gemini (cambios de versión de los externos), porque no inspecciona config de nadie: inspecciona **salida**. La preocupación de Gemini queda disuelta, no contradicha. En la síntesis lo registraré así: "el enfoque data-plane unifica el gate sobre los tres sensores y hace innecesaria la bifurcación aRGus-interno/externos-pasivo que propuso Gemini, resolviendo su preocupación de fragilidad por otra vía."

Confirmo entonces las cuatro decisiones para la síntesis:

1. **Gate por telemetría emitida (data-plane), no por config.** El gate inyecta/observa un flujo de referencia y verifica que los tres community_id coinciden. Engañarlo exigiría modificar binarios/plugins — precisamente lo que el resto del sistema (firmas Ed25519, AppArmor, -Werror) está diseñado para impedir. Defensa coherente.
2. **Identidad de flujo = hash con componente temporal.** `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`. `community_id` permanece como propiedad indexada (clave de *correlación* y verificable contra oráculo); el hash compuesto es la *identidad* del nodo en Neo4j. Recoge la objeción de DeepSeek (reutilización de 5-tupla en el tiempo) + la formalización de Gemini/Qwen.
3. **NAT/host↔red: investigación explícita y honesta.** Se adoptará el mecanismo disponible según despliegue (Translation node / proceso+puerto_local / agent_id / fallback temporal), y **siempre se anota en grafo y log** qué método de correlación se usó y con qué confianza — incluyendo los casos de medida incorrecta/incompleta. Nada silencioso.
4. **ADRs: siguiente libre = 050 y 051.** Yo implemento, Mistral y el resto revisan. Asignación:
    - **ADR-050 — Seed Parity Gate & Correlation Health** (P2: gate data-plane + health-check de huérfanos).
    - **ADR-051 — Multi-node Flow Identity & Host↔Net Correlation** (P3: clave temporal compuesta + P1: doble arista + NAT).

   *Una duda menor que resuelvo en la síntesis:* P1 y P3 podrían ir juntos (ambos tocan el modelo de grafo Neo4j) o separados. Los junto en ADR-051 porque comparten el esquema del grafo; si prefieres P1 en su propio ADR-052, dímelo. Por defecto: 050 (seed/health) + 051 (grafo: identidad + correlación host↔red).

Voy a escribir la síntesis ahora. La dejo en `docs/counsil/` siguiendo tu patrón (`Síntesis - ...`). Te muestro el contenido aquí y te doy el heredoc para crearla en disco:

---

# Síntesis — Consejo de Sabios · DAY 170 → DAY 171

**Fecha:** 2026-05-31 · **Consenso:** 8/8 en las tres preguntas · **Voto PI (Alonso):** alineado, sin veto ejercido

## Veredicto sobre DAY 170
Aprobado con nota alta (8/8). El community_id pasa de "campo del protobuf" a **invariante de identidad operacional verificable**: validado contra oráculo (pycommunityid), seed 0 explícito y persistente en los tres sensores de red, verificado byte a byte. La de-duplicación de BACKLOG.md se valora como "arqueología forense" (Kimi): causa raíz humana (cat manual), no del script. Lección elevada a regla: integridad documental se verifica con `grep secciones | sort | uniq -d`, no con `grep -c` de cabecera; idempotencia de provisión **por línea**, no por bloque.

## DAY 171: aprobado sin bloqueos
Cross-check E2E de tres ventanas (cliente .50 replaya Neris en LAN; aRGus/Suricata/Zeek capturan en paralelo de eth1; los tres deben emitir `1:IN7uq...` sobre el mismo paquete). Añadidos pedidos por el Consejo (Kimi, Grok, Mistral): registrar **timestamp relativo de emisión y nº de paquete/flow** por sensor además del community_id (los sensores pueden converger en valor pero diferir en *cuándo* emiten — Suricata por flow.timeout, Zeek al cierre TCP); incluir caso con IPs invertidas (respuesta) y, si es posible, NAT simulado.

## P1 — Wazuh ↔ red · CONSENSO: (A)+(C), descartar (B) como base
Wazuh es host-based; la mayoría de sus eventos no tienen 5-tupla, luego no puede generar community_id nativo. **No se fuerza** (B sería cobertura parcial frágil que rompe responsabilidad única). El grafo modela dos dimensiones:
- Arista **flujo↔flujo** (`:SHARES_COMMUNITY_ID`): aRGus/Suricata/Zeek, determinista por community_id.
- Arista **host↔flujo** (`:OCCURRED_ON_HOST_WITHIN_WINDOW`): eventos Wazuh → nodo `Host` (identificado por **host_id/agent_id canónico, NUNCA por IP cruda**) → flujo, por ventana temporal.

(B) admitida solo como enriquecimiento oportunista para la fracción de eventos Wazuh con 5-tupla completa, nunca como mecanismo primario.

**Ventanas asimétricas:** red↔red estricta (±5s o duración del flujo); host↔red laxa y **causal-bidireccional** alrededor del pico de CrisisWindow (un proceso puede preceder o seguir a su tráfico). Parámetro `host_correlation_window` separado de `source_wait_timeout`, alineado con `late_arrival: true` de ADR-046.

**NAT (el agujero peligroso):** la IP que ve Wazuh ≠ la IP observada en el flujo. Menú de mecanismos según disponibilidad, **siempre anotando en grafo y log el método usado y su confianza**:
1. Nodo/arista de traducción explícito si hay logs de NAT (`(:Host)-[:SEEN_AS {type:NAT, valid_from, valid_to}]->(:Flow)`).
2. Identidad lógica por agent_id/hostname cuando esté disponible.
3. Puente `(proceso, puerto_local, timestamp)` — el socket local que Wazuh conoce sobrevive a la traducción de dirección.
4. Fallback graceful a correlación temporal+host (degradada, marcada como baja confianza) — **nunca fallo silencioso por IP no coincidente**.

→ Investigación abierta: cubrir explícitamente los casos correctos, incorrectos, e incompletos de medida.

## P2 — Invariante seed · CONSENSO: gate P0 + health-check, basado en DATA-PLANE
El fallo es silencioso y catastrófico (seed divergente → cero matches sin error). Dos capas:
- **Gate de arranque P0** (análogo a NTP): el correlation-engine verifica paridad **midiendo el community_id que cada sensor emite en runtime** sobre un flujo de referencia, NO leyendo sus ficheros de config. Razón (PI + Qwen + Gemini): el JSON/yaml puede mentir o ser sobrescrito por paquetes; la única verdad es lo que el binario emite. Este enfoque data-plane **unifica el gate sobre los tres sensores** y disuelve la preocupación de Gemini sobre fragilidad ante cambios de versión de los externos — no inspecciona config de nadie, observa salida. Divergencia → `SEED_MISMATCH`, abort.
- **Health-check continuo:** ratio `community_id.orphan_rate` (flujos sin corroboración cross-sensor cuando deberían tenerla). Caída de matches a ~0 o orfandad sistemática >umbral en N ventanas → alerta CRITICAL. Captura deriva post-arranque (reconfiguración, parche, pérdida de sensor).

## P3 — Identidad de flujo multi-nodo · CONSENSO: clave compuesta CON componente temporal
community_id global colisiona en multi-nodo (misma 5-tupla en sedes distintas → mismo hash) **y en el tiempo** (puertos efímeros reciclados → misma 5-tupla, conexiones distintas — objeción de DeepSeek). Decisión:
- **Identidad del nodo-flujo en Neo4j:** `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`.
- **community_id permanece como propiedad indexada** — clave de *correlación* intra-nodo y verificable contra oráculo; legible para debug. No se "namespacea" dentro del string (rompería la verificación contra oráculo — apunte de Kimi).
- `node_id` como propiedad obligatoria en `:NetworkFlow`, `:Alert`, `:TelemetryEvent`.
- Constraint compuesto nativo Neo4j 5.x. Correlación intra-nodo por community_id; identidad/dedup inter-nodo por flow_uid.
- Decidirlo hoy (grafo vacío) es gratis; retrofitear con datos en producción es doloroso. Unánime.

*Fuera de alcance FEDER (investigación futura):* correlación de "flujo global" inter-sede (movimiento lateral hospital A→B). Tercer tipo de arista; no sobre-diseñar ahora.

## Acciones → BACKLOG / ADR
- **ADR-050 — Seed Parity Gate & Correlation Health** (P2): gate data-plane + orphan_rate health-check.
- **ADR-051 — Multi-node Flow Identity & Host↔Net Correlation** (P3+P1): flow_uid temporal compuesto, doble arista, ventanas asimétricas, menú NAT con anotación de confianza.
- **DEBT-NEO4J-FLOW-KEY-001 (P0 esquema):** flow_uid + node_id obligatorio antes de poblar el grafo. Bloquea el diseño del correlation-engine.
- **DEBT-CORRELATION-SEED-GATE-001:** implementación del gate P0 + health-check.
- **RESEARCH — puente host↔red bajo NAT:** Translation node / agent_id / (proceso, puerto_local) / fallback temporal, con anotación explícita de método y confianza en grafo+log. Cubrir casos correctos/incorrectos/incompletos.
- **DAY 171:** cross-check E2E tres ventanas + registro de timestamp/nº-paquete por sensor + caso IPs invertidas + NAT simulado si posible.

## Notas de proceso
- Consenso 8/8 alcanzado en primera pasada; no se requiere segunda ronda. PI no ejerce veto.
- Convergencia notable: los 8 coinciden en (A)+(C), gate+health-check, y clave compuesta. Refinamientos clave aportados: data-plane sobre config (PI/Qwen/Gemini), componente temporal en la clave (DeepSeek/Gemini/Qwen), NAT por host_id canónico (unánime).
- Implementación: Claude implementa bajo TDH; Mistral y el resto del Consejo como revisores. Para Wazuh, se compartirá la implementación de forma explícita y generosa con el equipo.

---

Esa es la síntesis. Dos cosas antes de escribirla en disco:

- **Nombres de fichero:** ¿`docs/counsil/Síntesis - Consejo de Sabios — DAY 170.md`? Sigue tu patrón (`Síntesis - CONSEJO DE SABIOS — DAY NNN.md`). Y mi respuesta individual ya está subida como `...-CLAUDE.md`, así que solo falta la síntesis.
- **Los DEBT/ADR** los he nombrado provisionalmente. Cuando me pases el BACKLOG.md veré la numeración real de DEBTs existentes y ajusto IDs para no colisionar (lección del community_id: verificar antes de asignar).

¿Escribo la síntesis en `docs/counsil/` con ese nombre, o ajustas algo del contenido primero? Y cuando digas, me pasas BACKLOG.md / README.md / prompt de continuidad y los actualizo con todo esto ya asimilado.