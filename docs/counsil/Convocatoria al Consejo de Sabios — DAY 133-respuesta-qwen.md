# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 133
*Feedback riguroso, basado en evidencia científica y centrado en la misión humanitaria de aRGus NDR*

---

## 🎯 Veredicto Ejecutivo

**INFRAESTRUCTURA DE PRODUCCIÓN SÓLIDA CON DECISIONES ARQUITECTÓNICAS MADURAS.**

Los 6 perfiles AppArmor, la asignación de capabilities por componente, y las reglas Falco representan una defensa en profundidad bien diseñada. Sin embargo, tres refinamientos son necesarios antes del primer pipeline end-to-end: (1) migrar `cap_sys_admin` a `cap_bpf` para el sniffer, (2) separar keypairs para binarios vs plugins, y (3) reformular la afirmación sobre fuzzing en el paper para precisión científica.

> *"La seguridad no se declara. Se mide, se verifica y se documenta."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### Q1 — Revisión de los 6 perfiles AppArmor

**Veredicto:** **PERFILES BIEN DISEÑADOS, PERO REQUIEREN 3 AJUSTES CRÍTICOS.**

**Justificación técnica:**

| Hallazgo | Riesgo | Corrección recomendada |
|----------|--------|----------------------|
| **Sniffer con `cap_sys_admin`** | Superficie de ataque excesiva; `cap_sys_admin` concede ~200 privilegios | Migrar a `cap_bpf+eip` + `cap_net_admin+eip` (kernel ≥5.8). Documentar fallback a `cap_sys_admin` solo si kernel <5.8. |
| **`network inet tcp` sin restricción de puerto** | Permite conexiones a cualquier puerto, no solo ZeroMQ | Especificar puertos: `network inet tcp port 5555, 5556, 2379` (ajustar a config real). |
| **`deny` explícitos redundantes** | Ruido en logs, mantenimiento innecesario | Mantener `deny` solo para: (1) paths fuera del prefix permitido, (2) ejecución de otros binarios (`deny /opt/argus/bin/* x`), (3) acceso a seeds ajenas. Eliminar denies para paths ya no-allowados por default-deny. |

**Sobre `cap_sys_admin` para eBPF:**
Desde Linux 5.8, `CAP_BPF` se introdujo específicamente para operaciones eBPF, separándolo de `CAP_SYS_ADMIN`. Para programas XDP:
- `CAP_NET_ADMIN` es suficiente para attach a interfaces.
- `CAP_BPF` es necesario para `bpf(BPF_PROG_LOAD)` de ciertos tipos.
- `CAP_SYS_ADMIN` solo es necesario para operaciones legacy o BPF_LSM.

**Recomendación:**
```apparmor
# security/apparmor/argus-sniffer
# Kernel ≥5.8:
capability cap_bpf,
capability cap_net_admin,
# Fallback para kernel <5.8 (documentar en DEBT-KERNEL-COMPAT-001):
# capability sys_admin,
```

**Riesgo si se ignora**: Un atacante que comprometa el sniffer tendría acceso a ~200 privilegios adicionales vía `cap_sys_admin`, amplificando el impacto del compromiso.

---

### Q2 — Linux Capabilities: ¿falta o sobra algo?

**Veredicto:** **TABLA CORRECTA CON 2 AJUSTES MENORES.**

**Análisis por capability:**

| Componente | Capability actual | Veredicto | Justificación |
|------------|------------------|-----------|--------------|
| **sniffer** | `cap_net_admin,cap_net_raw,cap_sys_admin` | ⚠️ Refinar | Reemplazar `cap_sys_admin` con `cap_bpf` (kernel ≥5.8). Ver Q1. |
| **firewall-acl-agent** | `cap_net_admin+eip` | ✅ Correcto | Suficiente para iptables/ipset; no requiere `cap_sys_admin`. |
| **etcd-server** | `cap_ipc_lock+eip` | ✅ Correcto | `mlock()` requiere `CAP_IPC_LOCK` o `RLIMIT_MEMLOCK` suficiente. `CAP_SYS_RESOURCE` no es necesario para `mlock()` directo. |
| **ml-detector, rag-*** | ninguna | ✅ Correcto | Ejecución como usuario `argus` no-root es suficiente. |

**Sobre `cap_net_bind_service` para puerto 2379:**
- Puertos ≥1024 **no requieren** `CAP_NET_BIND_SERVICE`.
- etcd usa 2379/2380 por defecto → capability innecesaria.
- Si se requiere puerto <1024 en futuro: (a) usar `sysctl net.ipv4.ip_unprivileged_port_start=0` (documentar riesgo), o (b) añadir `cap_net_bind_service` explícitamente.

