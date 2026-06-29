## Kimi — Respuesta al Consejo de Sabios — DAY 142

*Evaluación bajo criterios de proporcionalidad de respuesta defensiva, continuidad operacional durante incidentes, y política de mínimo privilegio en AppArmor.*

---

### P1 — Criterio de disparo: umbral único vs matriz de decisión

**Hipótesis:** Un umbral único es auditable pero puede generar falsos positivos catastróficos en entornos hospitalarios. Una matriz de decisión reduce falsos positivos pero aumenta la complejidad cognitiva.

**Veredicto: Umbral único para MVP FEDER, pero con **ventana de confirmación** y **exclusiones configurables** que mitigan el riesgo de falso positivo sin añadir complejidad de matriz.**

**Análisis de riesgo institucional:**

| Escenario | Umbral único 0.95 | Matriz de decisión |
|-----------|-------------------|-------------------|
| Ransomware real detectado | ✅ Aislamiento correcto | ✅ Aislamiento correcto |
| Falso positivo a las 3 AM (un evento) | ❌ Aislamiento incorrecto, hospital despierta | ✅ Probablemente no dispara (ventana temporal) |
| Falso positivo durante cirugía (un evento) | ❌ **Crítico** — interrupción de equipos médicos | ✅ No dispara si no hay patrón |
| Explicabilidad al admin | ✅ "Score >= 0.95" | ❌ "Score + tipo + ventana + hora" |

**La solución no es la matriz, es la **ventana de confirmación** con **whitelist de dispositivos críticos**:**

```json
{
  "auto_isolate": true,
  "threat_score_threshold": 0.95,
  "confirmation_window_seconds": 30,
  "critical_devices_whitelist": [
    "10.0.0.50",   // Monitor de quirófano
    "10.0.0.51",   // Bomba de infusión
    "10.0.0.52"    // Ventilador mecánico
  ],
  "isolate_except_whitelist": true
}
```

**Semántica:**
1. Evento con score >= 0.95 detectado
2. `argus-network-isolate` entra en modo **"pending"** — notifica al admin, aísla todo EXCEPTO whitelist
3. Si en 30 segundos el admin no confirma (o niega), se completa el aislamiento total (o se revierte)
4. Los dispositivos críticos nunca se aíslan — el tráfico de/bacia ellos sigue fluyendo

**Esto es más simple que una matriz y más seguro que un umbral único.**

**Regla permanente propuesta:**

> **RULE-IRP-PROPORTIONALITY-001:** El aislamiento automático nunca interrumpe dispositivos médicos críticos configurados en whitelist. El aislamiento siempre incluye una ventana de confirmación configurable (default: 30s). El umbral es único y auditable. La excepción es explícita y documentada.

**Para FEDER:** Implementar umbral único + whitelist + ventana de confirmación. Registrar matriz de decisión como `IDEA-IRP-DECISION-MATRIX-001` para v0.7+.

---

### P2 — `execv()` vs `fork() + execv()` en firewall-acl-agent

**Hipótesis:** El agente de firewall debe sobrevivir al aislamiento para continuar registrando evidencia y permitir rollback controlado.

**Veredicto: `fork() + execv()` obligatorio. `execv()` directo es un fallo de diseño que mata el componente de monitoreo durante el incidente.**

**Análisis de continuidad:**

| Método | Estado del agente post-aislamiento | Capacidad de rollback | Registro de evidencia |
|--------|-----------------------------------|----------------------|----------------------|
| `execv()` directo | Muerto | Ninguna — el proceso que haría rollback ya no existe | Parcial — logs previos al execv |
| `fork() + execv()` | Vivo | Sí — el padre puede ejecutar rollback | Completa — logs continuos |

**Riesgo de `execv()` directo:** Si el aislamiento se activa por falso positivo y el admin quiere revertir, no hay proceso vivo que ejecute `argus-network-isolate rollback`. El admin debe conectarse manualmente al nodo (que está aislado de red) vía consola física o IPMI.

