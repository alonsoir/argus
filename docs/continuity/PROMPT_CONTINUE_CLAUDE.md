## ARRANQUE DAY 191 — H-2 NÚCLEO 2 (último foco para cerrar H-2)

### ESTADO AL CERRAR DAY 190 (mergeado a main)
- PR #103 mergeado a main (395ee014). Rama feature/day188-security-debt-audit borrada (local+remota).
- main local actualizado vía pull. Árbol limpio.
- EMECAS++ 3 actos VERDE. 73/73 tests (los nuevos: #49-#52 ParseAutonomyCidrInjection, #72 test_ip_cidr_validator).

### LO QUE SE CERRÓ EN DAY 190 (no re-hacer)
- **Punto 1 / CWE-78 autonomy.whitelist_cidrs: CERRADO Y PROBADO.**
  - is_valid_ip_cidr extraído a header compartido firewall/ip_cidr_validator.hpp
    (lógica idéntica a IPSetWrapper::is_valid_ip — behavior-preserving; is_valid_ip ahora delega).
  - parse_autonomy (config_loader.cpp) valida cada CIDR ANTES de aceptar — fail-fast throw.
    parse_autonomy movido a public en config_loader.hpp (patrón parse_irp, testabilidad directa).
  - Tests de ataque verdes: ;  \n  $() → throw. Control AcceptsLegitimateCidrs → no throw.
  - nosemgrep INTERINO en autonomy_reactor (pegado al return std::system, no huérfano).
    Verificado con semgrep acotado al fichero = limpio.

### 🔴 PRIMERO MAÑANA — H-2 NÚCLEO 2 (lo único que falta para cerrar H-2)
- **Objetivo:** campo `comment` en IPSetWrapper::add_batch (ipset_wrapper.cpp).
  Hoy escapa comillas `"` pero NO rechaza `\n`. El comment se escribe en el fichero
  'ipset restore' (mini-lenguaje por líneas) → un `\n` en comment podría inyectar línea.
- **Paso 1 (MEDIR, no votar):** qué hace `ipset restore` REAL con `"` / `\n` / `\` en el
  comment, AHORA que ya no hay shell (post NÚCLEO 3). Probar el parser real, no asumir.
- **Paso 2:** RECHAZAR `\n` (no stripear — fail-fast como en is_valid_ip). Decidir `\` y `"`
  según lo que mida el paso 1.
- **Paso 3:** test de ataque (comment con `\n` → rechazo) + canario e2e si aplica.
- **Al cerrar:** AHORA SÍ marcar H-2 CERRADA en docs/BACKLOG.md (era la condición de DAY 189).

### RAMA
git checkout -b feature/day191-h2-nucleo2-comment main

### DEUDAS ABIERTAS (no perder)
- **DEBT-AUTONOMY-REACTOR-SAFEEXEC-002 (P2, POST-FEDER):** el std::system de autonomy_reactor
  sigue presente, silenciado por nosemgrep interino. Refactor a safe_exec (execv sin shell):
  IptablesExecutor function<int(const string&)> → function<int(const vector<string>&)>,
  reescribir ~10 run("iptables..."), toca StubExecutor + T1-T9 de test_autonomy_subscriber.
  Retirar el nosemgrep cuando el system() desaparezca.
- **DEBT-AUDIT-VBOXSF-IO-001 (P2):** make audit (semgrep árbol completo) se estrangula por I/O
  de vboxsf sobre /vagrant (proceso en estado D, no el hang CPU de DEBT-SEMGREP-CPP-HANG-001).
  Workaround: semgrep acotado por fichero (segundos). Mitigación: copiar a fs nativo del guest
  antes de semgrep — misma lección que kuzu_concurrency_smoke ("fs NATIVO, NUNCA /vagrant").

### RECORDATORIOS DE FLUJO (cazados en DAY 190, no repetir)
- make test-firewall = SOLO ctest, NO compila. Para recoger tests nuevos: `make firewall &&
  make test-firewall` (el && corta si el build falla → evita correr el binario viejo).
- Borrar CMakeCache.txt NO basta si el target solo hace ctest. make firewall reconfigura+compila.
- nosemgrep debe tocar la línea del finding (misma línea o inmediatamente anterior, sin comentarios
  en medio). Bloque explicativo largo va ARRIBA; la directiva PEGADA al return.
- Tools de un solo uso (.py/.sh) → .gitignore explícito (los patrones genéricos day* no cazan todo).

### CONTADORES
- FEDER: deadline 22 sep 2026. Go/no-go 1 ago 2026.
- arXiv:2604.04952 Draft v18 activo.