**Consejo de Sabios — aRGus NDR — DAY 143**

Saludos, equipo. Hemos revisado con rigor el estado actual del branch `feature/variant-b-libpcap`, los EMECAS, las deudas cerradas y las preguntas abiertas. Nuestra evaluación combina método científico (falsabilidad, reproducibilidad, minimización de deuda técnica) y principios de sistemas distribuidos/críticos (fail-safe defaults, least privilege, defense-in-depth, graceful degradation).

### Evaluación General de Hoy (DAY 143)

**Positivo fuerte:**
- Regresiones detectadas y corregidas rápido vía EMECAS es excelente disciplina. La lección “cambio de firma → actualizar *todos* los call sites en el mismo commit” debe quedar grabada en hierro.
- Cierre de **DEBT-IRP-NFTABLES-001** con tests unitarios + integración + AppArmor enforce es trabajo de calidad. El uso de `fork()+execv()` separado del pipeline principal es correcto para no bloquear detección.
- `IsolateConfig` con defaults seguros y JSON explícito es mantenible.
- TimestampUniqueness fix y tolerancia IEEE 754 muestran que los tests están cumpliendo su función (encontrar bugs sutiles).

**Críticas constructivas:**
- Aún se introdujeron dos regresiones en DAY 142. Esto indica que el gate `make test-all` antes de push/merge no es lo suficientemente estricto o que hay call sites ocultos (posiblemente en headers o tests generados). Endurecer el CI.
- `DetectionType` enum limitado es aceptable ahora (DEBT-PROTO-DETECTION-TYPES-001), pero el mapeo string debe ser bidireccional y versionado si se expone en red.

EMECAS verde + AppArmor enforce = merge candidate razonable, pero no óptimo todavía.

### Respuestas a las Preguntas Difíciles

**P1 — fork()+execv() sin wait()**

Sí, acumularéis zombies. En un escenario ransomware persistente o flooding de detecciones (posible en prueba roja o ataque real), el proceso padre (firewall-acl-agent) generará hijos huérfanos que `init` recogerá eventualmente, pero con coste: entrada en la tabla de procesos, descriptor leaks potenciales y ruido en logs/forense.

**Recomendación fuerte:**
- Mantened `fork()+execv()` (buena separación de privilegios).
- En el worker thread del `BatchProcessor`, añadid un reaper periódico: `waitpid(-1, &status, WNOHANG)` cada 1-5 segundos (o tras cada batch). Es barato.
- Alternativa más robusta (preferida para producción): usar `systemd-run --scope --property=Delegate=yes` o un socket activation/unit transitorio para el isolate action. Esto delega la gestión del ciclo de vida a systemd (que ya maneja zombies y cgroups).
- Registrar PID + timestamp del aislamiento en etcd o log JSONL para auditabilidad.

**P2 — Tolerancia IEEE 754 1e-6**

La tolerancia actual es pragmática y funciona, pero es síntoma de deuda de diseño.

**Decisión recomendada:** Haced `threshold` `float` en `IsolateConfig` (y en JSON). El ML Detector ya trabaja con `float` confidence en la mayoría de pipelines. Tipos consistentes eliminan la raíz del problema y evitan sorpresas en otras comparaciones. `double` solo donde se necesite precisión (cálculos internos). Documentad la política de tipos numéricos en el repo (DEBT-FLOAT-CONSISTENCY-001).

**P3 — auto_isolate: true por defecto en hospitales**

**Cambiad a `false` por defecto.**

Un ventilador o bomba de infusión no puede quedar aislado por un solo pipeline sin confirmación humana en fase inicial. “Instalar y funcionar” es buena UX, pero en entornos safety-critical viola el principio fail-safe.

**Propuesta equilibrada:**
- Default: `false`.
- Durante onboarding (`argus-setup`): wizard interactivo que obliga a elegir interfaces críticas, whitelist de activos médicos (por MAC/OUI o asset tag), y confirmación explícita de auto_isolate.
- Añadir `auto_isolate_grace_period_seconds` y `dry_run_mode` inicial.
- Mantened el “instalar y funcionar” para entornos no-críticos (labs, oficinas).

Esto es coherente con estándares médicos (IEC 62304, FDA guidance on cybersecurity).

**P4 — AppArmor /tmp demasiado permisivo**

Sí, es un vector. Globbing `argus-*.nft` en `/tmp` permite que un atacante comprometido escriba otros archivos con nombres coincidentes (TOCTOU, symlinks, etc.).

**Fix inmediato:**
- Usar directorio dedicado: `/var/lib/argus/irp/` (o `/run/argus/irp/` para tmpfs).
- Permisos: `rw` solo para owner `argus:argus`, modo 0600, y `ix` solo en los binarios necesarios.
- En el perfil: `deny /tmp/**` explícito + `audit deny` para detectar intentos.
- Operación transaccional: escribir en archivo temporal con nombre predecible + `rename()` atómico.

Actualizad el perfil y `hardened-setup-apparmor` antes del merge.

**P5 — Criterio de disparo: ¿dos señales suficientes?**

En hospital: **no es suficiente** para aislamiento automático de interfaces críticas.

**Arquitectura recomendada (DEBT-IRP-MULTI-SIGNAL-001):**
1. **Nivel 1 (bajo impacto):** 1 señal (score alto + tipo específico) → alert + log + optional packet sample.
2. **Nivel 2 (aislamiento temporal):** 2 señales independientes (e.g. Sniffer Variant B + ML Detector o RAG correlation) + score ≥ 0.95 → aislamiento con timer rollback (ya tenéis).
3. **Nivel 3 (crítico):** 3 señales o confirmación humana + verificación de whitelist (activos médicos conocidos) → aislamiento + notificación inmediata al SOC + snapshot forense.

Añadir “second sensor” (e.g. NetFlow/sFlow de router upstream o eBPF en otro punto) es oro. Usar etcd para compartir estado entre sensores. Registrar la decisión completa (señales, scores, timestamp) inmutablemente.

Esto sigue el espíritu de “dos condiciones AND” que ya aplicáis, pero con escalado.

### Recomendación para DAY 144

**Opción prioritaria: A (Merge a main) + gates duros.**

- Merge `feature/variant-b-libpcap` **solo después de**:
    - Resolver P1, P3, P4 (mínimo).
    - `PROFILE=production make all` verde.
    - Un último `vagrant destroy -f && vagrant up && make test-all && make hardened-test`.

- **Inmediatamente después:** Opción B (Benchmarking A vs B). Esto es la contribución científica real del paper (arXiv 2604.04952). Medir throughput (Mpps), latencia cola, CPU, jitter y consumo memoria bajo tráfico sintético hospitalario (monitores, PACS, HIS). Publicad los datos crudos.

- Opción C (etcd HA) es P0 post-merge. Single-node etcd es aceptable para demo/PoC pero no para FEDER.

**Deuda crítica a priorizar pronto:** DEBT-ETCD-HA-QUORUM-001 + DEBT-MUTEX-ROBUST-001 + DEBT-COMPILER-WARNINGS-CLEANUP-001 (UB es inaceptable).

El proyecto muestra madurez creciente. Mantened el rigor: cada commit debe ser un paso hacia certifiable safety-critical software. Un falso positivo en quirófano sigue siendo inaceptable.

Estamos a disposición para la siguiente sesión.

*Via Appia Quality. Máxima verdad, mínima deuda.*