## RESPUESTA DEL CONSEJO DE SABIOS — DAY 134

**Acta de deliberación y guía para el procedimiento EMECAS hardened**  
**Fecha:** 28 abril 2026 (DAY 134)  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Destinatario:** Alonso Isidoro Román — enhorabuena por el cumpleaños y por el extraordinario progreso del DAY 134.

---

### Felicitación y valoración general

El Consejo celebra la **primera ejecución completa** del pipeline hardened con `check-prod-all PASSED`. Los 15 problemas resueltos demuestran la madurez del enfoque TDH (Test-Driven Hardening). La tabla de fuzzing en §6.8 del paper (2.4M runs, 0 crashes) es un dato publicable de alta calidad. Los dos nuevos ADRs (040 y 041) elevan el rigor científico del proyecto.

Ahora respondemos a las cinco preguntas con precisión quirúrgica.

---

### Pregunta 1 — Atomicidad del target `make hardened-full`

**Recomendación:**  
✅ **Fail‑fast con mecanismo de checkpoint explícito (no automático).**  
Es decir: el target `hardened-full` ejecuta cada paso de forma secuencial y se detiene en el primer error (`set -e`). No hay reanudación automática. Pero se proporciona un segundo target `hardened-continue` que reanuda desde el último paso exitoso, basado en la existencia de ficheros marcadores (`.step_compiled`, `.step_signed`, `.step_deployed`, etc.).

**Justificación técnica (reproducibilidad):**
- **Fail‑fast** garantiza que cualquier error —por pequeño que sea— invalida la ejecución completa. Esto es esencial para la **reproducibilidad científica**: si un paso falla, no se puede afirmar que el entorno final es idéntico al de otra ejecución.
- Los **checkpoints manuales** (no automáticos) permiten ahorrar tiempo durante el desarrollo: un fallo en `check-prod-falco` no obliga a recompilar 30 minutos. Pero la **receta oficial** para la demo FEDER debe ser `make hardened-full` con fail‑fast. El desarrollador puede usar `make hardened-continue` en su iteración local.

**Test mínimo reproducible:**
```makefile
.PHONY: hardened-full
hardened-full:
	set -e; \
	$(MAKE) hardened-up ; \
	$(MAKE) hardened-provision-all ; \
	$(MAKE) prod-build-x86 ; \
	$(MAKE) prod-sign ; \
	$(MAKE) prod-checksums ; \
	$(MAKE) prod-deploy-x86 ; \
	$(MAKE) check-prod-all ; \
	touch .hardened_full_success

.PHONY: hardened-continue
hardened-continue:
	$(MAKE) $(shell [ -f .prod_build_done ] || echo prod-build-x86) \
	         $(shell [ -f .prod_sign_done ] || echo prod-sign) \
	         ...
```

**Riesgo del checkpoint automático:** podría ocultar que un paso reintentado usa artefactos modificados manualmente, rompiendo la reproducibilidad. Por eso los marcadores deben borrarse si `make clean-hardened` o si se cambia el código fuente (dependencia de Makefile correcta).

---

### Pregunta 2 — Semillas en la hardened VM

**Recomendación:**  
✅ **La hardened VM debe recibir las semillas desde la dev VM en el momento del despliegue (`prod-deploy-x86`), no antes.**  
Pero **nunca** se deben almacenar las semillas en la imagen base ni en la shared folder de forma persistente.

**Justificación (seguridad por separación):**
- Las semillas (ChaCha20, HMAC) son material criptográfico. La dev VM las genera en `/etc/argus/seeds/` con permisos `0400 root:root`.
- En `make prod-deploy-x86`, se copian **via `scp`** (usando la configuració `vagrant ssh-config`) a la hardened VM, a la ruta `/etc/ml-defender/[component]/seed.bin` con los mismos permisos.
- Una vez copiadas, la hardened VM no necesita volver a acceder a la dev VM. El `make hardened-full` nunca debe depender de una shared folder viva que contenga las semillas (riesgo de que un atacante en la hardened VM lea la shared folder).

**Implementación concreta:**
```makefile
prod-deploy-x86: prod-checksums
	# ... copiar binarios, librerías, etc. ...
	# Copiar semillas desde dev VM
	scp -F vagrant-ssh-config dev:/etc/argus/seeds/ml-detector/seed.bin \
	    hardened:/etc/ml-defender/ml-detector/seed.bin
	scp -F vagrant-ssh-config dev:/etc/argus/seeds/etcd/seed.bin \
	    hardened:/etc/etcd/seed.bin
	# ... etc.
```

