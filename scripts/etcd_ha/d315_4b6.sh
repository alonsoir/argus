#!/usr/bin/env bash
# [ETCD-B4-D315] DEBT-ETCD-HA-TLS-RAFT-001, paso 4b.6 (decisiones de Alonso DAY315).
#   B4: POST /register devuelve las rutas con el nombre completo (= CN): /secrets/<CN> y /config/<CN>. Antes cortaba en
#       el primer guion (firewall-acl-agent -> /secrets/firewall): con mTLS la regla 'propio' daba 403 y el firewall se
#       quedaba sin clave HMAC para su CSV (reproducido en el banco). Nadie verifica hoy el CSV del firewall con
#       /secrets/firewall (git grep): cambiar la ruta no rompe ninguna verificación.
#   crypto_token fuera de los dos lados: el servidor no tiene ninguna ruta /crypto; ServicePaths::is_valid() de
#       etcd-client deja de exigirlo (solo hmac_key y config).
#   Fuera las variantes muertas de etcd-client (DEBT-ETCD-CLIENT-DEAD-VARIANTS-001): etcd_client_base.cpp,
#       etcd_client_manual.cpp, *.day54_* (ningún CMake ni el Makefile las nombran).
#   NO toca (decisión DAY315): HttpEtcdRegistrar y CryptoEpochCoordinator de common/ (ADR-045) -> se decide en el paso 5.
#   Probado en el banco con g++-12 y las opciones de production: etcd_server.cpp y etcd_client.cpp 0 avisos.
# Requiere el paso 3 (d315_paso3_codigo.sh) aplicado. No toca git.
# Uso (en el defender):  bash d315_4b6.sh --check [RAIZ]  |  bash d315_4b6.sh --apply [RAIZ]
set -euo pipefail
export LC_ALL=C
MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"
declare -A SHA=(
  [etcd-server/src/etcd_server.cpp]=056cd1ebc4e58c9b8a231279f785ef2ac7e75c23716ee5a8e01b9b9de3e3aff7
  [etcd-client/include/etcd_client/etcd_client.hpp]=c636d4a3e44137b00a58129db623aa38d79874bcc7fb2e379e72786cdb8310d1
  [etcd-client/src/etcd_client.cpp]=d6702563ee7b59b8edef331f913d01e3f34c208a9d3eb1ab0d494b2affc563c9
  [etcd-client/tests/test_service_discovery.cpp]=5a946e9c813c40303838bbb1fab16f4dc7cbbb58419a97489f3e8f1cfb001a42
  [firewall-acl-agent/include/firewall/etcd_client.hpp]=f0ef52679800032883e7f656870f9e734a03589ee0eecbd12400b9d7852a7ea0
  [etcd-client/src/etcd_client_base.cpp]=a6580ec3c1eae993e0d9622f8b77772628b0872bda69c7fae659774d231bfbb3
  [etcd-client/src/etcd_client_manual.cpp]=a6580ec3c1eae993e0d9622f8b77772628b0872bda69c7fae659774d231bfbb3
  [etcd-client/src/etcd_client.cpp.day54_broken]=2a74b5d4b75aa1bb175a1c5cfe3300f829746ceb9cb0df43e1fffec83da9e959
  [etcd-client/include/etcd_client/etcd_client.hpp.day54_hmac_only]=a60885c57f82cb6f2799e08e19edc972979e66751e0ae31cda243474c0e5dd32
)
if grep -q 'ETCD-B4-D315' etcd-server/src/etcd_server.cpp && [ ! -e etcd-client/src/etcd_client_base.cpp ]; then
  echo "[ETCD-B4-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi
FALLOS=0
grep -q 'ETCD-ALMACEN-FATAL-D315' etcd-server/include/etcd_server/etcd_server_almacen.hpp && echo "✅ paso 3 aplicado" \
  || { echo "❌ falta el paso 3 (d315_paso3_codigo.sh)"; FALLOS=$((FALLOS+1)); }
for f in "${!SHA[@]}"; do
  if [ ! -f "$f" ]; then echo "❌ falta $f"; FALLOS=$((FALLOS+1)); continue; fi
  h=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$h" = "${SHA[$f]}" ]; then echo "✅ $f (${h:0:16})"; else echo "❌ $f: sha256 $h, se esperaba ${SHA[$f]}"; FALLOS=$((FALLOS+1)); fi
done
N=$( { git grep -l -E 'etcd_client_base|etcd_client_manual|day54_broken|day54_hmac_only' -- '*CMakeLists.txt' Makefile '*.cmake' 2>/dev/null || true; } | wc -l)
[ "$N" = 0 ] && echo "✅ ningún CMake ni el Makefile nombran las variantes muertas" || { echo "❌ $N ficheros de compilación nombran las variantes"; FALLOS=$((FALLOS+1)); }
if [ "$FALLOS" != 0 ]; then echo "[ETCD-B4-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[ETCD-B4-D315] --check: todo listo para --apply"; exit 0; fi

python3 - "$PWD" <<'PY'
import os, sys

RAIZ = sys.argv[1]


def cambiar(rel, pares):
    p = os.path.join(RAIZ, rel)
    s = open(p, encoding="utf-8").read()
    for viejo, nuevo in pares:
        n = s.count(viejo)
        assert n == 1, f"{rel}: {viejo[:70]!r} aparece {n} veces"
        s = s.replace(viejo, nuevo)
    open(p, "w", encoding="utf-8").write(s)


