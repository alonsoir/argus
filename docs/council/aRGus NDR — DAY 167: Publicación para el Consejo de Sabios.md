# aRGus NDR — DAY 167: Publicación para el Consejo de Sabios

---

## ✅ Lo que hemos hecho hoy

**BACKLOG-CI-ENTERPRISE-001: Pipeline Jenkins dev — CERRADO**

Después de 12 ejecuciones, el pipeline `Jenkinsfile.dev` está verde de extremo a extremo por primera vez.

**Componentes implementados:**

- `vagrant-shim.sh`: intercepta `vagrant destroy` y `vagrant up` dentro de la VM Jenkins y los convierte en no-ops, permitiendo que EMECAS++ corra en el entorno CI sin destruir la VM anfitriona.
- `Jenkinsfile.dev` con 7 stages funcionales: Checkout → Bootstrap → Wire Protocol → Unit Tests → Vault Start → Enterprise Plugin → EMECAS++ Gate → Build .deb (deferred) → Deploy Vagrant Test (deferred).
- Resolución del bug crítico `pkill -f etcd-server`: self-match en el proceso bash padre de make durante la Fase 5 del `vault-fault-inject`. Fix: `pkill -x etcd-server &` (match exacto de nombre + background para evitar propagación de señal SIGTERM).
- `KNOWN-FAIL-VM-PERF-001` documentado: 6 tests `IPSetWrapper` fallan por thresholds de bare metal no alcanzables en VM VirtualBox. No bloquean el pipeline porque `make test-all` permite fallos parciales en CTest; el gate real es EMECAS++.
- Dos targets deferred identificados y skipeados: `DEBT-PACKAGE-DEB-001` (`make package-deb`) y `DEBT-DEPLOY-VAGRANT-001` (`make deploy-vagrant-test`).

**Estado final del pipeline:**
```
✅ EMECAS++ PASSED — 3 Actos verdes
Pipeline dev PASSED — aRGus NDR
Finished: SUCCESS
```

---

## 📋 Lo que haremos mañana (DAY 168)

**P0 — Cerrar DAY 167 formalmente:**
1. Commit `Jenkinsfile.dev` + `vagrant-shim.sh` al repo con mensaje estructurado.
2. Registrar `DEBT-PACKAGE-DEB-001` en `docs/BACKLOG.md`: build de paquetes `.deb` para distribución (DAY 164 según roadmap).
3. Registrar `DEBT-DEPLOY-VAGRANT-001` en `docs/BACKLOG.md`: stage de deploy en VM de test post-merge.
4. Tag `v0.9.5-day167` o equivalente.

**P1 — Próximas deudas técnicas activas:**
- `DEBT-ARGUSPP-NTP-001`: instalar chrony en `provision.sh`, health-check offset >1s → exit 1 (P0 ADR-048 F2).
- `DEBT-ARGUSPP-COMMUNITY-ID-001`: `community_id` en configuración Suricata/Zeek.
- `DEBT-ARGUSPP-SURICATA-001`: integración Suricata en Vagrantfile + EMECAS (~2 sesiones, aprobado por Consejo 6/8).

---

## ❓ Preguntas para el Consejo

**Q1 — KNOWN-FAIL-VM-PERF-001: ¿excluir o aceptar?**
Los 6 tests `IPSetWrapper` (performance y funcionales) fallan sistemáticamente en VM por limitaciones de VirtualBox/hypervisor. El pipeline pasa porque el gate es EMECAS++, no CTest. Opciones:
- A) Marcarlos `DISABLED` en CMake con guard `#ifdef CI_VM_MODE` — limpia el output pero oculta fallos reales.
- B) Añadir `KNOWN-FAIL-VM-PERF-001` como exclusión explícita en el Jenkinsfile con `--gtest_filter=-IPSetWrapperTest.BatchAddPerformance:...` — transparente pero verboso.
- C) Dejar como está (fallos visibles, no bloqueantes) y documentar en `docs/KNOWN-FAILS.md` — Via Appia: honesto, sin esconder deuda.
- **¿Cuál recomienda el Consejo?**

**Q2 — `DEBT-PACKAGE-DEB-001`: ¿prioridad relativa vs Suricata?**
El roadmap original sitúa los paquetes `.deb` en DAY 164 y Suricata en DAY 166+. Con el retraso acumulado, ¿el Consejo mantiene el orden (`.deb` antes que Suricata) o considera que la integración Suricata tiene mayor valor de demostración para la presentación FEDER y debe adelantarse?

**Q3 — `EMECAS++` y NTP como P0 gate:**
ADR-046 v3 establece NTP/chrony como P0 boot gate. `DEBT-ARGUSPP-NTP-001` no está en EMECAS++ aún. ¿Debe incorporarse al Acto I de EMECAS++ antes de avanzar a Suricata, o puede ir en paralelo como check de provisioning independiente?

**Q4 — `BACKLOG-CI-ENTERPRISE-001` vs `BACKLOG-CRYPTO-VENDOR-KEY-001`:**
Con el pipeline CI verde, el siguiente bloque cryptográfico pendiente es mover `vendor.key` a Vault y leer la clave pública desde variable de entorno Jenkins (`BACKLOG-CRYPTO-VENDOR-KEY-001`). ¿Este trabajo debe preceder a Suricata (arquitectura más sólida primero) o puede ir en paralelo/posterior?

---

*DAY 167 cerrado. 12 ejecuciones. pkill -x. Pipeline verde.*
*Via Appia Quality.*