**Implementación recomendada:**

```cpp
// firewall-acl-agent.cpp
void trigger_isolation(const NetworkSecurityEvent& event) {
    pid_t pid = fork();
    if (pid == -1) {
        LOG_ERROR("fork failed — cannot trigger isolation");
        return;
    }
    
    if (pid == 0) {
        // Hijo: ejecuta aislamiento y termina
        const char* argv[] = {
            "/usr/local/bin/argus-network-isolate",
            "isolate",
            "--interface", event.interface().c_str(),
            "--reason", event.threat_type().c_str(),
            nullptr
        };
        execv(argv[0], const_cast<char**>(argv));
        _exit(127);  // execv falló
    }
    
    // Padre: registra el PID del hijo, continua monitorizando
    LOG_INFO("Isolation triggered via child PID {}", pid);
    active_isolations_.push_back(pid);
    
    // El padre puede:
    // - Monitorear si el hijo termina exitosamente
    // - Ejecutar rollback si se recibe comando del admin
    // - Continuar aplicando reglas de firewall independientemente
}
```

**AppArmor implicación:** El perfil de `firewall-acl-agent` necesita `capability sys_admin` o `capability net_admin` para `fork()` (no necesita privilegios especiales) pero el hijo hereda el perfil del padre. El hijo `argus-network-isolate` necesita su propio perfil con acceso a `nft`, `systemd-run`, etc.

**Regla permanente propuesta:**

> **RULE-IRP-FORK-001:** Todo trigger de aislamiento automático usa `fork() + execv()`. El proceso padre (monitor/agente) nunca se reemplaza. El hijo hereda el perfil AppArmor del padre o transita al suyo propio via `aa_change_profile`.

---

### P3 — AppArmor profile para argus-network-isolate: enforce vs complain

**Hipótesis:** Un perfil en `enforce` desde el primer día puede bloquear operaciones legítimas no anticipadas. Un perfil en `complain` genera deuda técnica.

**Veredicto: **Enforce desde el primer deploy, con fase de validación en dev VM antes de hardened VM.**

**Justificación:**

El argumento de "complain primero" es válido para software legacy que no se diseñó con AppArmor. `argus-network-isolate` se está diseñando **ahora**, consciente de AppArmor. Si no funciona en `enforce` en la dev VM, es un bug de diseño, no una sorpresa de producción.

**Fase de validación:**

| Fase | VM | Modo AppArmor | Duración | Acción |
|------|-----|--------------|----------|--------|
| 1 | Dev | `complain` | 1 día | Recolectar logs de denials |
| 2 | Dev | `enforce` | 2 días | Ajustar perfil hasta 0 denials |
| 3 | Hardened | `enforce` | Permanente | Gate `check-prod-apparmor` |

**Perfil propuesto:**

```apparmor
# /etc/apparmor.d/usr.local.bin.argus-network-isolate
#include <tunables/global>

/usr/local/bin/argus-network-isolate {
    #include <abstractions/base>
    #include <abstractions/nameservice>
    
    # Binario firmado — solo lectura
    /usr/local/bin/argus-network-isolate mr,
    
    # nftables — herramienta de aislamiento
    /usr/sbin/nft rix,
    /usr/share/nftables/** r,
    
    # Configuración
    /etc/ml-defender/firewall-acl-agent/isolate.json r,
    
    # Logs y forense
    /var/log/argus/firewall-acl-agent/** rw,
    /tmp/argus-isolate-*/** rw,
    
    # systemd-run para timer de rollback
    /usr/bin/systemd-run rix,
    /run/systemd/private rw,
    
    # Network interfaces (solo lectura de estado)
    /sys/class/net/ r,
    /sys/class/net/*/ r,
    
    # Denegado explícitamente
    deny /root/** rwx,
    deny /home/** rwx,
    deny /tmp/** w,  # Solo /tmp/argus-isolate-* permitido arriba
    deny /proc/*/mem rw,
    deny network,  # No necesita conectividad de red propia
}
```

