#!/usr/bin/env bash
# =============================================================================
# tools/provision.sh
# ML Defender — Cryptographic Provisioning Tool
#
# Genera keypairs Ed25519 + seeds ChaCha20 para todos los componentes
# del pipeline y sus plugins declarados en los JSONs de contrato.
#
# REQUIERE: sudo (escribe en /etc/ml-defender/ con chmod 0600)
# COMPATIBLE: AppArmor desde el primer día — paths fijos, nunca dinámicos
#             (ADR-019: /etc/ml-defender/{component}/ es el path canónico)
#
# PHASE 1 (DAY 95): keypairs Ed25519 + seed aleatorio en disco (chmod 0600)
# PHASE 2 (futuro): seed.enc cifrado con clave pública del receptor (seed-client)
#                   La HMAC key NO estará nunca en el JSON — se deriva del
#                   intercambio de keypairs en provisioning (ADR-013)
#
# USO:
#   sudo bash tools/provision.sh full                    # primer arranque
#   sudo bash tools/provision.sh status                  # tabla de estado
#   sudo bash tools/provision.sh verify                  # verifica todo (CI/CD)
#   sudo bash tools/provision.sh reprovision sniffer     # re-provisiona uno
#
# Authors: Alonso Isidoro Roman + Claude (Anthropic)
# DAY 97 — 25 marzo 2026
# =============================================================================

set -euo pipefail
set -o noclobber          # REC-2: prevenir truncado accidental con >

# =============================================================================
# CONFIGURACIÓN — SINGLE SOURCE OF TRUTH
# Estos paths son los que AppArmor permitirá (ADR-019).
# Si cambias un path aquí, debes actualizar los perfiles AppArmor también.
# =============================================================================

readonly KEYS_ROOT="/etc/ml-defender"
readonly SEED_BYTES=32           # ChaCha20 requiere exactamente 32 bytes
readonly KEY_ALGORITHM="ed25519" # Ed25519 para keypairs de identidad

# Componentes del pipeline en orden de dependencia
# etcd-server primero — es la autoridad de semillas
readonly COMPONENTS=(
    "etcd-server"
    "sniffer"
    "ml-detector"
    "firewall-acl-agent"
    "rag-ingester"
    "rag-security"
)

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Service user para ownership de seeds (DEBT-PROVISION-PORTABILITY-001)
ARGUS_SERVICE_USER="${ARGUS_SERVICE_USER:-vagrant}"

# =============================================================================
# UTILIDADES
# =============================================================================

log_info()    { echo -e "${GREEN}  ✅${NC} $*"; }
log_warn()    { echo -e "${YELLOW}  ⚠️ ${NC} $*"; }
log_error()   { echo -e "${RED}  ❌${NC} $*" >&2; }
log_section() { echo -e "\n${BOLD}${BLUE}══ $* ══${NC}"; }
log_item()    { echo -e "     ${CYAN}→${NC} $*"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "provision.sh debe ejecutarse con sudo"
        echo "  Uso: sudo bash /vagrant/tools/provision.sh <modo>"
        exit 1
    fi
}

check_dependencies() {
    local missing=()
    command -v openssl    >/dev/null 2>&1 || missing+=("openssl")
    command -v jq         >/dev/null 2>&1 || missing+=("jq")
    command -v wget       >/dev/null 2>&1 || missing+=("wget")
    command -v pkg-config >/dev/null 2>&1 || missing+=("pkg-config")
    command -v tmux       >/dev/null 2>&1 || missing+=("tmux")

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Dependencias faltantes: ${missing[*]}"
        echo "  Instalando dependencias faltantes..."
        apt-get install -y --quiet "${missing[@]}" >/dev/null 2>&1 || {
            log_error "No se pudieron instalar: ${missing[*]}"
            echo "  Instalar manualmente: apt-get install -y openssl jq wget pkg-config tmux"
            exit 1
        }
        log_item "Dependencias instaladas: ${missing[*]}"
    fi

    # Verificar que OpenSSL soporta Ed25519
    if ! openssl genpkey -algorithm ed25519 -out /dev/null 2>/dev/null; then
        log_error "OpenSSL no soporta Ed25519. Requiere OpenSSL >= 1.1.1"
        openssl version
        exit 1
    fi
}

# =============================================================================
# ENTROPÍA — DEBT-CRYPTO-003b
# Garantiza suficiente entropía antes de generar material criptográfico.
# Si el pool es bajo, instala haveged como fuente de entropía adicional.
# =============================================================================

check_entropy() {
    log_section "Verificación de entropía del sistema"

    local avail
    avail=$(cat /proc/sys/kernel/random/entropy_avail 2>/dev/null || echo 999)
    log_item "Entropía disponible: ${avail} bits"

    if [[ "$avail" -lt 256 ]]; then
        log_warn "Entropía baja (${avail} < 256 bits) — instalando haveged"
        apt-get install -y --quiet haveged >/dev/null 2>&1
        systemctl enable haveged >/dev/null 2>&1
        systemctl start  haveged >/dev/null 2>&1
        sleep 1
        avail=$(cat /proc/sys/kernel/random/entropy_avail)
        log_info "Entropía tras haveged: ${avail} bits"
    else
        log_info "Entropía suficiente (${avail} bits) — no se requiere haveged"
    fi
}

# =============================================================================
# LIBSODIUM 1.0.19 — Compilación desde fuente
#
# Debian Bookworm solo distribuye libsodium 1.0.18.
# crypto_kdf_hkdf_sha256_* (HKDF nativo) requiere >= 1.0.19 (ADR-013 PHASE 2).
#
# Función idempotente: salta si la versión correcta ya está instalada.
# Verificación SHA-256 obligatoria antes de compilar — supply-chain safety.
#
# SHA-256 verificado el 2026-03-25 contra:
#   https://download.libsodium.org/libsodium/releases/libsodium-1.0.19.tar.gz
# =============================================================================

readonly SODIUM_REQUIRED="1.0.19"
readonly SODIUM_URL="https://download.libsodium.org/libsodium/releases/libsodium-${SODIUM_REQUIRED}.tar.gz"
readonly SODIUM_SHA256="018d79fe0a045cca07331d37bd0cb57b2e838c51bc48fd837a1472e50068bbea"

