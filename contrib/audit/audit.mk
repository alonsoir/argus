# ============================================================================
# SECURITY AUDIT (DAY 180) — analisis estatico + taint especifico de aRGus
# ============================================================================
# Complementa Trivy (CVEs de deps) y -Werror (memoria/tipos) con lo que ninguno
# caza: inyeccion por interpolacion de datos no confiables en sinks peligrosos.
#   audit-static : cppcheck sobre el codigo de los componentes (no third_party)
#   audit-taint  : semgrep p/c + reglas custom (contrib/audit/argus-taint.yml)
#   audit        : ambos, fail-closed (exit 1 si hay hallazgos ERROR)
#
# Gate de CI: encadenar tras test-all, igual que el gate de Snyk.
# Todo corre en el guest sobre /vagrant (REGLA: nunca cmake directo desde host).
# ============================================================================
.PHONY: audit audit-static audit-taint audit-tools

# Componentes a auditar (codigo propio; se excluye third_party/dist/experiments).
AUDIT_DIRS := sniffer/src ml-detector/src firewall-acl-agent/src \
              etcd-server/src correlation-engine/src crypto-transport \
              plugin-loader rag-ingester/src common-rag-ingester libs

# Verifica que cppcheck + semgrep estan en el guest (se instalan en provision,
# ver Vagrantfile bloque all-dependencies). NO instala en runtime (ADR-039:
# separacion build/runtime). Si faltan -> re-provisionar.
audit-tools:
	@echo "🔧 Verificando herramientas de auditoria en el guest..."
	@vagrant ssh -c "command -v cppcheck >/dev/null 2>&1" \
	  || { echo "❌ cppcheck ausente. Re-provisiona: vagrant provision defender"; exit 1; }
	@vagrant ssh -c "command -v semgrep >/dev/null 2>&1" \
	  || { echo "❌ semgrep ausente. Re-provisiona: vagrant provision defender"; exit 1; }
	@echo "✅ cppcheck + semgrep disponibles"

# ── Analisis estatico C++ (cppcheck) ────────────────────────────────────────
audit-static: audit-tools
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔬 AUDIT (1/2) — cppcheck (analisis estatico C++)         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c "cd /vagrant && cppcheck \
	    --enable=warning,performance,portability \
	    --inline-suppr --suppress=missingInclude \
	    --std=c++20 --error-exitcode=2 --quiet \
	    --template='{file}:{line}: [{severity}] {message}' \
	    $(AUDIT_DIRS) 2>&1" \
	  && echo "✅ cppcheck: sin hallazgos" \
	  || (echo ""; echo "❌ AUDIT-STATIC: cppcheck encontro problemas (ver arriba)"; exit 1)

# ── Taint / inyeccion (semgrep estandar + reglas aRGus) ──────────────────────
audit-taint: audit-tools
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🛡️  AUDIT (2/2) — semgrep (taint: shell + Cypher)         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo "── [a] reglas custom aRGus (H-1 Cypher / H-2 command injection) ──"
	@vagrant ssh -c "cd /vagrant && semgrep scan --error --quiet \
	    --config contrib/audit/argus-taint.yml \
	    $(AUDIT_DIRS)" \
	  && echo "✅ reglas aRGus: limpio" \
	  || (echo ""; echo "❌ AUDIT-TAINT: regla custom disparada (inyeccion potencial)"; exit 1)
	@echo "── [b] ruleset estandar C (semgrep p/c) ──"
	@vagrant ssh -c "cd /vagrant && semgrep scan --error --quiet \
	    --config p/c --exclude third_party --exclude dist --exclude experiments \
	    $(AUDIT_DIRS)" \
	  && echo "✅ semgrep p/c: limpio" \
	  || (echo ""; echo "❌ AUDIT-TAINT: hallazgo en ruleset estandar p/c"; exit 1)

# ── Orquestador (gate completo) ──────────────────────────────────────────────
audit: audit-static audit-taint
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ AUDIT COMPLETO — sin hallazgos de severidad ERROR      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo "   medir, no votar: este gate mide; el Consejo decide el diseno."
