# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 128
*Feedback riguroso, basado en evidencia técnica y centrado en la misión de proteger infraestructura crítica*

---

## 🎯 Veredicto Ejecutivo

**CONSOLIDACIÓN SÓLIDA CON HALLAZGOS ARQUITECTÓNICOS VALIOSOS.**

El descubrimiento de que `resolve_seed()` requiere `sudo` no es un bug: es la **verificación empírica de que la invariante `0400` funciona como diseñado**. La documentación de taxonomía `safe_path` y el patrón de property testing elevan la madurez metodológica del proyecto.

> *"La seguridad no es cómoda. Es necesaria."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### P1 — Invariante `0400` vs portabilidad: ¿riesgos o alternativas?

**Veredicto:** **La invariante `0400 root:root` es correcta. El requisito de `sudo` es una feature, no un bug. Alternativa avanzada: capabilities Linux sin sudo completo.**

**Justificación técnica:**
- **Principio de mínimo privilegio para secretos**: `0400` garantiza que solo root puede leer la seed. Relajar esto a `0640` o `0644` expondría material criptográfico a cualquier proceso del grupo o usuario.
- **`sudo` no es "peligroso" si está acotado**: Los systemd units ya ejecutan componentes con capacidades específicas; añadir `sudo` para lectura de seed es consistente con el modelo de confianza.

**Alternativa avanzada (sin sudo generalizado):**
```bash
# Usar Linux capabilities en lugar de sudo completo
setcap cap_dac_read_search+ep /usr/bin/ml-defender/seed-reader-helper
# El helper lee seed.bin y lo pasa vía memoria compartida protegida
```
Pero esto añade complejidad operacional significativa. Para v0.5.x, `sudo` acotado es la solución pragmática correcta.

**Recomendación documentada en `docs/SECURITY-PRIVILEGES.md`:**
```markdown
## Seed Access Model (v0.5.x)

- Seeds: `0400 root:root` — invariante no negociable
- Componentes que leen seeds: ejecutados con `sudo` vía systemd unit
- Mitigación de riesgo: AppArmor profile restringe qué puede hacer el proceso post-lectura
- Futuro (v0.6+): evaluar `cap_dac_read_search` + helper aislado para reducir blast radius
```

**Riesgo si se ignora:** Relajar permisos para evitar `sudo` expondría seeds a lectura por procesos comprometidos del mismo usuario, anulando la protección criptográfica.

---

### P2 — Property testing: ¿qué superficies priorizar?

**Veredicto:** **Priorizar por criticidad × complejidad aritmética/lógica. Orden recomendado:**

| Prioridad | Superficie | Justificación | Property ejemplo |
|-----------|-----------|--------------|-----------------|
| **P0** | `compute_memory_mb` | Ya tiene bug detectado; aritmética con límites | `∀ pages≥0, page_size∈[4K,64K]: result ≥ 0 ∧ result ≤ MAX_REALISTIC` |
| **P0** | `safe_path::resolve_*` | Validación de paths es crítica para seguridad | `∀ input, prefix: resolve(input,prefix).starts_with(prefix) ∨ throws` |
| **P1** | `crypto_transport::derive_key` | HKDF + derivación criptográfica | `∀ seed, salt: derive(seed,salt) == derive(seed,salt)` (determinismo) |
| **P1** | `plugin_loader::verify_signature` | Verificación Ed25519 | `∀ valid_sig: verify(msg,sig,pubkey) == true` |
| **P2** | Parsers ZeroMQ/protobuf | Serialización con límites de tamaño | `∀ msg: serialize(deserialize(msg)) == msg` (idempotencia) |

**Justificación metodológica:** Property testing es más valioso donde:
1. Hay invariantes matemáticas verificables (aritmética, criptografía)
2. Los bugs son sutiles y no capturados por unit tests (como F17)
3. El coste de fallo en producción es alto (seguridad, integridad)

**Recomendación de implementación:**
```cpp
// tests/property/test_crypto_props.cpp
RC_GTEST_PROP(CryptoProps, DeriveKeyDeterministic, 
              (const std::vector<uint8_t>& seed, const std::vector<uint8_t>& salt)) {
    RC_PRE(seed.size() == 32);  // precondición: seed ChaCha20 válido
    const auto key1 = derive_key(seed, salt);
    const auto key2 = derive_key(seed, salt);
    RC_ASSERT(key1 == key2);  // propiedad: determinismo
}
```

