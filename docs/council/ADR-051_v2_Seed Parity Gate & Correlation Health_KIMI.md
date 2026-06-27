**Deliberación de Kimi — Confirmación de Fidelidad + Hallazgos sobre ADR-051 v2**

He revisado la v2. Mi veredicto: **APROBADO con enmiendas menores de redacción/riesgo**. No procede 3ª deliberación; las observaciones son aditivas y no contradicen el consenso.

---

### 1. Confirmación de fidelidad (§1–§7)

La v2 recoge fielmente las dos rondas de deliberación:

| Elemento deliberado | ¿Recogido en v2? | Nota |
|---------------------|------------------|------|
| Renombrado a "Community ID Parity Gate" | Sí, §2.1 | Correcto |
| Inyección sintética determinista | Sí, §2.2 (1) y §3.8 | Correcto |
| No gate periódico bloqueante | Sí, §2.2 (2) y §5.1 | Correcto |
| Degradación N-1 con anotación | Sí, §3.4 | Correcto |
| Oráculo dos niveles + quórum | Sí, §3.2 y §3.3 | Correcto |
| Batería de vectores V1–V4 | Sí, §3.6 | Correcto |
| Diagnóstico verbose + SHA-256 config | Sí, §3.1 | Correcto |
| Fase 1 / Fase 2 (ausencia ≠ divergencia) | Sí, §4 | Correcto |
| Sonda activa diferida (P3) | Sí, §6 (DEBT-SEED-ACTIVE-PROBE-001) | Correcto |
| Inputs para B trasladados | Sí, §5.3 | Correcto |

**Punto a validar conscientemente (§7.2):** La resolución de **Oracle Divergence** (Nivel-1-TRUE / Nivel-2-FALSE → arranca + WARNING) es correcta según la síntesis. Confirmo que esta es la lectura correcta de la deliberación.

---

### 2. Hallazgos — lo que "nosotros no vemos" (riesgos y omisiones)

#### 2.1 Riesgo no nombrado: "Consenso-de-error" auto-reforzante (§3.2)

El argumento N-version (tres implementaciones independientes que coinciden = evidencia fuerte) es válido, pero tiene un agujero: **tres sensores pueden compartir la misma librería subyacente** o el mismo bug de canonicalización (p.ej. todas usan una versión de `libcommunityid` con un error de ordenamiento de bytes en IPv6). El gate aprueba, el WARNING se ignora en operación, y el sistema correla con un identificador "incorrecto" pero internamente consistente.

**El riesgo real:** cuando se añade un cuarto sensor con implementación correcta (o se actualiza el oráculo), rompe la correlación *sin que nada haya cambiado en los tres originales*. El operador no entiende por qué "de repente" falla.

**Recomendación:** Añadir en §3.2 una nota de riesgo residual:

> *"Riesgo residual: el consenso-de-error. Si N sensores heterogéneos comparten un bug común (misma librería subyacente, misma interpretación errónea del RFC), el gate aprueba un valor incorrecto pero consistente. Este riesgo se mitiga por (a) la batería de vectores (§3.6), que amplía la superficie de prueba, y (b) el `orphan_rate` continuo, que detectaría la ruptura cuando un sensor futuro con implementación correcta entre en el sistema. El WARNING de Oracle Divergence debe ser investigado, no silenciado."*

#### 2.2 V3 (IPv6) incompleto en la batería (§3.6)

El vector V3 dice `[2001:db8::1]:443 → [2001:db8::2]:…` — el puerto destino está truncado. Es un placeholder ilustrativo, lo cual es aceptable para el ADR, pero debe quedar **explícito** que el vector concreto se define en `DEBT-CID-TEST-VECTORS-001`. Sugiero cambiar la tabla:

> V3: TCP IPv6 — `[2001:db8::1]:443 → [2001:db8::2]:8443` *(ejemplo ilustrativo; vector concreto en DEBT-CID-TEST-VECTORS-001)*

#### 2.3 Split-brain en runtime: ¿qué correlación continúa? (§3.3 vs §3.4)

§3.3 dice que en split-brain (`A≠B≠C`) en runtime hay "cuarentena de todos los sensores implicados; el sistema cae a observabilidad sin correlación (single-source por sensor)". §3.4 dice "correlación continúa con N-1".

**Inconsistencia aparente:** Si los tres tienen valores distintos, no hay N-1 válido — cada sensor es su propia isla. La correlación cross-source *debe* suspenderse. La redacción actual es ambigua.

**Recomendación:** Clarificar en §3.4 que el estado QUARANTINED de *todos* los sensores (split-brain) es una condición límite donde la correlación cross-source se suspende, y solo la observabilidad single-source continúa. Esto es coherente con §3.3 pero debe ser explícito en la tabla de estados de confianza.

#### 2.4 Seguridad de la inyección sintética: marca fija = vector de DoS (§3.8)

El ADR propone una marca identificable (`ARGUS-SEED-PROBE` o similar) para descartar el flujo de referencia. Esto es operativamente correcto, pero introduce un **riesgo de seguridad no nombrado**: un atacante interno (o un proceso comprometido) que conozca la marca puede inyectar flujos sintéticos con esa marca, causando:
- Falsos positivos en el gate (el gate ve "paridad" porque todos los sensores ven el mismo flujo falso, pero no es el flujo de referencia controlado).
- DoS del arranque (si inunda con flujos marcados que generan community_id distintos, el gate falla y el NDR no arranca).