install_libsodium_1019() {
    log_section "libsodium ${SODIUM_REQUIRED}"

    # ── Idempotencia: comprobar versión instalada ──────────────────────────
    local installed
    installed=$(pkg-config --modversion libsodium 2>/dev/null || echo "none")

    if [[ "$installed" == "$SODIUM_REQUIRED" ]]; then
        # Verificar además que crypto_kdf_hkdf_sha256 está en los headers
        if grep -r "crypto_kdf_hkdf_sha256_extract" /usr/local/include/sodium/ \
                >/dev/null 2>&1; then
            log_info "libsodium ${SODIUM_REQUIRED} ya instalada con HKDF nativo — saltando"
            return 0
        fi
        log_warn "libsodium ${SODIUM_REQUIRED} instalada pero HKDF headers ausentes — reinstalando"
    else
        log_item "Versión instalada: ${installed}  →  compilando ${SODIUM_REQUIRED} desde fuente"
    fi

    # ── Dependencias de compilación ────────────────────────────────────────
    log_item "Instalando dependencias de compilación"
    apt-get install -y --quiet build-essential wget pkg-config >/dev/null 2>&1

    # ── Directorio temporal (limpiado al salir de la función) ──────────────
    local tmpdir
    tmpdir=$(mktemp -d /tmp/sodium_build_XXXXXX)
    # shellcheck disable=SC2064
    trap "rm -rf ${tmpdir}" RETURN

    # ── Descarga ───────────────────────────────────────────────────────────
    log_item "Descargando libsodium-${SODIUM_REQUIRED}.tar.gz"
    if ! wget -q "${SODIUM_URL}" -O "${tmpdir}/libsodium.tar.gz"; then
        log_error "Descarga fallida: ${SODIUM_URL}"
        log_error "Comprueba conectividad: wget -q ${SODIUM_URL} -O /tmp/test.tar.gz"
        exit 1
    fi

    # ── Verificación SHA-256 — obligatoria, no salteable ──────────────────
    log_item "Verificando integridad SHA-256"
    local actual_sha
    actual_sha=$(sha256sum "${tmpdir}/libsodium.tar.gz" | awk '{print $1}')

    if [[ "$actual_sha" != "$SODIUM_SHA256" ]]; then
        log_error "SHA-256 no coincide — ABORTANDO"
        log_error "  Esperado: ${SODIUM_SHA256}"
        log_error "  Obtenido: ${actual_sha}"
        log_error "NO se instalará libsodium — posible supply-chain attack o descarga corrupta"
        rm -f "${tmpdir}/libsodium.tar.gz"
        exit 1
    fi
    log_info "SHA-256 verificado: ${actual_sha:0:16}…"

    # ── Compilación ────────────────────────────────────────────────────────
    log_item "Compilando libsodium ${SODIUM_REQUIRED} (~2 min en primera ejecución)"
    tar xzf "${tmpdir}/libsodium.tar.gz" -C "${tmpdir}"

    # Verificar que el directorio se extrajo correctamente
    local src_dir="${tmpdir}/libsodium-stable"
    if [[ ! -d "$src_dir" ]]; then
        log_error "tar no extrajo el directorio esperado: ${src_dir}"
        log_error "Contenido de ${tmpdir}: $(ls ${tmpdir})"
        exit 1
    fi

    cd "$src_dir"
    ./configure --prefix=/usr/local --quiet 2>/dev/null
    make -j"$(nproc)" --quiet
    make install --quiet
    cd /tmp

    ldconfig

    # ── Reinstalar dependencias que apt pudo eliminar al quitar libsodium23 ──
    # apt-get remove libsodium23 arrastra libzmq5, libzmq3-dev, cppzmq-dev
    # porque Bookworm los construyó contra libsodium.so.23. Los reinstalamos
    # explícitamente para no romper el resto del pipeline.
    log_item "Verificando dependencias del pipeline (ZeroMQ, vim...)"
    apt-get install -y --quiet         libzmq5 libzmq3-dev cppzmq-dev vim >/dev/null 2>&1
    log_info "Dependencias del pipeline verificadas"

    # ── Verificación post-instalación ─────────────────────────────────────
    local installed_now
    installed_now=$(pkg-config --modversion libsodium 2>/dev/null || echo "none")

    if [[ "$installed_now" != "$SODIUM_REQUIRED" ]]; then
        log_error "Instalación fallida — pkg-config reporta: ${installed_now}"
        log_error "Comprueba que /usr/local/lib está en ldconfig: ldconfig -p | grep sodium"
        exit 1
    fi

    # Verificar que el símbolo HKDF está presente
    if ! grep -r "crypto_kdf_hkdf_sha256_extract" /usr/local/include/sodium/ \
            >/dev/null 2>&1; then
        log_error "crypto_kdf_hkdf_sha256_* no encontrada tras instalación"
        log_error "Headers instalados en: $(ls /usr/local/include/sodium/ 2>/dev/null | head -5)"
        exit 1
    fi

    log_info "libsodium ${installed_now} instalada correctamente"
    log_item "Headers: /usr/local/include/sodium/"
    log_item "Libs:    /usr/local/lib/libsodium.so.${SODIUM_REQUIRED}"
    log_item "HKDF:    crypto_kdf_hkdf_sha256_extract/expand disponibles ✅"
}

# =============================================================================
# OPERACIONES DE CLAVES
# =============================================================================

# Crea el directorio para un componente con permisos correctos (AppArmor-safe)
create_component_dir() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"

    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_item "Directorio creado: $dir"
    fi

    # Permisos: root escribe, vagrant lee (necesario para SeedClient en dev)
    chmod 755 "$dir"
    chown root:vagrant "$dir"
}

# Genera keypair Ed25519 para un componente
# Salida: private.pem (0600) + public.pem (0644)
generate_keypair() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"
    local private_key="${dir}/private.pem"
    local public_key="${dir}/public.pem"

    if [[ -f "$private_key" ]] && [[ -f "$public_key" ]]; then
        log_warn "Keypair ya existe para ${component} (usa 'reprovision' para regenerar)"
        return 0
    fi

    # Generar clave privada Ed25519
    openssl genpkey -algorithm ed25519 -out "$private_key" 2>/dev/null
    chmod 600 "$private_key"
    chown root:root "$private_key"

    # Extraer clave pública
    openssl pkey -in "$private_key" -pubout -out "$public_key" 2>/dev/null
    chmod 644 "$public_key"
    chown root:root "$public_key"

    log_item "Keypair Ed25519 generado para ${component}"
}

# Genera seed ChaCha20 (32 bytes de entropía del SO)
# PHASE 1: seed en claro con chmod 0600
# PHASE 2: seed cifrado con clave pública del receptor (seed-client, ADR-013)
generate_seed() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"
    local seed_file="${dir}/seed.bin"

    if [[ -f "$seed_file" ]]; then
        log_warn "Seed ya existe para ${component} (usa 'reprovision' para regenerar)"
        return 0
    fi

    # 32 bytes de /dev/urandom — fuente de entropía del SO
    openssl rand -out "$seed_file" ${SEED_BYTES}
    chmod 0400 "$seed_file"
    chown root:root "$seed_file"

    # Verificación de integridad: el seed debe tener exactamente SEED_BYTES
    local actual_size
    actual_size=$(stat -c%s "$seed_file" 2>/dev/null || stat -f%z "$seed_file" 2>/dev/null)
    if [[ "$actual_size" -ne "$SEED_BYTES" ]]; then
        log_error "Seed incorrecto para ${component}: ${actual_size} bytes (esperado: ${SEED_BYTES})"
        rm -f "$seed_file"
        exit 1
    fi

    # Guardar también en hex para debugging (chmod 600)
    # Solo en PHASE 1 — en PHASE 2 el hex también irá cifrado
    openssl rand -hex ${SEED_BYTES} > "${dir}/seed.hex"
    chmod 0400 "${dir}/seed.hex"
    chown root:root "${dir}/seed.hex"

    log_item "Seed ChaCha20 (${SEED_BYTES}B) generado para ${component}"
}

# Genera un fingerprint SHA256 de la clave pública (para verificación rápida)
generate_fingerprint() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"
    local public_key="${dir}/public.pem"
    local fingerprint_file="${dir}/fingerprint.txt"

    if [[ ! -f "$public_key" ]]; then
        return 1
    fi

    openssl pkey -in "$public_key" -pubin -outform DER 2>/dev/null \
        | openssl dgst -sha256 -hex \
        | awk '{print $2}' > "$fingerprint_file"

    chmod 644 "$fingerprint_file"
    chown root:root "$fingerprint_file"
}

# Genera metadatos de provisioning (timestamp + version)
generate_metadata() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"
    local metadata_file="${dir}/provision_meta.json"

    cat > "$metadata_file" << EOF
{
  "component_id": "${component}",
  "provisioned_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "provisioned_by": "tools/provision.sh",
  "phase": "PHASE_1",
  "phase_note": "seed en claro (chmod 0600). PHASE 2: seed.enc via seed-client (ADR-013)",
  "key_algorithm": "${KEY_ALGORITHM}",
  "seed_bytes": ${SEED_BYTES},
  "keys_dir": "${dir}",
  "libsodium_version": "${SODIUM_REQUIRED}",
  "apparmor_compatible": true,
  "adr_refs": ["ADR-013", "ADR-019", "ADR-020"]
}
EOF
    chmod 644 "$metadata_file"
    chown root:root "$metadata_file"
}