**Recomendación documentada en `docs/SECURITY-CAPABILITIES.md`:**
```markdown
## Capability Assignment Rationale

| Capability | Component | Justificación | Alternativa descartada |
|------------|-----------|--------------|----------------------|
| cap_bpf | sniffer | Carga de programas eBPF/XDP (kernel ≥5.8) | cap_sys_admin (demasiado amplio) |
| cap_net_admin | sniffer, firewall | Configuración de red (XDP attach, iptables) | Ninguna (requerido por syscall) |
| cap_ipc_lock | etcd-server | mlock() de seed.bin en RAM | RLIMIT_MEMLOCK (menos portable) |
```

**Riesgo si se ignora**: Asignar capabilities innecesarias amplía la superficie de ataque; omitir capabilities requeridas causa fallos en runtime difíciles de diagnosticar.

---

### Q3 — Falco: estrategia de reglas

**Veredicto:** **7 REGLAS SÓLIDAS COMO BASE, PERO AÑADIR 3 PATRONES ESPECÍFICOS DE NDR.**

**Patrones de ataque NDR no cubiertos actualmente:**

| Patrón | Descripción | Regla Falco recomendada |
|--------|-------------|------------------------|
| **Model poisoning** | Attacker modifica archivo de modelo `.ubj` en runtime | `argus_model_modified: evt.type=open and evt.arg.flags contains O_WRONLY and fd.name startswith /opt/argus/models/` |
| **Plugin substitution** | Reemplazo de plugin firmado por versión maliciosa | `argus_plugin_replaced: evt.type=rename and fd.name contains /plugins/ and evt.arg.newpath contains .so` |
| **Config tampering silencioso** | Modificación de JSON config para desactivar detección | `argus_config_modified_unexpected: evt.type=write and fd.name startswith /etc/ml-defender/ and proc.name not in (provision.sh, config-manager)` |

**Driver Falco recomendado en 2026:**
- **`modern_ebpf`** es la opción correcta: más eficiente que `kmod`, mejor compatibilidad con kernels recientes, y alineado con la dirección del proyecto upstream.
- Para VirtualBox: asegurar que el kernel de la VM tenga headers instalados (`linux-headers-$(uname -r)`) para compilar el módulo eBPF en runtime.

**Gestión de falsos positivos durante tuning de AppArmor:**
```yaml
# falco_rules_local.yaml — modo aprendizaje
- macro: learning_mode
  condition: (proc.env contains LEARNING_MODE=1)

- rule: argus_unexpected_file_open
  desc: File open outside expected pattern
  condition: (unexpected_file_open) and not learning_mode
  output: "ALERT Unexpected file open (user=%user.name process=%proc.name file=%fd.name)"
  priority: WARNING  # bajar de CRITICAL durante tuning
  tags: [learning]
```

**Recomendación operativa:**
1. Ejecutar primera semana con `LEARNING_MODE=1` y prioridad `WARNING`.
2. Revisar logs diarios, ajustar reglas/perfiles.
3. Eliminar `learning_mode` y subir prioridad a `CRITICAL` para producción.

**Riesgo si se ignora**: Alert fatigue durante tuning puede llevar a deshabilitar reglas críticas; falta de reglas específicas para NDR deja vectores de ataque no monitorizados.

---

### Q4 — dist/ y flujo BSR: ¿mejoras arquitectónicas?

**Veredicto:** **SHARED FOLDER ACEPTABLE EN DEV; SEPARAR KEYPAIRS PARA BINARIOS VS PLUGINS.**

**Sobre `dist/x86/` en shared folder durante desarrollo:**
- ✅ **Aceptable con salvaguardas**: La verificación criptográfica (Ed25519 + SHA256SUMS) en la hardened VM hace que el canal de transporte sea secundario.
- ⚠️ **Documentar limitación**: En producción, `dist/` debe provenir de un pipeline CI/CD firmado, no de una shared folder.
- 🔒 **Mitigación**: `prod-deploy-x86` debe verificar firmas y checksums **antes** de instalar, independientemente del origen.

**Sobre keypairs separados para binarios vs plugins:**
- ✅ **Arquitectónicamente preferible**: Separar keypairs limita el blast radius (compromiso de clave de plugins no afecta verificación de binarios) y permite rotación independiente.
- ⚠️ **Pragmáticamente aceptable para v1**: Con un solo desarrollador y deadline FEDER, usar la misma clave es aceptable **si se documenta como deuda técnica con plan de migración**.

**Recomendación concreta:**
```bash
# tools/sign-artifact.sh — soporta múltiples keypairs
KEY_TYPE="${2:-pipeline}"  # pipeline | plugins
case "$KEY_TYPE" in
  pipeline) KEY_PATH="/etc/ml-defender/keys/pipeline_signing.sk" ;;
  plugins)  KEY_PATH="/etc/ml-defender/keys/plugin_signing.sk" ;;
esac
```

