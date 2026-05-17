**CONSEJO DE SABIOS — DICTAMEN TÉCNICO: INTEGRACIÓN, TOPOLOGÍA Y BENCHMARKS — DAY 155**
*Expertise en arquitectura distribuida C++20, ZeroMQ y modelos de amenaza para infraestructura crítica*

---

## 🎯 VEREDICTO EJECUTIVO

**TRABAJO APROBADO CON DIRECCIÓN CLARA** ✅

La cadena `argus-autonomy` con orden estructural garantizado es un ejemplo de ingeniería de firewall robusta. `AutonomyPublisher/Subscriber` con IPC + safety-net polling es un patrón maduro. EMECAS HARDENED con `-flto` + AppArmor es señal de calidad de producción.

**Respuestas concisas a Q1–Q5 abajo.**

---

## 🔍 RESPUESTA Q1: Proceso propietario de `CryptoAutonomyStateMachine`

**Veredicto**: 🎯 **Opción A (etcd-server) para FEDER**, con migración planificada a daemon dedicado post-FEDER.

### Matriz de decisión

| Opción | Pros | Contras | Veredicto |
|--------|------|---------|-----------|
| **A: etcd-server** | ✅ Ya tiene health-check loop; ya depende de `ICryptoProvider`; coordinación natural | 🟡 Acopla crypto state a consenso distribuido | ✅ **Recomendado para FEDER** |
| **B: daemon dedicado** | ✅ SRP limpio; escalable independientemente | 🟡 Añade proceso operativo; overhead para FEDER | 🔄 Post-FEDER refactor |
| **C: sniffer** | ✅ Primero en arrancar | ❌ Sniffer es captura de paquetes, no gestión de estado crypto | ❌ Rechazado |
| **D: cada componente** | ✅ Sin SPOF para publishing | ❌ Múltiples publishers = duplicación, ordering issues, complejidad subscriber | ❌ Rechazado |

### Justificación técnica para etcd-server

```cpp
// etcd-server/main.cpp — integración mínima
int main() {
    // ... bootstrap crypto existente ...
    
    // Instanciar máquina de estados de autonomía (FEDER)
    auto autonomy_sm = std::make_unique<CryptoAutonomyStateMachine>(config.autonomy);
    auto publisher = std::make_unique<AutonomyPublisher>("ipc:///run/argus/autonomy.sock");
    
    // Conectar callback: transición de estado → publicar evento ZMQ
    autonomy_sm->set_transition_callback(
        [pub = publisher.get()](CryptoAutonomyStateMachine::State new_state) {
            pub->publish_state_change(new_state);
        }
    );
    
    // Integrar con health-check loop existente de etcd-server
    HealthCheckLoop health_loop(vault_config, std::move(autonomy_sm));
    
    // ... resto del arranque de etcd ...
}
```

**Nota de migración post-FEDER**: Si la operabilidad requiere separación, extraer a `argus-crypto-daemon` es un refactor limpio porque la lógica ya está encapsulada en `CryptoAutonomyStateMachine`.

---

## 🔍 RESPUESTA Q2: Endpoint pub/sub — ¿`ipc://` o `tcp://` en producción?

**Veredicto**: ✅ **Mantener `ipc://` para todos los despliegues FEDER**.

### Justificación arquitectónica

```
El canal de autonomía es por-nodo-edge, no global:
- Cada edge node tiene su propio estado de autonomía (basado en su Vault local, su cache local)
- El firewall que subscribe está siempre en el mismo host que el publisher
- El servidor central, si tiene componente firewall, también es co-locado con el publisher

Por tanto: ipc:// es correcto, seguro y eficiente en todas las topologías FEDER.
```

### Beneficios de `ipc://` sobre `tcp://` en este caso

| Criterio | `ipc:///run/argus/autonomy.sock` | `tcp://127.0.0.1:XXXX` |
|----------|--------------------------------|----------------------|
| **Latencia** | ✅ ~10µs (sin stack de red) | 🟡 ~50-100µs (loopback TCP) |
| **Seguridad** | ✅ Permisos de fichero Unix (0600) | 🟡 Requiere firewall local o TLS |
| **Simplicidad** | ✅ Sin gestión de puertos | 🟡 Necesita asignación de puerto único |
| **Evolución futura** | 🟡 Si publisher/subscriber se separan, requiere refactor | ✅ Ya soporta red, pero over-engineering hoy |

