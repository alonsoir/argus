# Acta del Consejo de Sabios — DAY 133
*aRGus NDR — 27 Abril 2026 — Resolución sobre ADR-030 Variant A*

Participantes: Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral

---

## Convergencias — 8/8 unánimes

### C1: `cap_sys_admin` → `cap_bpf` en el sniffer
**Decisión: ADOPTAR inmediatamente.**

`cap_sys_admin` concede ~200 privilegios de administración del sistema.
`cap_bpf` (disponible desde Linux 5.8) restringe exactamente a operaciones eBPF.
Debian bookworm usa kernel 6.1 — `cap_bpf` está disponible sin fricción.

Cambios necesarios:
- `security/apparmor/argus.sniffer`: `cap_sys_admin` → `cap_bpf`
- `tools/prod/deploy-hardened.sh`: `setcap` del sniffer actualizado
- Verificación en DAY 134: si XDP falla con `cap_bpf`, documentar como fallback y abrir DEBT-KERNEL-COMPAT-001

### C2: `cap_net_bind_service` para etcd-server — NO necesaria
**Decisión: ELIMINAR.**

El puerto 2379 > 1024. La capability era incorrecta desde el principio. Eliminada
del perfil AppArmor y del `setcap` de etcd-server.

### C3: `cap_sys_resource` para etcd-server — NO necesaria
**Decisión: NO AÑADIR. Usar `LimitMEMLOCK` en systemd.**

El seed.bin es de 32 bytes. `mlock()` de 32 bytes no requiere elevar `RLIMIT_MEMLOCK`
más allá del límite de usuario estándar. La solución correcta es añadir
`LimitMEMLOCK=16M` en el unit de systemd del componente, no ampliar capabilities.
(Kimi y Mistral proponían `cap_sys_resource` — Claude, Grok y Gemini proponen
la solución systemd, que es más restrictiva y portable.)

### C4: Keypairs separados para binarios vs plugins
**Decisión: DOCUMENTAR como deuda, implementar post-FEDER.**

Arquitectónicamente correcto separar. Pragmáticamente, un solo desarrollador
con deadline FEDER justifica mantener la clave actual. Nuevo ítem:
**DEBT-KEY-SEPARATION-001**: pipeline-signing.sk/pk separado de plugin_signing.sk/pk.
No bloquea DAY 134.

### C5: Driver Falco — `modern_ebpf`
**Decisión: CONFIRMAR.**

`modern_ebpf` es la elección correcta para 2026 en VirtualBox. No requiere
compilación de módulo de kernel (lo cual violaría el BSR axiom en el host).
El módulo `kmod` está en proceso de deprecación.

### C6: Frase del paper §6.8 — incorrecta, reformular
**Decisión: REFORMULAR antes de subir a arXiv.**

"Fuzzing misses nothing within CPU time" es científicamente incorrecta
(el fuzzing es estocástico, no exhaustivo) y se contradice con la frase
siguiente del mismo párrafo. Ver formulación acordada en sección Divergencias.

---

## Divergencias — resueltas por el founder

### D1: `deny` explícitos — ¿mantener o eliminar?

- **Claude, Grok, ChatGPT, Gemini:** Mantener — documentación de intención y
  defensa ante futuros cambios en `abstractions/base`.
- **Kimi:** Mantener solo en los 3 perfiles más críticos.
- **Mistral:** Eliminar los redundantes para reducir complejidad.

**Decisión del founder: MANTENER todos los `deny` explícitos.**

Razón: estamos construyendo para hospitales. La claridad auditiva supera el
coste de mantenimiento. Un auditor externo (Andrés Caro, FEDER) debe poder
leer el perfil y entender la intención sin inferir del default-deny.

### D2: Restricción de `network inet tcp` a puertos específicos

- **ChatGPT, Qwen, Mistral:** Restringir a puertos ZeroMQ específicos.
- **Grok, Claude, Gemini:** Mantener `network inet tcp` — ZeroMQ usa puertos
  configurables vía JSON ("JSON es la ley"); hardcodear puertos en AppArmor
  crearía inconsistencia entre la fuente de verdad del JSON y el perfil AA.

**Decisión del founder: MANTENER `network inet tcp` por ahora.**

Documentar como futura mejora cuando los puertos sean estables y configurables
únicamente vía una fuente de verdad compartida entre el JSON y el perfil.
**DEBT-PROD-APPARMOR-PORTS-001.**

### D3: Reglas Falco adicionales — cuáles adoptar ahora

