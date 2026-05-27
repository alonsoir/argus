## DeepSeek — Retroalimentación DAY 97

Excelente trabajo. La implementación de `CryptoTransport` con HKDF-SHA256 nativo vía libsodium 1.0.19 cierra el círculo que comenzaste con `seed-client`. Las decisiones técnicas son sólidas y las incidencias detectadas (API de libsodium, reinstalación de ZeroMQ) se resolvieron de forma pragmática y documentada.

---

### Valoración general

- **API nativa vs. implementación manual:** Correcto. Usar `crypto_kdf_hkdf_sha256_*` en lugar de reimplementar RFC 5869 con HMAC evita errores sutiles y mantiene la auditoría más simple.
- **Separación TX/RX:** Decisión correcta. Claves distintas por dirección eliminan la posibilidad de reutilización de nonce entre flujos.
- **Nonce monotónico atómico:** Bien. La combinación de `uint64_t` con un prefijo fijo de 32 bits garantiza unicidad en los límites de la práctica (2⁶⁴ mensajes). El overflow explícito es preferible a un wrap silencioso.
- **Tests exhaustivos:** 10 tests específicos cubren casos límite (vacío, MAC failure, move, etc.). El hecho de que incluyan validación de wire format y no-reutilización de clave entre contextos distintos es un nivel de detalle que muchos proyectos omiten.

---

### Respuesta a las preguntas del Consejo

#### P1 — Contextos HKDF y forward secrecy

**Recomendación:** Mantener el contexto estático por sesión (`"ml-defender:{component}:v1:{tx|rx}"`) **sin** añadir timestamp o session_id en esta fase.

**Razonamiento:**
- El objetivo del contexto es **separar dominios de derivación**, no proporcionar forward secrecy por sí mismo. La separación entre componentes y entre direcciones ya está garantizada.
- Añadir un identificador efímero (timestamp, session nonce) requeriría que ambos extremos compartieran ese identificador de forma segura antes de derivar la clave, lo que reintroduce el problema de la negociación que `seed-client` precisamente elimina.
- La forward secrecy en este modelo se logra mediante **rotación de seeds**. Cuando se reprovisiona el seed (cada N meses o tras incidente), la clave derivada cambia completamente. No hay necesidad de añadir complejidad adicional en la derivación por sesión.
- Si más adelante se quiere soportar sesiones efímeras con claves de corta duración, se puede extender el protocolo de intercambio (ej. ECDH) sin tocar la base HKDF actual. Pero eso es para una fase posterior (post-PHASE 2).

**Decisión:** Aceptar contexto estático. Documentar que la rotación de seeds es el mecanismo de forward secrecy.

---

#### P2 — Migración CryptoManager → CryptoTransport

**Recomendación:** **Big-bang controlado** (migración simultánea de los 6 componentes) pero con flag de compatibilidad transitoria.

**Razonamiento:**
- `CryptoManager` usa el seed directamente como clave (USO INCORRECTO documentado). Mantener ambos sistemas en paralelo incrementa el riesgo de que algún componente quede accidentalmente usando el antiguo, creando una mezcla de esquemas de cifrado que será muy difícil de depurar.
- Dado que la comunicación entre componentes es simétrica (todos necesitan entenderse), migrar uno sin los otros rompe la comunicación. No hay una forma incremental que evite una ventana de indisponibilidad.
- Sin embargo, se puede implementar un **flag de compatibilidad** en `CryptoTransport` que, durante la migración, acepte mensajes cifrados con el formato antiguo (si se detecta por algún prefijo en el wire format) y los descifre con la clave antigua. Eso permite un despliegue azul-verde o una transición controlada donde los componentes antiguos y nuevos coexistan brevemente.
- Pero el esfuerzo de implementar ese modo de compatibilidad puede ser mayor que el coste de una parada corta coordinada. Dado que el target son entornos con baja tolerancia a fallos pero con ventanas de mantenimiento planificables (hospitales, escuelas), un corte planificado de 5-10 minutos es aceptable.

**Decisión:** Migración **big-bang** con plan de mantenimiento. Documentar claramente en el changelog que DAY 98 requiere reinicio completo de la pipeline.

---

#### P3 — mlock() en seed_client.cpp (DEBT-CRYPTO-003a)

**Recomendación:** **Error fatal con mensaje claro** y posibilidad de override via variable de entorno.

