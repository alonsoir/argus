## Mi opinión — Claude (Anthropic) — Consejo DAY 129

---

### P1 — REGLA PERMANENTE: transferencia de ficheros VM↔macOS
**APRUEBO. Prioridad alta.**

El bug costó ~20 minutos y produjo 3 commits de corrección. La regla es simple y el daño de violarla es silencioso (0 bytes sin error visible). Propongo redacción más precisa:

> **"Transferencia VM→macOS: usar `scp -F /tmp/vagrant-ssh-config` o `git show HEAD:fichero > destino`. Nunca `vagrant ssh -c "cat ..." > fichero` en zsh — el pipe trunca a 0 bytes silenciosamente sin error. El hook pre-commit de 0 bytes nos salvó en DAY 129 — mantenerlo activo."**

---

### P2 — build-debug en .gitignore
**APRUEBO sin reservas.**

`build-debug/` es artefacto de compilación. Que aparezca en `git status` en cada sesión es ruido cognitivo puro. Riesgo de añadirlo al `.gitignore`: cero. Beneficio: `git status` limpio en cada sesión.

---

### P3 — Prioridad DAY 130
**Recomiendo: C) Paper §5 primero, luego A) Fuzzing.**

Razonamiento:
- El paper es el único entregable con fecha externa implícita (Draft v17 antes de la presentación FEDER). Property testing y safe_path taxonomy son contribuciones originales que deben aparecer en el paper antes de que alguien más las publique.
- Fuzzing sobre `validate_chain_name` es el siguiente paso natural de seguridad — viene inmediatamente después del paper.
- `CAP_DAC_READ_SEARCH` (B) es v0.6 — no hay urgencia.

**Orden propuesto DAY 130:** Paper §5 → Fuzzing → CAP.

---

### P4 — Null byte en safe_exec() defensa en profundidad
**SÍ, recomiendo añadir el check en safe_exec().**

La razón es arquitectónica: `validate_chain_name()` protege la entrada específica de chain names, pero `safe_exec()` es un primitivo general que acepta `vector<string>` arbitrario. Si en el futuro alguien llama `safe_exec()` directamente sin pasar por `validate_chain_name()`, el null byte podría truncar un argumento de `execv()` de forma inesperada.

El check es trivial:
```cpp
for (const auto& a : args) {
    if (a.find('\0') != std::string::npos)
        return -1; // fail-closed
}
```

Coste: ~5 líneas. Beneficio: defensa en profundidad real. **Recomiendo añadirlo como DEBT-SAFE-EXEC-NULLBYTE-001 para DAY 130.**

---

### P5 — .gitguardian.yaml deprecated keys
**Limpiar ahora — es 5 minutos y elimina ruido permanente.**

Tres warnings en cada commit son 3 líneas de output que entrenamos a ignorar. Ignorar warnings es un hábito peligroso en un proyecto de seguridad. El fix es trivial: renombrar `paths-ignore` → `paths_ignore` y verificar la clave `unrecognized`. Si falla la validación de GitGuardian, lo vemos inmediatamente.

**Recomiendo incluirlo en el commit de cierre DAY 129.**

---

### Observación adicional no preguntada

El incidente de markdown corruption (`[rule.in](http://rule.in)_interface`) en el `.cpp` merece atención. Es probable que ese fichero fue editado alguna vez con un editor que interpretó el texto C++ como markdown. Recomiendo **añadir al pre-commit hook una verificación** que detecte patrones `[word](http://` en ficheros `.cpp`/`.hpp` — es un indicador inequívoco de corrupción silenciosa.

---

*Claude (Anthropic) — Consejo DAY 129 — 25 abril 2026*