Propuestas del Consejo:
- Config tampering (todos)
- Model poisoning (Qwen)
- Plugin substitution (Qwen)
- ptrace inesperado (Gemini)
- DNS tunneling desde componentes (Kimi)
- Conexiones salientes inesperadas (ChatGPT, Mistral)
- Acceso a `/dev/mem` (Mistral)
- Modificación de perfiles AppArmor en runtime (Mistral)

**Decisión del founder: Adoptar 3 en DAY 134, resto como deuda.**

Adoptar ahora:
- `argus_config_modified_unexpected` (todos coinciden, alta prioridad)
- `argus_model_or_plugin_replaced` (protege la cadena de integridad)
- `argus_apparmor_profile_modified` (un atacante que modifica AA invalida toda la defensa)

Resto: DEBT-PROD-FALCO-RULES-EXTENDED-001.

---

## Reformulación consensuada §6.8 — fuzzing

Texto actual (INCORRECTO):
> "Unit tests miss unseen inputs. Property tests miss parser-level structural
> anomalies. Fuzzing misses nothing within CPU time and cannot prove absence
> of defects, but systematically explores the boundary between valid and invalid
> input that adversaries exploit."

**Texto adoptado (síntesis de Claude + Grok + Kimi + Qwen):**
> "Unit tests miss unseen inputs. Property tests miss parser-level structural
> anomalies. Coverage-guided fuzzing (libFuzzer~\cite{libfuzzer2016})
> systematically explores the input space through mutation guided by code
> coverage feedback, increasing the probability of discovering crashes and
> undefined behavior at parser and protocol boundaries. It provides no
> completeness guarantee --- bugs may remain undiscovered after millions of
> executions --- but each corpus-expanding input permanently extends the
> regression suite, and no crashes or sanitizer violations observed after
> extensive runs constitute empirical evidence of robustness."

Razón del cambio: eliminar "misses nothing" (hipérbole falsa), explicitar
"coverage-guided" y "probabilistic", añadir la cita de libFuzzer, y terminar
con lo que el fuzzing sí garantiza (evidencia empírica de robustez).

---

## Nuevas deudas abiertas (DAY 133)

| ID | Descripción | Target |
|----|-------------|--------|
| DEBT-KEY-SEPARATION-001 | Keypair separado pipeline vs plugins | post-FEDER |
| DEBT-PROD-APPARMOR-PORTS-001 | Restringir network a puertos ZeroMQ específicos | post-estabilización JSON |
| DEBT-PROD-FALCO-RULES-EXTENDED-001 | ptrace, DNS tunneling, /dev/mem, conexiones salientes | DAY 135 |
| DEBT-KERNEL-COMPAT-001 | Verificar fallback cap_sys_admin si cap_bpf no funciona en XDP | DAY 134 |

---

## Ficheros a modificar en DAY 134

1. `security/apparmor/argus.sniffer` — `cap_sys_admin` → `cap_bpf`
2. `security/apparmor/argus.etcd-server` — eliminar `cap_net_bind_service`
3. `tools/prod/deploy-hardened.sh` — setcap sniffer actualizado
4. `vagrant/hardened-x86/scripts/setup-falco.sh` — 3 reglas nuevas
5. `docs/latex/main.tex` — reformular §6.8 fuzzing
6. `docs/SECURITY-CAPABILITIES.md` — nuevo documento de justificación

---

## Plan DAY 134

### P0 — Aplicar correcciones del Consejo (antes de ejecutar el pipeline)
Actualizar los 6 ficheros listados arriba.

### P1 — Primer pipeline end-to-end en hardened VM
```bash
make hardened-up
make hardened-provision-all   # AppArmor en complain mode primero
make prod-full-x86
# Observar logs 30 minutos
# aa-logprof ajusta perfiles
# Pasar a enforce
make check-prod-all
```

Estrategia de maduración (Gemini + Kimi):
- Falco prioridad WARNING durante tuning
- AppArmor complain → enforce solo cuando 30 min sin denegaciones inesperadas
- Ajustar AA y Falco en paralelo, no secuencialmente

### P2 — Tabla de fuzzing §6.8 (DEBT-PAPER-FUZZING-METRICS-001)
Recuperar métricas del DAY 130 y completar la tabla.

### P3 — Commit y prompt continuidad DAY 134

---

*"La seguridad no se instala. Se diseña. Se prueba. Se mide."*
*Via Appia Quality — DAY 133 → 134*