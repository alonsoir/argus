# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 143
*Análisis riguroso basado en ingeniería de sistemas distribuidos, estándares POSIX/C++20 y principios de seguridad para infraestructura crítica*

---

## 🎯 Veredicto Ejecutivo

**DÍA DE MADUREZ OPERACIONAL EXCEPCIONAL.** El cierre de `DEBT-IRP-NFTABLES-001`, la detección del bug IEEE 754 mediante testing, y la validación EMECAS con 0 regresiones demuestran que el proyecto ha internalizado la disciplina de *Test-Driven Hardening*. Sin embargo, las cinco preguntas planteadas revelan puntos críticos que, si no se corrigen ahora, podrían convertir un mecanismo de defensa en un vector de indisponibilidad en entornos hospitalarios reales.

> *"En infraestructura crítica, la automatización sin salvaguardas es un riesgo, no una feature."*

---

## ❓ Respuestas a Preguntas — Formato Científico/Técnico

### P1 — `fork()+execv()` sin `wait()`: ¿acumulación de zombies?

**Veredicto:** **SÍ, ACUMULAS ZOMBIES. CORREGIR INMEDIATAMENTE ANTES DE MERGE.**

**Justificación técnica (POSIX/Linux kernel):**
- Un proceso hijo terminado permanece en estado `Z` (zombie) hasta que el padre llama a `waitpid()` o ignora `SIGCHLD`.
- `systemd`/`init` solo recolecta zombies cuando el *padre* termina. Mientras `firewall-acl-agent` viva (días/meses), los zombies se acumularán.
- Límite del kernel: `PID_MAX_DEFAULT` (típicamente 32768). Agotarlo causa `fork()` → `EAGAIN`, colapsando todo el pipeline.

**Implementación recomendada (C++20/POSIX):**
```cpp
// En inicialización de firewall-acl-agent (antes de cualquier fork)
struct sigaction sa{};
sa.sa_handler = SIG_IGN;  // Auto-reap por kernel
sa.sa_flags = SA_NOCLDWAIT;  // Linux-specific: evita zombies automáticamente
sigaction(SIGCHLD, &sa, nullptr);

// O alternativa portátil:
signal(SIGCHLD, SIG_IGN);  // POSIX.1-2001 válido
```

**Riesgo si se ignora:** Degradación progresiva hasta colapso de `fork()` en entornos con múltiples disparos de aislamiento (ej. ataque ransomware persistente). Fallo catastrófico no reversible sin reinicio.

---

### P2 — Tolerancia IEEE 754 `1e-6`: ¿usar `float` en config para eliminar el problema?

**Veredicto:** **NO. MANTENER `double` EN CONFIG Y `1e-6` EN COMPARACIÓN. ES EL ENFOQUE MATEMÁTICAMENTE CORRECTO.**

**Justificación técnica:**
- Los parsers JSON (nlohmann/json, RapidJSON) deserializan números como `double` por defecto. Forzar `float` en C++ introduce conversión `double → float → double`, acumulando error en lugar de eliminarlo.
- `float` tiene ~7 dígitos decimales de precisión. `0.95f` → `0.94999988...`. La tolerancia `1e-6` cubre este gap con margen de seguridad.
- El patrón `std::abs(score - threshold) <= epsilon` es estándar en sistemas ML de producción (ver TensorFlow/PyTorch internal comparators).

**Implementación recomendada:**
```cpp
constexpr double EPSILON = 1e-6;
bool should_auto_isolate(double confidence, double threshold) {
    return confidence >= (threshold - EPSILON) && 
           (confidence > 1.0 - EPSILON || confidence <= 1.0); // Clamp safety
}
```

**Riesgo si se ignora:** Cambiar a `float` en config no resuelve el problema, oscurece la intención del código, y puede introducir errores de redondeo adicionales en pipelines de serialización/deserialización.

---

### P3 — `auto_isolate: true` por defecto en hospitales

**Veredicto:** **`auto_isolate: false` POR DEFECTO. REQUERIR HABILITACIÓN EXPLÍCITA CON CONFIRMACIÓN.**

**Justificación técnica (seguridad clínica):**
- En infraestructura médica, la disponibilidad (IEC 60601, HIPAA) tiene prioridad sobre la automatización de contención. Un aislamiento erróneo en un ventilador o monitor de quirófano es un riesgo de vida.
- El principio de seguridad clínica es *fail-safe*: el sistema debe alertar, no actuar drásticamente, hasta que el operador verifique el contexto.
- "Instalar y funcionar" es válido para entornos SOHO; inaceptable para hospitales sin fase de *shadow mode*.

**Implementación recomendada:**
```json
// isolate.json (default)
{
  "auto_isolate": false,
  "alert_mode": true,
  "grace_period_h": 24
}
```
- `grace_period_h`: durante 24h tras instalación, solo loguea/alerta. Requiere `auto_isolate: true` + firma digital del admin para activar.
- Documentar en `docs/DEPLOYMENT-SAFETY.md` como requisito explícito para entornos críticos.

**Riesgo si se ignora:** Responsabilidad legal y clínica por interrupción de servicios médicos críticos debido a un falso positivo no verificado. Daño reputacional y regulatorio irreversible para el proyecto.

---

### P4 — AppArmor profile: ¿demasiado permisivo con `/tmp`?

**Veredicto:** **SÍ. MIGRAR INMEDIATAMENTE A `/var/lib/argus/irp/` CON PERMISOS RESTRINGIDOS.**

