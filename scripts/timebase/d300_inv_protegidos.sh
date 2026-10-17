#!/usr/bin/env bash
# DAY300: inventario para el paso 5 de la etapa 1, DEBT-FW-PROTECTED-RANGES-001 (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "BACKLOG: definicion de la deuda"
git grep -n -A 25 "DEBT-FW-PROTECTED-RANGES-001" -- docs/BACKLOG.md
sec "diseno DAY298: rangos protegidos"
git grep -n -i -B 2 -A 8 -e "protegid" -e "protected" -- docs/ml-heads/diseno_etapa1_histeresis_day298.md
sec "firewall: menciones a protegidos / allowlist / whitelist"
git grep -n -i -e "protegid" -e "protected_range" -e "allowlist" -e "whitelist" -- firewall-acl-agent/src firewall-acl-agent/include firewall-acl-agent/config
sec "firewall: validador de CIDR (reutilizable)"
git grep -n -e "class " -e "bool " -e "struct " -e "std::optional" -- 'firewall-acl-agent/include/*cidr*' 'firewall-acl-agent/src/*cidr*'
sec "firewall: ficheros de DdosShadowPolicy"
git grep -l "DdosShadowPolicy" -- firewall-acl-agent
sec "firewall: donde decide la sombra (DROP / dry_run)"
git grep -n -e "dry_run" -e "SOMBRA-DDOS" -- firewall-acl-agent/src | head -n 40
sec "firewall: JSON de configuracion (ficheros)"
git ls-files firewall-acl-agent/config