# =============================================================================
# PROVISIONING DE COMPONENTE
# =============================================================================

provision_component() {
    local component="$1"
    echo -e "\n  ${BOLD}${component}${NC}"

    create_component_dir    "$component"
    generate_keypair        "$component"
    generate_seed           "$component"
    generate_fingerprint    "$component"
    generate_metadata       "$component"

    log_info "${component} provisionado correctamente"
}

# Mantiene máximo 2 backups por componente — elimina el más antiguo si hay 3+
# USO: cleanup_old_backups <base_dir>  (ej: /etc/ml-defender/etcd-server)
cleanup_old_backups() {
    local base_dir="$1"
    local parent
    parent="$(dirname "$base_dir")"
    local name
    name="$(basename "$base_dir")"
    local backups=()
    while IFS= read -r -d $'\0' d; do
        backups+=("$d")
    done < <(find "$parent" -maxdepth 1 -name "${name}.bak.*" -type d -print0 | sort -z)
    local count=${#backups[@]}
    if (( count >= 3 )); then
        local to_delete=$(( count - 2 ))
        for (( i=0; i<to_delete; i++ )); do
            rm -rf "${backups[$i]}"
            log_item "Backup antiguo eliminado: ${backups[$i]}"
        done
    fi
}

# Re-provisiona forzando regeneración (borra claves existentes)
reprovision_component() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"

    log_warn "Re-provisionando ${component} — borrando claves existentes"

    # Backup antes de borrar (nunca borres sin backup)
    if [[ -d "$dir" ]]; then
        local backup_dir="${dir}.bak.$(date +%Y%m%d_%H%M%S)"
        cp -r "$dir" "$backup_dir"
        chmod 700 "$backup_dir"
        log_item "Backup creado: $backup_dir"
        cleanup_old_backups "$dir"

        rm -f "${dir}/private.pem" \
              "${dir}/public.pem" \
              "${dir}/seed.bin" \
              "${dir}/seed.hex" \
              "${dir}/fingerprint.txt" \
              "${dir}/provision_meta.json"
    fi

    provision_component "$component"
    log_warn "Re-provisioning completo. Los demás componentes que intercambiaban claves con ${component} pueden necesitar re-provisioning también."
}




# =============================================================================
# RESET PLUGIN SIGNING KEYPAIR (ADR-025 D11)
# Fuerza regeneración del keypair de firma de plugins, con backup previo.
# NUNCA auto-firma plugins — operador debe ejecutar make sign-plugins después.
# =============================================================================
reset_plugin_signing_keypair() {
    log_section "Reset Plugin Signing Keypair (ADR-025 D11)"

    local signing_dir="${KEYS_ROOT}/plugins"
    local private_key="${signing_dir}/plugin_signing.sk"
    local public_key="${signing_dir}/plugin_signing.pk"

    # Backup obligatorio antes de borrar
    if [[ -f "$private_key" ]] || [[ -f "$public_key" ]]; then
        local backup_dir="${signing_dir}.bak.$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        [[ -f "$private_key" ]] && cp "$private_key" "$backup_dir/"
        [[ -f "$public_key"  ]] && cp "$public_key"  "$backup_dir/"
        chmod 700 "$backup_dir"
        log_item "Backup plugin signing keypair: $backup_dir"
        cleanup_old_backups "$signing_dir"
        rm -f "$private_key" "$public_key"
    fi

    # Regenerar
    mkdir -p "$signing_dir"
    chmod 755 "$signing_dir"

    openssl genpkey -algorithm ed25519 -out "$private_key" 2>/dev/null
    chmod 600 "$private_key"
    chown root:root "$private_key"

    openssl pkey -in "$private_key" -pubout -out "$public_key" 2>/dev/null
    chmod 644 "$public_key"
    chown root:root "$public_key"

    local pubkey_hex
    pubkey_hex=$(openssl pkey -in "$public_key" -pubin -outform DER 2>/dev/null | tail -c 32 | od -A n -t x1 | tr -d " \n")

    log_warn "Plugin signing keypair ROTADO"
    log_item ">>> NUEVA MLD_PLUGIN_PUBKEY_HEX=${pubkey_hex} <<<"
    log_item "    ⚠️  Hardcodear en plugin-loader/CMakeLists.txt y recompilar"
    log_item "    ⚠️  Los plugins existentes (.sig) son INVÁLIDOS hasta re-firma"
}

# =============================================================================
# RESET ALL KEYS (ADR-025 D11 — provision.sh --reset)
# Rota: seed_family + keypairs Ed25519 de 6 componentes + keypair firma plugins
# NO auto-firma plugins. Post-reset: operador debe ejecutar make sign-plugins.
# En dev con flag --dev: llama a check-plugins (firma automática).
# =============================================================================
reset_all_keys() {
    local dev_mode="${1:-false}"

    log_warn "════════════════════════════════════════════════════"
    log_warn "  RESET COMPLETO DE CLAVES — ADR-025 D11"
    log_warn "  Esto invalida TODOS los plugins firmados actuales"
    log_warn "════════════════════════════════════════════════════"

    # Confirmación explícita requerida (excepto si CI=true)
    if [[ "${CI:-false}" != "true" ]]; then
        echo ""
        read -r -p "  ¿Confirmar reset completo de claves? [escribe 'RESET' para continuar]: " confirm
        if [[ "$confirm" != "RESET" ]]; then
            log_error "Reset cancelado por el operador"
            exit 1
        fi
    fi

    # SEED FAMILY: generar UN solo seed compartido para todos los componentes.
    # Todos deben derivar HKDF desde el mismo seed para que CryptoTransport
    # produzca claves compatibles (CTX_ETCD_TX/RX). ADR-021.
    log_section "Generando seed_family compartido (ADR-021)"
    local shared_seed_tmp
    shared_seed_tmp=$(mktemp)
    openssl rand -out "$shared_seed_tmp" ${SEED_BYTES}
    chmod 600 "$shared_seed_tmp"

    log_section "Reset keypairs + seed_family de componentes (6/6)"
    for component in "${COMPONENTS[@]}"; do
        local dir="${KEYS_ROOT}/${component}"

        log_warn "Re-provisionando ${component} — borrando claves existentes"
        if [[ -d "$dir" ]]; then
            local backup_dir="${dir}.bak.$(date +%Y%m%d_%H%M%S)"
            cp -r "$dir" "$backup_dir"
            chmod 700 "$backup_dir"
            log_item "Backup creado: $backup_dir"
            cleanup_old_backups "$dir"
            rm -f "${dir}/private.pem" "${dir}/public.pem"                   "${dir}/seed.bin"    "${dir}/seed.hex"                   "${dir}/fingerprint.txt" "${dir}/provision_meta.json"
        fi

        # Regenerar keypair Ed25519
        provision_component "$component"

        # Sobreescribir seed con el seed_family compartido
        cp "$shared_seed_tmp" "${dir}/seed.bin"
        chmod 0400 "${dir}/seed.bin"
        chown root:root "${dir}/seed.bin"
        log_item "seed_family aplicado a ${component}"
    done

    rm -f "$shared_seed_tmp"
    log_item "seed_family distribuido a ${#COMPONENTS[@]} componentes"

    log_section "Reset plugin signing keypair"
    reset_plugin_signing_keypair

    log_section "Verificación post-reset"
    verify_all

    echo ""
    log_warn "════════════════════════════════════════════════════"
    log_warn "  CLAVES ROTADAS — PIPELINE EN FAIL-CLOSED"
    log_warn "  Los plugins existentes NO están firmados con la nueva clave."
    log_warn ""
    log_warn "  ACCIÓN REQUERIDA (operador):"
    log_warn "    1. Actualizar MLD_PLUGIN_PUBKEY_HEX en CMakeLists.txt"
    log_warn "    2. Recompilar:   make pipeline-build"
    log_warn "    3. Re-firmar:    make sign-plugins"
    log_warn "    4. Verificar:    make test-provision-1"
    log_warn "    5. Arrancar:     make pipeline-start"
    log_warn "════════════════════════════════════════════════════"

    if [[ "$dev_mode" == "true" ]]; then
        log_warn "Modo --dev: ejecutando check-plugins automáticamente..."
        bash /vagrant/tools/provision.sh check-plugins
    fi
}

