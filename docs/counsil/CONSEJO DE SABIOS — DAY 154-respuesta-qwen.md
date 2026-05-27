**CONSEJO DE SABIOS — DICTAMEN TÉCNICO: INTEGRACIÓN, FAIL-CLOSED Y TUNING — DAY 154**
*Expertise en arquitectura distribuida, seguridad de red crítica y ZeroMQ — para aRGus NDR v0.8.0-adr045*

---

## 🎯 VEREDICTO EJECUTIVO

**TRABAJO APROBADO CON DIRECCIÓN CLARA** ✅

La descomposición de `VaultClient` mediante composición (`IVaultTransport`, `ICacheManager`, `ICryptoDeriver`, `IEtcdRegistrar`) es un ejemplo de arquitectura C++20 madura. `FirewallAutonomyReactor` con executor inyectable es testable y operable. EMECAS verde en hardened-full es señal de calidad.

**Respuestas concisas a P1–P4 abajo.**

---

## 🔍 RESPUESTA P1: Polling vs. Eventos ZMQ para señal de autonomía

**Veredicto**: 🎯 **Opción A (Polling etcd) como trampolín para DAY 155**, con migración planificada a ZMQ post-FEDER.

### Matriz de decisión

| Criterio | Polling (etcd, 30s) | Eventos ZMQ (pub/sub) |
|----------|---------------------|----------------------|
| **Complejidad de implementación** | ✅ Baja: reutiliza health-check loop existente | 🟡 Media: nuevo topic, suscripción, manejo de desconexión |
| **Latencia de reacción** | 🟡 ≤30s (aceptable para transiciones de autonomía) | ✅ <1s (óptimo, pero no crítico para este caso) |
| **Fiabilidad en aislamiento** | ✅ etcd local ya está disponible; sin nuevo canal | 🟡 ZMQ interno añade dependencia; si falla, se pierde la señal |
| **Testabilidad** | ✅ Fácil de mockear en tests unitarios | 🟡 Requiere fixture de ZMQ context + pub/sub |
| **Evolución post-FEDER** | 🟡 Refactorizable a ZMQ sin cambiar interfaz pública | ✅ Ya está en el modelo "event-driven" final |

### Recomendación de implementación (DAY 155)

```cpp
// firewall-acl-agent/main_loop.cpp — polling como trampolín
void HealthCheckLoop::run() {
    while (running_) {
        // ... otros checks de salud ...
        
        // Polling de autonomía (trampolín DAY 155)
        auto autonomy_state = crypto_provider_->get_autonomy_state();
        if (autonomy_state != last_autonomy_state_) {
            firewall_reactor_->on_autonomy_state_changed(autonomy_state);
            last_autonomy_state_ = autonomy_state;
            log_info("Autonomy state changed: {}", to_string(autonomy_state));
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(30));
    }
}
```

**Nota de migración**: Documentar en `docs/ROADMAP.md` que el polling es temporal. Post-FEDER, reemplazar con:

```cpp
// Post-FEDER: ZMQ pub/sub (cuando CryptoAutonomyStateMachine emita eventos)
zmq::socket_t sub_socket(ctx_, ZMQ_SUB);
sub_socket.connect("inproc://argus.crypto.events");
sub_socket.set(zmq::sockopt::subscribe, "argus.crypto.autonomy");
// ... reactor escucha eventos en lugar de pollear ...
```

**Conclusión**: Polling primero. La señal de autonomía es un evento de baja frecuencia (transiciones cada horas/días, no milisegundos). La simplicidad operativa gana en infraestructura crítica.

---

## 🔍 RESPUESTA P2: Granularidad del default-deny en AUTONOMOUS

**Veredicto**: ✅ **Default-deny selectivo: bloquear externo, preservar interno**.

### Modelo de amenaza hospitalario

```
Escenario: Hospital aislado (WAN cortada), ransomware interno activo.

Tráfico que DEBE bloquearse:
- Entrante desde WAN (ya cortada, pero por defensa en profundidad)
- Lateral desde segmentos no críticos (IoT, invitados) hacia críticos (UCI, quirófanos)

Tráfico que DEBE preservarse:
- Loopback (127.0.0.0/8): servicios locales, health checks internos
- Subredes clínicas RFC1918 (10.x, 192.168.x): dispositivos médicos, historiales locales
- Tráfico establecido/relacionado (ESTABLISHED,RELATED): no romper sesiones activas
```

### Regla iptables recomendada

