# ADR-051 — Seed Parity Gate & Correlation Health

- **Estado:** BORRADOR v1 (pendiente de deliberación del Consejo de Sabios)
- **Día:** DAY 173
- **Recoge:** Consenso P2 del Consejo DAY 170 (gate de arranque análogo NTP + health-check de huérfanos continuo, sobre principio data-plane)
- **Relacionado:** ADR-046 v4 (pipeline multi-fuente, `source_wait_timeout`), ADR-052 v3.2 (identidad de flujo — consumida, no redefinida aquí), DEBT-ARGUSPP-NTP-001 (gate NTP precedente)
- **Evidencia empírica de referencia:** cross-check E2E `community_id` DAY 171/172 (`make crosscheck-up` / `make crosscheck-run`)

---

## 1. Contexto / Problema

La correlación cross-sensor del pipeline aRGus++ se apoya en `community_id` como clave de join determinista entre Suricata, Zeek y aRGus (y, por extensión, cualquier fuente que lo emita). El `community_id` es función del flujo canónico **y de un seed compartido**. Si dos sensores computan `community_id` con seeds distintos, los identificadores de un mismo flujo físico **divergen** y el join entre fuentes falla.

El modo de fallo crítico es que **el fallo es silencioso**: no hay excepción, no hay log de error, no hay alerta. El correlation-engine simplemente no encuentra correspondencias entre fuentes y el grafo de Neo4j queda poblado con nodos-flujo que nunca se unen. El sistema *parece* operativo — ingiere, procesa, escribe — pero su función esencial (correlacionar señales de múltiples paradigmas sobre el mismo flujo) está rota sin que nada lo indique.

En infraestructura hospitalaria esto es peor que un fallo ruidoso: un NDR que arranca con sensores desincronizados ofrece una **falsa sensación de cobertura**. El operador cree tener correlación multi-fuente cuando en realidad tiene tres silos desconectados.

### Por qué la validación por configuración no basta

La única garantía actual de paridad de seed es **leer la configuración** de cada sensor:
- Suricata: `community-id-seed` en `suricata.yaml`.
- Zeek: parámetro de `community_id` en `node.cfg` / scripts.
- aRGus: seed inyectado en provisión.

Esto es frágil. La configuración declara una intención; el binario emite un comportamiento. Entre ambos puede haber un override, un default no documentado, una versión distinta del sensor, o un build que ignora el campo. **Leer config valida lo que el sistema dice que hará, no lo que hace.** El incidente de DAY 172 — el VERDE de DAY 171 no era reproducible porque el entorno divergía de lo documentado en tres sitios — es la lección viva de esta brecha entre intención y comportamiento.

---

## 2. Decisión — Principio data-plane

El gate de paridad de seed y el health-check de correlación **no leen configuración**. Operan exclusivamente sobre lo que cada sensor **EMITE en runtime**: se mide el `community_id` que el binario produce sobre tráfico real, y se verifica paridad contra los demás sensores y contra el oráculo de referencia (`pycommunityid`).

Este es el mismo principio establecido en el consenso P2 del Consejo DAY 170: **la verdad está en el data-plane, no en el control-plane.** Un sensor puede tener `seed: 0` en su yaml y emitir con otro seed; lo único que importa para la correlación es el identificador que escribe en su log de salida.

El cross-check E2E de DAY 171/172 es la **implementación de referencia** de esta medición. ADR-051 no inventa un mecanismo nuevo: formaliza el cross-check existente — hasta ahora un experimento de validación — como un **gate operacional** y un **health-check continuo**.

---

## 3. Mecanismos

### 3.1 Seed Parity Gate (arranque) — BLOQUEANTE, fail-closed

Análogo al gate NTP de DEBT-ARGUSPP-NTP-001: antes de que el correlation-engine acepte tráfico productivo, debe demostrarse paridad de seed sobre un **flujo de referencia conocido**.

**Mecánica:**
1. Se inyecta (o se observa, si ya circula) el flujo-diana de referencia. Diana canónica actual: `147.32.84.165:1027 → 74.125.232.195:80` (TCP, dataset Neris), `community_id` esperado `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`.
2. Cada sensor activo (N sensores declarados en el mapa de cobertura — ver §3.4) emite su `community_id` para ese flujo.
3. El gate exige que **los N sensores coincidan byte a byte entre sí Y con el oráculo `pycommunityid`**.
4. Si hay paridad → el correlation-engine arranca.
5. Si **no** hay paridad → **fail-closed**: el correlation-engine NO arranca.

