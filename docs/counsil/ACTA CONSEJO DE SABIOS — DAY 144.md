La vulnerabilidad de GitHub la miramos después — es probable que sea una dependencia transitiva conocida, no código nuestro. Anotada para revisar.

---

**ACTA CONSEJO DE SABIOS — DAY 144**
*07 Mayo 2026 — 04:00 a ~08:00 Extremadura*

---

**LO QUE HEMOS HECHO HOY**

DAY 144 comenzó con EMECAS verde (43/43 tests, 0 FAILED) y cerró con gate ODR completo bajo `PROFILE=production`. Tres deudas P0 pre-merge cerradas y tres violaciones ODR reales detectadas y corregidas.

**DEBT-IRP-SIGCHLD-001 — CERRADA**
`fork()+execv()` del IRP acumulaba zombies sin `wait()`. Fix: `SA_NOCLDWAIT` en `setup_signal_handlers()` — el kernel recoge hijos automáticamente. Test: `SigchldTest.NoZombiesAfterNForks` — 20 forks con `/bin/true`, 500ms de espera, cero procesos `defunct` en `/proc`. PASSED.

**DEBT-IRP-AUTOISO-FALSE-001 — CERRADA**
`auto_isolate: true` era el default en tres lugares simultáneamente (struct C++, JSON fallback, `isolate.json`). Consejo 8/8 unánime: un falso positivo sobre un ventilador mecánico es un evento clínico, no un bug de software. Decisión arquitectural: `isolate.json` es la **única fuente de verdad**. `auto_isolate` es campo obligatorio — si falta, el arranque falla ruidosamente. No hay fallback silencioso. `parse_irp()` movida a `public` para testabilidad directa. 5 tests nuevos — todos PASSED. `provision.sh` falla con `exit 1` si el fichero fuente no existe.

**DEBT-IRP-BACKUP-DIR-001 — CERRADA**
Artefactos nftables del IRP vivían en `/tmp` — world-writable, sin permisos, sin AppArmor. Migrados a `/run/argus/irp/` (tmpfs, volátil) con permisos `0700 argus:argus`. AppArmor actualizado. `provision.sh` crea ambos directorios. Dry-run verificado: `backup=/run/argus/irp/argus-backup-*.nft`. Deudas derivadas registradas: `DEBT-IRP-TMPFILES-001` (tmpfiles.d para reboot) y `DEBT-IRP-IPSET-TMP-001` (ipset_wrapper.cpp aún usa `/tmp`).

**DEBT-COMPILER-WARNINGS-CLEANUP-001 — PARCIALMENTE CERRADA**
Gate `make PROFILE=production all` detectó cuatro categorías de ODR violations reales bajo `-flto -Werror`:

1. `tree_0[]`...`tree_99[]` con tipos distintos (`InternalNode` vs `TrafficNode`) visibles cross-módulo. Fix: anonymous namespace en ambos headers.
2. `contract_validator.h` incluía copia stale de protobuf (`src/protobuf/`, noviembre 2025) en lugar del unificado. Fix: path corregido + `src/protobuf/` eliminado (40k líneas de código generado borradas del repo).
3. Variables usadas solo en `assert()` aparecían como "no usadas" bajo `-DNDEBUG`. Fix: `-UNDEBUG` en targets de test de rag-ingester, rag y etcd-server — `assert()` siempre activo en tests independientemente del perfil.

**Estado del repo al cierre:**
```
feature/variant-b-libpcap — 3 commits nuevos
a44b7ab3 — DEBT-IRP-SIGCHLD-001 + AUTOISO-FALSE-001
646713e7 — DEBT-IRP-BACKUP-DIR-001  
e52870d5 — DEBT-COMPILER-WARNINGS-CLEANUP-001
65/65 tests verdes
Gate ODR: ✅ ALL COMPONENTS BUILT [production]
```

---

**LO QUE HAREMOS MAÑANA (DAY 145)**

1. EMECAS ritual obligatorio
2. PCAP relay x86 eBPF (Variant A) — baseline documentado F1=0.9985
3. PCAP relay x86 libpcap (Variant B) — métricas nuevas, contribución científica ADR-029
4. Si ambos pasan: `git merge --no-ff feature/variant-b-libpcap → main` → `tag v0.7.0-variant-b`
5. Refactor Makefile: targets explícitos por arquitectura (`production-x86`, `test-replay-neris-x86-ebpf`, `test-replay-neris-x86-libpcap`)
6. Abrir `feature/adr029-variant-c-arm64` con scope definido

---

**PREGUNTAS PARA EL CONSEJO**

**P1 — Diseño experimento ADR-029 Variant A vs B**
El PCAP relay sobre CTU-13 Neris nos dará métricas comparativas entre eBPF (Variant A) y libpcap (Variant B) en x86. Las hipótesis son: Variant B tiene menor overhead de kernel pero mayor latencia de userspace; Variant A tiene acceso más temprano al paquete pero mayor complejidad de provisioning. ¿Qué métricas consideráis más relevantes para la contribución científica al paper arXiv v19? ¿Throughput máximo (pps), latencia p99, tasa de detección bajo carga, o consumo de recursos (CPU/RAM)?

**P2 — Scope ARM64 Variant C**
La infraestructura hardened ARM64 existe (`vagrant/hardened-arm64/`) pero la cadena de build cross-compilation no. Para FEDER (deadline 22 septiembre), ¿consideráis que ARM64 libpcap es un diferenciador científico suficiente para justificar el trabajo de la feature completa (cross-compilation toolchain, CMakeLists aarch64, nuevo Vagrantfile ARM64 real)? ¿O es suficiente con x86 eBPF + x86 libpcap para el paper v19?

**P3 — Probabilidad conjunta multi-señal (DEBT-IRP-PROB-CONJUNTA-001)**
El IRP actual decide aislamiento sobre una única señal (score + tipo de detección). La deuda registrada propone una función de probabilidad conjunta multi-señal con pesos auditables. ¿Cuál es el modelo matemático más adecuado para combinar señales heterogéneas (score ML, tipo de evento, frecuencia, contexto temporal) en una decisión de aislamiento auditable y publicable? ¿Naive Bayes, regresión logística, o algo más sofisticado?

**P4 — Experimento post-merge: aRGus vs Suricata vs Zeek**
Acordado en DAY 143. El diseño propuesto usa CTU-13 Neris como baseline y MITRE ATT&CK como tráfico adversarial sin firma conocida. ¿Cuál es el protocolo experimental más riguroso para garantizar que la comparación es científicamente válida y reproducible? ¿Cómo aislamos el efecto de las reglas ET de Suricata del detector ML de aRGus en los resultados?

---

Listo para enviar al Consejo. Descansa, Alonso.