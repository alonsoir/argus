## CIERRE DAY 189 (07:03) — H-2 NÚCLEO 1+3 cerrados; audit destapó foco nuevo

### COMPLETADO HOY (verificado)
- **H-2 NÚCLEO 1 (set_name en add_batch/delete_batch): CERRADO.**
  - Validador `is_valid_set_name` extraído a header standalone `set_name_validator.hpp`
    (allowlist [A-Za-z0-9_-], ≤IPSET_MAXNAMELEN-1=31, rechaza '-' inicial CWE-88 + \n/control).
  - config_loader REUSA el validador (inline retirado, sin duplicación DRY).
  - Wrapper llama al guard en add/delete ANTES de set_exists_unlocked (orden verificado).
  - Enum INVALID_SET_NAME añadido y usado.
  - Tests: unit #42-#48 (config + standalone, 2 ejes ortogonales) VERDES.
  - Canario e2e #70 (set_name "\nadd evil" + "-X", aserta sobre efecto) VERDE con root.
- **H-2 NÚCLEO 3 (retirar shell de 11 métodos + validación universal): CERRADO.**
  - 12 focos shell (system/popen/execute_command) → safe_exec* (sin shell). grep = 0 focos reales.
  - execute_command eliminada.
  - Validación de entrada en CADA superficie: is_valid_set_name en create/destroy/flush/
    rename/swap/test/get_stats/list_entries; validate_filepath en save/restore.
  - kIpsetBin="/sbin/ipset" (execv NO usa PATH — ruta absoluta).
  - Canarios e2e #69+#70 VERDES tras conversión = comportamiento preservado.
  - test-firewall 68/68. semgrep acotado a ipset_wrapper.cpp: LIMPIO.

### 🔴 DESCUBIERTO HOY POR EL AUDIT — VIVO, SIN MITIGAR (PRIMERO MAÑANA)
- **DEBT-AUTONOMY-REACTOR-CWE78-001 — autonomy_reactor.cpp:11**
  - `default_executor`: `std::system(cmd.c_str())` con cmd construido por concatenación.
  - cmd línea 87: `"iptables -A "+ch+" -s "+cidr+...` donde cidr ∈ whitelist_cidrs_.
  - whitelist_cidrs viene de firewall.json["autonomy"]["whitelist_cidrs"], parseado por
    parse_autonomy (config_loader.cpp:493) SIN validar contenido (solo existe/array/no-vacío).
  - => CWE-78 VIVO: CIDR malicioso en JSON ("1.2.3.0/24; iptables -F") → system() root.
  - MISMA clase que H-2-ipset, en otro punto. El audit hizo su trabajo.
  - ESTADO: no tocado hoy (mismo estado que al empezar — ni introducido ni cerrado).

### PLAN DAY 190 (en orden, mitigación PRIMERO)
1. **MITIGAR CWE-78 (lo único vivo):** en parse_autonomy, validar cada CIDR ANTES de
   aceptarlo. Función libre is_valid_ip_cidr (extraer de IPSetWrapper::is_valid_ip, hoy
   es método — patrón idéntico a set_name_validator). Fail-fast: throw si CIDR inválido.
  + TEST DE ATAQUE: cargar JSON con CIDR malicioso → verificar throw.
2. **Refactor a safe_exec (defensa en profundidad):** IptablesExecutor de
   function<int(const string&)> → function<int(const vector<string>&)>. Reescribir los
   ~10 run("iptables...") a tokens + default_executor a safe_exec({...}). Toca mock de
   tests #66/#67/#68 — su propia rama, su propio EMECAS.
3. **NÚCLEO 2 (comment en add_batch):** medir qué hace `ipset restore` con `"`/`\n`/`\`
   en comment (parser real, ya SIN shell tras NÚCLEO 3). Rechazar \n (no stripear).
4. **make audit completo VERDE:** tras mitigación CIDR, semgrep aún marca línea 11 (ve el
   system(), no la validación en otro fichero). Opciones: nosemgrep JUSTIFICADO con ref a
   deuda + test de ataque como prueba (legítimo: falso-positivo-tras-mitigación), O cerrar
   el refactor safe_exec (mata el system() del todo, mejor). Decisión mañana.
5. **Canario cobertura 11 métodos:** un test parametrizado e2e que ataque
   destroy/rename/swap/etc con nombre malicioso (hoy solo add/delete tienen canario).

### ESTADO AUDIT (honesto)
- ipset_wrapper.cpp (H-2): LIMPIO en semgrep.
- H-1 Cypher (cypher_builder, DAY 188): cerrado.
- **make audit COMPLETO: NO verde.** autonomy_reactor.cpp:11 dispara (blocking).
  NO afirmar "audit verde" hasta resolver punto 1+4. Evidencia actual de H-1/H-2 =
  audit ACOTADO a ipset_wrapper.cpp + ml-detector/src, no el completo.
- DEBT-AUDIT-SEMGREP-PERF: descartado — el "timeout" de autonomy_reactor era HIT real
  (exit≠0 por --error), no backtracking. semgrep termina rápido, el finding es legítimo.

### ESTADO GIT (decidir antes de cerrar terminal)
- Rama feature/day188-security-debt-audit con NÚCLEO 1+3 sin commitear aún.
- NÚCLEO 1+3 son cierre coherente y testeado → COMMITEAR hoy (no dejar working tree sucio
  toda la noche). Mensaje: "DAY189 H-2 NÚCLEO 1+3: set_name validation + shell removal en
  ipset_wrapper (safe_exec, 0 focos shell, canarios e2e verdes)".
- autonomy_reactor NO entra en este commit (no tocado). Su mitigación = commit/rama propia mañana.
- NÚCLEO 2 pendiente → NO marcar H-2 CERRADA en BACKLOG todavía (falta comment + audit verde).
- Pushear rama como backup esta noche (estaba pendiente desde arranque DAY 188).