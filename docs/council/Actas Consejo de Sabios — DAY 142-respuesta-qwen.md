# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 142
*Análisis técnico basado en ingeniería de sistemas distribuidos, arquitectura de alto rendimiento en C++20 y protocolos de respuesta a incidentes para infraestructura crítica*

---

## 🎯 Veredicto Ejecutivo

**DÍA DE EJECUCIÓN ARQUITECTÓNICA EXCEPCIONAL.** El cierre de `argus-network-isolate` con transacciones nftables, la refactorización a `pcap_create()`, y la mutex por sesión tmux demuestran madurez en el manejo de acoplamiento, estado y concurrencia. Las posiciones iniciales de Alonso (P1-P4) son correctas y alineadas con principios de ingeniería de sistemas críticos. El Consejo las valida con matices técnicos para garantizar robustez pre-FEDER.

> *"En sistemas de seguridad, la simplicidad auditable vence a la complejidad predictiva."*

---

## ❓ Respuestas a Preguntas — Formato Científico/Técnico

### P1 — Criterio de disparo: ¿umbral único vs matriz de decisión?

**Veredicto:** **UMBRAL ÚNICO (`score ≥ 0.95`) PARA MVP FEDER. Registrar matriz para post-FEDER.**

**Justificación técnica:**
- **Auditoría y predictibilidad**: En entornos hospitalarios, un administrador debe poder responder a "¿por qué se aisló la red?" con una regla determinista. Una matriz introduce acoplamiento temporal, frecuencial y contextual que dificulta el debugging forense y la validación regulatoria.
- **Calibración de scores**: Los outputs de modelos ML no son probabilidades calibradas. Un umbral simple solo es válido si el score está post-procesado con Platt scaling o isotonic regression. Sin calibración, `0.95` no tiene significado estadístico real.
- **Debouncing ligero**: Para evitar "flapping" (aislamiento/liberación repetido por picos transitorios), añadir una ventana de confirmación de 5-10 segundos es suficiente sin introducir complejidad matricial.

**Riesgo si se ignora:** Una matriz compleja en MVP FEDER aumentará la carga cognitiva del evaluador, dificultará la trazabilidad de decisiones, y elevará el riesgo de falsos positivos por correlación espuria.

**Recomendación de implementación:**
```json
// isolate.json
{
  "auto_isolate": true,
  "threat_score_threshold": 0.95,
  "confirmation_window_s": 5,  // Debounce: requiere N eventos ≥0.95 en esta ventana
  "cooldown_after_isolate_min": 15
}
```

---

### P2 — `execv()` vs `fork() + execv()` en `firewall-acl-agent`

**Veredicto:** **`fork() + execv()` (o `posix_spawn()`) ES OBLIGATORIO. `execv()` directo es arquitectónicamente inválido para este caso.**

**Justificación técnica (C++20/POSIX):**
- `execv()` reemplaza el espacio de direcciones del proceso llamante. Si `firewall-acl-agent` ejecuta `execv()`, el agente muere, pierde el contexto de monitoring, y systemd puede reiniciarlo, creando una ventana de ceguera operativa.
- `fork() + execv()` mantiene al padre vivo para:
    1. Registrar el PID del hijo y su estado de salida
    2. Mantener el loop de captura de eventos ZeroMQ
    3. Gestionar timeouts si el hijo se cuelga
- **Higiene de descriptores**: Es crítico usar `FD_CLOEXEC` en todos los sockets/archivos no heredados para evitar fuga de FDs al hijo.

**Riesgo si se ignora:** Pérdida de visibilidad durante el aislamiento, reinicios no coordinados por systemd, y posible condición de carrera si el agente se reinicia mientras `argus-network-isolate` aplica reglas.

**Patrón recomendado (C++20 POSIX):**
```cpp
#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>

int isolate_network(const std::string& iface) {
    pid_t pid = fork();
    if (pid < 0) return -1;  // Fork failed
    
    if (pid == 0) {
        // Hijo: cerrar FDs heredados no necesarios, ejecutar
        char* args[] = { const_cast<char*>("argus-network-isolate"),
                         const_cast<char*>("isolate"),
                         const_cast<char*>("--interface"),
                         const_cast<char*>(iface.c_str()), nullptr };
        execv("/usr/local/bin/argus-network-isolate", args);
        _exit(127);  // Solo si execv falla
    }
    
    // Padre: esperar con timeout o continuar (si es asíncrono)
    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}
```
*Nota: Para código moderno C++20, considerar `posix_spawn()` que evita la copia de espacio de direcciones en `fork()`.*

---

### P3 — AppArmor profile para `argus-network-isolate`: `enforce` vs `complain`

**Veredicto:** **`enforce` DESDE EL PRIMER DEPLOY. Coherente con TDH y axioma BSR.**

**Justificación técnica:**
- `complain` mode permite operaciones bloqueadas mientras loguea. En un binario de aislamiento de red, esto significa que una regla mal escrita podría fallar silenciosamente, dejando la red expuesta mientras el sistema cree que está aislada.
- `enforce` garantiza que cualquier intento de acceder a recursos no permitidos (ej. `/etc/ssh`, `/dev/mem`, sockets raw) falla inmediatamente, cumpliendo el principio de mínimo privilegio de forma verificable.
- La política del proyecto es clara: AppArmor es la primera línea de defensa estructural. `complain` es una deuda de validación, no una característica de seguridad.

