# 🏛️ CONSEJO DE SABIOS — REVISIÓN DAY 135
*Feedback basado en evidencia técnica, modelado de amenazas y principios de ingeniería de sistemas reproducibles*

---

## 🎯 Veredicto Ejecutivo

**APROBACIÓN DE MERGE CON MATICES ARQUITECTÓNICOS CLAROS.**

DAY 135 cierra un ciclo fundamental: el pipeline hardened pasa de concepto a sistema verificable con 5/5 gates verdes, integridad de supply chain (apt + vendor), y separación explícita de secretos. La disciplina EMECAS y la documentación de deudas muestran madurez operativa. Las preguntas planteadas tocan puntos críticos de diseño que requieren respuestas precisas antes del merge.

> *"La seguridad no se negocia en la boot sequence. Se codifica, se verifica y se mantiene inmutable."*

---

## ❓ Respuestas a Preguntas — Formato Científico

### Q1 — `FailureAction=reboot` y ventana de 30s para logs

**Recomendación concreta:** **Mantener `FailureAction=reboot`. NO hacer configurable via etcd/JSON. Sustituir `TimeoutStartSec` por `ExecStopPre` para flush de logs local + remoto.**

**Justificación técnica:**
- `TimeoutStartSec=30s` aplica al *arranque* del servicio, no a la acción post-fallo. No garantiza que los logs se propaguen antes del reboot.
- Un servicio de integridad de apt sources **no debe depender de una fuente de configuración externa** (etcd/JSON). Si `apt` está comprometido, el canal de configuración también podría estarlo o ser inaccesible. La política debe ser estática y verificable en binario.
- La ventana de logs se garantiza con:
  ```ini
  # argus-apt-integrity.service
  FailureAction=reboot
  ExecStopPre=/usr/bin/journalctl --flush
  ExecStopPre=/usr/bin/logger -p auth.crit "APT INTEGRITY CHECK FAILED: Rebooting node."
  ```
  `journalctl --flush` fuerza escritura a disco persistente. `logger` envía a syslog remoto (si está configurado) y local. El reboot ocurre inmediatamente después de estos pasos.

**Riesgo si se ignora:** Configurar el comportamiento via etcd/JSON introduce un bootstrapping circular: si el nodo no confía en su propio filesystem, ¿cómo puede confiar en un servicio remoto que podría estar comprometido?

**Verificación mínima:**
```bash
# Simular corrupción y verificar comportamiento
sudo bash -c 'echo "malicious repo" >> /etc/apt/sources.list'
sudo systemctl restart argus-apt-integrity
journalctl -u argus-apt-integrity --since "1 min ago" | grep -i "flush\|FAILED\|reboot"
# Debe mostrar flush exitoso, log crítico, y reboot inmediato
```

---

### Q2 — `DEBT-SEEDS-SECURE-TRANSFER-001`: arquitectura de transferencia

**Recomendación concreta:** **OPCIÓN C (Generación local en hardened VM) + backup criptográfico obligatorio. NO viola ADR-013 si se redefine el "root of trust".**

**Justificación técnica:**
- **Opciones A/B** mantienen un canal de transferencia que, por definición, es un punto de ataque adicional (MITM, compromiso de clave efímera, dependencia de red en provisioning).
- **Opción C** elimina el vector de transferencia por completo. La hardened VM genera su propia semilla con `getrandom()` (bloqueo de `/dev/urandom` garantizado en Linux moderno), deriva su keypair localmente, y solo exporta la *pubkey* para registro en el fleet.
- **ADR-013 compatibilidad**: Si ADR-013 asumía generación centralizada para consistencia, se actualiza a: *"Consistencia criptográfica por derivación determinista desde seed local, con backup en HSM/YubiKey o passphrase cifrada. El trust se desplaza del canal de transferencia a la entropía local y el procedimiento de backup."*
- **Backup obligatorio**: La seed debe copiarse inmediatamente a un almacenamiento aislado (YubiKey, offline vault) post-generación. La pérdida de seed = pérdida de nodo.

**Riesgo si se ignora:** Mantener `/vagrant` como canal de seeds en producción normaliza una práctica insegura (shared folder hypervisor = superficie de escape potencial).

**Verificación mínima:**
```bash
# En hardened VM provisioning
if [ ! -f /etc/ml-defender/<comp>/seed.bin ]; then
    dd if=/dev/urandom bs=32 count=1 of=/etc/ml-defender/<comp>/seed.bin 2>/dev/null
    chmod 0400 seed.bin
    chown argus:argus seed.bin
    # Forzar backup a USB/vault antes de continuar provisioning
fi
```

---

### Q3 — Bloqueantes para merge `feature/adr030-variant-a` → `main`

**Veredicto:** **NO BLOQUEANTES. APROBADO PARA MERGE.**

**Justificación técnica:**
- `check-prod-all` 5/5 PASSED con gates objetivos y verificables.
- `hardened-full` reproduce desde cero sin intervención manual.
- Las deudas conocidas (`COMPILER-WARNINGS`, `SEEDS-SECURE-TRANSFER`) están clasificadas correctamente como post-merge/post-FEDER.
- La separación de seeds del flujo EMECAS es arquitectónicamente correcta (seguridad > conveniencia).

