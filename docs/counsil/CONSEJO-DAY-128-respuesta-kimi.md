## Consejo de Sabios — Respuesta DAY 128

Buen cierre de día. El pipeline 6/6 y la documentación de deuda técnica son señales de salud. Respondo por orden de riesgo y dependencia.

---

### P1 — Invariante `0400` vs portabilidad

**Veredicto: Mantened la invariante. El `sudo` generalizado no es el problema; la falta de granularidad sí lo es.**

La decisión de `0400 root:root` es correcta para material criptográfico de sistema. Sin embargo, "generalizado" es la palabra clave. No todos los componentes del pipeline deberían necesitar `CAP_DAC_OVERRIDE` implícito vía `sudo`.

**Estrategia recomendada: `AmbientCapabilities` + `CapabilityBoundingSet` en systemd units.**

En lugar de `sudo` blanket, definid units con:
```ini
[Service]
User=argus-service
Group=argus-service
AmbientCapabilities=CAP_DAC_READ_SEARCH
CapabilityBoundingSet=CAP_DAC_READ_SEARCH
NoNewPrivileges=true
```
Esto permite al servicio leer el seed sin ser root, sin relajar `0400`. Verificad que `resolve_seed()` haga `faccessat(AT_EACCESS)` para validar que el caller *podría* leerlo, no solo que el UID efectivo lo permite.

**Riesgo identificado:** Si usáis `sudo env LD_LIBRARY_PATH=...` en Makefiles, el `env` hereda el entorno del caller. Auditad que `LD_LIBRARY_PATH` no provenga de input no controlado. Considerad `sudo -E` solo donde sea estrictamente necesario.

**Alternativa sin `sudo`:** Linux capabilities son la respuesta. No relajáis la invariante, distribuís el privilegio.

---

### P2 — Property testing como gate de merge

**Veredicto: Sí, pero con prioridad estricta por superficie de ataque, no por cobertura lineal.**

Los 5 tests actuales cubren paths y seeds. La siguiente prioridad debería ser:

| Prioridad | Superficie | Justificación | Framework sugerido |
|-----------|-----------|---------------|-------------------|
| **P0** | `compute_memory_mb` (F17) | Overflow aritmético → DoS o alloc masivo | RapidCheck / libfuzzer |
| **P0** | HKDF key derivation | Propiedad: `derive(seed, salt) != derive(seed', salt)` si seed cambia; longitud output fija | RapidCheck + libsodium harness |
| **P1** | Parsers ZeroMQ | Propiedad: parse(serialize(x)) == x; frames malformadas no crashean | RapidCheck con generador de frames arbitrarias |
| **P1** | Serialización protobuf | Propiedad: round-trip; campos desconocidos ignorados sin crash | libprotobuf-mutator |
| **P2** | `IPTablesWrapper` | Propiedad: `cleanup_rules()` nunca genera cmd > MAX_CMD_LEN | RapidCheck + mock de `execute_command` |

**Regla de oro para el gate:** Un property test debe fallar con un input mínimo que un unit test tradicional no habría encontrado. Si no encontráis un counter-example en 10.000 iteraciones, el test no está ejercitando la propiedad correcta.

**Acción inmediata:** Antes de declarar "property testing como gate", definid un harness común en `contrib/testing/property_harness.hpp` con generadores de paths válidos/inválidos, seeds mock, y frames ZMQ. Evitad que cada developer reinvente el generador.

---

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

**Veredicto: Opción (b) `execve()` directo sin shell, con fallback a (c) `libiptc` si el refactor es viable.**

Análisis de opciones:

- **(a) Whitelist:** Frágil. `iptables` tiene ~100 subcomandos y sintaxis depende de la versión del kernel. Mantener una whitelist es deuda técnica garantizada.
- **(b) `execve()` directo sin shell:** **Recomendada a corto plazo.** Construíd el `argv[]` vector en C++, validando cada argumento con una regex estricta (`^[a-zA-Z0-9_:-]+$` para nombres de cadena, `^\d+\.\d+\.\d+\.\d+(/\d+)?$` para CIDRs). Nunca concatenéis strings.
- **(c) `libiptc`:** **Recomendada a medio plazo.** Elimina el fork/exec por completo, pero requiere linkear contra `libip4tc`/`libip6tc` y manejar la API de bajo nivel de netfilter. Es el camino correcto si el `IPTablesWrapper` es componente crítico permanente.

**Implementación inmediata para (b):**
```cpp
// Antes (vulnerable):
std::string cmd = "iptables -A INPUT -p tcp --dport " + user_port + " -j ACCEPT";
execute_command(cmd);  // shell interpreta ';', '|', '$()'

// Después:
const char* argv[] = {
    "/sbin/iptables", "-A", "INPUT", "-p", "tcp",
    "--dport", validated_port.c_str(), "-j", "ACCEPT", nullptr
};
execve("/sbin/iptables", const_cast<char**>(argv), environ);
```

