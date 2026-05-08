## Kimi — Respuesta al Consejo de Sabios — DAY 143

*Evaluación bajo criterios de gestión de procesos zombie, coherencia de tipos numéricos, seguridad operacional en entornos médicos, y mínimo privilegio en AppArmor.*

---

### P1 — `fork()+execv()` sin `wait()`: acumulación de zombies

**Hipótesis:** Un proceso hijo sin `wait()` se convierte en zombie hasta que `init` lo recoge. En un pipeline de larga duración con aislamientos repetidos, esto puede agotar la tabla de procesos del kernel.

**Veredicto: **Sí, se acumulan zombies. El diseño actual es incorrecto para operación prolongada.** Implementar `waitpid(-1, WNOHANG)` periódico o `SIGCHLD` handler.**

**Análisis técnico:**

En Linux, un proceso hijo que termina pero cuyo padre no hace `wait()` entra en estado `Z` (zombie). Ocupa una entrada en la tabla de procesos (PID, estado de salida, recursos). La tabla de procesos tiene límite (`/proc/sys/kernel/pid_max`, típicamente 32768). En un ataque ransomware persistente que dispara aislamiento cada 30 segundos durante horas:

- 120 aislamientos/hora × 24h = 2880 zombies/día
- En 11 días: 31680 zombies → agotamiento de PIDs → kernel no puede crear más procesos → **DoS del sistema**

**Solución 1: `SIGCHLD` handler (recomendada)**

```cpp
// firewall-acl-agent.cpp — inicialización
void setup_sigchld_handler() {
    struct sigaction sa;
    sa.sa_handler = [](int) {
        // Reap all available children without blocking
        while (waitpid(-1, nullptr, WNOHANG) > 0) {}
    };
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART | SA_NOCLDSTOP;
    sigaction(SIGCHLD, &sa, nullptr);
}
```

Ventajas:
- No requiere cambios en el hilo worker
- `SA_RESTART` evita que `EINTR` interrumpa syscalls
- Reap asíncrono, no bloqueante

**Solución 2: `waitpid(-1, WNOHANG)` periódico en worker thread**

```cpp
// BatchProcessor::process_batch() — al final de cada batch
void reap_zombies() {
    pid_t pid;
    int status;
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        LOG_INFO("Reaped isolation child PID {} with status {}", pid, status);
        active_isolations_.erase(pid);
    }
}
```

Ventajas:
- Síncrono, predecible
- Permite logging de estado de salida
- Permite detectar fallos repetidos de `argus-network-isolate`

**Recomendación:** Implementar **ambas**. `SIGCHLD` como línea de defensa principal, `waitpid(-1, WNOHANG)` periódico como verificación explícita y oportunidad de logging.

**Test de cierre:**

```cpp
TEST(AutoIsolate, NoZombieAccumulation) {
    // Disparar 100 aislamientos sintéticos
    for (int i = 0; i < 100; ++i) {
        trigger_isolation(synthetic_event_0_97);
    }
    std::this_thread::sleep_for(100ms);  // Tiempo para que terminen
    
    // Verificar que no hay zombies
    auto zombies = count_zombie_processes();
    EXPECT_EQ(zombies, 0) << "Zombie processes detected: " << zombies;
}
```

---

### P2 — Tolerancia IEEE 754: ¿`float` vs `double` para threshold?

**Hipótesis:** La comparación `float confidence` vs `double threshold` introduce imprecisión que requiere tolerancia. Tipos consistentes eliminarían la necesidad de tolerancia.

**Veredicto: **El threshold debe ser `float`, no `double`.** La precisión de `float` (~7 dígitos decimales) es suficiente para un threshold de 0.95. La inconsistencia de tipos es el bug de raíz; la tolerancia es un parche.**

**Análisis de precisión:**

| Tipo | Dígitos significativos | Representación de 0.95 | Error absoluto |
|------|----------------------|------------------------|----------------|
| `float` (IEEE 754 single) | ~7 | `0.949999988079071044921875` | ~1.2×10⁻⁸ |
| `double` (IEEE 754 double) | ~15 | `0.949999999999999955591079` | ~4.4×10⁻¹⁷ |