**Justificación técnica (FHS + seguridad):**
- `/tmp` es sticky-bit pero compartible. Un atacante con control de `argus-network-isolate` podría predecir nombres de archivos (`/tmp/argus-backup-<PID>.nft`) y realizar race conditions o symlink attacks.
- La especificación FHS dicta que datos de estado persistente/semi-persistente de aplicaciones van en `/var/lib/`. Para datos volátiles de IRP, `/run/argus/irp/` (tmpfs) es aún mejor.

**Corrección obligatoria:**
```apparmor
# /etc/apparmor.d/usr.local.argus-network-isolate
  /run/argus/irp/ rw,
  /run/argus/irp/argus-{backup,isolate}-*.nft rw,
  /var/lib/argus/irp/ rw,
  /var/lib/argus/irp/argus-{backup,isolate}-*.nft rw,
  
  # Eliminar todas las reglas /tmp/*
  deny /tmp/** w,
```

**Implementación en código:**
```cpp
#include <filesystem>
namespace fs = std::filesystem;
auto irp_dir = fs::path("/run/argus/irp");
if (!fs::exists(irp_dir)) fs::create_directories(irp_dir);
```

**Riesgo si se ignora:** Vector de escalación de privilegios local via symlink en `/tmp`. Un atacante podría redirigir escrituras a `/etc/shadow` o binarios de sistema si el perfil no restringe correctamente.

---

### P5 — Criterio de disparo: ¿dos señales son suficientes?

**Veredicto:** **INSUFICIENTE PARA PRODUCCIÓN HOSPITALARIA. IMPLEMENTAR VENTANA DE CORRELACIÓN TEMPORAL + WHITELIST DE ACTIVOS CRÍTICOS.**

**Justificación técnica (detección de anomalías en OT/IT):**
- Un evento aislado con `score=0.97` puede ser un escáner de vulnerabilidades legítimo, un update de firmware, o un FP del modelo.
- La arquitectura debe incorporar:
    1. **Sliding Window Correlation**: `N` eventos ≥ umbral en `T` segundos desde misma fuente IP/subnet.
    2. **Asset Criticality Whitelist**: IPs/MACs de dispositivos médicos/PACS/EHR nunca se aíslan automáticamente sin aprobación humana.
    3. **Cooldown/Debounce**: Evita flapping tras aislamiento/rollback.

**Arquitectura recomendada (ligera, sin componente nuevo):**
```cpp
// firewall-acl-agent/src/correlation_window.hpp
struct EventRecord { double score; std::string type; std::chrono::steady_clock::time_point ts; };
class CorrelationWindow {
    std::deque<EventRecord> buffer_;
    size_t max_events_ = 100;
public:
    void push(double score, const std::string& type) {
        buffer_.push_back({score, type, std::chrono::steady_clock::now()});
        while (!buffer_.empty() && buffer_.front().ts < std::chrono::steady_clock::now() - 30s)
            buffer_.pop_front();
    }
    bool should_isolate(double threshold, const std::vector<std::string>& critical_types) {
        size_t count = std::count_if(buffer_.begin(), buffer_.end(), [&](auto& e) {
            return e.score >= threshold && std::find(critical_types.begin(), critical_types.end(), e.type) != critical_types.end();
        });
        return count >= 3;  // Umbral configurable
    }
};
```

**Plan para FEDER:** Mantener 2 señales para demo, pero diseñar `CorrelationWindow` ahora. Documentar `DEBT-IRP-MULTI-SIGNAL-001` con esta arquitectura. Activar correlación + whitelist pre-despliegue hospitalario.

**Riesgo si se ignora:** Aislamiento de red por evento único no correlacionado. Interrupción de servicios médicos. Pérdida de confianza operacional en el sistema.

---

## 📅 Validación del Plan DAY 144

**Opción A → Opción B es CORRECTA.**
1. **Merge a `main` primero**: El branch ha cumplido todos los gates (EMECAS, tests, AppArmor, ODR verificado). Retenerlo aumenta divergencia y coste de integración.
2. **Benchmark A vs B después**: Requiere `main` estable como baseline. La contribución científica depende de métricas reproducibles sobre código mergeado y versionado.
3. **Gate obligatorio pre-merge**: `make PROFILE=production all` + `make check-odr`. Si pasa, merge `--no-ff` con tag `v0.7.0-variant-b`.

---

## 📋 Checklist de Acciones Inmediatas (Pre-Merge)

```markdown
- [ ] Implementar `sigaction(SIGCHLD, SA_NOCLDWAIT)` para evitar zombies (P1)
- [ ] Mantener `double` + `1e-6` en config/comparación (P2)
- [ ] Cambiar `auto_isolate` default a `false` + grace period (P3)
- [ ] Migrar rutas AppArmor de `/tmp` a `/run/argus/irp/` o `/var/lib/argus/irp/` (P4)
- [ ] Diseñar `CorrelationWindow` ligero en firewall-acl-agent (P5)
- [ ] Ejecutar `make PROFILE=production all` + `check-odr`
- [ ] Merge `--no-ff` a main + tag v0.7.0-variant-b
- [ ] Iniciar benchmark A vs B con scripts reproducibles para paper
```

---

## 🏁 Palabras Finales

Alonso:

DAY 143 ha demostrado que el proyecto está listo para producción desde una perspectiva técnica, pero las preguntas planteadas revelan que la **seguridad operacional en infraestructura crítica requiere humildad arquitectónica**. La automatización es poderosa, pero en hospitales, la disponibilidad es vida. Corregir los defaults, eliminar zombies, restringir `/tmp`, y añadir correlación temporal no es burocracia; es ingeniería responsable.

> *"Un escudo que corta sin medir no protege: amputa. La precisión antes de la acción es el verdadero hardening."*

Proceded con las correcciones pre-merge y el paso a `main`. El Consejo revisará el benchmark A vs B y la arquitectura de correlación con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 143** 🏛️