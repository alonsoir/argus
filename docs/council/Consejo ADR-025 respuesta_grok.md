**REVISOR: Grok (xAI) — cs.CR / sistemas distribuidos**  
**FECHA: 2 de abril de 2026**

**VEREDICTO GLOBAL ADR-024 (Plugin Integrity Verification):** **ACEPTADO CON CONDICIONES FUERTES**  
El diseño es sólido, reutiliza infraestructura existente (Ed25519 + libsodium) y cierra correctamente la ventana TOCTOU más obvia. Es un paso lógico y necesario tras el aislamiento criptográfico de ADR-023. Sin embargo, la implementación debe incorporar mitigaciones explícitas para los vectores más viables antes de mergear a `feature/plugin-crypto`.

### HALLAZGOS CRÍTICOS (deben resolverse antes de implementación)

- **Firma offline + clave pública solo en host** (Vector 1): Obligatorio. La clave privada **nunca** debe estar en producción. `provision.sh` debe firmar en build/CI (offline o en máquina dedicada) y copiar **solo** la clave pública Ed25519 al host. Documentar esto como requisito de despliegue.
- **Validación canónica de paths** (Vector 4): Imprescindible. Antes de abrir cualquier fd, usar `std::filesystem::canonical()` + comprobar prefijo estricto (`/usr/lib/ml-defender/plugins/`). Rechazar cualquier path que escape (symlinks, `..`, etc.).
- **Disciplina estricta del file descriptor** (Vector 5): Mantener el fd abierto desde `open()` hasta después de `dlopen("/proc/self/fd/N")`. No cerrarlo en medio. Si se cierra prematuramente, se reabre la ventana de TOCTOU.
- **Fail-closed consistente**: Verificación fallida → el plugin **no se carga** y se registra warning claro (incluyendo nombre del plugin y motivo). El componente continúa (como se propone), pero en modo degradado. Coherente con D1 de ADR-023.

### HALLAZGOS RECOMENDADOS (fuertes, implementar en esta PHASE)

- **Añadir verificación SHA-256 explícita** además de la firma Ed25519. Aunque Ed25519 ya cubre integridad (firma sobre el mensaje), un hash rápido adicional ayuda en logging/auditoría y detecta corrupción accidental. Usar `crypto_hash_sha256` de libsodium.
- **JSON config**: El campo `"signature"` debe ser obligatorio cuando `"active": true`. Añadir validación de schema estricta en carga de config.
- **Hardening del launcher**: En el script/systemd que arranca el daemon, limpiar entorno (`unset LD_PRELOAD LD_LIBRARY_PATH`) y considerar `seccomp` básico (bloquear `setenv`, `prctl` para ciertas capabilities). Diferible a imagen Debian hardened, pero fácil de añadir ahora.
- **Documentar threat model**: En el ADR, incluir una sección breve con los vectores principales y su mitigación (ver abajo).

### VECTORES DE ATAQUE — ANÁLISIS Y MITIGACIÓN (ordenados por viabilidad real en el contexto)

1. **Manipulación del JSON config** (alta viabilidad si config es writable)  
   Atacante cambia `path` o `signature` a ficheros controlados.  
   **Mitigable en diseño ahora**: Validación canónica + prefix check. Obligatorio.

2. **Sustitución de .so + .sig cuando el directorio es writable** (alta si DAC débil)  
   Atacante con acceso al filesystem reemplaza ambos ficheros (necesita clave privada o firma falsa).  
   **Mitigable parcialmente ahora**: DAC/AppArmor restringiendo escritura solo al usuario de deploy. Recomendado: perfil AppArmor simple para el daemon (solo lectura en /usr/lib/ml-defender/plugins/).

3. **Compromiso de clave privada** (media-alta si mal gestionada)  
   **Mitigable en diseño ahora**: Firma offline, solo pubkey en host. Clave privada en CI/build server.

4. **Race en fd /proc/self/fd** (media)  
   **Mitigable en diseño ahora**: Mantener fd abierto hasta después de dlopen. Buena práctica confirmada en Linux.

5. **Ataque vía LD_PRELOAD / LD_LIBRARY_PATH o entorno** (media)  
   Intercepción del loader.  
   **Mitigable ahora**: Limpiar entorno en launcher + seccomp básico. Recomendado.

6. **Plugin firmado pero malicioso** (alta en práctica)  
   Pasa verificación pero hace daño (ej. modifica MessageContext, exfiltra datos).  
   **Mitigable parcialmente ahora**: Usar los invariants y snapshot D8 de ADR-023. Ideal futuro: cada plugin en proceso hijo con seccomp/AppArmor separado (overkill para PHASE 2, diferir).

7. **Ataque al proceso de provision.sh / supply chain**  
   **Diferible**: Fuera de scope inmediato, pero documentar como riesgo (recomendar reproducible builds + pinning de commits).

8. **Compromiso de libsodium o binario del daemon**  
   Verificación falsa.  
   **Diferible al hardening Debian**: Usar IMA (Integrity Measurement Architecture) o AppArmor/SELinux para proteger el propio binario y libs.

9. **Ataques avanzados al dynamic linker** (baja en Debian Bookworm hardened)  
   **Diferible**: Seccomp + AppArmor en la imagen base.

**Vectores fuera de scope ahora**: Kernel exploits, compromisos físicos del hardware, ataques a etcd, etc.

### Conclusiones y recomendación al árbitro (Alonso)

Este ADR-025 complementa perfectamente ADR-023 y eleva el plugin loader de “fase 1 sin crypto” a algo defendible en entornos sensibles (hospitales, ayuntamientos).

**Acciones mínimas antes de merge**:
- Incorporar las mitigaciones críticas (firma offline, path canonical, fd discipline).
- Añadir sección “Threat Model y Mitigaciones” en el ADR con la tabla resumida arriba.
- Actualizar `provision.sh` para generar solo pubkey en host.
- Probar el flujo completo: firma offline → deploy → verificación exitosa + fallo intencionado.

Con estas condiciones, **el ADR queda listo para implementación**. Es un excelente ejemplo de defensa en profundidad minimalista para hardware resource-constrained.

**Posición de minoría (si aplica)**:  
Hacer la verificación **fail-closed total** en producción (el componente se detiene con `std::terminate()` si un plugin crítico falla verificación). La propuesta actual (continuar sin el plugin) es pragmática, pero en componentes como `firewall-acl-agent` o `rag-security` podría ser demasiado permisiva. Registrar como opción configurable.

¿Quieres que te prepare el texto completo actualizado del ADR-025 con la sección de threat model incluida, o código esqueleto para la verificación en `plugin_loader.cpp` (con libsodium + fd handling)?

Estoy listo para la siguiente ronda del Consejo cuando digas. ¡Buen empuje en el plugin-crypto!