El problema ocurre porque:
1. `IsolateConfig` almacena `threshold` como `double` (JSON parsea a double)
2. `NetworkSecurityEvent.confidence_score()` devuelve `float` (protobuf `float` = `float32`)
3. La comparación promociona `float` a `double`, pero el valor ya perdió precisión al ser `float`

**Fix correcto:**

```cpp
// isolate_config.hpp
struct IsolateConfig {
    float threat_score_threshold;  // Era double — cambiar a float
    // ...
};

// should_auto_isolate() — sin tolerancia, tipos consistentes
bool should_auto_isolate(float score, DetectionType type, const IsolateConfig& config) {
    return score >= config.threat_score_threshold && 
           config.auto_isolate_event_types.contains(type);
}
```

**JSON parseo:** `nlohmann::json` parsea números a `double` por defecto. Cast explícito a `float`:

```cpp
config.threat_score_threshold = j.value("threat_score_threshold", 0.95f);  // float literal
```

**Eliminar tolerancia:** Con tipos consistentes, `0.95f >= 0.95f` es exactamente `true`. La tolerancia `1e-6` es un parche que oculta el bug de diseño.

**Riesgo de eliminar tolerancia:** Si alguien cambia el JSON a `0.95000001`, `float` no puede representarlo exactamente. Pero eso es un error de configuración, no un bug numérico.

**Regla permanente propuesta:**

> **RULE-TYPE-CONSISTENCY-001:** Los thresholds, scores y métricas comparables deben usar el mismo tipo numérico en toda la pipeline. `float` es suficiente para scores de ML (0.0–1.0, precisión ~10⁻⁷). `double` solo para cálculos intermedios de alta precisión. Nunca comparar tipos diferentes sin cast explícito documentado.

---

### P3 — `auto_isolate: true` por defecto en hospitales

**Hipótesis:** Un default `true` protege por omisión pero puede causar daño en el primer falso positivo si el admin no ha leído el manual.

**Veredicto: **Mantener `true` por defecto, pero con gate de onboarding obligatorio.** El principio de "instalar y funcionar" no significa "instalar y olvidar". Un sistema de seguridad que requiere habilitación manual está deshabilitado en la práctica.**

**Análisis de riesgo:**

| Escenario | `auto_isolate: false` default | `auto_isolate: true` + gate |
|-----------|------------------------------|----------------------------|
| Hospital instala, no lee manual | ❌ Sin protección automática | ✅ Protegido tras gate |
| Falso positivo en primer día | N/A (no dispara) | ⚠️ Posible, pero whitelist protege |
| Admin experto quiere control total | Debe habilitar explícitamente | Puede deshabilitar en onboarding |
| Auditoría de seguridad | "¿Por qué estaba deshabilitado?" | "Gate completado el día X" |

**Gate de onboarding propuesto:**

```bash
# /usr/local/bin/argus-onboarding-check
#!/bin/bash
set -euo pipefail

ONBOARDING_FILE="/etc/ml-defender/.onboarding-complete"

if [ -f "$ONBOARDING_FILE" ]; then
    exit 0  # Onboarding ya completado
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  aRGus NDR — First-Time Setup                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Auto-isolation is ENABLED by default."
echo "This will isolate network segments when threats are detected."
echo ""
echo "CRITICAL: Add medical devices to whitelist before proceeding:"
echo "  /etc/ml-defender/firewall-acl-agent/isolate.json"
echo ""
echo "Options:"
echo "  [1] I have configured the whitelist — ENABLE auto-isolate"
echo "  [2] I need to configure whitelist first — DISABLE auto-isolate"
echo "  [3] I understand the risks — ENABLE without whitelist"
echo ""
read -p "Select option [1-3]: " option

case $option in
    1)
        echo "Auto-isolate ENABLED. Whitelist configured."
        ;;
    2)
        sed -i 's/"auto_isolate": true/"auto_isolate": false/' \
            /etc/ml-defender/firewall-acl-agent/isolate.json
        echo "Auto-isolate DISABLED. Re-enable after whitelist configuration."
        ;;
    3)
        echo "WARNING: Auto-isolate ENABLED without whitelist."
        echo "Medical devices may be isolated during false positives."
        ;;
    *)
        echo "Invalid option. Auto-isolate remains ENABLED."
        ;;
esac

touch "$ONBOARDING_FILE"
logger -p auth.notice "aRGus onboarding completed with option $option"
```

