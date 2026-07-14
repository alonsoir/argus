Antes de seguir: cierra el día por escrito
Son las deudas nuevas y valen dinero. Si no las anotas ahora, mañana serán arqueología:

DEBT-SOURCE-TREE-BACKUP-FILES-001 → P1 (era P2). Razón nueva: no es que el árbol confunda al grep; es que el proyecto compilaba contra dos declaraciones de la misma clase. Sobrevivió porque eran idénticas byte a byte. Si hubieran divergido en un campo en vez de un método, no habría error de compilación — habría corrupción de memoria silenciosa.
DEBT-SHARDED-INIT-CALL-ONCE-MUTE-001 → P2. initialize() descarta la Config nueva en silencio. Mitigado con clear(). El defecto sigue.
DEBT-FULL-CONTRACT-POPULATION-THEATRE-001 → P1. total_fields += 7, comprueba 6. dpkts, dbytes y 5 flags se cuentan como poblados sin mirarlos. Un population_rate bonito por construcción.
Casos 19, 20, 21 del patrón — y el 21 es mío: una red de seguridad que se disparó contra su propia documentación.
Trampa: ctes t | grep -c sobre un test que no compila devuelve 0, igual que un test que corre y no imprime. Un cero que significa "no medí nada".