**Condición de merge:**
- Tag `v0.6.0-hardened-variant-a` con release notes explícitas listando las 2 deudas no bloqueantes y su impacto.
- Incluir `docs/KNOWN-DEBTS-v0.6.md` referenciando `DEBT-COMPILER-WARNINGS-001` y `DEBT-SEEDS-SECURE-TRANSFER-001`.

**Riesgo si se retrasa:** Acumulación de contexto técnico y divergencia de ramas, aumentando coste de integración futura.

---

### Q4 — Flujo diario: `hardened-redeploy` + `prod-deploy-seeds` + ¿`hardened-full-with-seeds`?

**Recomendación concreta:** **Mantener flujo actual para desarrollo. Añadir `make hardened-full-with-seeds` EXCLUSIVAMENTE para testing/FEDER, con documentación explícita de límite de uso.**

**Justificación técnica:**
- Separar `redeploy` (código/config) de `deploy-seeds` (secretos) es un **principio de seguridad operacional**: evita que un script de CI o un commit automático filtre o sobrescriba secretos.
- Para demos FEDER o validación end-to-end, un target único es práctico. Pero debe estar marcado como `PHASE=TESTING` y no usarse en pipelines de producción.

**Implementación recomendada:**
```makefile
# Makefile
.PHONY: hardened-full-with-seeds
hardened-full-with-seeds:
	@echo "⚠️  TARGET FOR TESTING/FEDER ONLY — seeds deployed inline"
	@make hardened-full
	@make prod-deploy-seeds
	@make check-prod-all
	@echo "✅ Full hardened env + seeds ready for integration testing"
```

**Riesgo si se ignora:** Unificar seeds en el flujo principal incentiva la automatización de transferencia de secretos en CI, violando el principio de mínimo privilegio y aumentando superficie de ataque en pipelines.

---

### Q5 — Próximos pasos post-merge (DAY 136): A, B o C

**Recomendación concreta:** **OPCIÓN B (Variant B/libpcap) → luego transición a A (FEDER prep). Opción C se aborda incrementalmente.**

**Justificación estratégica y científica:**
1. **Variant B es prerequisito para FEDER**: La baseline de aceptación (Q1-Q6 DAY 134) exige métricas para ARM64 + libpcap. Sin Variant B, la demo FEDER solo cubre x86, reduciendo el alcance y la contribución científica.
2. **Delta XDP/libpcap es publicación independiente**: Como acordó el Consejo, el rendimiento/compatibilidad trade-off es una contribución válida para workshops de seguridad o arXiv cs.CR.
3. **Compiler warnings (Opción C)**: Son ruido pre-certificación. Abordarlos ahora frena el ritmo hacia FEDER. Se resuelven en batch post-Demo o durante refactorización de ADR-036 (Formal Verification).
4. **Cronograma realista**:
  - MAY-JUN: Variant B estable + benchmarks x86 vs ARM
  - JUL: Script FEDER `feder-demo.sh` + paper §5 actualización con métricas reales
  - AGO: Dry-run FEDER + hardening final
  - SEP 22: Presentación

**Riesgo si se ignora**: Priorizar FEDER prep (A) sin Variant B lista producirá una demo incompleta; priorizar warnings (C) retrasará entregables críticos con deadline fijo.

**Verificación mínima:**
```bash
# DAY 136 objetivo:
git checkout -b feature/variant-b-libpcap
cp -r vagrant/hardened-x86 vagrant/hardened-arm64
# Modificar Vagrantfile: base box ARM64, sin eBPF headers, con libpcap-dev
make hardened-full ARCH=arm64 VARIANT=libpcap
# Validar: check-prod-all PASSED + benchmark libpcap vs xdp
```

---

## 📋 Checklist de Acciones Inmediatas (DAY 136)

```markdown
- [ ] Ajustar `argus-apt-integrity.service` con `ExecStopPre=/usr/bin/journalctl --flush`
- [ ] Eliminar dependencia de etcd/JSON para política de apt integrity
- [ ] Aprobar merge `feature/adr030-variant-a` → `main` con tag `v0.6.0-hardened-variant-a`
- [ ] Crear `docs/KNOWN-DEBTS-v0.6.md` con deudas no bloqueantes documentadas
- [ ] Añadir `hardened-full-with-seeds` marcado como TEST/FEDER ONLY
- [ ] Iniciar `feature/variant-b-libpcap` con base ARM64 + libpcap
- [ ] Configurar benchmark comparativo x86/XDP vs ARM/libpcap para paper
- [ ] Postergar DEBT-COMPILER-WARNINGS-001 a batch post-FEDER o ADR-036
```

---

## 🏁 Palabras Finales

Alonso:

DAY 135 consolida la transición de arquitectura a sistema operacional. La decisión de `FailureAction=reboot`, la separación de seeds del EMECAS, y la verificación de `confidence_score` demuestran que el proyecto internaliza principios de seguridad crítica: **confianza cero, verificación explícita, recuperación rápida**.

Las preguntas que planteáis tocan la esencia del diseño seguro. Las respuestas propuestas mantienen el equilibrio entre rigor metodológico y viabilidad operativa, alineado con el deadline FEDER y la misión humanitaria del proyecto.

> *"Un escudo que no se prueba contra el ataque real es un escudo de teatro. Vosotros estáis forjando acero."*

Proceded con el merge y la apertura de Variant B. El Consejo revisará los primeros benchmarks ARM/libpcap y la estructura de la demo FEDER con el mismo rigor con el que evaluamos cada línea de este pipeline.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 135** 🏛️