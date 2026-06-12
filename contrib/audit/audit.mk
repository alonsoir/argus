# ============================================================================
# SECURITY AUDIT (DAY 180) — analisis estatico + taint especifico de aRGus
# ============================================================================
.PHONY: audit audit-static audit-taint audit-tools

AUDIT_DIRS := sniffer/src ml-detector/src firewall-acl-agent/src \
              etcd-server/src correlation-engine/src crypto-transport \
              plugin-loader rag-ingester/src common-rag-ingester libs

audit-tools:
	echo "🔧 Verificando herramientas de auditoria en el guest..."
	vagrant ssh -c "command -v cppcheck >/dev/null 2>&1" || { echo "❌ cppcheck ausente. Re-provisiona: vagrant provision defender"; exit 1; }
	vagrant ssh -c "command -v semgrep >/dev/null 2>&1" || { echo "❌ semgrep ausente. Re-provisiona: vagrant provision defender"; exit 1; }
	echo "✅ cppcheck + semgrep disponibles"

audit-static: audit-tools
	echo ""
	echo "🔬 AUDIT (1/2) — cppcheck (analisis estatico C++)"
	vagrant ssh -c "cd /vagrant && cppcheck --enable=warning,performance,portability --inline-suppr --suppress=missingInclude --suppress=unmatchedSuppression -i sniffer/src/kernel --std=c++20 --quiet --template='{file}:{line}: [{severity}] {message}' $(AUDIT_DIRS) 2>/tmp/argus-cppcheck.txt; cat /tmp/argus-cppcheck.txt; if grep -q '\[error\]' /tmp/argus-cppcheck.txt; then echo ''; echo '❌ AUDIT-STATIC: cppcheck encontro errores [error]'; exit 1; else WARN=\$$(grep -cE '\[(performance|portability|warning)\]' /tmp/argus-cppcheck.txt); echo ''; echo \"✅ cppcheck: sin [error] (\$$WARN aviso(s) no-bloqueante(s))\"; fi"

# ⚠️  DEBT-SEMGREP-CPP-HANG-001: semgrep-core se cuelga sobre el arbol C++ completo
#     (no ficheros sueltos; NO es memoria, 5.6GB libres). Reglas custom validadas
#     OK sobre ficheros individuales. NO usar como gate hasta resolver el debt.
audit-taint: audit-tools
	echo ""
	echo "🛡️  AUDIT (2/2) — semgrep (taint: shell + Cypher)"
	echo "── [a] reglas custom aRGus (H-1 Cypher / H-2 command injection) ──"
	vagrant ssh -c "cd /vagrant && semgrep scan --error --quiet --config contrib/audit/argus-taint.yml $(AUDIT_DIRS)" && echo "✅ reglas aRGus: limpio" || (echo ""; echo "❌ AUDIT-TAINT: regla custom disparada (inyeccion potencial)"; exit 1)
	echo "── [b] ruleset estandar C (semgrep p/c) ──"
	vagrant ssh -c "cd /vagrant && semgrep scan --error --quiet --config p/c --exclude third_party --exclude dist --exclude experiments $(AUDIT_DIRS)" && echo "✅ semgrep p/c: limpio" || (echo ""; echo "❌ AUDIT-TAINT: hallazgo en ruleset estandar p/c"; exit 1)

audit: audit-static audit-taint
	echo ""
	echo "✅ AUDIT COMPLETO — sin hallazgos de severidad ERROR"
	echo "   medir, no votar: este gate mide; el Consejo decide el diseno."
