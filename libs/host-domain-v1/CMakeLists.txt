# libs/host-domain-v1/CMakeLists.txt
# aRGus NDR — libhost_domain_v1: biblioteca del contrato bronce del dominio host (Wazuh).
# Patrón IDÉNTICO a libs/correlation-v1 y libs/seed-client:
#   build standalone (Release) → install /usr/local. Sin -Werror (las libs no reciben
#   $(CMAKE_FLAGS); solo Release). Las deps (OpenSSL, libsodium, nlohmann) las garantiza
#   el Vagrantfile de la VM defender (líneas 63, 331-344), NO CMake.
# OJO: se compila e instala en la VM `defender` (todo el toolchain), como correlation-v1.
# El wazuh-adapter (Pieza 1) la enlazará desde la VM `wazuh` vía /usr/local.

cmake_minimum_required(VERSION 3.16)
project(host_domain_v1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- biblioteca del contrato -------------------------------------------------
# Deps enlazadas directas (presentes en la VM, sin find_package — patrón correlation-v1):
#   crypto  -> HMAC-SHA256 (serialize, col 33)
#   sodium  -> BLAKE2b-256 (mint_event_id)
add_library(host_domain_v1 SHARED
        src/host_domain_v1.cpp
)
target_include_directories(host_domain_v1 PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
target_link_libraries(host_domain_v1 PUBLIC crypto sodium)

# --- install system-wide (/usr/local) — como correlation-v1 ------------------
install(TARGETS host_domain_v1 LIBRARY DESTINATION lib)
install(DIRECTORY include/host_domain_v1 DESTINATION include)

# --- test (spec ejecutable, se cuelga de test-all vía CTest) -----------------
enable_testing()
add_executable(test_host_domain_v1 tests/test_host_domain_v1.cpp)
target_link_libraries(test_host_domain_v1 PRIVATE host_domain_v1)
add_test(
        NAME host_domain_v1_golden
        COMMAND test_host_domain_v1
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/vectors/host_domain_v1_vectors.json
)