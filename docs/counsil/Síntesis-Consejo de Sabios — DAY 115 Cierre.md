Síntesis Árbitro DAY 115 Cierre
Q1 — AppArmor: complain vs enforce
6/6 COMPLAIN primero. Unanimidad. Flujo: complain → pipeline OK + logs limpios → enforce.
Nota ARM64: AppArmor funcionalmente idéntico en x86 y ARM64. Paths de dispositivos pueden diferir — parametrizar si necesario. Validar en RPi antes de enforce.
Q2 — provision.sh --reset scope
6/6: NO auto-firma en producción. Proceso en dos pasos:

provision.sh --reset → regenera seed_family + keypairs Ed25519 + keypair de firma. Sistema queda en fail-closed.
Operador ejecuta provision.sh sign / make sign-plugins explícitamente.
Flag opcional --dev para entornos de desarrollo (Grok/Qwen). En producción: mensaje claro post-reset indicando el paso manual obligatorio.

Q3 — Orden AppArmor vs DEBT-ADR025-D11
División: 3 AppArmor primero (ChatGPT, DeepSeek, Grok) vs 2 DEBT-ADR025-D11 primero (Gemini, Qwen). Claude: DEBT-ADR025-D11 primero.
Veredicto árbitro: DEBT-ADR025-D11 primero. Razones:

Deadline 18 Apr no se mueve (4 días).
AppArmor arranca en complain — no bloqueará --reset.
Los perfiles AppArmor se diseñan incluyendo paths de --reset desde el principio, eliminando el riesgo de bloqueo posterior.
Posición ChatGPT/DeepSeek/Grok registrada como minoría.

Q4 — TEST-PROVISION-1 checks faltantes
Dos checks añadir en DAY 116:

Check 6: Permisos de ficheros sensibles — find /etc/ml-defender /usr/lib/ml-defender -name "*.sk" -perm /022 (Qwen, más simple y alto impacto inmediato)
Check 7: Consistencia JSONs — cada plugin referenciado en configs de producción tiene .so + .sig presente (DeepSeek)

Diferido para PHASE 4: hash SHA-256 de binarios contra manifest firmado (Grok/ChatGPT) — requiere infraestructura adicional no en scope actual.