**Razonamiento:**
- El seed en disco es material base sensible. Si el sistema operativo lo swapea, la protección de memoria se pierde. En entornos con swap, un atacante con acceso físico o con capacidad de volcar memoria podría recuperarlo.
- Sin embargo, en hardware muy limitado (ej. N100 con 4GB RAM), `mlock()` puede fallar porque la región solicitada excede el límite de memoria bloqueable (RLIMIT_MEMLOCK). En esos casos, un error fatal impediría arrancar la pipeline.
- **Solución equilibrada:** Intentar `mlock()`. Si falla con `ENOMEM`, loguear un error **crítico** y abortar **a menos** que se haya definido explícitamente una variable de entorno `MLD_ALLOW_SWAP=1`. Esto permite al operador en hardware muy limitado asumir el riesgo conscientemente, mientras que en despliegues normales el sistema se niega a arrancar sin protección.
- Además, en la fase de `provision.sh` se puede verificar el límite y sugerir aumentarlo vía `ulimit -l` o añadir una entrada en `/etc/security/limits.conf` para el usuario que ejecuta los componentes.

**Decisión:** Error fatal + variable de escape documentada.

---

#### P4 — Tests de integración E2E

**Recomendación:** Target separado `make test-integ` (no ejecutado por `ctest` normal).

**Razonamiento:**
- Los tests de integración E2E requieren `seed.bin` real en `/etc/ml-defender/` con permisos 0600, y probablemente dependen de tener los 6 componentes corriendo con configuraciones específicas.
- Ejecutarlos como parte del `ctest` normal significaría que cualquier desarrollador que clone el repo y ejecute `make test` sin provisionar primero obtendría fallos (y además podría intentar escribir en `/etc` si no se previene). Eso es una mala experiencia de desarrollo.
- Separarlos en `make test-integ` (que a su vez puede invocar `provision.sh --check` y mostrar instrucciones) mantiene la CI ligera para cambios en el código, y permite que quien quiera validar el stack completo lo haga de forma explícita.

**Decisión:** Target separado. En CI, se puede ejecutar `test-integ` en un job específico tras el provisionamiento.

---

### Observaciones adicionales

1. **Reinstalación de ZeroMQ tras compilar libsodium:**  
   Buena captura. La dependencia transitiva de `libzmq5` sobre `libsodium23` en Debian es un detalle que muchos equipos descubren en producción. Tu script lo maneja explícitamente. Asegúrate de que la reinstalación de ZeroMQ también incluya los paquetes de desarrollo (`libzmq3-dev`, `cppzmq-dev`) si el sistema los necesita.

2. **Verificación de entropía con `haveged`:**  
   Correcto para entornos virtualizados o embebidos sin fuente de entropía suficiente. Sin embargo, `haveged` es un generador pseudoaleatorio basado en HAVEGE, no un RNG criptográfico certificado. Es aceptable para acelerar la recolección de entropía durante el arranque, pero la recomendación para producción es tener un RNG de hardware (o `rng-tools` con fuente de hardware). Documenta que `haveged` es una ayuda para desarrollo/entornos limitados, no una solución final.

3. **SHA-256 del tarball de libsodium:**  
   Excelente práctica. Incluir el hash en el script protege contra descargas corruptas o ataques a la cadena de suministro durante la compilación.

4. **ADR-020 (cifrado siempre obligatorio):**  
   Decisión acertada. Simplifica el modelo de amenaza y elimina una fuente de errores de configuración. En entornos donde el rendimiento es crítico, el overhead de ChaCha20-Poly1305 en CPU moderna es despreciable comparado con el coste de una brecha.

5. **Próximos pasos (DAY 98):**  
   La migración de los 6 componentes requerirá tocar muchos ficheros de configuración y código. Asegúrate de tener un plan de rollback: poder volver a una versión con `CryptoManager` en caso de que surja algún problema imprevisto. Un tag de Git antes de la migración es el mínimo.

---

### Cierre

El trabajo de DAY 97 es de una calidad que refleja madurez de ingeniería. Las decisiones técnicas son correctas, las incidencias se resolvieron con criterio y la documentación acompaña. El proyecto avanza con paso firme.

Estoy a disposición para revisar la migración de DAY 98 cuando esté lista.

— DeepSeek, miembro del Consejo de Sabios