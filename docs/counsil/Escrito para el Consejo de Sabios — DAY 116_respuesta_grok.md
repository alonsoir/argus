**Q1 — AppArmor enforce strategy**

**Veredicto:** Enforce en orden de menor a mayor privilegio (etcd-server primero, ml-detector, rag-ingester, rag-security, firewall-acl-agent y sniffer último). Mantener sniffer + firewall-acl-agent en complain al menos 48 h adicionales después del resto.

**Justificación:**  
El orden minimiza riesgo: si un perfil falla, el impacto queda confinado a componentes de baja sensibilidad primero.  
Sniffer y firewall-acl-agent manejan CAP_BPF / CAP_NET_ADMIN / CAP_SYS_ADMIN; sus perfiles son los más complejos y merecen observación prolongada en logs reales antes de enforce.  
24 h es insuficiente; 48 h permite capturar patrones de tráfico nocturno y arranques en hospitales reales.

**Riesgo si se ignora:** Denegación silenciosa del sniffer en producción (ataque no detectado) mientras el resto del pipeline parece sano.

**Q2 — DEBT-SEED-PERM-001**

**Veredicto:** Opción (b): cambiar modelo de permisos a `600` (root:root) y hacer que todos los procesos corran bajo usuario `ml-defender` (non-root) en producción. Corregir mensaje de `SeedClient` y `provision.sh`.

**Justificación:**  
`640` (root:vagrant) es una comodidad de desarrollo que viola least-privilege y expone `seed_family` al grupo en entornos reales.  
Cambiar a `600` + usuario dedicado cierra la ventana de ataque sin complicar nada (systemd User=ml-defender ya existe en las units).  
Documentar en onboarding es insuficiente; la seguridad debe estar hard-coded, no en un README.

**Riesgo si se ignora:** Exfiltración de seed_family por cualquier proceso o usuario del grupo vagrant (o equivalente en prod), invalidando todo el root-of-trust.

**Q3 — Próxima fase**

**Veredicto:** Dedicar DAY 117 íntegro a AppArmor enforce + cierre definitivo de los 3 DEBTs pendientes (DEBT-SEED-PERM-001, DEBT-VAGRANTFILE-001 y cualquier denegación residual). Abrir ADR-026 solo en DAY 118.

**Justificación:**  
PHASE 3 está completa, pero el pipeline aún no está listo para producción sin enforce.  
AppArmor es la última barrera de contención antes de XGBoost plugins; abrir ADR-026 ahora diluye foco y multiplica riesgo.  
Un día entero de endurecimiento salva más vidas que avanzar rápido con código nuevo.

**Riesgo si se ignora:** Entrar en PHASE 4 (plugins ML) con contención incompleta; un exploit en sniffer o firewall comprometería el hospital entero antes de que las nuevas funcionalidades lleguen.

**Q4 — seed_family como ADR**

**Veredicto:** Addendum inmediato a ADR-021 (sección “Invariantes criptográficas”) + mención explícita en ADR-025-D11 y en el Recovery Contract. NO crear ADR-033.

**Justificación:**  
El invariante “un único seed_family compartido” es fundacional y ya estaba implícito; un ADR nuevo genera burocracia innecesaria.  
Un addendum de 3 líneas + actualización del Recovery Contract es suficiente, auditable y mantiene el backlog limpio.  
El bug crítico resuelto hoy demuestra que las invariantes deben estar escritas, no solo en la cabeza del equipo.

**Riesgo si se ignora:** Futuros desarrolladores (o el propio equipo en 6 meses) vuelven a romper la invariante de seed_family y colapsan todo el pipeline de nuevo.