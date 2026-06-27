## Claude (Consejo de Sabios) — Respuestas DAY 167

---

**Q1 — KNOWN-FAIL-VM-PERF-001: ¿excluir o aceptar?**

**Recomiendo la opción C**, con una mejora: crear `docs/KNOWN-FAILS.md` si no existe y documentar los 6 tests con causa raíz explícita (VirtualBox overhead en syscalls de netfilter/ipset). La razón es filosófica además de técnica: estos tests *no son falsos negativos*, son verdaderos negativos en el entorno VM. Esconderlos con `DISABLED` o `--gtest_filter` crearía una discrepancia silenciosa entre lo que el CI ejecuta y lo que el código promete. Cuando llegue el hardware real de FEDER (BM-A/B/C/D del BACKLOG-BENCHMARK-CAPACITY-001), estos tests deberían pasar — y ese momento tendrá valor de demostración precisamente porque estaban documentados como conocidos. La transparencia es el activo, no el problema.

---

**Q2 — `.deb` vs Suricata: ¿orden de prioridad?**

**Suricata primero.** El argumento es de valor de demostración FEDER: un `.deb` es un artefacto de empaquetado que no cambia la capacidad observable del sistema; Suricata es un sensor de red real que convierte aRGus en un NDR funcional contra tráfico auténtico. Para la presentación a Dr. Andrés Caro Lindo, mostrar `suricata → aRGus → firewall-acl` con `community_id` como clave primaria tiene un impacto narrativo incomparablemente mayor que un paquete instalable. El `.deb` puede venir después de Suricata sin penalizar el deadline de septiembre.

---

**Q3 — NTP/chrony como P0 gate en EMECAS++**

**Incorporar a provisioning, no a EMECAS++ todavía.** El razonamiento: EMECAS++ actualmente corre dentro de una VM ya provisionada donde chrony puede presuponerse instalado como prerequisito de bootstrap. Añadirlo al Acto I de EMECAS++ antes de validarlo en `provision.sh` introduce un gate que falla por razones de entorno antes de llegar al código. El orden correcto es: (1) `DEBT-ARGUSPP-NTP-001` en `provision.sh` con health-check de offset, (2) validar que el check pasa en `make test-provision` o equivalente, (3) *entonces* considerar si merece ser Acto 0 de EMECAS++. No al revés.

---

**Q4 — `vendor.key` a Vault vs Suricata: ¿orden?**

**Pueden ir en paralelo conceptualmente, pero Suricata va antes en la práctica.** `BACKLOG-CRYPTO-VENDOR-KEY-001` es una mejora de hardening de la cadena de distribución de claves — importante para producción, pero no cambia el comportamiento observable del sistema en la demo. Suricata sí lo cambia. Dicho esto, si al llegar a la integración Suricata el pipeline CI tiene el `vendor.key` todavía en claro en el repo, hay un riesgo reputacional ante el revisor académico. Mi recomendación concreta: resolver `BACKLOG-CRYPTO-VENDOR-KEY-001` *durante* el sprint de Suricata, en paralelo, como tarea de media sesión — no como bloqueante previo.

---

*Votación implícita: C / Suricata primero / provision.sh antes que EMECAS++ / paralelo con Suricata.*