# ------------------------------------------------------------------ etcd-server: rutas con el CN, sin crypto_token
cambiar("etcd-server/src/etcd_server.cpp", [(
    """        // Extract component short name (e.g., "firewall-acl-agent" -> "firewall")
        std::string short_name = component_name;
        size_t dash_pos = component_name.find('-');
        if (dash_pos != std::string::npos) short_name = component_name.substr(0, dash_pos);
        json response = {
            {"status", "success"},
            {"message", "Componente registrado correctamente"},
            {"component", component_name},
            {"paths", {
                {"hmac_key", "/secrets/" + short_name},
                {"crypto_token", "/crypto/" + short_name + "/tokens"},
                {"config", "/config/" + short_name}
            }}
        };
""",
    """        // [ETCD-B4-D315] rutas con el nombre completo (= CN): la autorización de /secrets/{c} y /config/{c} exige
        // 'propio'. Antes se cortaba en el primer guion (firewall-acl-agent -> /secrets/firewall: 403 con mTLS, sin clave
        // HMAC para su CSV). Fuera crypto_token: apuntaba a /crypto/<corto>/tokens, ruta que este servidor no tiene.
        json response = {
            {"status", "success"},
            {"message", "Componente registrado correctamente"},
            {"component", component_name},
            {"paths", {
                {"hmac_key", "/secrets/" + component_name},
                {"config", "/config/" + component_name}
            }}
        };
""")])

# ------------------------------------------------------------------ etcd-client: ServicePaths sin crypto_token
cambiar("etcd-client/include/etcd_client/etcd_client.hpp", [(
    """struct ServicePaths {
    std::string hmac_key;      // e.g., "/secrets/firewall"
    std::string crypto_token;  // e.g., "/crypto/firewall/tokens"
    std::string config;        // e.g., "/config/firewall"

    // Helper to check if paths were received from etcd-server
    bool is_valid() const {
        return !hmac_key.empty() && !crypto_token.empty() && !config.empty();
    }
};""",
    """// [ETCD-B4-D315] con el nombre completo del componente (= CN del certificado); sin crypto_token (el etcd-server no tiene
// ninguna ruta /crypto: era un dato muerto que además hacía falta para is_valid())
struct ServicePaths {
    std::string hmac_key;      // e.g., "/secrets/firewall-acl-agent"
    std::string config;        // e.g., "/config/firewall-acl-agent"

    // Helper to check if paths were received from etcd-server
    bool is_valid() const {
        return !hmac_key.empty() && !config.empty();
    }
};""")])

cambiar("etcd-client/src/etcd_client.cpp", [
    ("""                pImpl->service_paths_.crypto_token = paths.value("crypto_token", "");
""", ""),
    ("""                std::cout << "   - Crypto token: " << pImpl->service_paths_.crypto_token << std::endl;
""", ""),
])

cambiar("etcd-client/tests/test_service_discovery.cpp", [
    ("""    assert(!paths.crypto_token.empty() && "Crypto token path is empty");
""", ""),
    ("""    std::cout << "   - Crypto token: " << paths.crypto_token << std::endl;
""", ""),
    ("""    assert(paths.crypto_token.find("/crypto/") == 0 && "Crypto path doesn't start with /crypto/");
    assert(paths.config.find("/config/") == 0 && "Config path doesn't start with /config/");
""",
     """    assert(paths.config.find("/config/") == 0 && "Config path doesn't start with /config/");
    // [ETCD-B4-D315] nombre completo (= CN), sin cortar en el primer guion
    assert(paths.hmac_key == "/secrets/test-service-discovery" && "HMAC path is not /secrets/<component>");
    assert(paths.config == "/config/test-service-discovery" && "Config path is not /config/<component>");
"""),
])

# ------------------------------------------------------------------ firewall: el comentario del ejemplo
cambiar("firewall-acl-agent/include/firewall/etcd_client.hpp", [(
    """     * @param key_path Path to key in etcd (e.g., "/secrets/firewall/log_hmac_key")""",
    """     * @param key_path Path to key in etcd-server (e.g., "/secrets/firewall-acl-agent", the one /register returns)""")])

# ------------------------------------------------------------------ variantes muertas de etcd-client
for rel in ("etcd-client/src/etcd_client_base.cpp", "etcd-client/src/etcd_client_manual.cpp",
            "etcd-client/src/etcd_client.cpp.day54_broken", "etcd-client/include/etcd_client/etcd_client.hpp.day54_hmac_only"):
    os.remove(os.path.join(RAIZ, rel))
print("p4b6_codigo: etcd_server.cpp, etcd-client (cabecera, fuente, test), comentario del firewall; 4 variantes muertas borradas")
PY

set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
! grep -q 'short_name' etcd-server/src/etcd_server.cpp && grep -q '"/secrets/" + component_name' etcd-server/src/etcd_server.cpp; chk "etcd-server: /register con el nombre completo, sin short_name" $?
[ "$(git grep -h 'crypto_token' -- etcd-server/src etcd-client/include etcd-client/src etcd-client/tests | grep -vc '^ *//')" = 0 ]; chk "sin crypto_token en el código trackeado de etcd-server ni etcd-client (git grep; solo comentarios)" $?
grep -q 'return !hmac_key.empty() && !config.empty();' etcd-client/include/etcd_client/etcd_client.hpp;                            chk "is_valid(): solo hmac_key y config" $?
[ ! -e etcd-client/src/etcd_client_base.cpp ] && [ ! -e etcd-client/src/etcd_client_manual.cpp ] && [ ! -e etcd-client/src/etcd_client.cpp.day54_broken ] && [ ! -e etcd-client/include/etcd_client/etcd_client.hpp.day54_hmac_only ]; chk "4 variantes muertas borradas" $?
echo "[ETCD-B4-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