**Conclusión**: No over-engineer para un escenario que no existe en FEDER. Si post-FEDER surge una topología distribuida para autonomía, se diseña un nuevo canal — no se compromete el actual.

---

## 🔍 RESPUESTA Q3: `reconcile_interval_sec=90` — ¿configurable y qué hace el reconciliador?

**Veredicto**: 🎯 **Configurable desde JSON + re-aplicar último estado (no consultar Vault)**.

### Parte 1: Configurabilidad

```json
// firewall.json — autonomía
{
  "autonomy": {
    "whitelist_cidrs": ["10.0.0.0/8", "192.168.0.0/16"],
    "reconcile_interval_sec": 90,  // ← configurable, default 90s
    "safety_net_enabled": true
  }
}
```

**Justificación**: En infraestructura crítica, la flexibilidad operativa es un requisito. Un hospital con red muy dinámica puede preferir 30s; uno estable, 300s. El coste de hacerlo configurable es mínimo (ya está en el schema); el beneficio es alto.

### Parte 2: Comportamiento del reconciliador

```cpp
// AutonomySubscriber::reconcile() — safety net, no mecanismo primario
void AutonomySubscriber::reconcile() {
    if (!safety_net_enabled_) return;
    
    // NO consultar Vault/etcd — eso es responsabilidad del path event-driven
    // El reconciliador solo asegura que el estado local (iptables) coincide con el último estado conocido
    
    if (last_known_state_ == AutonomyState::AUTONOMOUS) {
        // Re-aplicar reglas de forma idempotente
        firewall_reactor_->apply_default_deny_selective(whitelist_cidrs_);
        log_debug("Reconciler: re-applied autonomous deny rules");
    } else {
        // En NORMAL/REVOKED, asegurar que no hay reglas residuales
        firewall_reactor_->lift_default_deny_if_active();
        log_debug("Reconciler: ensured deny rules lifted");
    }
}
```

**Justificación de seguridad**: Si el reconciliador consultara Vault durante autonomía extendida, introduciría una dependencia externa que puede estar inaccesible — convirtiendo el safety net en un punto de fallo adicional. El reconciliador debe ser **autónomo por diseño**.

---

## 🔍 RESPUESTA Q4: Estructura de carpetas para código enterprise (`vault_client`, `VaultProvider`)

**Veredicto**: 🎯 **`enterprise/` al mismo nivel que `common/`**, con CMake condicional.

### Estructura recomendada

```
src/
├── common/              # Open-core: idéntico en community/enterprise
│   ├── crypto_autonomy.h
│   ├── autonomy_publisher.h
│   └── ...
├── enterprise/          # Enterprise: solo con ARGUS_VAULT_ENABLED=ON
│   ├── vault_client.h/.cpp
│   ├── vault_provider.h/.cpp
│   └── CMakeLists.txt
├── sniffer/
├── firewall-acl-agent/
└── ...
```

### CMakeLists.txt raíz — anticipación

```cmake
# Root CMakeLists.txt
add_subdirectory(common)

if(ARGUS_VAULT_ENABLED)
    add_subdirectory(enterprise)
    target_link_libraries(argus-core PRIVATE enterprise)
    target_compile_definitions(argus-core PRIVATE ARGUS_VAULT_ENABLED=1)
endif()

add_subdirectory(sniffer)
add_subdirectory(firewall-acl-agent)
# ...
```

### Beneficios de esta estructura

| Beneficio | Impacto |
|-----------|---------|
| **Claridad de licenciamiento** | Desarrolladores ven inmediatamente qué código es community vs enterprise |
| **Build condicional limpio** | CMake maneja la inclusión; no hay `#ifdef` dispersos más allá de `CryptoProvider::create()` |
| **Evolución futura** | Si se añaden más módulos enterprise (Falco integration, Neo4j connector), tienen un hogar claro |
| **Auditabilidad** | Un auditor puede verificar que `enterprise/` no se incluye en builds community |

**Conclusión**: Documentar esta estructura en `docs/OPEN_CORE.md` ahora, aunque la migración física de ficheros sea post-FEDER.

---

## 🔍 RESPUESTA Q5: Benchmarks sintéticos en VirtualBox — ¿sí o no?

**Veredicto**: ✅ **Sí, ejecutar benchmarks sintéticos en VirtualBox ahora**, con labeling explícito y foco en comparativas relativas.

### Estrategia recomendada

