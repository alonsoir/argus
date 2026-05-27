#!/usr/bin/env python3
"""
update_adr043.py — Actualiza BACKLOG.md y README.md con las decisiones de ADR-0043 v4.

Uso:
    python3 update_adr043.py [--repo-path /ruta/al/repo]

Por defecto busca los ficheros en el directorio actual.
El script es idempotente: si se ejecuta dos veces no duplica contenido.
"""

import sys
import os
import re
import argparse
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# CONTENIDO A INSERTAR
# ─────────────────────────────────────────────────────────────────────────────

# Nuevas deudas para el README (tabla "Deuda técnica abierta")
NUEVAS_DEUDAS_README = """\
| DEBT-PARQUET-SCHEMA-001 | 🔴 P0 bloqueante | Definir schema Parquet ml-detector y firewall-acl-agent desde CSVs reales |
| DEBT-VAULT-FEDERATION-001 | 🟡 P1 pre-FEDER | Offboarding instalaciones: destrucción de claves, retención de datos GDPR |
| DEBT-LEGAL-DATA-RETENTION-001 | 🟡 P1 pre-FEDER | Dictamen jurídico GDPR retención datos pseudonimizados post-cliente |
| DEBT-KPSEUDO-ROTATION-MIGRATION-001 | 🟡 P1 pre-FEDER | Migración identidades Neo4j tras rotación K_pseudo |
| DEBT-GDPR-ERASURE-001 | 🟡 P1 pre-FEDER | Flujo derecho al olvido Art. 17 GDPR — comando borrado firmado |
| DEBT-KPSEUDO-HKDF-HIERARCHY-001 | ⏳ P3 post-FEDER | Jerarquía HKDF para K_pseudo (host/flow/model desde K_root) |"""

# Nuevas decisiones de diseño para BACKLOG (tabla "Decisiones de diseño consolidadas")
NUEVAS_DECISIONES_BACKLOG = """\
| **MAC unicast como identidad primaria** | `HMAC-SHA256(K_pseudo, MAC)`. Jerarquía MAC→hostname→IP. `Host` vs `NetworkPresence`. MAC nunca sale del nodo. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Pseudonimización determinista K_pseudo** | HMAC-SHA256 con clave por instalación en Vault local. Coherencia temporal garantizada. Rotación es evento excepcional. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Paquete mensual edge→central** | Parquet ×2 + plugin firmado + metadatos. idempotency_key = firma Ed25519(batch_content). Estable a N reintentos. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Cola local batches pendientes (D9)** | `/var/spool/argus/batches/pending/`. Independiente de SQLite. Retención 90 días. FIFO. Backoff exponencial. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Neo4j DAG sin ciclos** | Patrón entidad persistente + episodio temporal. Sin PRECEDES materializado — ordenamiento por Episode.period ISO 8601. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Timestamps UTC epoch nanoseconds** | int64 UTC en Parquet. ISO 8601 con sufijo Z en JSON. Sin excepciones. system_clock en C++20, nunca steady_clock. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Vault jerarquía root+operativo** | Vault central = root of trust (wrapping keys). Vault local = operativo (K_pseudo, Ed25519, seeds). | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **Flujo GDPR Art. 17** | Borrado via comando firmado Ed25519 desde instalación → DELETE en Neo4j → auditoría certificada inmutable. | ADR-0043 v4 · Consejo 8/8 · DAY 147 |
| **ADR-035 OQ-2 CERRADA** | Topología etcd parametrizada por tamaño de instalación. Single-node aceptado en instalaciones pequeñas con SPOF documentado. | ADR-0043 v4 · cierra ADR-035 OQ-2 · DAY 147 |
| **ADR-038 §Anonimización SUPERSEDIDA** | Rotating salt → HMAC determinista (ADR-0043 D2-D3). BitTorrent → ZeroMQ (ADR-0043 D4). Resto ADR-038 vigente. | ADR-0043 v4 · DAY 147 |"""