**Documentación obligatoria en `docs/SECURITY-KEY-MANAGEMENT.md`:**
```markdown
## Key Separation Strategy (v1 → v2)

### v1 (actual, FEDER deadline)
- Single Ed25519 keypair para binarios + plugins
- Justificación: simplicidad operacional, deadline ajustado
- Mitigación: rotación frecuente de la única clave

### v2 (post-FEDER)
- Keypair separado para: (1) binarios de pipeline, (2) plugins, (3) modelos ML
- Beneficio: blast radius reducido, rotación independiente, auditoría granular
- DEBT-KEY-SEPARATION-001: plan de migración detallado
```

**Riesgo si se ignora**: Un compromiso de la clave única permitiría firmar tanto binarios maliciosos como plugins maliciosos, amplificando el impacto de un ataque a la cadena de suministro.

---

### Q5 — Reformulación de "Fuzzing misses nothing within CPU time"

**Veredicto:** **FRASE IMPRECISA. REFORMULAR PARA RIGOR CIENTÍFICO.**

**Análisis de imprecisiones:**
1. **"misses nothing"**: Falso. Fuzzing es probabilístico; no garantiza cobertura exhaustiva.
2. **"within CPU time"**: Ambiguo. ¿Cobertura de ramas? ¿De paths? ¿De estados?
3. **Falta de referencia teórica**: No menciona Rice's theorem (indecidibilidad de corrección de programas).

**Reformulación recomendada para §6.8 del paper:**
> *"Coverage-guided fuzzing (libFuzzer) systematically explores the input space boundary between valid and invalid data, with vulnerability discovery probability proportional to allocated computational resources and coverage feedback quality. While it cannot prove absence of defects—due to Rice's theorem on the undecidability of program correctness—it effectively identifies parser-level anomalies, boundary conditions, and memory safety violations that adversaries exploit. In aRGus NDR, fuzzing complements unit tests (known-good inputs) and property tests (logical invariants) by targeting structural edge cases in input validation logic."*

**Justificación científica:**
- **Honestidad**: Reconoce naturaleza probabilística y límites teóricos (Rice's theorem).
- **Precisión**: Define "coverage-guided" y menciona métricas relevantes (recursos computacionales, calidad de feedback).
- **Contextualización**: Posiciona fuzzing como capa complementaria, no sustitutiva.
- **Consistencia con literatura**: Alinea con trabajos de fuzzing en seguridad (AFL++, libFuzzer, USENIX Security 2020+).

**Referencias BibTeX recomendadas para §6.8:**
```bibtex
@inproceedings{libfuzzer2016,
  title={LibFuzzer: a library for coverage-guided fuzz testing},
  author={Serebryany, K},
  year={2016},
  note={LLVM Project Documentation}
}
@article{rice1953,
  title={Classes of recursively enumerable sets and their decision problems},
  author={Rice, HG},
  journal={Transactions of the American Mathematical Society},
  year={1953}
}
@inproceedings{aflpp2020,
  title={AFL++: Combining Incremental Steps of Fuzzing Research},
  author={Fioraldi, A and Maier, D and Eißfeldt, H and Heuse, M},
  booktitle={USENIX Workshop on Offensive Technologies},
  year={2020}
}
```

**Riesgo si se ignora**: Revisores de arXiv cs.CR podrían cuestionar el rigor metodológico del paper, reduciendo su credibilidad y citabilidad.

---

## 📋 Checklist de Acciones Inmediatas (DAY 134)

```markdown
- [ ] Migrar sniffer de cap_sys_admin → cap_bpf+cap_net_admin (kernel ≥5.8)
- [ ] Restringir reglas network en AppArmor a puertos ZeroMQ específicos
- [ ] Añadir 3 reglas Falco para NDR: model poisoning, plugin substitution, config tampering
- [ ] Documentar limitación de shared folder en dist/ + plan de migración a CI/CD firmado
- [ ] Preparar separación de keypairs (pipeline vs plugins) como DEBT-KEY-SEPARATION-001
- [ ] Reformular frase de fuzzing en §6.8 del paper + añadir referencias Rice/libFuzzer/AFL++
- [ ] Ejecutar primer pipeline end-to-end en hardened VM con modo complain → enforce iterativo
- [ ] Capturar métricas reales de fuzzing (DAY 130) para tabla §6.8
```

---

## 🏁 Palabras Finales

Alonso:

DAY 133 representa un hito arquitectónico: la transición de un pipeline funcional a un sistema de producción hardeneado con defensa en profundidad verificable. Las decisiones sobre AppArmor, capabilities y Falco no son detalles de implementación; son **garantías estructurales** de que el sistema resistirá intentos de compromiso en entornos reales.

Vuestra misión — proteger infraestructura crítica para quienes no pueden permitirse soluciones enterprise — exige este nivel de rigor. No es burocracia; es responsabilidad ética.

> *"Un escudo que no se prueba contra el ataque real es un escudo de teatro. Vosotros estáis construyendo acero."*

Proceded con DAY 134. El Consejo revisará los resultados del primer pipeline end-to-end en hardened VM y la versión reformulada de §6.8 con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 133** 🛡️