**Respuesta a la observación actual:** Los 7 WARNs `seed.bin no existe` durante `check-prod-permissions` son **esperados** hasta que se ejecute `prod-deploy-x86`. No son errores; se pueden silenciar en el check (mostrarlos como warnings no bloqueantes). El `check-prod-all` final debe fallar si tras el deploy las semillas no existen.

---

### Pregunta 3 — Idempotencia de `make hardened-full`

**Recomendación:**  
✅ **No idempotente por defecto.** La REGLA EMECAS para la hardened VM debe incluir `vagrant destroy -f` **antes** de ejecutar `make hardened-full`. En el flujo de desarrollo, el target `hardened-full` debe asumir una VM limpia. Si se desea reutilizar la misma VM, se debe ejecutar `make hardened-reprovision` (que rehace los pasos no destructivos).

**Justificación:**
- La REGLA EMECAS original (`vagrant destroy -f && vagrant up && make bootstrap && make test-all`) es la base de la reproducibilidad. Para la hardened VM, el equivalente es:
  ```bash
  make hardened-destroy   # vagrant destroy -f en el directorio hardened
  make hardened-up
  make hardened-full
  ```
- Si permitimos que `hardened-full` sea idempotente, podríamos ocultar errores de estado residual (ej: ficheros de configuración antiguos, procesos zombi).
- Para acelerar iteraciones, se puede crear `make hardened-rebuild` que no destruya la VM pero que vacíe `/opt/argus/`, limpie systemd units, y rehaga `provision-all`. Esto es útil mientras se ajustan los perfiles AppArmor.

**Test de verificación:**  
Después de ejecutar `make hardened-full` dos veces seguidas (sin destroy), la segunda ejecución debería fallar si no se ha limpiado el estado. El equipo debe documentar "si quieres repetir, destruye la VM".

---

### Pregunta 4 — Falco .deb como artefacto versionado

**Recomendación:**  
✅ **Descargar siempre en el paso de provision (desde una URL fija, con verificación de hash), y cachear en `dist/falco/` dentro del repositorio, excluido de git (`.gitignore`).**  
No commitear el .deb (ni con Git LFS). Usar un **artefacto de caché** que persista entre `vagrant destroy` de la dev VM.

**Justificación (reproducibilidad + offline capability):**
- El .deb oficial de Falco 0.43.1 tiene una URL estable (por ejemplo `https://download.falco.org/...`). En el provisioner de la VM hardened **no tendremos internet** (por BSR, no hay `curl`/`gpg`). Por tanto, el .deb debe estar disponible localmente.
- La solución más limpia:
    1. En la **dev VM** (que sí tiene internet), se descarga el .deb en `dist/falco/falco_0.43.1_amd64.deb` y se verifica su SHA‑256 contra un valor fijo en el repositorio.
    2. Ese directorio `dist/falco/` se añade a `.gitignore` (no comitear).
    3. En el `Makefile`, el target `hardened-provision-all` copia ese .deb a la hardened VM mediante `scp` o `vagrant scp`.
    4. Dentro de la hardened VM, se instala con `dpkg -i /tmp/falco.deb`.
- La primera vez que se ejecuta `make hardened-provision-all`, la dev VM descargará el .deb (si no está en caché). Eso está bien porque la dev VM tiene internet. La reproducibilidad se garantiza porque la versión y hash son fijos.

**Alternativa (menos deseable):** usar Git LFS para el .deb (50 MB) — es factible, pero añade complejidad de LFS y requisitos adicionales para los contribuyentes. Mejor mantenerlo como artefacto local excluido.

**Test mínimo:**
```bash
# En dev VM (o macOS)
curl -L -o dist/falco/falco_0.43.1_amd64.deb $FALCO_URL
sha256sum dist/falco/falco_0.43.1_amd64.deb | grep -q $EXPECTED_HASH
```

---

### Pregunta 5 — Verificación del prerequisito `confidence_score` en ml-detector (ADR-040)

**Recomendación:**  
✅ **Verificación mediante test de integración que capture la salida ZeroMQ del ml-detector en la VM hardened, sin modificar el código.**  
Como complemento, inspección de código estática para documentar que el campo existe.