**Justificación del fail-closed (decisión explícita):** en entorno hospitalario, un NDR con sensores desincronizados correla basura silenciosamente, lo que es estrictamente peor que no correlar. La filosofía es coherente con el sniffer, que aborta limpio sin etcd (*"hardcoded keys NOT acceptable"*): aquí, *unaligned seeds NOT acceptable*. No se arranca un sistema de correlación que no puede correlar.

**Requisito de diagnóstico en el fallo (crítico para operación):** un gate bloqueante en infraestructura crítica obliga a un camino de diagnóstico inmediato. Un fallo a las 03:00 no puede ser un `gate failed` opaco. El mensaje de fallo DEBE volcar, por cada sensor que rompió paridad:
- identidad del sensor,
- `community_id` esperado (oráculo),
- `community_id` emitido,
- delta sugerido (seed declarado vs. comportamiento observado, si es inferible).

El operador debe poder realinear el sensor culpable en segundos, sin arqueología. Esta granularidad por-sensor es la misma del health-check (§3.2): el sistema señala al culpable, no se limita a declarar que algo va mal.

### 3.2 Correlation Health (continuo) — `community_id.orphan_rate` PER-SENSOR

Métrica de salud continua que detecta drift de seed (o cobertura asimétrica, o pérdida) **después** del arranque, cuando el gate ya pasó pero las condiciones cambian en runtime.

**Definición:** `orphan_rate` por sensor = fracción de flujos que ese sensor emite y que **ningún otro** sensor corrobora dentro de la ventana de correlación.

**Per-sensor, no global (decisión explícita):** la métrica per-sensor es accionable — identifica *cuál* sensor drifta para realinearlo a los demás. La métrica global solo dice que algo va mal sin señalar el culpable. El coste extra de mantener contadores por fuente es trivial frente a la información de diagnóstico que aporta.

**Interpretación de un `orphan_rate` alto** (tres causas, distinguibles solo con contexto):
- **Drift de seed:** el sensor empezó a emitir `community_id` incompatibles. Causa-raíz objetivo de esta métrica.
- **Cobertura asimétrica legítima:** el sensor ve protocolos/segmentos que otros no (p.ej. aRGus cubre solo TCP/UDP). NO es un fallo. Se distingue con el mapa de cobertura (§3.4).
- **Pérdida real:** el flujo debería haber sido visto por otros y no lo fue (drop, saturación). Fallo de captura, no de seed.

### 3.3 Huérfano vs. pendiente — el problema del timestamp (hallazgo DAY 172)

El health-check **no puede** marcar como huérfano un flujo no corroborado sin antes descartar que esté simplemente **pendiente** — dentro de la ventana `source_wait_timeout` de un sensor más lento.

El hallazgo de DAY 172 es directamente relevante y se incorpora como motivación: los timestamps internos de los sensores **no son comparables** (Suricata ancla a fin-de-flujo vía `flow.timeout`; Zeek a inicio-de-conexión; aRGus usa reloj sintético). Spreads medidos de 9.7 ms (flujos cortos) a ~116 s (flujos largos). En consecuencia:

1. Los `source_wait_timeout` supuestos de ADR-046 v4 (argus=5s / suricata=10s / zeek=20s / wazuh=90s) son **casi con seguridad demasiado bajos**, especialmente para Suricata en flujos largos, que no emite el evento de flujo hasta que el flujo termina.
2. La correlación temporal (y por tanto la distinción huérfano/pendiente) **debe medirse por wall-clock de aparición** (`time.monotonic` en el host de correlación), nunca restando timestamps internos.

**Consecuencia para ADR-051:** el gate (§3.1) es sólido y definitivo — la paridad de seed es booleana y verificable contra oráculo. Pero el **umbral del health-check** (§3.2) es **provisional** hasta que B calibre los `source_wait_timeout` reales. ADR-051 declara esta dependencia honestamente: el mecanismo de health-check queda definido aquí; su parámetro de ventana se calibra en DEBT-CORRELATION-TIMEOUT-CALIB-001.

### 3.4 Relación con el mapa de cobertura sensor↔segmento

