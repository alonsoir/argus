Síntesis Consejo DAY 119
Consenso unánime (5/5)
QVeredictoAcción DAY 120Q1 sync-pubkeyVálido pero incompleto — añadir verificación post-sync + idempotenciaMejorar targetQ2 Vagrantfile/MakefileSeparación correcta — formalizar con make check-system-depsNuevo targetQ3 bootstrapSÍ, obligatorio — con checkpoints, verbose, idempotentemake bootstrapQ4 contrato payloadfloat32[] + num_features + validación NaN/Inf + fallo explícitodocs/xgboost/plugin-contract.mdQ5 puntos ciegosPersistencia etcd, permisos plugins, caché CMake, reloj VMmake post-up-verify
Observación crítica destacada — ChatGPT5

Mover la pubkey a fichero runtime, no a CMake.
file(READ "/etc/ml-defender/plugins/plugin_pubkey.hex" PUBKEY_HEX) en CMakeLists.txt.
Elimina sync-pubkey completamente. 100% reproducible. No mezcla host/VM.

Esta es la solución estructural real. Los demás miembros robustecen sync-pubkey como parche — ChatGPT5 ataca la causa raíz.
Nuevos items para DAY 120
ItemTipoOrigenmake bootstrap (9 pasos, checkpoints, verbose)Bloqueante DAY 120Unánimemake check-system-depsBloqueante DAY 120Qwen + Grokmake post-up-verifyBloqueante DAY 120QwenPubkey → fichero runtime (eliminar sync-pubkey)Bloqueante DAY 120ChatGPT5docs/xgboost/plugin-contract.mdNo bloqueanteUnánimefeature_schema_v1.mdNo bloqueanteChatGPT5DEBT-XGBOOST-APT-001 versión bookwormNo bloqueante