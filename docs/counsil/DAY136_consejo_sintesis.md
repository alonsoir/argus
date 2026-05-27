# Síntesis Consejo de Sabios — DAY 136
# aRGus NDR — v0.6.0-hardened-variant-a MERGEADO
# Fecha: 2026-04-29

## Contexto
Primer Consejo post-merge de feature/adr030-variant-a → main.
EMECAS PASSED completo. Tag v0.6.0-hardened-variant-a publicado.

## Convergencias (8/8)

### Q1 — Riesgos antes de demo FEDER (1 agosto)
- **DEBT-IRP-NFTABLES-001** — argus-network-isolate no implementado.
  Si se dispara el IRP en demo, el sistema llama a un binario inexistente.
  Fail catastrófico ante evaluadores. Prioridad máxima pre-FEDER.
- **Seeds via Mac laptop** — inaceptable en producción real.
  Todos coinciden: Jenkins (o equivalente CI/CD) debe asumir
  la distribución de seeds. El portátil del founder no puede ser
  parte de la cadena criptográfica de producción.
- **Material criptográfico sin solución robusta** — seeds, keypairs Ed25519.
  Necesita propuesta open source implementada para la demo.
  Candidatos: HashiCorp Vault (open source), YubiKey, TPM 2.0.
- **Compiler warnings** — TODOS los compañeros los quieren resueltos YA.
  No les gustan ni un pelo. Argumento: en infraestructura crítica los
  warnings son puertas de entrada a vulnerabilidades no detectadas.
  Bloqueantes para cualquier proceso de certificación o auditoría formal.

### Q2 — Delta XDP vs libpcap (contribución científica)
- **Punto de captura**: XDP antes del stack de red vs libpcap después.
  Diferencia medible en latencia y paquetes perdidos bajo carga.
- **CPU por paquete**: eBPF maps vs copy-to-userspace. Cuantificable.
- **Hardware mínimo**: el dato más relevante para el paper FEDER —
  F1≥0.9985 con 0 paquetes perdidos en cada variante, con qué hardware mínimo.
- **Temperatura ARM**: gate ≤75°C sin ventilador (armarios hospitalarios 24/7).
  DeepSeek: verificar driver NIC antes de comprar x86.

### Q3 — Deuda más preocupante para infraestructura crítica
- **DEBT-SEEDS-BACKUP-001** — pérdida del nodo = pérdida del seed = pipeline
  que no arranca. En hospital sin equipo técnico, nadie sabe regenerarlos.
  Protocolo documentado simple, ejecutable sin conocimientos de criptografía.
- **DEBT-COMPILER-WARNINGS-001** — todos los modelos coinciden en que los
  warnings ODR/LTO/signed-unsigned son el mayor riesgo silencioso actual.
  En C++ un ODR violation es UB. UB en producción hospitalaria = inaceptable.

## Divergencias

- **Timing de Jenkins**: Claude y Grok proponen implementar el mecanismo
  antes de la demo aunque no esté en CI "real". ChatGPT y Mistral dicen
  que basta con documentar el protocolo para FEDER y posponer.
  **Decisión founder pendiente.**

- **HashiCorp Vault vs YubiKey vs TPM**: DeepSeek prefiere TPM 2.0
  (hardware presente en servers hospitalarios modernos). Kimi prefiere
  Vault por ser más portable. Claude propone Vault para demo FEDER
  (más fácil de instalar en Vagrant) + TPM como objetivo final.
  **Decisión founder pendiente.**

## Nuevas deudas técnicas identificadas

| ID | Descripción | Severidad | Target |
|----|-------------|-----------|--------|
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | Jenkins/CI para distribución de seeds (quitar Mac del chain) | 🔴 Alta | pre-FEDER |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | Propuesta + implementación almacenamiento material criptográfico open source | 🔴 Alta | pre-FEDER demo |
| DEBT-COMPILER-WARNINGS-CLEANUP-001 | Resolver TODOS los warnings de compilación (ODR, LTO, signed/unsigned, deprecated) | 🔴 Alta | DAY 137+ |

## Decisiones vinculantes

D1: DEBT-IRP-NFTABLES-001 es P0 pre-FEDER — antes de cualquier demo.
D2: Jenkins seed distribution — crear mecanismo aunque sea Vagrant-local primero.
D3: Propuesta material criptográfico — HashiCorp Vault para demo FEDER.
D4: Compiler warnings — rama dedicada `fix/compiler-warnings-001` en DAY 137.
D5: feature/variant-b-libpcap — DAY 137 PASO 5.

## Citas del Consejo

"Los warnings ODR en C++ son bombas de reloj. En infraestructura crítica,
el comportamiento indefinido no es hipotético — es inevitable." — Grok

"Un hospital no tiene un DevOps team. El protocolo de backup de seeds
debe ser ejecutable por el administrador de sistemas que también gestiona
las impresoras." — Kimi

"Jenkins no es lujo. Es el mínimo de profesionalismo para cualquier sistema
que procese datos de pacientes." — ChatGPT

"Vault open source + Vagrant = demo reproducible sin hardware especial.
TPM es el objetivo, Vault es el camino." — Claude