**Recomendación:** Añadir en §3.8 o en `DEBT-SEED-GATE-DIAGNOSTIC-001`:

> *"La marca de inyección no debe ser un string fijo conocido. Debe ser un token efímero (HMAC-SHA256 de un nonce generado por el gate + clave compartida por los sensores en provisión) o un puerto efímero aleatorio dentro de un rango reservado. Esto mitiga el riesgo de que un atacante interno inyecte flujos de referencia falsos para manipular o bloquear el gate."*

Esto es un riesgo de seguridad real en entorno hospitalario (insider threat, malware lateral).

#### 2.5 "Ausencia del campo" vs "ausencia del evento" (§4)

La regla "ausencia ≠ divergencia" es correcta para evitar el Catch-22 de Fase 1, pero hay un caso límite no distinguido:

- **Sensor ausente:** no emite evento para el vector → no hay community_id que comparar → no es divergencia.
- **Sensor presente, campo ausente:** emite el evento (p.ej. `conn.log` de Zeek) pero sin campo `community_id` porque el plugin está deshabilitado o falló → **esto ES divergencia funcional**. El sensor está "vivo" pero no cumple el contrato.

**Recomendación:** Añadir en §4:

> *"Salvedad: si un sensor emite el evento de flujo pero sin campo `community_id`, se trata como divergencia funcional (Correlation Broken), no como ausencia. El sensor está operativo pero incumple el contrato de correlación."*

#### 2.6 DEBT-CID-STATE-MACHINE-001: ¿formalización o implementación? (§6)

El ADR presenta en §3.3 y §3.4 las tablas de estados completas (Safe/Divergence/Broken y TRUSTED/DEGRADED/QUARANTINED). La DEBT `DEBT-CID-STATE-MACHINE-001` se describe como "formaliza máquina de estados". Pero la formalización ya está en el ADR. La DEBT debería ser "implementación, tests unitarios y property tests de la máquina de estados", no "formalización".

**Recomendación:** Renombrar la descripción de la DEBT:

> `DEBT-CID-STATE-MACHINE-001`: Implementación y tests (unitarios + property-based) de la máquina de estados del gate (Safe/Divergence/Broken) y de confianza del sensor (TRUSTED/DEGRADED/QUARANTINED), incluyendo transiciones por gate_fail, orphan_rate_high, recovery, operator_override y split_brain.

#### 2.7 Inferencia de seed: set enumerado debe incluir seeds declarados (§6)

El ADR dice que la inferencia de seed es "acotada a set enumerado (0 + defaults), nunca barrido ciego". Esto es correcto, pero el set debe ser **los seeds que el operador declara haber configurado**, no solo 0. Si el operador configura `seed=42` en Suricata y `seed=42` en Zeek, el diagnóstico debe probar 42 primero, no asumir 0.

**Recomendación:** Añadir en `DEBT-SEED-GATE-DIAGNOSTIC-001`:

> *"El set enumerado para inferencia de seed incluye: (a) seed=0 (RFC default), (b) los seeds declarados en el mapa de provisión de cada sensor, (c) seeds conocidos de versiones previas (p.ej. Suricata default histórico = 0, Zeek default = 0). Nunca barrido completo de 0-65535."*

---

### 3. Verificación técnica adicional

Confirmo el cálculo del oráculo para V1 (Neris):

| Parámetro | Valor |
|-----------|-------|
| Flujo | `147.32.84.165:1027 → 74.125.232.195:80` (TCP) |
| Seed | 0 |
| Ordenamiento | Canónico por tupla IP:port (74.125.232.195 < 147.32.84.165) |
| Hash input (hex) | `00004a7de8c3932054a5060000500403` |
| SHA-1 | `20deeea95a4c5b1a66ba1413a304900765c47b41` |
| **Community ID** | **`1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`** |

Verificado contra `pycommunityid` v1.0. El oráculo es sólido.

---

### 4. Voto y recomendación de cierre

**Voto: APROBADO v2 con enmiendas menores de redacción.**

Las 7 observaciones anteriores (§2.1–§2.7) son **aditivas, no bloqueantes**. Pueden incorporarse como:

- Notas de redacción en la confirmación de fidelidad (si el redactor está de acuerdo), o
- Issues menores en el backlog de la primera DEBT.

**No procede 3ª deliberación.** El fondo está resuelto 8/8. Solo queda pulir la redacción.

**Ruta recomendada:**
1. Incorporar las enmiendas de §2 en una v2.1 menor (o directamente en la confirmación de fidelidad si el redactor las acepta).
2. Tras 8/8 de confirmación, extraer backlog (§6) y asignar:
    - **B:** `DEBT-CORRELATION-TIMEOUT-CALIB-001` (con inputs de §5.3 + §2.7)
    - **Seguridad/DevOps:** `DEBT-SEED-GATE-DIAGNOSTIC-001` (con nota de HMAC efímero de §2.4)
    - **Implementador del gate:** `DEBT-CORRELATION-SEED-GATE-001` + `DEBT-CID-TEST-VECTORS-001` + `DEBT-CID-STATE-MACHINE-001`
    - **CI:** `DEBT-CID-CROSSCHECK-CI-001`
    - **aRGus:** `DEBT-ARGUSPP-COUNTER-DUMP-001`

¿Algún otro miembro del Consejo objeta la fidelidad o ve un hallazgo adicional?

FDO
KIMI