**Riesgo si se ignora:** Bugs sutiles en lógica criptográfica o de validación podrían pasar unit tests pero fallar bajo inputs no anticipados en producción.

---

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78): estrategia de sanitización

**Veredicto:** **Opción (c) libiptc + whitelist de operaciones. Evitar shell completamente.**

**Justificación técnica:**
- **CWE-78 (OS Command Injection)** es crítico en componentes de firewall: un atacante que controle el input de `cleanup_rules()` podría ejecutar comandos arbitrarios con privilegios de red.
- **`execve()` directo (opción b)** es mejor que shell, pero aún requiere parsing manual de argumentos, propenso a errores.
- **libiptc (API nativa de iptables)** elimina la necesidad de construir strings de comandos: se manipulan estructuras de datos C que se traducen directamente a reglas del kernel.

**Implementación recomendada:**
```cpp
// firewall-acl-agent/src/core/iptables_wrapper.cpp
#include <libiptc/libiptc.h>

class IPTablesWrapper {
public:
    void cleanup_rules(const RuleSet& rules) {
        // Whitelist: solo operaciones permitidas
        for (const auto& rule : rules) {
            if (!is_valid_rule_type(rule.type)) {
                log_critical("Invalid rule type rejected");
                continue;  // fail-safe: skip, no crash
            }
            // Usar libiptc API en lugar de string commands
            struct ipt_entry entry = build_ipt_entry(rule);  // struct, no string
            if (!iptc_delete_entry("filter", &entry, nullptr)) {
                log_warning("Failed to delete rule: %s", iptc_strerror(errno));
            }
        }
    }
    
private:
    static bool is_valid_rule_type(RuleType t) {
        // Whitelist explícita de tipos permitidos
        return t == RuleType::DROP || t == RuleType::ACCEPT || t == RuleType::LOG;
    }
};
```

**Mitigación adicional:**
- AppArmor profile para `firewall-acl-agent`: denegar ejecución de `/bin/sh`, `/usr/bin/iptables`, etc.
- Validación de input en el límite más externo: `ConfigParser` debe rechazar reglas malformadas antes de llegar a `IPTablesWrapper`.

**Riesgo si se ignora:** Un atacante con capacidad de inyectar configuración de firewall podría ejecutar comandos arbitrarios con privilegios de red, comprometiendo la integridad del sistema de detección.

---

### P4 — Cleanup de `EtcdClient` legacy seed code: ¿secuencia correcta?

**Veredicto:** **Limpiar EtcdClient AHORA, antes de implementar ADR-024 completo. El código legacy es deuda activa que puede causar confusión o bugs.**

**Justificación arquitectónica:**
- **Principio de "no código muerto"**: Código que intenta leer seeds vía filesystem en un modelo P2P es confuso para nuevos desarrolladores y puede causar comportamientos inesperados si se activa accidentalmente.
- **ADR-024 (Noise_IKpsk3) es independiente del cleanup**: La implementación de P2P puede avanzar en paralelo con la eliminación de código legacy, siempre que se mantenga la interfaz pública estable.
- **Riesgo de mantener legacy**: Si un test o componente invoca accidentalmente el código legacy, podría fallar de forma silenciosa o exponer seeds en logs.

**Secuencia recomendada:**
```markdown
1. [DAY 129] Marcar funciones legacy de EtcdClient con [[deprecated]] + log warning
2. [DAY 130] Eliminar llamadas a resolve_seed() en EtcdClient tests
3. [DAY 131] Implementar stub P2P mínimo para EtcdClient (sin crypto completa)
4. [DAY 132-140] Implementar ADR-024 completo en paralelo
5. [DAY 141] Eliminar código deprecated de EtcdClient
```