**Este gate:**
- No requiere leer el manual completo
- Fuerza una decisión consciente sobre whitelist
- Deja audit trail (`logger` + `.onboarding-complete`)
- No bloquea la instalación (el admin puede elegir opción 2 y volver luego)

**Regla permanente propuesta:**

> **RULE-ONBOARDING-001:** Todo componente con acción automática de alto impacto (aislamiento de red, bloqueo de tráfico) requiere gate de onboarding interactivo en primera instalación. El default es protección máxima, pero el admin debe confirmar conocimiento de las implicaciones.

---

### P4 — AppArmor `/tmp`: glob vs directorio específico

**Hipótesis:** Un glob en `/tmp/argus-*.nft` permite que un atacante con control del nombre escriba archivos arbitrarios en `/tmp`.

**Veredicto: **El glob es aceptable si el nombre incluye un componente impredecible, pero un directorio dedicado es arquitectónicamente superior.** Implementar `/var/lib/argus/irp/` con permisos estrictos.**

**Análisis de ataque:**

Si el atacante compromete `argus-network-isolate`, puede:
1. Escribir `/tmp/argus-isolate-../../etc/cron.d/backdoor.nft`
2. El glob `argus-isolate-*.nft` NO coincide con `../../etc/cron.d/backdoor.nft`
3. **Pero** si hay un bug en el parsing del path dentro del binario...

El glob de AppArmor es una línea de defensa, no la única. El binario debe sanitizar sus propios paths.

**Mejora recomendada:**

```apparmor
# ANTES (glob en /tmp)
/tmp/argus-backup-*.nft rw,
/tmp/argus-isolate-*.nft rw,

# DESPUÉS (directorio dedicado)
/var/lib/argus/irp/ rw,
/var/lib/argus/irp/** rw,
```

**Y en el binario:**

```cpp
// argus-network-isolate.cpp — generación de paths segura
std::filesystem::path get_irp_temp_dir() {
    auto dir = std::filesystem::path("/var/lib/argus/irp");
    std::filesystem::create_directories(dir);
    // 0700 — solo owner puede leer/escribir
    std::filesystem::permissions(dir, 
        std::filesystem::perms::owner_all);
    return dir;
}

std::filesystem::path generate_temp_file(const std::string& prefix) {
    auto dir = get_irp_temp_dir();
    // Nombre con componente aleatorio de 16 bytes hex
    auto random = crypto::random_bytes(16);
    auto filename = fmt::format("{}-{}.nft", prefix, hex_encode(random));
    return dir / filename;
}
```

**Ventajas del directorio dedicado:**
- No compite con otros procesos en `/tmp`
- Permisos `0700` por defecto
- No depende de glob parsing en AppArmor
- Más fácil de auditar (`ls -la /var/lib/argus/irp/`)

**Para FEDER:** El glob en `/tmp` es aceptable si se documenta la limitación. El directorio dedicado es `DEBT-IRP-DEDICATED-DIR-001` para v0.7.

---

### P5 — Criterio de disparo: ¿dos señales son suficientes?

**Hipótesis:** Dos condiciones AND (score + tipo) pueden no ser suficientes en un entorno hospitalario con equipos médicos críticos. Una tercera señal podría reducir falsos positivos catastróficos.

**Veredicto: **Dos señales son suficientes para FEDER, pero la arquitectura debe permitir extensión a multi-señal sin refactor mayor.** Implementar `should_auto_isolate()` como composable strategy pattern.**

**Análisis de señales:**

