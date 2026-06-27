Q1: COMPLAIN primero. Unánime con el Consejo. CAP_BPF + CAP_SYS_ADMIN son demasiado sensibles para ir directo a enforce.

Q2: Dos modos explícitos: --reset (sin firma) + operador ejecuta provision.sh sign manualmente. 
En dev, flag opcional --auto-sign. La prohibición de firma automática en producción es innegociable.

Q3: Me alineo con Gemini y Qwen: DEBT-ADR025-D11 primero. El deadline 18 Apr es real y no se mueve. 
AppArmor arranca en complain de todos modos — no bloqueará --reset. Diseñar los perfiles incluyendo los paths de --reset 
desde el primer borrador elimina el riesgo señalado por ChatGPT/Grok.

Q4: Dos checks de mayor impacto/coste: permisos de ficheros sensibles (Qwen — simple, alto impacto) + consistencia JSONs 
con plugins reales (DeepSeek — cierra la cadena completa).