Distinguir cobertura asimétrica legítima de pérdida real (§3.2) requiere saber **qué sensor debería ver qué**. Esto es DEBT-SENSOR-COVERAGE-MAP-001 (ADR-052 §3.8): mapa declarativo, versionado, sensor↔segmento. ADR-051 lo declara como **prerequisito del health-check** para que `orphan_rate` sea interpretable: sin el mapa, un huérfano de aRGus en un flujo ICMP es indistinguible de una pérdida, cuando en realidad aRGus no cubre ICMP por diseño.

El gate de arranque (§3.1) **no** depende del mapa de cobertura: opera sobre un flujo-diana de referencia que, por construcción, todos los sensores activos deben ver. El mapa es dependencia del health-check continuo, no del gate.

---

## 4. Consecuencias

### 4.1 Positivas
- Elimina el modo de fallo silencioso más peligroso de la arquitectura de correlación: sensores que arrancan sin paridad de seed.
- Coherencia filosófica con el resto del sistema (fail-closed, data-plane, gate de arranque análogo NTP).
- El cross-check E2E deja de ser un experimento manual y se convierte en infraestructura operacional reutilizable.
- Diagnóstico per-sensor accionable, tanto en arranque (mensaje de fallo del gate) como en runtime (`orphan_rate`).

### 4.2 Costes / riesgos
- El gate añade una fase de arranque bloqueante. Mitigado: es rápido (un flujo de referencia) y el coste de no tenerlo (correlar basura en un hospital) es inaceptable.
- El health-check `orphan_rate` depende de un contador de aRGus que aún no existe (ver §5, prerequisito COUNTER-DUMP-001). Hasta entonces, `orphan_rate` es aspiracional para la fuente aRGus.
- El umbral del health-check es provisional hasta la calibración de B.

### 4.3 Prerequisitos explícitos (declarados, no detalles)
- **DEBT-ARGUSPP-COUNTER-DUMP-001 (P1):** volcado de contadores de aRGus a fichero parseable. **Prerequisito duro del health-check**: sin la cifra base de aRGus con que comparar, `orphan_rate` para aRGus no es computable. Esta dependencia es la razón del reorden de prioridad 2→3 en el plan DAY 173: el ADR define el health-check, pero su operatividad para aRGus está bloqueada hasta el volcado.
- **DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1, "B"):** calibración de `source_wait_timeout` por wall-clock de aparición sobre 2-3 formas de flujo. El umbral huérfano/pendiente del health-check es provisional hasta su cierre.
- **DEBT-SENSOR-COVERAGE-MAP-001 (P1, ADR-052 §3.8):** prerequisito de interpretabilidad de `orphan_rate` (distinguir asimetría legítima de pérdida).

---

## 5. DEBTs generadas / cerradas

- **Cierra el diseño de** DEBT-CORRELATION-SEED-GATE-001 (gate data-plane + health-check de huérfanos). ADR-051 es su especificación.
- **Declara prerequisito** DEBT-ARGUSPP-COUNTER-DUMP-001 (P1) para operatividad del health-check.
- **Declara dependencia de calibración** DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1, B) para el umbral del health-check.
- **Declara prerequisito de interpretabilidad** DEBT-SENSOR-COVERAGE-MAP-001 (P1).
- **Nueva (propuesta):** DEBT-SEED-GATE-DIAGNOSTIC-001 (P1) — implementar el volcado de diagnóstico del fallo del gate (sensor / cid esperado / cid emitido) según §3.1.

---

## 6. Preguntas abiertas para el Consejo

1. **Flujo-diana de referencia:** ¿se inyecta sintéticamente en arranque (determinista, repetible) o se espera a observar tráfico real que produzca un flujo conocido (no bloquea boot con inyección artificial pero introduce latencia de arranque indeterminada)? Recomendación del borrador: inyección sintética del flujo Neris-diana, por determinismo y porque ya es la diana del cross-check.
2. **Re-ejecución periódica del gate:** ¿el Seed Parity Gate corre solo en arranque, o se re-ejecuta periódicamente como parte del health-check? Argumento a favor: un sensor puede recargar config en caliente y driftar post-arranque. Argumento en contra: el `orphan_rate` continuo ya detectaría ese drift. ¿Gate periódico redundante o cinturón-y-tirantes justificado?
3. **Política de degradación:** fail-closed total está decidido para arranque. ¿Y si un sensor de N pierde paridad **en runtime** (orphan_rate dispara)? ¿Se degrada a correlación con los N-1 restantes anotando la pérdida en el grafo (coherente con la filosofía de "anotar método y confianza, nunca fallo silencioso"), o se considera condición de crisis?