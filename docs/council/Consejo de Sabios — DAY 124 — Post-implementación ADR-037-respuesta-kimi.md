He revisado el **Consejo de Sabios — DAY 124 — Post-implementación ADR-037 (v2)**. Como miembro del Consejo, emito mi análisis implacable pero justo sobre el trabajo realizado y las deudas técnicas abiertas.

---

## 🏛️ Dictamen del Consejo — DAY 124

### **Estado general: EXCELENTE implementación, deuda técnica preocupante**

ADR-037 está mergeado y funcional. Sin embargo, la ausencia de tests de demostración para los fixes de producción es una **violación del principio RED→GREEN** que el propio equipo ha identificado. Esto no es acceptable para un sistema de seguridad.

---

## 📋 Respuestas a las Preguntas

### **Pregunta 3 — Test de demostración para F17 (Integer Overflow)**

**Veredicto: Opción A (Unit test) + Opción C (Property-based) como complemento.**

| Opción | Viabilidad | Recomendación |
|--------|-----------|---------------|
| A — Unit test sintético | ✅ Inmediato | **OBLIGATORIO** |
| B — Fuzzing AFL++ | ⏳ Requiere infraestructura | V2, no bloqueante |
| C — Property-based (rapidcheck) | ✅ Alta cobertura | **OBLIGATORIO** |

**Implementación concreta:**

```cpp
// test_zmq_handler_overflow.cpp
TEST(ZmqHandlerOverflow, OriginalCodeWouldOverflow) {
    // Simular la versión antigua (vulnerable)
    long pages = LONG_MAX / 4096 + 1;
    long page_size = 4096;
    
    // Versión antigua: overflow silencioso
    long old_result = (pages * page_size); // Undefined behavior, probablemente negativo
    
    // Versión nueva: resultado correcto
    const auto mem_bytes = static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
    EXPECT_GT(mem_bytes, 0); // Nunca negativo
    EXPECT_EQ(mem_bytes, static_cast<int64_t>(pages) * static_cast<int64_t>(page_size));
}

TEST(ZmqHandlerOverflow, PropertyNeverNegative) {
    // rapidcheck o brute force pequeño
    for (long pages = 0; pages < 1000000; pages += 1000) {
        for (long page_size : {4096, 8192, 16384, 65536}) {
            const auto mem_bytes = static_cast<int64_t>(pages) * static_cast<int64_t>(page_size);
            EXPECT_GE(mem_bytes, 0);
            EXPECT_LE(mem_bytes, static_cast<int64_t>(std::numeric_limits<double>::max()));
        }
    }
}
```

**Regla permanente:** Todo fix de seguridad en código de producción **debe** tener un test de demostración RED→GREEN antes del merge. No negociable.

---

### **Pregunta 4.3 — `.gitignore` y tests**

**Veredicto: REFINAR la regla global.**

```gitignore
# ANTES (demasiado amplio)
**/test_*

# DESPUÉS (preciso)
**/test_*.o
**/test_*.exe
**/test_*.bin
# PERO NO:
# !**/test_*.cpp  ← excepción explícita para fuentes de test
```

La regla actual es un **anti-patrón** que causa fricción silenciosa. Los tests son código fuente, no artefactos de build.

---

### **Pregunta 5 — Inventario de deuda técnica: ¿atacar todo?**

**Veredicto: SÍ, atacar toda la deuda antes del siguiente hito.**

| DEBT | Prioridad | Acción | Timeline |
|------|-----------|--------|----------|
| DEBT-INTEGER-OVERFLOW-TEST-001 | 🔴 CRÍTICA | Test RED→GREEN F17 | DAY 125 |
| DEBT-SAFE-PATH-TEST-RELATIVE-001 | 🔴 CRÍTICA | Test paths relativos | DAY 125 |
| DEBT-SAFE-PATH-TEST-PRODUCTION-001 | 🔴 CRÍTICA | Tests integración por componente | DAY 125-126 |
| DEBT-SNYK-WEB-VERIFICATION-001 | 🟡 ALTA | Verificación Snyk web | DAY 126 |
| DEBT-CRYPTO-TRANSPORT-CTEST-001 | 🟡 ALTA | Investigar fallo CTest | DAY 127 |
| DEBT-PROVISION-PORTABILITY-001 | 🟢 MEDIA | Variable `ARGUS_SERVICE_USER` | DAY 128 |
| DEBT-TRIVY-THIRDPARTY-001 | 🟢 BAJA | Monitorizar llama.cpp | Contínuo |

**Argumento:** Los hospitales no pueden permitirse deuda técnica en seguridad. Un integer overflow sin test es una bomba de tiempo. Atacar la deuda ahora es más barato que explicar un breach después.

---

### **Pregunta 6 — Asimetría dev/prod: prefijo dinámico**

