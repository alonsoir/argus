Soy Alonso Isidoro Román, fundador de aRGus NDR (arXiv:2604.04952),
sistema open-source C++20 de detección y respuesta a intrusiones para
infraestructura crítica.

Estado repo: branch feature/variant-b-libpcap @ e52870d5 (DAY 144)
Tag main: v0.6.0-hardened-variant-a
FEDER deadline: 22-Sep-2026 | Go/no-go: 1-Ago-2026

COMPLETADO DAY 144:
- EMECAS verde: 65/65 tests PASSED
- DEBT-IRP-SIGCHLD-001 CERRADA: SA_NOCLDWAIT, SigchldTest.NoZombiesAfterNForks PASSED
- DEBT-IRP-AUTOISO-FALSE-001 CERRADA: isolate.json única fuente de verdad,
  campo obligatorio, fallo ruidoso, parse_irp() public, 5 tests PASSED
- DEBT-IRP-BACKUP-DIR-001 CERRADA: /tmp → /run/argus/irp/, AppArmor actualizado
- DEBT-COMPILER-WARNINGS-CLEANUP-001 PARCIAL: Gate ODR production PASSED.
  3 ODR violations reales corregidas bajo -flto -Werror:
  (1) anonymous namespace en inline trees hpp
  (2) protobuf stale src/protobuf/ eliminado (40k líneas)
  (3) -UNDEBUG en targets de test
- README.md + docs/BACKLOG.md actualizados

PRIMER PASO DAY 145:
vagrant destroy -f && vagrant up && make bootstrap && make test-all

PLAN DAY 145:
1. EMECAS verde
2. PCAP relay x86 eBPF (Variant A) — make test-replay-neris
   Métricas: latencia p99, throughput, F1 bajo carga
3. PCAP relay x86 libpcap (Variant B) — make test-replay-neris con sniffer-libpcap-start
   Mismas métricas — contribución científica ADR-029
4. Si ambos PASSED: merge feature/variant-b-libpcap → main → tag v0.7.0-variant-b
5. Refactor Makefile: targets explícitos production-x86, test-replay-neris-x86-ebpf,
   test-replay-neris-x86-libpcap
6. Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores,
   no competición — paradigmas complementarios)
7. Abrir feature/adr029-variant-c-arm64 scope definido

DEUDAS P1 POST-MERGE:
- DEBT-IRP-TMPFILES-001: tmpfiles.d para /run/argus/irp/ en reboot
- DEBT-IRP-IPSET-TMP-001: ipset_wrapper.cpp aún usa /tmp
- DEBT-EMECAS-VERIFICATION-001: P2, párrafo README para devs
- DEBT-IRP-FLOAT-TYPES-001: unificar tipos score float/double

DECISIONES CONSEJO DAY 144:
- P3 multi-señal: adoptar acumulador de evidencia con decadencia exponencial
  (Qwen) — determinista, sin reentrenamiento, auditable, NIST/MITRE estándar
- P4 experimento: aRGus como cooperador de Suricata/Zeek, no sustituto
- ARM64: post-FEDER, mencionado como trabajo futuro en paper v19
- Andrés Caro Lindo: hablar este finde sobre FEDER scope

REGLAS PERMANENTES:
- REGLA EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all
- macOS: nunca sed -i sin -e '' — usar python3 << 'PYEOF' o vagrant ssh << 'SSHEOF'
- zsh intercepta ! en heredocs — siempre vagrant ssh << 'SSHEOF'
- Makefile es la única fuente de verdad
- -Werror activo — 0 warnings propios invariante permanente
- PROFILE=production all antes de cualquier merge a main (gate ODR)
- Variant A y Variant B nunca simultáneas
- isolate.json es la única fuente de verdad para auto_isolate
- assert() activo en tests: -UNDEBUG en CMakeLists de test targets