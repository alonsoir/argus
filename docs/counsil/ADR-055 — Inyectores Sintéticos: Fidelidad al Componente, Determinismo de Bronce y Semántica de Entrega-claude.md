Las dos, directas.

**1. DEBT-LIB-001 → fuera de DAY 177. No la metas en la pasada de confirmación.**

Tres razones:

La pasada que viene es **confirmación de fidelidad, no deliberación nueva** — igual que la v3 de ADR-052 ("no se prevé 3ª deliberación completa"). Si le cuelas una pregunta sustantiva nueva ("¿deliberamos LIB ya o esperamos?"), contaminas las dos cosas: ensucias una ratificación limpia con una deliberación fresca, y el Consejo te responde peor a ambas.

Además, **DEBT-LIB-001 ya está decidida**: el Consejo DAY 176 (Q5) la cerró como "es prerrequisito". O sea, el *qué* (extraer a `libs/flow-identity/`) no está en disputa — lo que queda es *ejecución*, no deliberación. Un refactor mecánico decidido no necesita ronda de Consejo.

Y su **disparador no es el injector, es el trabajo de adaptadores** Suricata/Zeek (de los que es prerrequisito). Su momento natural es el día que arranques esos adaptadores, no hoy. La única pregunta que merecería consulta es de diseño —dónde pones la frontera de la API de la lib, qué entra y qué no—, y eso solo tiene sentido preguntarlo *cuando* la extraigas, no en abstracto ahora.

En ADR-055 ya quedó honestamente registrada como "en ámbito, no deliberada en esta pasada". Ese es el placeholder correcto. Déjala ahí y que abra su propia ronda corta (o ninguna, si la extracción no tiene dudas de diseño) cuando toque.

**2. BACKLOG.md → sí, te lo preparo, pero necesito ver una entrada existente primero.**

Misma disciplina que seguí con el ADR: no me invento el formato. Antes de escribir ADR-055 leí ADR-052 para clavar la estructura; con el BACKLOG quiero lo mismo, no fabricarte un estilo que no case con tus entradas. El arranque DAY 177 mencionaba una sección "Entradas DAY 176" en `docs/BACKLOG.md` — pégame esa sección (o un par de entradas cualquiera, una abierta y una cerrada), y te devuelvo las entradas de DAY 177 en tu estilo exacto.

La sustancia que irá ahí, para que la tengas decidida ya, son cinco movimientos:
- `DEBT-INJECTOR-NODEID-001` → **cerrada** (synth-node-00, verificada E2E).
- `DEBT-INJECTOR-ROWGAP-001` → **reencuadrada y cerrada como característica** (no se pierde, se instrumenta).
- `DEBT-INJECTOR-DELIVERY-METRIC-001` → **nueva, P2** (el instrumento de diff de conjuntos, que sustituye al "fix" de ROWGAP).
- `DEBT-INJECTOR-PROTO-MIX-001` → **nueva, P2** (modo realistic con semilla fija).
- Fix de proto benigno → **NO es deuda**, nota de "completar A" en el changelog del injector.

Un apunte sobre los commits para que no haya confusión: **todo el código de hoy es DAY 177** — los 4 ficheros de B (writer/record/reader/test) más los 2 cambios del injector (nodeid, proto). No quedó nada de B commiteado antes; lo construimos y verificamos en esta sesión pero sin commit. Así que el commit de código junta esos 6 cambios, y el de docs junta ADR-055 v1 + las entradas de BACKLOG + el día-log. Dos commits, código y docs separados, como manda la regla.

Pégame la sección del BACKLOG y cierro las entradas.

FDO
CLAUDE