Validad `validated_port` con `std::stoi` + rango 1-65535 + regex `^\d+$`. Rechazad cualquier caracter no numérico.

**Nota:** Si usáis `system()` o `popen()` en cualquier otro lado del codebase, cread `DEBT-SHELL-INJECTION-AUDIT-001` y auditad todo.

---

### P4 — Arquitectura P2P seeds vs etcd-server

**Veredicto: Limpiad EtcdClient **después** de ADR-024 funcional, no antes.**

La secuencia correcta es:

```
ADR-024 (Noise_IKpsk3) → Integración P2P seed exchange → EtcdClient deprecado → Cleanup
```

**Razonamiento:** `EtcdClient` es el fallback de seed actual. Si lo limpiáis antes de que ADR-024 distribuya seeds de forma confiable, el sistema no puede arrancar en un entorno limpio (como demostró el DAY 128 con la VM nueva). El `resolve_seed()` fallaría silenciosamente o requeriría un mecanismo de bootstrap que no existe todavía.

**Plan de transición sugerido:**

1. **Fase 1 (ahora):** Marcad `EtcdClient::resolve_seed()` como `[[deprecated("Replaced by P2P seed exchange per ADR-024")]]`. No lo borréis.
2. **Fase 2:** Implementad ADR-024 con un modo "hybrid": intenta P2P primero, fallback a etcd si no hay peers disponibles (útil para el nodo bootstrap).
3. **Fase 3:** Cuando el pipeline arranque 6/6 con P2P puro en la VM destruida/reconstruida, entonces eliminad el fallback etcd y limpiad `EtcdClient`.

**Dependencia crítica:** El nodo bootstrap (el primero en la red) necesita una seed inicial. Resolved si el bootstrap usa un seed local `0400` (que requiere `sudo` o capabilities) o si el seed se inyecta vía otro canal (TPM, cloud-init, etc.). Esto debe estar en el ADR-024 antes de tocar EtcdClient.

---

### P5 — Demo FEDER (deadline: 22 septiembre 2026)

**Veredicto: NDR standalone es el scope mínimo viable. Federación real es deseable pero no requerida para la demo.**

**Análisis de riesgo-tiempo:**

| Escenario | Probabilidad de éxito | Esfuerzo estimado |
|-----------|----------------------|-------------------|
| NDR standalone + UI | Alta (>85%) | 6-8 semanas |
| NDR + federación básica (2 nodos) | Media (50-60%) | 12-16 semanas |
| NDR + federación completa (ADR-038) | Baja (<30%) | 20+ semanas |

Tenéis ~5 meses hasta septiembre. El riesgo no es técnico — es de integración. ADR-038 implica consenso distribuido, descubrimiento de peers, y resolución de conflictos de policy. Cualquiera de esos tres puede consumir 2 meses inesperados.

**Scope recomendado para la demo:**

1. **NDR standalone completo:** Detección, clasificación, respuesta automática (contención), y reporte.
2. **Simulación de federación:** Un segundo nodo que reciba un feed resumido (no full P2P) vía un túnel pre-configurado. Demuestra la *intención* arquitectural sin la complejidad del consenso.
3. **Dashboard unificado:** Que muestre ambos nodos, aunque el segundo sea "mock" o semi-manual.

**Milestone de go/no-go:** 1 de agosto. Si para esa fecha no tenéis ADR-024 estable y P2P básico entre 2 VMs, congelad en NDR standalone puro. Es mejor una demo sólida de un sistema que funciona que una demo frágil de federación.

---

### Estado del Consejo al cierre

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| P1 | Mantener `0400`, migrar a capabilities | Auditar `sudo env` en Makefiles |
| P2 | Gate sí, con prioridad P0/P1/P2 | Crear `property_harness.hpp` común |
| P3 | `execve()` sin shell ahora, `libiptc` después | Implementar validación estricta de argv |
| P4 | EtcdClient cleanup post-ADR-024 | Marcar como deprecated, no borrar |
| P5 | NDR standalone viable, federación simulada | Milestone go/no-go: 1 agosto |

**Deuda técnica crítica pendiente:** `DEBT-IPTABLES-INJECTION-001` debe resolverse antes del siguiente tag. Es el único item bloqueante real.

Buen trabajo en el DAY 128. La reconstrucción de la VM desde cero y el hallazgo del `0400` demuestran que el sistema es reproducible y las invariantes se respetan. Eso es más valioso que cualquier feature nuevo.

— Kimi