# =============================================================================
# SIGN PLUGIN (ADR-025 D1)
# Firma un plugin .so con la clave privada Ed25519 de firma de plugins.
# Genera <plugin>.so.sig (64 bytes, Ed25519 detached signature).
#
# USO: sign_plugin <path_to_plugin.so>
#
# PREREQUISITOS:
#   - /etc/ml-defender/plugins/plugin_signing.sk debe existir
#     (generado por provision_plugin_signing_keypair)
#   - openssl con soporte Ed25519 (>= 1.1.1)
#
# NOTAS:
#   - La clave privada NUNCA sale de este host
#   - El .sig se deposita junto al .so (mismo directorio)
#   - Repetible: re-firmar sobreescribe el .sig anterior
#   - Rotacion de clave: provision.sh --reset (ADR-025 D11)
# =============================================================================

sign_plugin() {
    local so_path="$1"
    local sig_path="${so_path}.sig"
    local private_key="${KEYS_ROOT}/plugins/plugin_signing.sk"

    if [[ -z "$so_path" ]]; then
        log_error "sign_plugin: se requiere path al .so"
        return 1
    fi

    if [[ ! -f "$so_path" ]]; then
        log_error "sign_plugin: plugin no encontrado: ${so_path}"
        return 1
    fi

    if [[ ! -f "$private_key" ]]; then
        log_error "sign_plugin: clave privada no encontrada: ${private_key}"
        log_error "  Ejecuta: sudo bash tools/provision.sh full"
        return 1
    fi

    openssl pkeyutl -sign \
        -inkey "$private_key" \
        -rawin \
        -in  "$so_path" \
        -out "$sig_path" 2>/dev/null

    if [[ $? -ne 0 ]]; then
        log_error "sign_plugin: firma fallida para ${so_path}"
        return 1
    fi

    local sig_size
    sig_size=$(stat -c%s "$sig_path" 2>/dev/null || stat -f%z "$sig_path" 2>/dev/null)

    if [[ "$sig_size" -ne 64 ]]; then
        log_error "sign_plugin: .sig size inesperado ${sig_size} bytes (esperado 64)"
        return 1
    fi

    log_item "Plugin firmado: $(basename ${so_path}) → $(basename ${sig_path}) (${sig_size} bytes)"
    return 0
}

# =============================================================================
# SIGN ALL PLUGINS (ADR-025)
# Firma todos los plugins instalados en /usr/lib/ml-defender/plugins/
# Llamado desde: make sign-plugins
# =============================================================================