| Señal | Disponibilidad | Valor añadido | Coste de falso negativo |
|-------|---------------|---------------|------------------------|
| Score >= 0.95 | Siempre | Alto | Bajo |
| Tipo en whitelist | Siempre | Alto | Bajo |
| Segundo sensor confirma | Post-FEDER (requiere HA) | Muy alto | Medio |
| Ausencia en asset whitelist | Siempre | Alto | Bajo |
| Hora del día (no quirófano) | Siempre | Medio | Alto (ataques nocturnos) |

**Arquitectura extensible propuesta:**

```cpp
// isolation_strategy.hpp
class IsolationStrategy {
public:
    virtual ~IsolationStrategy() = default;
    virtual bool should_isolate(const NetworkSecurityEvent& event,
                                const AssetInventory& inventory) = 0;
    virtual std::string name() const = 0;
};

// Estrategia actual (FEDER)
class TwoSignalStrategy : public IsolationStrategy {
public:
    bool should_isolate(const NetworkSecurityEvent& event,
                        const AssetInventory& inventory) override {
        return event.confidence_score() >= config_.threshold &&
               config_.event_types.contains(event.type());
    }
    std::string name() const override { return "two-signal"; }
};

// Estrategia futura (post-FEDER)
class MultiSignalStrategy : public IsolationStrategy {
public:
    bool should_isolate(const NetworkSecurityEvent& event,
                        const AssetInventory& inventory) override {
        // Señal 1: Score
        if (event.confidence_score() < config_.threshold) return false;
        
        // Señal 2: Tipo
        if (!config_.event_types.contains(event.type())) return false;
        
        // Señal 3: Asset no está en whitelist crítica
        if (inventory.is_critical(event.dst_ip())) return false;
        
        // Señal 4: Segundo sensor confirmó (si disponible)
        if (config_.require_second_sensor && !event.second_sensor_confirmed()) {
            return false;
        }
        
        return true;
    }
    std::string name() const override { return "multi-signal"; }
};
```

**Configuración:**

```json
{
  "isolation_strategy": "two-signal",
  "two_signal": {
    "threshold": 0.95,
    "event_types": ["ransomware", "lateral_movement", "c2_beacon"]
  },
  "_multi_signal": {
    "_comment": "Available post-FEDER",
    "require_second_sensor": true
  }
}
```

**Para FEDER:** Implementar `TwoSignalStrategy` como default. Registrar `DEBT-IRP-MULTI-SIGNAL-001` con diseño aprobado (`MultiSignalStrategy`). La demo FEDER puede mencionar: *"La arquitectura soporta estrategias de decisión plug-in; la actual usa dos señales, extensible a N señales sin cambios en el core."*

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **P1** | Zombies se acumulan — implementar `SIGCHLD` + `waitpid(-1, WNOHANG)` | Añadir handler `SIGCHLD` en `firewall-acl-agent`; test `NoZombieAccumulation` |
| **P2** | Threshold debe ser `float`, no `double` — eliminar tolerancia | Cambiar `IsolateConfig::threat_score_threshold` a `float`; cast explícito en JSON parseo |
| **P3** | Mantener `auto_isolate: true` + gate de onboarding obligatorio | Implementar `argus-onboarding-check` interactivo; crear `.onboarding-complete` |
| **P4** | Glob en `/tmp` aceptable para FEDER; directorio dedicado post-FEDER | Registrar `DEBT-IRP-DEDICATED-DIR-001`; sanitizar paths en binario |
| **P5** | Dos señales para FEDER; arquitectura extensible a multi-señal | Implementar `IsolationStrategy` pattern; `TwoSignalStrategy` como default |

**Moción:** Propongo que el DAY 144 priorice el merge de `feature/variant-b-libpcap` a `main` (Opción A) con los fixes de P1 (zombies) y P2 (float threshold) como commits obligatorios pre-merge. P3 (onboarding) puede ser un commit rápido post-merge. P4 y P5 quedan como deudas documentadas. El benchmark Variant A vs B (Opción B) es el siguiente hito crítico para el paper.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*