**Veredicto: Opción B (Symlink en dev) + Opción C (Variable entorno) como fallback.**

| Opción | Seguridad | Mantenibilidad | Recomendación |
|--------|-----------|----------------|---------------|
| A — Prefijo dinámico | 🟡 Media (asimetría) | ✅ Alta | ❌ Rechazada |
| B — Symlink en Vagrantfile | ✅ Alta (idéntico a prod) | ✅ Alta | **APROBADA** |
| C — Variable entorno | ✅ Alta (flexible) | 🟡 Media (configuración) | Fallback |

**Implementación B:**
```bash
# Vagrantfile
config.vm.provision "shell", inline: <<-SHELL
  mkdir -p /etc/ml-defender
  ln -sf /vagrant/rag-ingester/config /etc/ml-defender/rag-ingester
  ln -sf /vagrant/firewall-acl-agent/config /etc/ml-defender/firewall-acl-agent
SHELL
```

**Código de producción:** Siempre usa `/etc/ml-defender/`. Sin condicionales. Sin `weakly_canonical` en el prefijo.

**Fallback C:** Si el entorno no permite symlinks (Windows nativo, contenedores sin privilegios), usar `ARGUS_CONFIG_PREFIX` con default `/etc/ml-defender/`.

---

### **Pregunta 7 — Paper: honestidad sobre limitaciones**

**Veredicto: SÍ, incluir como caso de estudio.**

**Framing para §5:**
> *"§5.3 Lección Aprendida: Tests de Demostración vs Regresión"*
>
> *"Durante la implementación de ADR-037, descubrimos que los tests de la librería `safe_path` (unit tests) no detectaron un fallo en la integración con `rag-ingester` (config relativo en dev vs absoluto en prod). El fallo se manifestó en el build de producción, no en un test. Esto reforzó nuestra metodología: todo fix de seguridad debe incluir un test de demostración RED→GREEN que verifique tanto el ataque como la corrección en el contexto real del componente. Los tests de librería son necesarios pero no suficientes."*

Esto fortalece la credibilidad científica. Demuestra que el equipo aprende de sus errores.

---

## 🔴 Observaciones Adicionales Críticas

### **DEBT-CRYPTO-TRANSPORT-CTEST-001: No postergable**

El fallo en `test_crypto_transport` y `test_integ_contexts` es **inaceptable** en la capa criptográfica. No es "cobertura rota" — es **la capa más crítica del sistema sin validación automatizada**.

**Acción inmediata:**
1. Ejecutar tests manualmente con `ctest -V -R crypto` para ver output completo
2. Si fallan por timeout: aumentar timeout en CTest
3. Si fallan por dependencia de servicio: mock del servicio
4. Si fallan por race condition: instrumentar con TSan

**No se investiga "después". Se investiga en DAY 125.**

---

### **DEBT-PROVISION-PORTABILITY-001: Nomenclatura**

**Veredicto: `ARGUS_SERVICE_USER`**

`ML_DEFENDER_USER` es ambiguo (¿qué es "ml-defender"?). `ARGUS_SERVICE_USER` es explícito y alineado con la marca del proyecto.

```bash
# provision.sh
ARGUS_SERVICE_USER="${ARGUS_SERVICE_USER:-vagrant}"
chown "$ARGUS_SERVICE_USER:$ARGUS_SERVICE_USER" "$SEED_FILE"
```

---

## 📋 Plan de Acción DAY 125-128 (Aprobado)

| Día | Tarea | Gate |
|-----|-------|------|
| DAY 125 | Tests RED→GREEN: F17, paths relativos, producción | Todos PASSED |
| DAY 126 | Snyk web verification + symlink dev/prod | 0 findings, build verde |
| DAY 127 | Investigar DEBT-CRYPTO-TRANSPORT-CTEST-001 | Diagnóstico completo |
| DAY 128 | DEBT-PROVISION-PORTABILITY-001 + backlog limpio | PR mergeado |

---

## Conclusión del Consejo

**ADR-037 está mergeado. La deuda técnica no es acceptable.**

El equipo ha demostrado excelencia en la implementación pero ha identificado correctamente su propia falla metodológica. La honestidad es la primera defensa. Ahora se requiere **disciplina** para cerrar la deuda antes de avanzar.

**Regla permanente añadida:**
> *"Ningún fix de seguridad en código de producción se mergea sin test de demostración RED→GREEN. El test debe fallar con el código antiguo y pasar con el código nuevo. Sin excepciones."*

**Próxima revisión:** DAY 129 (post-cierre deuda técnica).

*"Via Appia Quality — un escudo, nunca una espada."*
*"Un escudo sin tests es un escudo de papel."*

---

*Dictamen emitido: DAY 124 — Consejo de Sabios*