# Nuevas entradas en "Estado global del proyecto"
NUEVAS_ENTRADAS_ESTADO = """\
ADR-0043 v4 Memoria Episódica Distribuida:  100% ✅  DAY 147 (Consejo 8/8 · ACEPTADO)
ADR-035 OQ-2 cerrada (etcd topología):     100% ✅  DAY 147 (referenciada en ADR-0043 D6)
DEBT-PARQUET-SCHEMA-001:                     0% ⏳  P0 bloqueante (schema Parquet ml-detector + firewall)
DEBT-VAULT-FEDERATION-001:                   0% ⏳  P1 pre-FEDER (offboarding instalaciones GDPR)
DEBT-LEGAL-DATA-RETENTION-001:               0% ⏳  P1 pre-FEDER (dictamen jurídico retención datos)
DEBT-KPSEUDO-ROTATION-MIGRATION-001:         0% ⏳  P1 pre-FEDER (migración Neo4j tras rotación K_pseudo)
DEBT-GDPR-ERASURE-001:                       0% ⏳  P1 pre-FEDER (flujo derecho al olvido Art. 17)
DEBT-KPSEUDO-HKDF-HIERARCHY-001:             0% ⏳  P3 post-FEDER (jerarquía HKDF para K_pseudo)"""

# Nota Consejo DAY 147 para BACKLOG (sección ADR-0043)
NOTA_CONSEJO_ADR043 = """
## 📝 Notas del Consejo de Sabios — ADR-0043 v4 (8/8) · DAY 147

> "ADR-0043 v4 — APROBADO UNÁNIMEMENTE. Cuatro versiones, tres rondas de revisión del Consejo, ocho modelos.
>
> **Decisiones clave:**
> - Identidad por MAC unicast con jerarquía de fallback (MAC→hostname→IP). DHCP no rompe la coherencia del grafo.
> - Pseudonimización determinista HMAC-SHA256 con K_pseudo por instalación en Vault local. La MAC nunca abandona el nodo.
> - idempotency_key = firma Ed25519(batch_content). Estable a través de cualquier número de reintentos.
> - Cola local /var/spool/argus/batches/ independiente de SQLite. Retención 90 días. OQ-1 convertida en D9.
> - DAG Neo4j sin PRECEDES materializado. Episode.period ISO 8601 como eje temporal.
> - Timestamps UTC epoch nanoseconds en Parquet. system_clock en C++20.
> - ADR-035 OQ-2 cerrada: topología etcd parametrizable por tamaño de instalación.
> - ADR-038 §Anonimización y §Canal de distribución supersedidos.
>
> **Deudas P0/P1 pre-FEDER registradas:** DEBT-PARQUET-SCHEMA-001 (P0 bloqueante), DEBT-VAULT-FEDERATION-001, DEBT-LEGAL-DATA-RETENTION-001, DEBT-KPSEUDO-ROTATION-MIGRATION-001, DEBT-GDPR-ERASURE-001.
>
> **Próximo paso:** examinar CSVs reales de ml-detector y firewall-acl-agent en entorno Vagrant para cerrar DEBT-PARQUET-SCHEMA-001. Sin schema real no hay contrato de interfaz.
>
> 'La memoria distribuida no es solo almacenamiento: es un pacto de confianza temporal entre el edge y el centro.' — Qwen"
> — Consejo de Sabios (8/8) · DAY 147

"""

# Badge ADR-0043 para README
BADGE_ADR043 = "[![ADR-043](https://img.shields.io/badge/ADR--043-Memoria_Episódica_Distribuida-blue)](docs/adr/ADR-0043-memoria-episodica-distribuida-v4.md)"

# Hito DAY 147 para README (añadir línea en milestones)
HITO_ADR043 = "- ✅ DAY 147: **ADR-0043 v4 ACEPTADO** — Memoria Episódica Distribuida, Consejo 8/8, 4 versiones 🎉"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE EDICIÓN
# ─────────────────────────────────────────────────────────────────────────────