sign_all_plugins() {
    log_section "Firma de plugins (ADR-025 D1)"

    local plugins_dir="/usr/lib/ml-defender/plugins"

    if [[ ! -d "$plugins_dir" ]]; then
        log_warn "Directorio de plugins no encontrado: ${plugins_dir}"
        return 0
    fi

    local count=0
    local failed=0

    for so_file in "${plugins_dir}"/*.so; do
        [[ -f "$so_file" ]] || continue
        if sign_plugin "$so_file"; then
            count=$((count+1))
        else
            failed=$((failed+1))
        fi
    done

    if [[ $count -eq 0 && $failed -eq 0 ]]; then
        log_item "No hay plugins .so en ${plugins_dir}"
        return 0
    fi

    if [[ $failed -gt 0 ]]; then
        log_error "${failed} plugin(s) no firmados — verifica la clave privada"
        return 1
    fi

    log_info "${count} plugin(s) firmados correctamente"
    return 0
}

# =============================================================================
# PLUGIN SIGNING KEYPAIR (ADR-025)
# Keypair dedicado a firma offline de plugins .so
# OPERACION DE BOOTSTRAPPING UNICO:
#   - Se genera UNA SOLA VEZ en el primer provision full
#   - Si ya existe: warning + skip (nunca sobreescribir silenciosamente)
#   - La private key NUNCA sale del host de build/dev
#   - En produccion: solo la pubkey llega hardcodeada en el binario (CMake)
#   - Rotacion: provision.sh --reset (ADR-025 D11) operacion manual explicita
# Paths:
#   Private key: /etc/ml-defender/plugins/plugin_signing.sk  (0600, root:root)
#   Public key:  /etc/ml-defender/plugins/plugin_signing.pk  (0644, root:root)
# La pubkey raw (32 bytes hex) se inyecta en CMakeLists.txt como
# MLD_PLUGIN_PUBKEY_HEX para hardcodear en el binario del plugin-loader.
# =============================================================================

provision_plugin_signing_keypair() {
    log_section "Plugin Signing Keypair (ADR-025)"

    local signing_dir="${KEYS_ROOT}/plugins"
    local private_key="${signing_dir}/plugin_signing.sk"
    local public_key="${signing_dir}/plugin_signing.pk"

    mkdir -p "$signing_dir"
    chmod 755 "$signing_dir"

    if [[ -f "$private_key" ]] && [[ -f "$public_key" ]]; then
        log_warn "Plugin signing keypair ya existe -- skip (usa --reset para rotar)"
        local pubkey_hex
        pubkey_hex=$(openssl pkey -in "$public_key" -pubin -outform DER 2>/dev/null | tail -c 32 | od -A n -t x1 | tr -d " \n")
        log_item "Public key hex (MLD_PLUGIN_PUBKEY_HEX): ${pubkey_hex}"
        return 0
    fi

    openssl genpkey -algorithm ed25519 -out "$private_key" 2>/dev/null
    chmod 600 "$private_key"
    chown root:root "$private_key"

    openssl pkey -in "$private_key" -pubout -out "$public_key" 2>/dev/null
    chmod 644 "$public_key"
    chown root:root "$public_key"

    local pubkey_hex
    pubkey_hex=$(openssl pkey -in "$public_key" -pubin -outform DER 2>/dev/null | tail -c 32 | od -A n -t x1 | tr -d " \n")

    log_item "Plugin signing keypair generado"
    log_item "Private key: ${private_key} (0600 -- NUNCA fuera de este host)"
    log_item "Public key:  ${public_key} (0644)"
    log_item ""
    log_item ">>> MLD_PLUGIN_PUBKEY_HEX=${pubkey_hex} <<<"
    log_item "    Hardcodear en plugin-loader/CMakeLists.txt (ADR-025 D7)"
    log_item "    Esta es la UNICA vez que se muestra en provision.sh"
}

# =============================================================================
# PLUGINS USERSPACE (ADR-017)
# Lee los JSONs de componentes y provisiona los plugins declarados
# =============================================================================

provision_plugins() {
    local vagrant_root="/vagrant"
    local plugins_provisioned=0

    log_section "Plugins Userspace (ADR-017)"

    # Buscar plugins declarados en los JSONs de componentes
    local component_configs=(
        "${vagrant_root}/sniffer/config/sniffer.json"
        "${vagrant_root}/ml-detector/config/ml_detector_config.json"
        "${vagrant_root}/firewall-acl-agent/config/firewall.json"
        "${vagrant_root}/rag-ingester/config/rag-ingester.json"
        "${vagrant_root}/rag/config/rag-config.json"
        "${vagrant_root}/etcd-server/config/etcd-server.json"
    )

    for config in "${component_configs[@]}"; do
        if [[ ! -f "$config" ]]; then
            continue
        fi

        local plugins
        plugins=$(jq -r '.identity.plugins[]? // empty' "$config" 2>/dev/null || true)

        if [[ -n "$plugins" ]]; then
            while IFS= read -r plugin_id; do
                echo -e "\n  ${BOLD}plugin: ${plugin_id}${NC}"
                create_component_dir "plugins/${plugin_id}"
                generate_keypair     "plugins/${plugin_id}"
                generate_seed        "plugins/${plugin_id}"
                generate_fingerprint "plugins/${plugin_id}"
                generate_metadata    "plugins/${plugin_id}"
                log_info "Plugin ${plugin_id} provisionado"
                ((plugins_provisioned++))
            done <<< "$plugins"
        fi
    done

    if [[ $plugins_provisioned -eq 0 ]]; then
        log_item "No hay plugins declarados en los JSONs (PHASE 2 pendiente)"
        log_item "Directorio /etc/ml-defender/plugins/ creado y listo"
        mkdir -p "${KEYS_ROOT}/plugins"
        chmod 755 "${KEYS_ROOT}/plugins"
    fi
}

# =============================================================================
# PLUGINS eBPF (ADR-018)
# =============================================================================

provision_ebpf_plugins() {
    local ebpf_config="/vagrant/sniffer/config/kernel_telemetry.json"

    log_section "Plugins eBPF (ADR-018)"

    mkdir -p "${KEYS_ROOT}/ebpf-plugins"
    chmod 755 "${KEYS_ROOT}/ebpf-plugins"

    if [[ ! -f "$ebpf_config" ]]; then
        log_item "kernel_telemetry.json no encontrado (ADR-018 pendiente)"
        log_item "Directorio /etc/ml-defender/ebpf-plugins/ creado y listo"
        return 0
    fi

    local ebpf_programs
    ebpf_programs=$(jq -r '.programs[]?.id // empty' "$ebpf_config" 2>/dev/null || true)

    if [[ -z "$ebpf_programs" ]]; then
        log_item "No hay programas eBPF declarados en kernel_telemetry.json"
        return 0
    fi

    while IFS= read -r prog_id; do
        echo -e "\n  ${BOLD}ebpf-plugin: ${prog_id}${NC}"
        create_component_dir "ebpf-plugins/${prog_id}"
        generate_keypair     "ebpf-plugins/${prog_id}"
        generate_seed        "ebpf-plugins/${prog_id}"
        generate_fingerprint "ebpf-plugins/${prog_id}"
        generate_metadata    "ebpf-plugins/${prog_id}"
        log_info "eBPF plugin ${prog_id} provisionado"
    done <<< "$ebpf_programs"
}

# =============================================================================
# VERIFICACIÓN
# =============================================================================

verify_component() {
    local component="$1"
    local dir="${KEYS_ROOT}/${component}"
    local ok=true

    local private_key="${dir}/private.pem"
    local public_key="${dir}/public.pem"
    local seed_file="${dir}/seed.bin"

    [[ -f "$private_key" ]] || { log_error "${component}: private.pem ausente";  ok=false; }
    [[ -f "$public_key"  ]] || { log_error "${component}: public.pem ausente";   ok=false; }
    [[ -f "$seed_file"   ]] || { log_error "${component}: seed.bin ausente";     ok=false; }

    if [[ "$ok" == "false" ]]; then
        return 1
    fi

    # Verificar permisos
    local priv_perms
    priv_perms=$(stat -c "%a" "$private_key" 2>/dev/null || stat -f "%OLp" "$private_key" 2>/dev/null)
    if [[ "$priv_perms" != "600" ]]; then
        log_error "${component}: private.pem permisos incorrectos (${priv_perms}, esperado 600)"
        ok=false
    fi

    # Verificar tamaño del seed
    local seed_size
    seed_size=$(stat -c%s "$seed_file" 2>/dev/null || stat -f%z "$seed_file" 2>/dev/null)
    if [[ "$seed_size" -ne "$SEED_BYTES" ]]; then
        log_error "${component}: seed.bin tamaño incorrecto (${seed_size}B, esperado ${SEED_BYTES}B)"
        ok=false
    fi

    # Verificar que el keypair es válido
    local pub_from_priv
    pub_from_priv=$(openssl pkey -in "$private_key" -pubout 2>/dev/null | openssl dgst -sha256 | awk '{print $2}')
    local pub_stored
    pub_stored=$(openssl pkey -in "$public_key" -pubin -pubout 2>/dev/null | openssl dgst -sha256 | awk '{print $2}')

    if [[ "$pub_from_priv" != "$pub_stored" ]]; then
        log_error "${component}: keypair inconsistente"
        ok=false
    fi

    [[ "$ok" == "true" ]]
}

verify_all() {
    log_section "Verificación de integridad"
    local all_ok=true

    for component in "${COMPONENTS[@]}"; do
        if verify_component "$component"; then
            log_info "${component}: OK"
        else
            all_ok=false
        fi
    done

    if [[ "$all_ok" == "true" ]]; then
        echo -e "\n${GREEN}${BOLD}  ✅ Todas las claves verificadas correctamente${NC}"
        return 0
    else
        echo -e "\n${RED}${BOLD}  ❌ Verificación fallida — ejecuta: sudo bash tools/provision.sh full${NC}"
        return 1
    fi
}

# =============================================================================
# STATUS — Tabla visual de estado
# =============================================================================

status_all() {
    echo -e "\n${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  ML Defender — Estado de Provisioning Criptográfico           ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # libsodium version
    local sodium_installed
    sodium_installed=$(pkg-config --modversion libsodium 2>/dev/null || echo "none")
    if [[ "$sodium_installed" == "$SODIUM_REQUIRED" ]]; then
        echo -e "  ${GREEN}✅${NC} libsodium: ${sodium_installed} (HKDF nativo disponible)"
    else
        echo -e "  ${RED}❌${NC} libsodium: ${sodium_installed} (requiere ${SODIUM_REQUIRED} — ejecuta 'full')"
    fi
    echo ""

    printf "  %-25s %-12s %-12s %-12s %-20s\n" \
        "COMPONENTE" "PRIVATE KEY" "PUBLIC KEY" "SEED" "FINGERPRINT"
    printf "  %-25s %-12s %-12s %-12s %-20s\n" \
        "─────────────────────────" "───────────" "──────────" "────" "──────────────────"

    for component in "${COMPONENTS[@]}"; do
        local dir="${KEYS_ROOT}/${component}"

        local priv_status pub_status seed_status fingerprint

        [[ -f "${dir}/private.pem" ]] && priv_status="${GREEN}✅ OK${NC}" || priv_status="${RED}❌ FALTA${NC}"
        [[ -f "${dir}/public.pem"  ]] && pub_status="${GREEN}✅ OK${NC}"  || pub_status="${RED}❌ FALTA${NC}"
        [[ -f "${dir}/seed.bin"    ]] && seed_status="${GREEN}✅ OK${NC}" || seed_status="${RED}❌ FALTA${NC}"

        if [[ -f "${dir}/fingerprint.txt" ]]; then
            fingerprint=$(head -c 16 "${dir}/fingerprint.txt")...
        else
            fingerprint="${RED}❌ FALTA${NC}"
        fi

        local prov_date=""
        if [[ -f "${dir}/provision_meta.json" ]]; then
            prov_date=$(jq -r '.provisioned_at // "?"' "${dir}/provision_meta.json" 2>/dev/null | cut -c1-10)
        fi

        printf "  %-25s " "$component"
        echo -e "${priv_status}       ${pub_status}      ${seed_status}   ${fingerprint}  ${prov_date}"
    done

    echo ""
    local plugin_count=0
    [[ -d "${KEYS_ROOT}/plugins" ]] && \
        plugin_count=$(find "${KEYS_ROOT}/plugins" -name "private.pem" 2>/dev/null | wc -l)
    local ebpf_count=0
    [[ -d "${KEYS_ROOT}/ebpf-plugins" ]] && \
        ebpf_count=$(find "${KEYS_ROOT}/ebpf-plugins" -name "private.pem" 2>/dev/null | wc -l)

    echo -e "  ${CYAN}Plugins userspace provisionados:${NC} ${plugin_count}"
    echo -e "  ${CYAN}Plugins eBPF provisionados:${NC}      ${ebpf_count}"
    echo ""
    echo -e "  ${CYAN}Keys root:${NC} ${KEYS_ROOT}/"
    echo -e "  ${CYAN}Phase:${NC}     PHASE 1 (seed en claro, chmod 0600)"
    echo -e "  ${YELLOW}  → PHASE 2:${NC} seed.enc via seed-client (ADR-013)"
    echo ""
}

# =============================================================================
# MODO FULL — Provisioning completo
# =============================================================================

# =============================================================================
# SHARED LIBS — build e install de seed-client + crypto-transport
# Necesario tras vagrant destroy: los headers y .so desaparecen de /usr/local
# =============================================================================
install_shared_libs() {
    log_section "Shared libs (seed-client + crypto-transport + plugin-loader)"

    # ── seed-client ──────────────────────────────────────────────────────────
    if pkg-config --exists seed_client 2>/dev/null || \
       [[ -f /usr/local/lib/libseed_client.so ]]; then
        log_info "seed-client ya instalada — saltando"
    else
        log_item "Compilando seed-client..."
        local sc_dir="/vagrant/libs/seed-client"
        if [[ ! -d "$sc_dir" ]]; then
            log_error "seed-client no encontrada en ${sc_dir}"
            exit 1
        fi
        rm -rf "${sc_dir}/build"
        mkdir -p "${sc_dir}/build"
        pushd "${sc_dir}/build" > /dev/null
        cmake -DCMAKE_BUILD_TYPE=Release .. > /dev/null 2>&1
        make -j"$(nproc)" > /dev/null 2>&1
        make install > /dev/null 2>&1
        ldconfig
        popd > /dev/null
        log_item "seed-client instalada en /usr/local"
    fi

    # ── crypto-transport ─────────────────────────────────────────────────────
    if [[ -f /usr/local/lib/libcrypto_transport.so ]] && \
       [[ -f /usr/local/include/crypto_transport/transport.hpp ]]; then
        log_info "crypto-transport ya instalada — saltando"
    else
        log_item "Compilando crypto-transport..."
        local ct_dir="/vagrant/crypto-transport"
        if [[ ! -d "$ct_dir" ]]; then
            log_error "crypto-transport no encontrada en ${ct_dir}"
            exit 1
        fi
        rm -rf "${ct_dir}/build"
        mkdir -p "${ct_dir}/build"
        pushd "${ct_dir}/build" > /dev/null
        cmake -DCMAKE_BUILD_TYPE=Release \
              -DCMAKE_INSTALL_PREFIX=/usr/local \
              -DCMAKE_PREFIX_PATH=/usr/local \
              .. > /dev/null 2>&1
        make -j"$(nproc)" > /dev/null 2>&1
        make install > /dev/null 2>&1
        ldconfig
        popd > /dev/null
        log_item "crypto-transport instalada en /usr/local"
    fi

    # ── plugin_signing.pk debe existir ANTES de compilar plugin-loader ──────
    # plugin-loader/CMakeLists.txt lee la pubkey en cmake-time (DEBT-PUBKEY-RUNTIME-001)
    if [[ ! -f /etc/ml-defender/plugins/plugin_signing.pk ]]; then
        log_item "Generando plugin signing keypair (requerido por plugin-loader cmake)..."
        provision_plugin_signing_keypair
    fi

    # ── plugin-loader ─────────────────────────────────────────────────────────
    if [[ -f /usr/local/lib/libplugin_loader.so ]]; then
        log_info "plugin-loader ya instalada — saltando"
    else
        log_item "Compilando plugin-loader..."
        local pl_dir="/vagrant/plugin-loader"
        if [[ ! -d "$pl_dir" ]]; then
            log_warn "plugin-loader no encontrada en ${pl_dir} — saltando"
        else
            rm -rf "${pl_dir}/build"
            mkdir -p "${pl_dir}/build"
            pushd "${pl_dir}/build" > /dev/null
            cmake -DCMAKE_BUILD_TYPE=Release \
                  -DCMAKE_INSTALL_PREFIX=/usr/local \
                  -DCMAKE_PREFIX_PATH=/usr/local \
                  .. > /dev/null 2>&1
            make -j"$(nproc)" > /dev/null 2>&1
            make install > /dev/null 2>&1
            ldconfig
            popd > /dev/null
            log_item "plugin-loader instalada en /usr/local"
        fi
    fi

    # ── libsnappy (apt) ──────────────────────────────────────────────────────
    if ! dpkg -l libsnappy1v5 2>/dev/null | grep -q "^ii"; then
        log_item "Instalando libsnappy..."
        apt-get install -y --quiet libsnappy1v5 libsnappy-dev >/dev/null 2>&1
        log_item "libsnappy instalada"
    else
        log_info "libsnappy ya instalada — saltando"
    fi

    # ── etcd-client ───────────────────────────────────────────────────────────
    if [[ -f /usr/local/lib/libetcd_client.so ]]; then
        log_info "etcd-client ya instalada — saltando"
    else
        log_item "Instalando etcd-client..."
        local ec_dir="/vagrant/etcd-client"
        if [[ ! -d "$ec_dir" ]]; then
            log_error "etcd-client no encontrada en ${ec_dir}"
            exit 1
        fi
        rm -rf "${ec_dir}/build"
        mkdir -p "${ec_dir}/build"
        pushd "${ec_dir}/build" > /dev/null
        cmake -DCMAKE_BUILD_TYPE=Release \
              -DCMAKE_INSTALL_PREFIX=/usr/local \
              -DCMAKE_PREFIX_PATH=/usr/local \
              .. > /dev/null 2>&1
        make -j"$(nproc)" > /dev/null 2>&1
        make install > /dev/null 2>&1
        ldconfig
        popd > /dev/null
        log_item "etcd-client instalada en /usr/local"
    fi

    log_info "Shared libs OK"
}

provision_full() {
    echo -e "\n${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  ML Defender — Provisioning Criptográfico PHASE 1            ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}Keys root:${NC}  ${KEYS_ROOT}/"
    echo -e "  ${CYAN}Algorithm:${NC}  Ed25519 keypairs + ChaCha20 seeds (${SEED_BYTES}B)"
    echo -e "  ${CYAN}libsodium:${NC}  ${SODIUM_REQUIRED} (HKDF nativo, ADR-013)"
    echo -e "  ${CYAN}AppArmor:${NC}   Compatible (paths fijos, ADR-019)"
    echo ""

    check_root
    check_dependencies
    check_entropy
    install_libsodium_1019
    install_shared_libs

    # Crear directorio raíz
    if [[ ! -d "$KEYS_ROOT" ]]; then
        mkdir -p "$KEYS_ROOT"
        chmod 755 "$KEYS_ROOT"
        chown root:root "$KEYS_ROOT"
        log_info "Directorio raíz creado: ${KEYS_ROOT}"
    fi

    # Provisionar los 6 componentes del pipeline
    log_section "Componentes del pipeline (6)"
    for component in "${COMPONENTS[@]}"; do
        provision_component "$component"
    done

    # Provisionar plugins
    provision_plugins
    provision_ebpf_plugins
    provision_plugin_signing_keypair

    # ── FIX DAY 107: seed maestro → distribuir a los 5 componentes restantes ──
    log_section "Sincronización de seed maestro (etcd-server → 5 componentes)"
    local master_seed="${KEYS_ROOT}/etcd-server/seed.bin"
    if [[ ! -f "$master_seed" ]]; then
        log_error "Seed maestro no encontrado: $master_seed"
        exit 1
    fi
    for component in sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do
        local dst="${KEYS_ROOT}/${component}/seed.bin"
        cp "$master_seed" "$dst"
        chmod 0400 "$dst"
        chown root:vagrant "$dst"
        log_item "Seed sincronizado → ${component}"
    done
    log_info "Seeds sincronizados (todos los componentes usan el seed de etcd-server)"

    # ── FIX DAY 107: symlinks JSON /etc/ml-defender/* → /vagrant/*/config/ ──
    log_section "Symlinks JSON config (6 componentes)"
    declare -A CONFIG_MAP=(
        ["etcd-server"]="/vagrant/etcd-server/config"
        ["sniffer"]="/vagrant/sniffer/config"
        ["ml-detector"]="/vagrant/ml-detector/config"
        ["firewall-acl-agent"]="/vagrant/firewall-acl-agent/config"
        ["rag-ingester"]="/vagrant/rag-ingester/config"
        ["rag-security"]="/vagrant/rag-security/config"
    )
    for component in "${COMPONENTS[@]}"; do
        local link_dir="${KEYS_ROOT}/${component}"
        local target="${CONFIG_MAP[$component]}"
        if [[ -d "$target" ]]; then
            # Crear symlinks para cada JSON en el directorio config
            for json_file in "${target}"/*.json; do
                [[ -f "$json_file" ]] || continue
                local fname
                fname=$(basename "$json_file")
                local link_path="${link_dir}/${fname}"
                if [[ ! -L "$link_path" ]]; then
                    ln -sf "$json_file" "$link_path"
                    log_item "Symlink: ${link_path} → ${json_file}"
                fi
            done
        else
            mkdir -p "$target"
            log_item "Config dir creado: ${target}"
            for json_file in "${target}"/*.json; do
                [[ -f "$json_file" ]] || continue
                local fname
                fname=$(basename "$json_file")
                local link_path="${link_dir}/${fname}"
                if [[ ! -L "$link_path" ]]; then
                    ln -sf "$json_file" "$link_path"
                    log_item "Symlink: ${link_path} → ${json_file}"
                fi
            done
        fi
    done

    # ── FIX DAY 107: libsodium.so.23 → libsodium.so.26 + ldconfig ────────────
    log_section "libsodium compat symlink (so.23 → so.26)"
    local so26
    so26=$(find /usr/local/lib -name "libsodium.so.26" 2>/dev/null | head -1)
    if [[ -n "$so26" ]]; then
        local so_dir
        so_dir=$(dirname "$so26")
        if [[ ! -L "${so_dir}/libsodium.so.23" ]]; then
            ln -sf "${so_dir}/libsodium.so.26" "${so_dir}/libsodium.so.23"
            log_item "Symlink creado: ${so_dir}/libsodium.so.23 → libsodium.so.26"
        else
            log_info "Symlink libsodium.so.23 ya existe"
        fi
        ldconfig
        log_item "ldconfig ejecutado"
    else
        log_warn "libsodium.so.26 no encontrada — instalar primero con install_libsodium_1019"
    fi

    # ── FIX DAY 107: verificar/rebuild libcrypto_transport si es antigua ──────
    log_section "libcrypto_transport.so — verificación de fecha"
    local lib_path="/usr/local/lib/libcrypto_transport.so"
    local today
    today=$(date +%Y-%m-%d)
    if [[ -f "$lib_path" ]]; then
        local lib_date
        lib_date=$(date -r "$lib_path" +%Y-%m-%d 2>/dev/null || echo "unknown")
        if [[ "$lib_date" < "$today" ]]; then
            log_warn "libcrypto_transport.so fecha: ${lib_date} — rebuilding"
            if [[ -d "/vagrant/crypto-transport" ]]; then
                pushd /vagrant/crypto-transport > /dev/null
                mkdir -p build && cd build
                cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local                     -DCMAKE_PREFIX_PATH=/usr/local > /dev/null 2>&1
                make -j"$(nproc)" > /dev/null 2>&1 && make install > /dev/null 2>&1
                ldconfig
                popd > /dev/null
                log_item "libcrypto_transport.so rebuilt y reinstalada"
            else
                log_warn "/vagrant/crypto-transport no encontrado — rebuild manual requerido"
            fi
        else
            log_info "libcrypto_transport.so actualizada (${lib_date})"
        fi
    else
        log_warn "libcrypto_transport.so no encontrada en ${lib_path}"
    fi

    # ── ADR-042 IRP: instalar isolate.json + directorio forense ─────────────
    log_section "argus-network-isolate — ADR-042 IRP config"
    local irp_dir="/etc/ml-defender/firewall-acl-agent"
    local irp_config="${irp_dir}/isolate.json"
    local src_config="/vagrant/tools/argus-network-isolate/config/isolate.json"
    mkdir -p "${irp_dir}"
    if [[ ! -f "${irp_config}" ]]; then
        if [[ -f "${src_config}" ]]; then
            cp "${src_config}" "${irp_config}"
            chmod 640 "${irp_config}"
            chown root:vagrant "${irp_config}" 2>/dev/null || true
            log_item "isolate.json instalado en ${irp_config}"
        # DEBT-IRP-BACKUP-DIR-001: directorios IRP seguros
        mkdir -p /run/argus/irp
        chmod 0700 /run/argus/irp
        chown argus:argus /run/argus/irp 2>/dev/null || chown root:root /run/argus/irp
        mkdir -p /var/lib/argus/irp
        chmod 0700 /var/lib/argus/irp
        chown argus:argus /var/lib/argus/irp 2>/dev/null || chown root:root /var/lib/argus/irp
        log_item "IRP dirs: /run/argus/irp (tmpfs) + /var/lib/argus/irp (persistente)"
        else
            log_error "isolate.json no encontrado en ${src_config} — despliegue abortado (ADR-042)"
            exit 1
        fi
    else
        log_item "isolate.json ya presente en ${irp_config}"
    fi
    mkdir -p /var/log/argus
    chmod 750 /var/log/argus
    chown root:vagrant /var/log/argus 2>/dev/null || true
    log_item "/var/log/argus/ listo (forense ADR-042)"

    # Verificación final
    log_section "Verificación post-provisioning"
    if verify_all; then
        echo -e "\n${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}${BOLD}║  ✅ PROVISIONING COMPLETADO CORRECTAMENTE                    ║${NC}"
        echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "  ${CYAN}libsodium:${NC}     ${SODIUM_REQUIRED} con HKDF nativo"
        echo -e "  ${CYAN}Siguiente:${NC}     make pipeline-start"
        echo -e "  ${CYAN}Verificar:${NC}     make provision-status"
        echo ""
    else
        echo -e "\n${RED}${BOLD}  ❌ Provisioning fallido — revisa los errores anteriores${NC}"
        exit 1
    fi
}


# =============================================================================
# DEBT-SIGN-AUTO — PHASE 3 (DAY 115)
# check_plugins_smart: firma-si-necesario en provisioning, solo-verifica en producción
#
# REGLA DE ORO (Consejo DAY 114):
#   Firma automática SOLO en build/provision time con artefactos recién compilados.
#   NUNCA firmar automáticamente en producción — solo verificar.
#
# USO:
#   provision.sh check-plugins             # dev/provisioning: sign if needed
#   provision.sh check-plugins --production # producción: verify-only, fail si inválido
#
# IDEMPOTENCIA:
#   Si .sig existe Y es válido para la clave pública actual → skip.
#   Si .sig ausente O inválido → (re-)firmar (solo en dev).
# =============================================================================

# Verifica que el .sig de un .so es válido para la clave pública actual.
# Retorna 0 si válido, 1 si inválido o ausente.
verify_plugin_sig() {
    local so_path="$1"
    local sig_path="${so_path}.sig"
    local public_key="${KEYS_ROOT}/plugins/plugin_signing.pk"

    [[ -f "$sig_path"    ]] || return 1
    [[ -f "$public_key"  ]] || return 1

    openssl pkeyutl -verify \
        -pubin -inkey "$public_key" \
        -rawin \
        -in      "$so_path" \
        -sigfile "$sig_path" \
        >/dev/null 2>&1
}

# Lógica principal DEBT-SIGN-AUTO.
# $1: --production (opcional) → verify-only mode
check_plugins_smart() {
    local production_mode=false
    [[ "${1:-}" == "--production" ]] && production_mode=true

    local plugins_dir="/usr/lib/ml-defender/plugins"
    local public_key="${KEYS_ROOT}/plugins/plugin_signing.pk"
    local private_key="${KEYS_ROOT}/plugins/plugin_signing.sk"

    log_section "check-plugins (DEBT-SIGN-AUTO, ADR-025)"

    if $production_mode; then
        log_item "Modo: PRODUCCIÓN — solo verificar, nunca firmar"
    else
        log_item "Modo: PROVISIONING — firmar si necesario"
    fi

    if [[ ! -d "$plugins_dir" ]]; then
        log_warn "Directorio de plugins no encontrado: ${plugins_dir}"
        return 0
    fi

    if [[ ! -f "$public_key" ]]; then
        log_error "Clave pública de firma no encontrada: ${public_key}"
        log_error "Ejecuta: sudo bash tools/provision.sh full"
        return 1
    fi

    local count_ok=0
    local count_signed=0
    local count_failed=0
    local found_any=false

    for so_file in "${plugins_dir}"/*.so; do
        [[ -f "$so_file" ]] || continue
        found_any=true
        local name
        name=$(basename "$so_file")

        if verify_plugin_sig "$so_file"; then
            # .sig válido para clave actual
            log_item "${name}: .sig válido — skip"
            count_ok=$((count_ok + 1))
        else
            # .sig ausente o inválido para clave actual
            if $production_mode; then
                log_error "${name}: .sig ausente o inválido en modo PRODUCCIÓN"
                count_failed=$((count_failed + 1))
            else
                # Provisioning: firmar
                if [[ ! -f "$private_key" ]]; then
                    log_error "Clave privada no encontrada: ${private_key}"
                    log_error "Ejecuta: sudo bash tools/provision.sh full"
                    count_failed=$((count_failed + 1))
                    continue
                fi
                log_item "${name}: firmando..."
                if sign_plugin "$so_file"; then
                    count_signed=$((count_signed + 1))
                else
                    count_failed=$((count_failed + 1))
                fi
            fi
        fi
    done

    if [[ "$found_any" == "false" ]]; then
        log_item "No hay plugins .so en ${plugins_dir}"
        return 0
    fi

    echo ""
    [[ $count_ok     -gt 0 ]] && log_info "${count_ok} plugin(s) ya firmados y válidos (skip)"
    [[ $count_signed -gt 0 ]] && log_info "${count_signed} plugin(s) firmados ahora"

    if [[ $count_failed -gt 0 ]]; then
        log_error "${count_failed} plugin(s) fallidos"
        if $production_mode; then
            log_error "PRODUCCIÓN: pipeline NO debe arrancar con plugins sin firma válida"
        fi
        return 1
    fi

    log_info "check-plugins completado — todos los plugins firmados y verificados"
    return 0
}

# =============================================================================
# ENTRY POINT
# =============================================================================

MODE="${1:-full}"
COMPONENT="${2:-}"

case "$MODE" in
    full)
        provision_full
        ;;

    status)
        check_root
        status_all
        ;;

    sign)
        check_root
        sign_all_plugins
        ;;

    check-plugins)
        check_root
        PROD_FLAG="${2:-}"
        check_plugins_smart "$PROD_FLAG"
        ;;


    verify)
        check_root
        verify_all
        ;;

    reprovision)
        check_root
        check_dependencies
        if [[ -z "$COMPONENT" ]]; then
            log_error "reprovision requiere un nombre de componente"
            echo "  Uso: sudo bash tools/provision.sh reprovision <componente>"
            echo "  Componentes válidos: ${COMPONENTS[*]}"
            exit 1
        fi
        valid=false
        for c in "${COMPONENTS[@]}"; do
            [[ "$c" == "$COMPONENT" ]] && valid=true && break
        done
        if [[ "$valid" == "false" ]]; then
            log_error "Componente desconocido: ${COMPONENT}"
            echo "  Componentes válidos: ${COMPONENTS[*]}"
            exit 1
        fi
        reprovision_component "$COMPONENT"
        verify_component "$COMPONENT" && log_info "Verificación post-reprovision: OK"
        ;;

    help|--help|-h)
        echo ""
        echo "  ML Defender — tools/provision.sh"
        echo ""
        echo "  FASE:  PHASE 1 (DAY 97) — Ed25519 keypairs + ChaCha20 seeds + libsodium 1.0.19"
        echo ""
        echo "  USO:"
        echo "    sudo bash tools/provision.sh full                 # Provisiona todo"
        echo "    sudo bash tools/provision.sh status               # Tabla de estado"
        echo "    sudo bash tools/provision.sh verify               # Verifica integridad\n    sudo bash tools/provision.sh sign                 # Firma todos los plugins (ADR-025)"
        echo "    sudo bash tools/provision.sh reprovision <name>   # Re-provisiona uno
    sudo bash tools/provision.sh --reset               # Rota TODAS las claves (ADR-025 D11)
    sudo bash tools/provision.sh --reset --dev         # Reset + auto-firma (solo dev)"
        echo ""
        echo "  COMPONENTES: ${COMPONENTS[*]}"
        echo ""
        echo "  PATHS (AppArmor-safe, ADR-019):"
        echo "    ${KEYS_ROOT}/{componente}/private.pem   chmod 600"
        echo "    ${KEYS_ROOT}/{componente}/public.pem    chmod 644"
        echo "    ${KEYS_ROOT}/{componente}/seed.bin      chmod 600"
        echo ""
        echo "  LIBSODIUM:"
        echo "    Versión requerida: ${SODIUM_REQUIRED}"
        echo "    SHA-256:           ${SODIUM_SHA256}"
        echo "    HKDF nativo:       crypto_kdf_hkdf_sha256_extract/expand"
        echo ""
        ;;


    --reset)
        check_root
        check_dependencies
        DEV_MODE="false"
        [[ "${COMPONENT}" == "--dev" ]] && DEV_MODE="true"
        reset_all_keys "$DEV_MODE"
        ;;

    --reset--dev|"--reset --dev")
        check_root
        check_dependencies
        reset_all_keys "true"
        ;;

    *)
        log_error "Modo desconocido: ${MODE}"
        echo "  Modos válidos: full | status | verify | reprovision | help"
        exit 1
        ;;
esac