```bash
# FirewallAutonomyReactor::apply_default_deny() — versión selectiva
# 1. Preservar loopback
iptables -I INPUT 1 -i lo -j ACCEPT --comment "argus-autonomy-lo"

# 2. Preservar subredes clínicas internas (configurable vía JSON)
iptables -I INPUT 2 -s 10.0.0.0/8 -j ACCEPT --comment "argus-autonomy-rfc1918-a"
iptables -I INPUT 3 -s 172.16.0.0/12 -j ACCEPT --comment "argus-autonomy-rfc1918-b"
iptables -I INPUT 4 -s 192.168.0.0/16 -j ACCEPT --comment "argus-autonomy-rfc1918-c"

# 3. Preservar sesiones establecidas (no romper comunicaciones activas)
iptables -I INPUT 5 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT --comment "argus-autonomy-established"

# 4. DROP todo lo demás (fail-closed para tráfico nuevo externo/no clasificado)
iptables -I INPUT 6 -j DROP --comment "argus-autonomy-deny-new-external"
```

### Configuración vía JSON (inyectable)

```json
// firewall-acl-agent.prod.json
{
  "autonomy_mode": {
    "preserve_loopback": true,
    "preserve_rfc1918": true,
    "preserve_established": true,
    "custom_internal_subnets": ["10.42.0.0/16"],  // subred específica del hospital
    "log_dropped": true  // auditar qué se bloquea en autonomía
  }
}
```

### Justificación de seguridad

| Postura | Riesgo si se equivoca | Veredicto |
|---------|----------------------|-----------|
| **Fail-closed total** | Bloquea comunicaciones clínicas internas → impacto en atención al paciente | ❌ Demasiado agresivo para infraestructura crítica |
| **Fail-open parcial** | Permite tráfico externo no filtrado → ransomware se propaga | ❌ Demasiado permisivo |
| **Fail-closed selectivo** | Balancea seguridad operativa con continuidad clínica | ✅ **Recomendado** |

**Conclusión**: Default-deny selectivo con preservación de loopback, RFC1918 y sesiones establecidas. Documentar en ADR-045 §FirewallAutonomyReactor.

---

## 🔍 RESPUESTA P3: Parámetros ZMQ críticos antes de benchmarks

**Veredicto**: 🎯 **HWM (High Water Mark) primero**, luego `reconnect_ivl`/`reconnect_ivl_max`, finalmente timeouts.

### Prioridad de tuning ZeroMQ para benchmarks de capacidad

| Parámetro | Por qué es crítico | Valor recomendado para benchmark |
|-----------|-------------------|--------------------------------|
| **`ZMQ_SNDHWM` / `ZMQ_RCVHWM`** | Controla backpressure; si es demasiado bajo, se pierden mensajes bajo carga; si es demasiado alto, se consume memoria excesiva | 1000–10000 (empezar con 1000, escalar según observación) |
| **`ZMQ_RECONNECT_IVL` / `ZMQ_RECONNECT_IVL_MAX`** | Define comportamiento ante desconexión transitoria; crítico para medir resiliencia, no solo throughput | 100ms / 5000ms (reintento exponencial) |
| **`ZMQ_SNDTIMEO` / `ZMQ_RCVTIMEO`** | Timeouts de operación; importantes para latencia percentil 99, pero menos críticos para throughput bruto | -1 (bloqueante) para benchmarks de capacidad pura; ajustar después para tests de latencia |
| **`ZMQ_LINGER`** | Comportamiento al cerrar socket; afecta limpieza de recursos en tests repetidos | 0 (no esperar, limpiar rápido) |

### Plan de tuning escalonado

```bash
# Fase 1 (DAY 155-156): HWM básico
# Configurar HWM=1000 en todos los sockets, medir pérdida de mensajes bajo carga sintética

# Fase 2 (post-FEDER): Reconnect + timeouts
# Añadir reconnect_ivl exponencial, medir recuperación ante fallos simulados

# Fase 3 (benchmark final): Ajuste fino por percentil
# Optimizar para p99 latency sin sacrificar throughput
```

### Script de validación mínima (DAY 155)

```cpp
// test_zmq_hwm.cpp — validar que HWM no causa pérdida silenciosa
TEST(ZmqTuning, HWMDoesNotDropUnderExpectedLoad) {
    // Configurar socket con HWM=1000
    // Enviar 900 mensajes rápidos sin receiver
    // Verificar que todos se encolan (no se pierden)
    // Enviar 1100 mensajes: los últimos 100 deben bloquear o descartar según policy
    // Assert: comportamiento es predecible y documentado
}
```

