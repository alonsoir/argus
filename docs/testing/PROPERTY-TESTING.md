# Property Testing — Patrón Formal

> **Consejo 8/8 DAY 125 — PERMANENTE**
> Todo fix de seguridad incluye: (1) unit test sintético, (2) property test
> de invariante, (3) test de integración en componente real.

---

## ¿Qué es un property test?

Un **property test** verifica una invariante matemática sobre un espacio
de inputs, no un caso específico. La diferencia es fundamental:

| Unit test | Property test |
|-----------|---------------|
| `assert compute_memory_mb(1024) == 1` | `for all x > 0: compute_memory_mb(x) > 0` |
| Verifica un ejemplo concreto | Verifica una propiedad para todo el dominio |
| Falla solo si el ejemplo falla | Falla si la propiedad se viola para cualquier input |
| No detecta overflow en int64 | Detecta overflow en int64 para x cercano a INT64_MAX |

---

## Cuándo usar property testing

Usar en **toda superficie crítica** con:
- Operaciones aritméticas (riesgo de overflow, underflow, división por cero)
- Operaciones de paths (riesgo de traversal, escape de prefix)
- Parsers y deserializadores (riesgo de inputs malformados)
- Criptografía (invariantes de longitud, entropía, prefijos)

---

## Patrón estándar

1. Identificar invariante
"Para todo input válido X, f(X) cumple propiedad P"
2. Escribir el loop de verificación
for (auto x : test_inputs) {
auto result = f(x);
ASSERT invariante(result);
}
3. Verificar RED con código antiguo
El test debe FALLAR con la implementación defectuosa.
Sin RED no hay demostración.
4. Verificar GREEN con código nuevo
El test debe PASAR con el fix aplicado.
Sin GREEN el fix no es correcto.

---

## Ejemplos reales del proyecto

### F17 — `compute_memory_mb` (DAY 125)

**Invariante:** `compute_memory_mb(x)` nunca retorna negativo para x > 0.

**Bug encontrado:** `int64_t` overflow para x cercano a `INT64_MAX`.

```cpp
// Property test que encontró el bug
TEST(PropertyTest, ComputeMemoryMbNeverNegative) {
    std::vector<int64_t> inputs = {
        1, 100, 1024, 1024*1024,
        INT64_MAX / 1024,
        INT64_MAX / 1024 - 1,
        INT64_MAX / 1024 + 1,  // overflow aquí con código antiguo
    };
    for (auto x : inputs) {
        if (x > 0) {
            EXPECT_GE(compute_memory_mb(x), 0)
                << "Overflow para x=" << x;
        }
    }
}
```

### `resolve_seed` (DAY 126)

**Invariantes:**
1. Nunca retorna un path fuera del prefix.
2. Nunca acepta un path con symlinks.

```cpp
TEST(PropertyTest, ResolveSeedNeverEscapesPrefix) {
    const std::string prefix = "/etc/ml-defender/etcd-server";
    std::vector<std::string> traversal_attempts = {
        prefix + "/../../etc/passwd",
        prefix + "/../sniffer/seed.bin",
        prefix + "/./../../root/.ssh/id_rsa",
    };
    for (const auto& attempt : traversal_attempts) {
        EXPECT_THROW(safe_path::resolve_seed(attempt, prefix),
                     std::runtime_error)
            << "Debería rechazar: " << attempt;
    }
}
```

### `resolve_config` (DAY 127)

**Invariante:** Acepta symlinks dentro del prefix, rechaza los que escapan.

```cpp
TEST(PropertyTest, ResolveConfigAcceptsLegitimateSymlinks) {
    // /etc/ml-defender/sniffer/sniffer.json → /vagrant/sniffer/config/sniffer.json
    // Este symlink es legítimo (paridad dev/prod ADR-027)
    EXPECT_NO_THROW(
        safe_path::resolve_config(
            "/etc/ml-defender/sniffer/sniffer.json",
            "/etc/ml-defender/sniffer"
        )
    );
}

TEST(PropertyTest, ResolveConfigRejectsEscapingSymlinks) {
    // Symlink que escaparía el prefix
    EXPECT_THROW(
        safe_path::resolve_config(
            "/etc/ml-defender/sniffer/../../etc/passwd",
            "/etc/ml-defender/sniffer"
        ),
        std::runtime_error
    );
}
```

---

## Relación con otras técnicas de testing

Unit tests (base)
└─ Verifican comportamiento en casos concretos conocidos
└─ Rápidos, deterministas, fáciles de escribir
└─ No detectan casos extremos no anticipados
Property tests (invariantes)
└─ Verifican que la invariante se mantiene para todo el dominio
└─ Detectan bugs en casos extremos (overflow, boundary, traversal)
└─ OBLIGATORIOS en toda superficie de seguridad (Consejo DAY 125)
Fuzzing con libFuzzer (parsers)
└─ Genera inputs aleatorios para encontrar crashes
└─ Especialmente útil para parsers y deserializadores
└─ BACKLOG — DEBT-FUZZING-LIBFUZZER-001 (post-property-testing)
Mutation testing (calidad de suite)
└─ Muta el código y verifica que los tests detectan la mutación
└─ Mide la calidad de la suite de tests existente
└─ Backlog lejano — requiere suite estable primero

---

## Regla de oro

> **Un property test que no tiene un estado RED demostrado
> no es un property test — es documentación con sintaxis de test.**

El estado RED (fallo con código antiguo) es la firma del hallazgo.
Sin él, no podemos afirmar que el test valida algo real.

---

## Referencias

- QuickCheck: Claessen & Hughes (2000) — origen del property testing
- CWE-22/23: Path Traversal
- TOCTOU literature
- `docs/SECURITY-PATH-PRIMITIVES.md` — taxonomía safe_path