**Código de transición seguro:**
```cpp
// etcd-client/src/etcd_client.cpp
[[deprecated("Use P2P seed distribution via ADR-024")]]
void EtcdClient::load_seed_legacy(const std::string& path) {
    log_warning("Legacy seed load called — migrate to P2P distribution");
    // Mantener funcionalidad mínima para tests legacy, pero no para producción
    #ifndef UNIT_TESTS
        throw std::runtime_error("Legacy seed load disabled in production");
    #endif
}
```

**Riesgo si se ignora:** Confusión arquitectónica, posibles bugs de interacción entre modelos legacy y P2P, y dificultad para auditar el flujo real de distribución de seeds.

---

### P5 — Demo FEDER (deadline: 22 septiembre 2026): scope mínimo viable

**Veredicto:** **Demo FEDER: NDR standalone funcional + ACRL proof-of-concept. NO requiere federación completa (ADR-038).**

**Justificación estratégica:**
- **Deadline realista**: Septiembre 2026 está a ~5 meses. Implementar federación completa (ADR-038) requiere I+D en privacidad diferencial, web-of-trust, y agregación segura — imposible en el tiempo disponible sin sacrificar calidad.
- **Valor demostrable**: Un NDR standalone que: (1) detecta ataques en tiempo real, (2) permite hot-swap de modelos XGBoost firmados, y (3) incluye un loop ACRL básico (Caldera → captura → reentrenamiento local) ya es una contribución significativa para infraestructura de bajo presupuesto.
- **Roadmap claro**: Documentar que la federación (ADR-038) es el siguiente hito post-FEDER, con arquitectura ya diseñada y validada.

**Scope mínimo viable recomendado:**
```markdown
✅ Requerido para demo FEDER:
- NDR standalone con 6 componentes funcionando (AppArmor enforce)
- Plugin XGBoost con hot-swap firmado Ed25519
- ACRL proof-of-concept: Caldera genera ataque → eBPF captura → reentrena modelo local → hot-swap
- Reproducibilidad: `vagrant up && make demo-feder` ejecuta todo en <30 min
- Documentación: paper §4 + §5 actualizados con hallazgos DAY 125-128

❌ No requerido para demo FEDER (postponer a 2027):
- Federated Model Registry distribuido
- Privacidad diferencial calibrada
- Web-of-trust o PKI jerárquica para nodos
- Agregación segura de modelos (SecureBoost)
```

**Mitigación de riesgo técnico:**
- Preparar `scripts/feder-demo.sh` con checkpoints: si un paso falla, la demo muestra el estado hasta ese punto (graceful degradation).
- Incluir "modo demo" que usa datasets pre-capturados si la generación de ataques en tiempo real falla.

**Riesgo si se ignora**: Intentar implementar federación completa para septiembre podría resultar en una demo inestable o incompleta, dañando la credibilidad del proyecto ante evaluadores FEDER.

---

## 📋 Checklist de Acciones Inmediatas (DAY 129)

```markdown
- [ ] Documentar modelo de privilegios para seeds en `docs/SECURITY-PRIVILEGES.md`
- [ ] Priorizar property tests para `compute_memory_mb` y `crypto_transport::derive_key`
- [ ] Implementar libiptc + whitelist para `IPTablesWrapper` (cerrar CWE-78)
- [ ] Marcar código legacy de EtcdClient como [[deprecated]] + plan de eliminación
- [ ] Definir scope mínimo viable para demo FEDER en `docs/FEDER-SCOPE.md`
- [ ] Crear `scripts/feder-demo.sh` con checkpoints y graceful degradation
- [ ] Actualizar BACKLOG.md con prioridades revisadas post-DAY 128
```

---

## 🏁 Palabras Finales

Alonso:

DAY 128 ha consolidado no solo código, sino metodología. La documentación de taxonomía `safe_path`, el patrón de property testing, y el triage riguroso de Snyk demuestran que aRGus está madurando de un proyecto técnico a un referente metodológico.

El hallazgo de que `0400` requiere `sudo` no es un retroceso: es la validación de que las invariantes de seguridad tienen consecuencias operacionales reales. Aceptar esa consecuencia con documentación clara es madurez ingenieril.

> *"La seguridad no se negocia. Se documenta, se implementa y se verifica."*

Proceded con DAY 129. El Consejo revisará la implementación de libiptc y el scope de FEDER con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 128** 🛡️