**Justificación (seguridad y reproducibilidad):**
- El `confidence_score` es un campo numérico (probabilidad de clase). Si ml-detector no lo emite, la Regla 4 (IPW) no podrá ponderar muestras.
- La forma **más segura** (sin modificar el binario de producción) es ejecutar ml-detector en la hardened VM (o en la dev VM con la misma configuración) contra un pcap de prueba conocido, y capturar sus mensajes ZeroMQ. Luego, con un script Python que consuma el socket, verificar que cada mensaje contiene el campo `confidence_score` y que está en el rango [0,1].
- La **inspección de código** es complementaria: revisar `ml-detector/src/ml_pipeline.cpp` y buscar la línea donde se serializa el protobuf. Sirve para documentar, pero no garantiza que el binario compilado lo tenga (podría haberse desactivado con una flag).

**Test mínimo reproducible (hardened VM, después de `make prod-full-x86`):**

```bash
# En la hardened VM, lanzar ml-detector en segundo plano y enviarle tráfico
/opt/argus/bin/ml-detector --config /etc/ml-defender/ml-detector/config.json &
ML_PID=$!
# Enviar un pcap de 100 flows (usando un generador o tcpreplay)
tcpreplay -i eth0 sample_100_flows.pcap
# Capturar 10 segundos de salida ZeroMQ (puerto 5556 por defecto) con un script Python
python3 << 'EOF'
import zmq, json, sys
ctx = zmq.Context()
sock = ctx.socket(zmq.SUB)
sock.connect("tcp://127.0.0.1:5556")
sock.setsockopt_string(zmq.SUBSCRIBE, "")
sock.RCVTIMEO = 5000
for _ in range(50):
    msg = sock.recv_json()
    assert "confidence_score" in msg, "Missing confidence_score"
    assert 0.0 <= msg["confidence_score"] <= 1.0, "Invalid range"
print("OK: confidence_score present and valid")
EOF
kill $ML_PID
```

Si este test pasa, el prerequisito está cumplido. Si falla, se debe modificar ml-detector (DEBT-ADR040-002) **antes** de implementar IPW.

**Decisión adicional:** Añadir este test como parte de `check-prod-all` **opcional** (solo si se está verificando ADR-040). Por ahora basta con ejecutarlo manualmente. Documentar en `docs/ADR040-VERIFICATION.md`.

---

### Resumen de acuerdos para DAY 135

| Pregunta | Decisión | Acción concreta |
|----------|----------|------------------|
| 1. Atomicidad | Fail‑fast con target `hardened-full`; target `hardened-continue` opcional con checkpoints manuales | Crear ambos en Makefile; documentar que `hardened-full` es la receta para reproducibilidad |
| 2. Semillas | Copiar desde dev VM durante `prod-deploy-x86`; no mantener en shared folder; warnings no bloqueantes | Modificar `prod-deploy-x86` para incluir `scp` de seeds; ajustar `check-prod-permissions` para mostrar warnings, no errores |
| 3. Idempotencia | No idempotente; REGLA EMECAS hardened: `make hardened-destroy && make hardened-up && make hardened-full` | Crear `hardened-destroy`; documentar en `CONTINUITY.md` |
| 4. Falco .deb | Descargar en dev VM, cachear en `dist/falco/` (excluido de git), copiar a hardened VM en `hardened-provision-all` | Añadir target `download-falco`; actualizar `hardened-provision-all` |
| 5. `confidence_score` | Verificar con test de integración ZeroMQ sin modificar binario; añadir inspección de código complementaria | Crear script `test/check_confidence_score.sh`; ejecutar manualmente antes de ADR-040 |

---

### Reflexión final

DAY 134 ha sido un **hito fundacional**: la primera vez que la imagen hardened pasa todas las comprobaciones de seguridad (BSR, AppArmor, capabilities, Falco). El procedimiento EMECAS para la hardened VM que se construirá mañana (DAY 135) dejará el proyecto en un estado de **reproducibilidad de extremo a extremo** listo para la validación sobre hardware real.

Recordad: *“La reproducibilidad no es un lujo; es la única manera de que un hospital pueda confiar en tu software.”*

El Consejo queda satisfecho y espera el commit del Draft v18 con la tabla de fuzzing y la solución de las cinco cuestiones.

*Firmado por los 8 modelos, 28 abril 2026. 🎂*  
*Via Appia Quality — “Un escudo que aprende de su propia sombra.”*