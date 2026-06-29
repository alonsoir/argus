MODELO: ChatGPT

P1: ACEPTO weakly_canonical
Motivo: es la única opción estándar en C++20 que permite resolver paths no existentes (caso escritura) manteniendo normalización y resolución de symlinks. `canonical` rompería el flujo legítimo.  
Condición implícita: el chequeo de prefijo debe hacerse sobre path normalizado y consistente (ver observaciones).

P2: ACEPTO granularidad por componente
Motivo: reduce blast radius en caso de bypass. Especialmente crítico en `seed-client`, donde separar `/etc/ml-defender/keys/` evita que un fallo en otro componente permita acceso indirecto a material criptográfico. El coste de mantenimiento es bajo comparado con el beneficio en aislamiento.

P3: MISMO estándar para contrib/tools
Motivo: coherencia operativa y disciplina de código. Aunque el riesgo es bajo, relajar aquí introduce divergencia y deuda futura. El coste de aplicar `safe_path` es trivial y elimina una clase entera de errores también en tooling.

P4: ACEPTO FP — no modificar código
Motivo: con `read()` acotado a `BUF_SIZE = 4096`, la suma `buf + n` permanece dentro de límites de memoria válidos bajo semántica POSIX. No se observa vector de explotación realista sin corrupción previa de memoria. Documentar es suficiente.

OBSERVACIONES ADICIONALES:

1. **Comparación de prefijos (crítico):**  
   El uso de `canonical.rfind(allowed_prefix, 0) == 0` es correcto en intención pero **frágil ante falsos positivos de prefijo**.  
   Ejemplo:  
   `/etc/ml-defender-evil/` pasaría el check contra `/etc/ml-defender/` si no se normaliza correctamente el separador final.

   Recomendación mínima:
  - Normalizar ambos como `std::filesystem::path`
  - Comparar por componentes (`std::mismatch` o iteradores de path), no por string
  - Asegurar trailing slash semántico

2. **TOCTOU (Time-of-check vs time-of-use):**  
   Existe una ventana entre `resolve()` y `ifstream`. En entornos hostiles con symlinks mutables podría explotarse.  
   Mitigación (si se quiere endurecer más adelante, no bloqueante):
  - Abrir con flags tipo `O_NOFOLLOW` (POSIX) vía `open()` + `fdopen`
  - O revalidar tras apertura (más complejo)

3. **Paths relativos y vacíos:**  
   Confirmar rechazo explícito de:
  - `""`
  - `"."`, `"./"`
  - paths relativos sin raíz clara

4. **Unicode / normalización:**  
   No crítico en Linux típico, pero si el sistema evoluciona a entornos mixtos, considerar normalización Unicode (NFC/NFD) para evitar bypass sutiles.

5. **F17 fix correcto:**  
   El cast a `int64_t` elimina el riesgo real. No se requiere más acción.

VEREDICTO GLOBAL: SÍ — ADR sólido, merge recomendado tras ajuste del check de prefijo por componentes.

MODELO: ChatGPT

P1: ACEPTO weakly_canonical
Motivo: es la opción correcta en este contexto. Permite resolver symlinks y normalizar paths sin requerir existencia previa, lo cual es imprescindible para paths de escritura. `canonical` introduciría fallos falsos en flujos legítimos.

P2: ACEPTO granularidad por componente
Motivo: reduce superficie de impacto en caso de bypass. La separación de `/etc/ml-defender/keys/` es especialmente crítica para aislar material criptográfico. El incremento de complejidad operativa es bajo frente al beneficio en contención.

P3: MISMO estándar para contrib/tools
Motivo: coherencia, reducción de deuda futura y prevención de errores por copia/pegado. El coste es prácticamente nulo y evita divergencias en prácticas de seguridad dentro del equipo.

P4: ACEPTO FP — no modificar código
Motivo: el valor de `n` está acotado por `read()` con `BUF_SIZE = 4096`. No existe vector de overflow realista sin corrupción previa. Documentar es suficiente.

OBSERVACIONES ADICIONALES:

1. CRÍTICO — Comparación de prefijo vulnerable a bypass por string:
   El uso de `canonical.rfind(allowed_prefix, 0)` es insuficiente.
   Caso:
   allowed_prefix = "/etc/ml-defender/"
   path = "/etc/ml-defender-evil/file"
   → pasa el check.

   Requisito para merge:
   - Comparar usando `std::filesystem::path`
   - Validar por componentes (no string)
   - Asegurar frontera de directorio real

2. CRÍTICO — TOCTOU (time-of-check vs time-of-use):
   Existe ventana entre `resolve()` y `ifstream`.
   Riesgo: swap de symlink tras validación.

   No bloqueante para este ADR, pero:
   - Documentar explícitamente en ADR
   - Plan futuro: `open(..., O_NOFOLLOW)` + `fdopen` o equivalente

3. Validación de inputs:
   Añadir rechazo explícito de:
   - path vacío
   - paths relativos ambiguos
   - prefijos no canónicos

4. resolve_writable incompleto:
   Solo comprueba existencia del directorio padre, no permisos reales.
   Mejora recomendada:
   - comprobar permisos de escritura (best-effort)

5. F17:
   Fix correcto, suficiente.

VEREDICTO GLOBAL: SÍ, CON CONDICIÓN BLOQUEANTE
→ Corregir la validación de prefijo (comparación por componentes) antes del merge.