**Conclusión**: HWM primero. Es el parámetro que más afecta a la relación throughput/memoria/pérdida. Los demás se ajustan iterativamente.

---

## 🔍 RESPUESTA P4: Interface Segregation en CaptureBackend — ¿DAY 155?

**Veredicto**: 🟡 **No hoy; consolidar ZMQ primero, ISP en DAY 156**.

### Justificación de priorización

| Factor | Mover ISP hoy (DAY 155) | Mover ISP mañana (DAY 156) |
|--------|------------------------|---------------------------|
| **Dependencia con ZMQ integration** | 🟡 Ninguna directa | ✅ ZMQ estabilizado primero reduce superficie de cambio |
| **Riesgo de regresión** | 🟡 Medio: tocar interfaz base afecta a sniffer + tests | 🟢 Bajo: refactor aislado, tests ya verdes |
| **Valor para FEDER deadline** | 🟡 Bajo: mejora de diseño, no funcionalidad | 🟢 Alto: ZMQ integrado → demo de autonomía operativa |
| **Esfuerzo estimado** | 🟡 4-6h (refactor + tests + validación EMECAS) | 🟢 2-3h (refactor limpio, sin presión de integración) |

### Plan recomendado

```bash
# DAY 155: Integrar ZMQ events (P1) + HWM tuning (P3)
# DAY 156 por la mañana: Cerrar DEBT-CAPTURE-BACKEND-ISP-001
#   - Mover get_xdp_stats() a EbpfBackend
#   - Actualizar tests de Variant B (libpcap) para verificar que no ven métodos eBPF
#   - Validar EMECAS tras refactor
```

**Patrón de refactor seguro**:
```cpp
// Antes (violación ISP):
class CaptureBackend {
    virtual void start() = 0;
    virtual XdpStats get_xdp_stats() = 0;  // ← eBPF-specific, visible en libpcap
};

// Después (ISP aplicado):
class CaptureBackend {
    virtual void start() = 0;
    virtual ~CaptureBackend() = default;
};

class EbpfBackend : public CaptureBackend {
public:
    XdpStats get_xdp_stats() override;  // ← solo en backend eBPF
};

class LibpcapBackend : public CaptureBackend {
    // No implementa get_xdp_stats() — compilador garantiza aislamiento
};
```

**Conclusión**: ISP es importante, pero no bloquea la demo de autonomía. Consolidar ZMQ primero, refactorizar después.

---

## 📋 RESUMEN DE DECISIONES PARA DAY 155

| Pregunta | Decisión | Acción inmediata |
|----------|----------|-----------------|
| **P1: Polling vs ZMQ** | Polling etcd como trampolín | Implementar en `HealthCheckLoop`, documentar migración futura |
| **P2: Granularidad deny** | Selectivo: preservar loopback+RFC1918+ESTABLISHED | Actualizar `FirewallAutonomyReactor::apply_default_deny()` |
| **P3: ZMQ tuning** | HWM primero (1000), luego reconnect, luego timeouts | Crear `test_zmq_hwm.cpp`, configurar sockets con HWM=1000 |
| **P4: ISP en CaptureBackend** | Postponer a DAY 156 | Añadir ticket `DEBT-CAPTURE-BACKEND-ISP-001` a backlog DAY 156 AM |

---

## 🚀 PLAN DE TRABAJO DAY 155

```bash
# Mañana (P1 + P2 + P3):
1. Integrar polling de autonomía en firewall-acl-agent health loop
2. Implementar default-deny selectivo con preservación de tráfico clínico
3. Configurar HWM=1000 en todos los sockets ZMQ, añadir test de validación
4. Validar EMECAS tras cambios (bootstrap + test-all + hardened)

# Tarde (si sobra tiempo):
5. Esbozar migración a ZMQ pub/sub en docs/ROADMAP.md
6. Preparar skeleton para ISP refactor (DAY 156 AM)
```

---

## 💬 FRASE DE CIERRE

> *"La arquitectura no es solo separar responsabilidades; es elegir qué separar hoy y qué dejar para mañana. En infraestructura crítica, la simplicidad operativa no es un lujo: es un requisito de seguridad. Que cada regla iptables preserve vida, y cada parámetro ZMQ mida lo que importa."*

---

**¿Procedemos a implementar el polling de autonomía en `HealthCheckLoop` y el default-deny selectivo en `FirewallAutonomyReactor` para DAY 155?** 🛡️🔐🧠