```yaml
# docs/BENCHMARKS.md — política de reporting
virtualbox_benchmarks:
  purpose: "Regression baseline, not production capacity"
  labeling: "Results obtained on VirtualBox 7.2 / Debian bookworm64; bare-metal FEDER hardware will show higher throughput"
  focus: "Relative comparisons (A vs B config), not absolute numbers"
  metrics:
    - throughput_pps_relative  # % cambio entre configuraciones
    - latency_p99_delta        # diferencia en ms, no valor absoluto
    - memory_efficiency_ratio  # MB por 1K flujos, comparativo
```

### Beneficios de hacer benchmarks en VirtualBox ahora

| Beneficio | Justificación |
|-----------|-------------|
| **Validar harness de benchmarking** | Mejor encontrar bugs en el script de medición en VirtualBox que en hardware FEDER |
| **Establecer baseline de regresión** | Si un commit hace caer un 20% el throughput en VirtualBox, es señal de alerta temprana |
| **Documentar metodología para el paper** | La sección de benchmarks puede escribirse mientras se espera hardware; los revisores valoran transparencia metodológica |
| **Identificar cuellos de botella algorítmicos** | Ineficiencias O(n²) se manifiestan en cualquier entorno; VirtualBox es suficiente para detectarlas |

### Mitigación de riesgos de malinterpretación

```markdown
## Advertencia en todos los reportes de VirtualBox

> **Nota de capacidad**: Los resultados presentados se obtuvieron en entorno virtualizado (VirtualBox 7.2, Debian bookworm64, 6 vCPU, 8GB RAM asignados). 
> 
> - **No representan capacidad de producción**: El hardware FEDER bare-metal mostrará throughput significativamente mayor.
> - **Propósito**: Estos números sirven como *baseline de regresión* y *validación metodológica*, no como garantía de capacidad operativa.
> - **Comparativas válidas**: Las diferencias relativas entre configuraciones (ej: "BM-B es 15% más eficiente que BM-A") suelen preservarse entre entornos.
```

**Conclusión**: Ejecutar benchmarks sintéticos ahora acelera el ciclo de desarrollo sin comprometer la credibilidad, siempre que el labeling sea explícito.

---

## 📋 RESUMEN DE DECISIONES PARA DAY 156

| Pregunta | Decisión | Acción inmediata |
|----------|----------|-----------------|
| **Q1: Proceso owner** | etcd-server para FEDER | Integrar `CryptoAutonomyStateMachine` + `AutonomyPublisher` en `etcd-server/main.cpp` |
| **Q2: Endpoint pub/sub** | Mantener `ipc://` | Documentar en `docs/ARCHITECTURE.md` que autonomía es por-nodo, no global |
| **Q3: Reconciliador** | Configurable + re-aplicar estado | Pasar `reconcile_interval_sec` desde JSON; implementar `reconcile()` idempotente |
| **Q4: Estructura enterprise** | `enterprise/` paralelo a `common/` | Añadir nota en `docs/OPEN_CORE.md`; preparar CMake condicional |
| **Q5: Benchmarks VirtualBox** | Sí, con labeling explícito | Crear `scripts/benchmark-virtualbox.sh` con disclaimer integrado |

---

## 🚀 PLAN DE TRABAJO DAY 156

```bash
# Mañana (P0 + P1):
1. Integrar CryptoAutonomyStateMachine en etcd-server (Q1)
2. Pasar reconcile_interval_sec desde firewall.json a AutonomySubscriber (Q3)
3. Implementar reconcile() idempotente que re-aplica estado conocido
4. Validar EMECAS tras integración (bootstrap + test-all + hardened)

# Tarde (P2):
5. Actualizar docs/OPEN_CORE.md con estructura enterprise/ propuesta (Q4)
6. Crear script de benchmark sintético con disclaimer integrado (Q5)
7. Esbozar migración post-FEDER a argus-crypto-daemon en docs/ROADMAP.md
```

---

## 💬 FRASE DE CIERRE

> *"La autonomía no se delega; se coordina. El IPC no es un detalle de implementación; es un pacto de localidad. Y el benchmark no mide mentiras: mide metodología. Que cada transición de estado sea un acto de soberanía, y cada número, una promesa de transparencia."*

---

**¿Procedemos a integrar `CryptoAutonomyStateMachine` en `etcd-server/main.cpp` y pasar `reconcile_interval_sec` desde `firewall.json` para DAY 156?** 🛡️🔐🧠