def leer(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def escribir(path: Path, contenido: str) -> None:
    path.write_text(contenido, encoding="utf-8")
    print(f"  ✅ Escrito: {path}")


def insertar_antes(texto: str, ancla: str, nuevo: str, etiqueta: str) -> str:
    """Inserta `nuevo` antes de `ancla`. Idempotente: no inserta si `etiqueta` ya existe."""
    if etiqueta in texto:
        print(f"  ⏭  Ya existe (skip): {etiqueta}")
        return texto
    if ancla not in texto:
        print(f"  ⚠️  Ancla no encontrada: {ancla!r}")
        return texto
    return texto.replace(ancla, nuevo + "\n" + ancla, 1)


def insertar_despues(texto: str, ancla: str, nuevo: str, etiqueta: str) -> str:
    """Inserta `nuevo` después de `ancla`. Idempotente."""
    if etiqueta in texto:
        print(f"  ⏭  Ya existe (skip): {etiqueta}")
        return texto
    if ancla not in texto:
        print(f"  ⚠️  Ancla no encontrada: {ancla!r}")
        return texto
    return texto.replace(ancla, ancla + "\n" + nuevo, 1)


def insertar_al_final_de_tabla(texto: str, ancla_fin_tabla: str, nuevas_filas: str, etiqueta: str) -> str:
    """Inserta filas antes del ancla de fin de tabla. Idempotente."""
    if etiqueta in texto:
        print(f"  ⏭  Ya existe (skip): {etiqueta}")
        return texto
    if ancla_fin_tabla not in texto:
        print(f"  ⚠️  Ancla fin tabla no encontrada: {ancla_fin_tabla!r}")
        return texto
    return texto.replace(ancla_fin_tabla, nuevas_filas + "\n" + ancla_fin_tabla, 1)


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZACIÓN README.md
# ─────────────────────────────────────────────────────────────────────────────

def actualizar_readme(path: Path) -> None:
    print(f"\n📄 Actualizando {path}")
    texto = leer(path)

    # 1. Badge ADR-043 — insertar después del badge ADR-042
    ANCLA_BADGE = "[![IRP](https://img.shields.io/badge/IRP-argus--network--isolate_ADR--042-red)]()"
    texto = insertar_despues(
        texto,
        ANCLA_BADGE,
        BADGE_ADR043,
        "ADR--043"
    )

    # 2. Deudas técnicas — añadir nuevas filas al final de la tabla
    # La tabla tiene una fila de cierre implícita justo antes de "### Próxima frontera"
    ANCLA_FIN_DEUDAS = "### Próxima frontera — DAY 146+"
    texto = insertar_antes(
        texto,
        ANCLA_FIN_DEUDAS,
        NUEVAS_DEUDAS_README,
        "DEBT-PARQUET-SCHEMA-001 | 🔴 P0"
    )

    # 3. Hito DAY 147 — añadir línea en milestones (antes del hito DAY 148 si existiera,
    #    o al final de la lista de hitos ✅)
    ANCLA_HITO = "- ✅ DAY 147: **Experimento tres paradigmas"
    if ANCLA_HITO in texto and HITO_ADR043 not in texto:
        # Añadir después de la línea del experimento tres paradigmas
        lineas = texto.split("\n")
        nuevas = []
        for linea in lineas:
            nuevas.append(linea)
            if linea.strip().startswith("- ✅ DAY 147:") and "tres paradigmas" in linea:
                nuevas.append(HITO_ADR043)
        texto = "\n".join(nuevas)
        print("  ✅ Hito ADR-0043 añadido en milestones")
    elif HITO_ADR043 in texto:
        print("  ⏭  Hito ADR-0043 ya existe (skip)")
    else:
        print("  ⚠️  Ancla hito DAY 147 no encontrada")

    escribir(path, texto)


# ─────────────────────────────────────────────────────────────────────────────
# ACTUALIZACIÓN BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

def actualizar_backlog(path: Path) -> None:
    print(f"\n📄 Actualizando {path}")
    texto = leer(path)

    # 1. Nuevas deudas técnicas abiertas — insertar antes de DEBT-ETCD-HA-QUORUM-001
    ANCLA_ETCD = "### DEBT-ETCD-HA-QUORUM-001"
    BLOQUE_DEUDAS_ADR043 = """\
### DEBT-PARQUET-SCHEMA-001 — Schema Parquet ml-detector y firewall-acl-agent
**Severidad:** 🔴 P0 bloqueante
**Estado:** ABIERTO — DAY 147
**Componente:** `ml-detector` + `firewall-acl-agent` + pipeline de ingesta Neo4j

Schema candidato definido en ADR-0043 v4 D4b. Debe validarse contra los CSVs reales producidos por el pipeline en entorno Vagrant. Confirmar granularidad de eventos (por flow vs. por paquete) y política de registro (todos los eventos vs. solo alertas/denies). Sin schema validado no existe contrato de interfaz y el pipeline de ingesta Neo4j no puede implementarse.

**ADR relacionado:** ADR-0043 D4b
**Test de cierre:** schema Parquet candidato validado contra CSVs reales. Tipos Arrow confirmados. Volumen estimado por nodo por mes documentado.
**Estimación:** 1 sesión en Vagrant

---

### DEBT-VAULT-FEDERATION-001 — Offboarding de instalaciones GDPR
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + Vault central + Neo4j

Procedimiento de offboarding cuando un cliente abandona la red aRGus: destrucción certificada del Vault local, política de retención de datos históricos pseudonimizados en Neo4j. La destrucción del Vault local convierte los datos en Neo4j en efectivamente irrecuperables (anonimización efectiva bajo GDPR). Requiere validación jurídica.

**ADR relacionado:** ADR-0043 D7, DEBT-LEGAL-DATA-RETENTION-001
**Test de cierre:** runbook de offboarding ejecutado en entorno de prueba. Confirmación de irrecuperabilidad de datos.
**Estimación:** 2 sesiones + validación jurídica

---

### DEBT-LEGAL-DATA-RETENTION-001 — Dictamen jurídico retención datos post-cliente
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Interlocutor:** Dr. Andrés Caro Lindo (UEx/INCIBE)

Pregunta específica para el jurista: ¿cuándo exactamente los datos pseudonimizados con HMAC-SHA256 dejan de ser datos personales bajo GDPR si la clave de reversión (K_pseudo) existe pero está técnicamente aislada en un Vault destruido certificadamente? La respuesta determina la política de retención histórica post-offboarding.

**ADR relacionado:** ADR-0043 D2, D7, D8
**Test de cierre:** dictamen jurídico documentado. Política de retención registrada en ADR-0043 o ADR complementario.
**Estimación:** gestión externa — no depende de implementación técnica

---

### DEBT-KPSEUDO-ROTATION-MIGRATION-001 — Migración Neo4j tras rotación K_pseudo
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + Neo4j + pipeline de ingesta

La rotación de K_pseudo cambia todos los anon_id. El procedimiento de migración requiere: coordinación con drenado de batches en vuelo, actualización de relaciones :PREVIOUS_IDENTITY en Neo4j, atomicidad durante la migración, auditoría firmada del proceso. Las queries de evolución histórica a través de múltiples rotaciones requieren recursividad Cypher con límite de profundidad explícito.

**ADR relacionado:** ADR-0043 D3, ADR-004
**Test de cierre:** rotación K_pseudo en entorno de prueba con datos históricos. Continuidad de anon_id verificada via :PREVIOUS_IDENTITY. 0 entidades duplicadas.
**Estimación:** 2 sesiones

---

### DEBT-GDPR-ERASURE-001 — Flujo derecho al olvido GDPR Art. 17
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** instalación local + servidor central Neo4j + canal Ed25519

Implementar el flujo completo: (1) instalación local calcula anon_id = HMAC(K_pseudo, identidad_real), (2) borra registros en SQLite, (3) envía comando firmado Ed25519 al servidor central, (4) servidor ejecuta DELETE en Neo4j, (5) registra auditoría inmutable, (6) instalación recibe confirmación y certifica cumplimiento. Limitación conocida: si el mismo dispositivo generó múltiples anon_id por cambio de identidad primaria, el borrado de uno no alcanza automáticamente a los demás.

**ADR relacionado:** ADR-0043 D8
**Test de cierre:** solicitud de borrado E2E en entorno de prueba. Verificación de ausencia del anon_id en Neo4j. Auditoría firmada verificable.
**Estimación:** 2 sesiones + validación jurídica

---

### DEBT-KPSEUDO-HKDF-HIERARCHY-001 — Jerarquía HKDF para K_pseudo
**Severidad:** ⏳ P3 post-FEDER
**Estado:** ABIERTO — DAY 147
**Componente:** Vault local + función de pseudonimización en nodo

Derivar subclaves especializadas desde K_root usando HKDF (NIST SP 800-108): K_pseudo_host, K_pseudo_flow, K_pseudo_model. Reduce el radio de daño ante compromiso de subclave individual y permite rotación selectiva sin romper coherencia en otras dimensiones. Relevante especialmente para instalaciones de alto valor (hospitales universitarios, municipios grandes). Alineado con ADR-004 (cooldown y máximo 2 claves concurrentes).

**ADR relacionado:** ADR-0043 D3, ADR-004
**Test de cierre:** derivación HKDF en Vault local. Verificación de independencia entre subclaves. Rotación de K_pseudo_flow sin afectar K_pseudo_host.
**Estimación:** 1 sesión post-FEDER

---

"""
    texto = insertar_antes(
        texto,
        ANCLA_ETCD,
        BLOQUE_DEUDAS_ADR043,
        "DEBT-PARQUET-SCHEMA-001 — Schema Parquet"
    )

    # 2. Decisiones de diseño consolidadas — añadir antes del cierre de la tabla
    # La tabla termina justo antes de "---\n\n## 📊 Estado global"
    ANCLA_FIN_DECISIONES = "---\n\n## 📊 Estado global del proyecto"
    texto = insertar_antes(
        texto,
        ANCLA_FIN_DECISIONES,
        NUEVAS_DECISIONES_BACKLOG,
        "MAC unicast como identidad primaria"
    )

    # 3. Estado global del proyecto — añadir nuevas líneas antes de la sección de cierre
    ANCLA_FIN_ESTADO = "ADR-031 aRGus-seL4:"
    texto = insertar_antes(
        texto,
        ANCLA_FIN_ESTADO,
        NUEVAS_ENTRADAS_ESTADO,
        "ADR-0043 v4 Memoria Episódica Distribuida"
    )

    # 4. Nota Consejo ADR-0043 — insertar antes de las notas DAY 147 del experimento
    ANCLA_NOTAS_147 = "## 📝 Notas del Consejo de Sabios — DAY 147 (8/8)"
    texto = insertar_antes(
        texto,
        ANCLA_NOTAS_147,
        NOTA_CONSEJO_ADR043.strip(),
        "ADR-0043 v4 (8/8) · DAY 147"
    )

    # 5. Cerrar ADR-035 OQ-2 en las notas (si existe la mención como abierta)
    # Buscar y anotar que OQ-2 fue cerrada por ADR-0043
    PATRON_OQ2 = "OQ-2 | Despliegues muy pequeños"
    if PATRON_OQ2 in texto and "CLOSED — ADR-0043" not in texto:
        texto = texto.replace(
            "OQ-2 | Despliegues muy pequeños",
            "OQ-2 [CLOSED — ADR-0043 D6] | Despliegues muy pequeños"
        )
        print("  ✅ ADR-035 OQ-2 marcada como CLOSED")
    elif "CLOSED — ADR-0043" in texto:
        print("  ⏭  ADR-035 OQ-2 ya marcada como CLOSED (skip)")

    escribir(path, texto)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Actualiza BACKLOG.md y README.md con ADR-0043 v4")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Ruta al directorio raíz del repositorio (default: directorio actual)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué se haría sin escribir nada"
    )
    args = parser.parse_args()

    repo = Path(args.repo_path).resolve()
    readme = repo / "README.md"
    backlog = repo / "docs" / "BACKLOG.md"

    print(f"📁 Repositorio: {repo}")

    # Verificar existencia
    errores = []
    for f in [readme, backlog]:
        if not f.exists():
            errores.append(f"No encontrado: {f}")
    if errores:
        for e in errores:
            print(f"  ❌ {e}")
        sys.exit(1)

    if args.dry_run:
        print("\n🔍 DRY RUN — no se escribirá nada")
        print(f"  Se actualizaría: {readme}")
        print(f"  Se actualizaría: {backlog}")
        sys.exit(0)

    # Ejecutar actualizaciones
    actualizar_readme(readme)
    actualizar_backlog(backlog)

    print("\n✅ Actualizaciones completadas.")
    print("\nAcciones manuales recomendadas tras ejecutar este script:")
    print("  1. Copiar docs/adr/ADR-0043-memoria-episodica-distribuida-v4.md al repo")
    print("  2. Anotar ADR-035 OQ-2 como CLOSED con referencia a ADR-0043 D6")
    print("  3. Anotar §Anonimización y §Canal de distribución en ADR-038 como SUPERSEDED")
    print("  4. Añadir referencia a ADR-0043 en §8 Future Work de ADR-004")
    print("  5. git add -A && git commit -m 'docs: ADR-0043 v4 aceptado, actualiza BACKLOG y README'")


if __name__ == "__main__":
    main()