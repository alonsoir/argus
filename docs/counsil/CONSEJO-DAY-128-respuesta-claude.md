## Respuestas de Claude — Consejo DAY 128

---

### P1 — Invariante `0400` vs portabilidad

La decisión de `0400 root:root` + `sudo` es correcta y no debe relajarse. El argumento:

Los seeds ChaCha20 son equivalentes a claves privadas de sistema. En cualquier sistema Unix maduro (OpenSSH, GPG, HSM software), el material criptográfico pertenece a root y los daemons que lo necesitan corren con privilegios. La alternativa — relajar a `0440` o usar un grupo específico — introduce una superficie de ataque: cualquier proceso corriendo como `vagrant` (o el grupo equivalente) podría leer el seed si compromete un componente menos privilegiado.

La única alternativa que no relaja la invariante sería un daemon intermediario tipo `systemd-creds` o un socket Unix con autenticación SCM_CREDENTIALS — pero eso es complejidad de ADR-038 en adelante, no para ahora.

**Conclusión: sudo es correcto. Documentar como patrón permanente.**

---

### P2 — Superficies prioritarias para property testing

Por orden de criticidad:

**Inmediato (próximo sprint):**
- `HKDF key derivation` — la derivación de claves debe cumplir invariantes de longitud y entropía mínima para cualquier input válido. Un overflow o truncado aquí es silencioso y catastrófico.
- `ZeroMQ message parser` — `MAX_PLUGIN_PAYLOAD_SIZE=65536`. Property: para todo mensaje de tamaño x donde x > MAX, el parser rechaza. Para todo x <= MAX, no hay overflow en el buffer receptor.

**Segundo sprint:**
- `protobuf serialization` — round-trip invariant: `deserialize(serialize(x)) == x` para todo x válido. Especialmente importante para `NetworkSecurityEvent`.
- `compute_memory_mb` (F17) — ya identificado, overflow en int64. Fix documentado, falta el test formal en ctest.

**Más adelante:**
- ChaCha20 nonce monotonicity — para todo par de mensajes consecutivos, `nonce[i+1] > nonce[i]`. Crítico para prevenir reutilización de nonce.

---

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

La opción **execve() directo sin shell** es la correcta para este proyecto. El razonamiento:

`execute_command(cmd)` probablemente usa `system()` o `popen()` que invoca `/bin/sh -c cmd`. Cualquier metacarácter en `cmd` (`;`, `|`, `$()`) se ejecuta. La solución de whitelist es frágil — siempre hay casos edge.

`execve()` directo elimina el shell del camino:
```cpp
// En vez de: system("iptables -A INPUT -s " + ip + " -j DROP");
// Usar:
std::vector<std::string> args = {"iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"};
execve("/sbin/iptables", ...);  // sin shell, sin interpolación
```

`libiptc` es la opción más correcta a largo plazo (API nativa sin fork/exec), pero requiere más refactoring. Para el fix RED→GREEN inmediato: `execve()` + validación de IP con regex antes de pasarla como argumento.

---

### P4 — Secuencia cleanup EtcdClient vs ADR-024

La secuencia correcta es: **limpiar EtcdClient antes de implementar ADR-024**, no después. El argumento:

El `EtcdClient` con lectura de seed es código muerto en el modelo P2P — ya no es el distribuidor de seeds. Mantenerlo activo mientras desarrollamos ADR-024 crea confusión sobre qué modelo está realmente en uso. El cleanup es simple: eliminar la inicialización de `CryptoTransport` en el constructor de `EtcdClient` y añadir un test que verifique que el constructor funciona sin seed.

Esto también desbloquea `EtcdClientHmacTest` 9/9 GREEN sin necesidad de sudo, que es una victoria de test suite limpia antes de la complejidad de ADR-024.

**Secuencia propuesta:**
1. Limpiar EtcdClient (1-2 días, RED→GREEN en EtcdClientHmacTest)
2. Implementar ADR-024 Noise_IKpsk3 sobre base limpia

---

### P5 — Scope mínimo viable demo FEDER

**NDR standalone es suficiente para la demo FEDER.** El argumento:

El objetivo de FEDER no es demostrar tecnología de federación — es demostrar valor para hospitales, municipios y escuelas de Extremadura. Un NDR standalone que detecta ataques reales con F1=0.9978 sobre CIC-IDS-2017, con AppArmor enforce, pipeline hardened y paper arXiv publicado, es una propuesta más sólida que una federación inestable.

La federación (ADR-038) es la propuesta de valor para el servicio cloud de pago — no para la demo inicial. Lo que necesita la demo FEDER:

- Pipeline 6/6 estable en Vagrant (✅ ya tenemos)
- Modelo XGBoost validado con datos reales (✅ DAY 122)
- Paper arXiv:2604.04952 como respaldo académico (✅)
- Demo reproducible en hardware modesto (Raspberry Pi / mini PC) — esto sí requiere hardware FEDER

**La pregunta a clarificar con Andrés Caro Lindo no es técnica sino política:** ¿FEDER financia investigación aplicada (NDR standalone) o requiere demostrar componente federado? Esa respuesta cambia el scope más que cualquier decisión técnica.