**Nota:** `deny network` es intencional. `argus-network-isolate` no necesita conectividad de red para ejecutar `nft`. Si necesita enviar notificaciones, lo hace via `logger` (syslog) o via el padre `firewall-acl-agent`.

**Regla permanente propuesta:**

> **RULE-APPARMOR-NEW-COMPONENT-001:** Todo nuevo componente aRGus se diseña con perfil AppArmor en `enforce` desde el commit inicial. La fase `complain` dura como máximo 1 día en dev VM. Ningún componente llega a hardened VM sin perfil `enforce` validado.

---

### P4 — Rollback con backup persistente

**Hipótesis:** El snapshot actual solo captura la tabla `argus_isolate`, que es vacía en primera ejecución. En entornos con rulesets nftables propios del cliente, el rollback podría dejar reglas huérfanas.

**Veredicto: Estado persistente **opcional** para FEDER, **obligatorio** para producción hospitalaria con rulesets personalizados.**

**Análisis de escenarios:**

| Escenario | Snapshot actual | Estado persistente |
|-----------|----------------|-------------------|
| aRGus en VM limpia (demo FEDER) | ✅ Suficiente | No necesario |
| aRGus en hospital con rulesets nftables propios | ❌ Insuficiente — rollback deja reglas huérfanas | ✅ Necesario |
| aRGus después de múltiples aislamientos/rollbacks | ⚠️ Riesgo de acumulación | ✅ Limpieza garantizada |

**Implementación del estado persistente:**

```cpp
// En argus-network-isolate, opcional via --persist
class PersistentState {
    static constexpr const char* STATE_FILE = 
        "/etc/ml-defender/firewall-acl-agent/last-known-good.nft";
    
public:
    void save(const std::string& ruleset) {
        // Firmar con Ed25519 del nodo antes de escribir
        auto signature = crypto::sign(ruleset, node_key_);
        
        std::ofstream f(STATE_FILE);
        f << "# aRGus last-known-good ruleset\n";
        f << "# timestamp: " << iso8601_now() << "\n";
        f << "# signature: " << signature << "\n";
        f << ruleset;
        f.close();
        
        chmod(STATE_FILE, 0400);
    }
    
    std::optional<std::string> load() {
        std::ifstream f(STATE_FILE);
        if (!f) return std::nullopt;
        
        std::string content((std::istreambuf_iterator<char>(f)),
                            std::istreambuf_iterator<char>());
        
        // Verificar firma
        if (!crypto::verify(content, node_pubkey_)) {
            LOG_ERROR("last-known-good signature invalid — possible tampering");
            return std::nullopt;
        }
        
        return content;
    }
};
```

**Para FEDER:** No implementar. Documentar como `DEBT-IRP-LAST-KNOWN-GOOD-001` con diseño aprobado.

**Para producción:** Implementar cuando un hospital reporte rulesets nftables propios.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **P1** | Umbral único + whitelist de dispositivos críticos + ventana de confirmación 30s | Implementar `critical_devices_whitelist` e `isolate_except_whitelist` en `isolate.json` |
| **P2** | `fork() + execv()` obligatorio; agente padre nunca muere | Refactorizar `trigger_isolation()`; añadir `active_isolations_` tracking |
| **P3** | `enforce` desde primer deploy; fase `complain` máximo 1 día en dev | Crear perfil AppArmor; validar en dev VM; gate `check-prod-apparmor` |
| **P4** | Snapshot actual suficiente para FEDER; estado persistente post-FEDER | Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001` con diseño aprobado |

**Moción:** Propongo que el DAY 143 implemente P1 (whitelist + ventana) y P2 (`fork+execv`) como bloqueantes para la integración firewall-acl-agent. P3 (AppArmor) puede paralelizarse. P4 queda como deuda documentada.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*