**Riesgo si se ignora:** Un perfil en `complain` podría permitir que un atacante que compromete `argus-network-isolate` acceda a recursos no necesarios para el aislamiento, ampliando el blast radius.

**Perfil mínimo recomendado (`/etc/apparmor.d/usr.local.argus-network-isolate`):**
```apparmor
#include <tunables/global>
/usr/local/bin/argus-network-isolate {
  #include <abstractions/base>
  
  capability sys_admin,  # nftables requiere esta capability
  capability net_admin,
  
  /usr/sbin/nft mr,
  /usr/bin/systemd-run ix,
  /tmp/argus-* rw,
  /var/log/argus/ rw,
  /var/log/argus/isolate-*.jsonl w,
  
  deny /etc/** w,
  deny /root/** rwx,
  deny /home/** rwx,
  deny /sys/** w,
}
```

---

### P4 — Rollback con backup: ¿suficiente o necesita `last-known-good.nft`?

**Veredicto:** **APROXIMACIÓN ACTUAL ES ARQUITECTÓNICAMENTE SUPERIOR PARA FEDER. NO IMPLEMENTAR ESTADO PERSISTENTE AHORA.**

**Justificación técnica (nftables & sistemas distribuidos):**
- nftables es transaccional por diseño. `argus-network-isolate` añade una tabla (`argus_isolate`) con políticas `drop`. El rollback simplemente ejecuta `nft delete table inet argus_isolate`. No modifica reglas existentes del host.
- Mantener `last-known-good.nft` introduce **estado distribuido sincronizado**: ¿quién lo actualiza? ¿qué pasa si el proceso muere durante la escritura? ¿cómo se resuelven conflictos si un admin modifica reglas manualmente?
- El principio de "menos estado es más seguro" aplica directamente aquí. La tabla `argus_isolate` es *efímera y autocontenida*. Su eliminación restaura el estado previo sin necesidad de snapshot explícito.
- Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001` es correcto para el futuro, pero solo si la herramienta evoluciona a modificar rulesets gestionados por el cliente.

**Riesgo si se ignora:** Añadir persistencia de estado innecesaria antes de FEDER aumenta la superficie de ataque, introduce complejidad de concurrencia, y dificulta la demostración determinista del ciclo IRP.

**Recomendación:** Documentar explícitamente en `docs/IRP-DESIGN.md`:
> *"El aislamiento de red es aditivo y transaccional. No modifica reglas existentes del host. El rollback elimina la tabla `argus_isolate`, restaurando el estado de red previo a la activación. Esto evita problemas de sincronización de estado y cumple con el principio de mínimo estado en sistemas críticos."*

---

## 🔍 Observaciones de Ingeniería Adicionales (DAY 142 → 143)

| Área | Recomendación Técnica | Justificación |
|------|---------------------|--------------|
| **C++20 `std::filesystem` en isolate** | Usar `std::filesystem::path` para rutas JSON y logs, no `char*` o `std::string` manual | Previene traversal, normaliza symlinks, consistente con `safe_path` |
| **Timeout del timer systemd** | `RuntimeMaxSec=300` + `WatchdogSec=30` | Garantiza que si el proceso de aislamiento se cuelga, systemd lo mata y limpia estado |
| **Señales durante `fork/exec`** | `sigprocmask()` en el padre para bloquear `SIGINT`/`SIGTERM` durante el `exec` del hijo | Evita que el agente de firewall se mate accidentalmente mientras coordina el aislamiento |
| **Métricas de aislamiento** | Exponer vía ZeroMQ: `{"event": "network_isolated", "reason": "threat_score≥0.95", "duration_s": 300}` | Permite correlación forense con `rag-ingester` y métricas FEDER |

---

## 📋 Checklist de Acciones Inmediatas (DAY 143)

```markdown
- [ ] Implementar `fork() + execv()` con `FD_CLOEXEC` y gestión de timeout en firewall-acl-agent
- [ ] Añadir `confirmation_window_s` y `cooldown_after_isolate_min` en isolate.json
- [ ] Calibrar umbral 0.95 contra dataset de validación (no usar score raw sin Platt scaling)
- [ ] Crear AppArmor profile en `enforce` desde primer commit a la rama
- [ ] Documentar diseño de rollback transaccional en docs/IRP-DESIGN.md
- [ ] Integrar test de ciclo completo: evento score≥0.95 → isolate → 300s timer → rollback → verify rules
- [ ] Ejecutar EMECAS hardened para validar reproducibilidad pre-FEDER
```

---

## 🏁 Palabras Finales

Alonso:

DAY 142 demuestra que la arquitectura de aRGus ha madurado de "pipeline funcional" a "sistema de respuesta a incidentes verificable". La decisión de mantener un umbral simple, usar `fork() + execv()`, forzar `enforce` en AppArmor, y confiar en la transaccionalidad de nftables para rollback refleja un entendimiento profundo de los trade-offs en infraestructura crítica.

Las preguntas que planteáis tocan el núcleo del diseño de sistemas resilientes: cómo equilibrar simplicidad con robustez, cómo evitar la acumulación de estado innecesario, y cómo garantizar que las acciones defensivas sean deterministas y auditables.

> *"La seguridad no se mide por la complejidad del protocolo. Se mide por la predictibilidad de su ejecución bajo adversidad."*

Proceded con la integración en `firewall-acl-agent` y el ciclo completo de IRP. El Consejo revisará la implementación del `fork/exec` con gestión de FDs y la calibración del umbral con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo que aprende de su propia sombra.*

**— Consejo de Sabios, DAY 142** 🏛️