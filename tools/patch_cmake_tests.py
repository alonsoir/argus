#!/usr/bin/env python3
# patch_cmake_tests.py — añade test_autonomy_integration y test_autonomy_e2e a CMakeLists
from pathlib import Path
import sys

OK = '✅'; ERR = '❌'

def fail(msg):
    print(f'{ERR} {msg}', file=sys.stderr)
    sys.exit(1)

# ── etcd-server ───────────────────────────────────────────────────────────────
etcd_cmake = Path('/vagrant/etcd-server/CMakeLists.txt')
content = etcd_cmake.read_text()

if 'test_autonomy_integration' in content:
    print(f'{OK} etcd-server CMakeLists: test_autonomy_integration ya presente — skip')
else:
    # Buscar anchor para insertar antes de los tests existentes
    anchor = 'if(BUILD_TESTS)'
    if anchor not in content:
        fail(f'etcd-server CMakeLists: anchor "{anchor}" no encontrado')

    insert = '''# ── Test B: Autonomy Integration DAY 156 ─────────────────────────────────────
add_executable(test_autonomy_integration
    tests/test_autonomy_integration.cpp
)
target_include_directories(test_autonomy_integration PRIVATE
    ${CMAKE_SOURCE_DIR}/src
    /usr/local/include
    /usr/local/include/vault_client
)
target_link_libraries(test_autonomy_integration PRIVATE
    GTest::gtest_main
    crypto_provider
    zmq
    nlohmann_json::nlohmann_json
)
add_test(NAME test_autonomy_integration COMMAND test_autonomy_integration)

'''
    # Insertar DENTRO del bloque BUILD_TESTS, tras la apertura
    content = content.replace(anchor, anchor + '\n' + insert, 1)
    etcd_cmake.write_text(content)
    print(f'{OK} etcd-server CMakeLists: test_autonomy_integration añadido')

# ── firewall-acl-agent ────────────────────────────────────────────────────────
fw_cmake = Path('/vagrant/firewall-acl-agent/CMakeLists.txt')
content = fw_cmake.read_text()

if 'test_autonomy_e2e' in content:
    print(f'{OK} firewall CMakeLists: test_autonomy_e2e ya presente — skip')
else:
    # Insertar junto a test_autonomy_subscriber
    anchor = 'add_test(NAME test_autonomy_subscriber COMMAND test_autonomy_subscriber)'
    if anchor not in content:
        fail(f'firewall CMakeLists: anchor test_autonomy_subscriber no encontrado')

    insert = '''
# ── Test A: Autonomy E2E DAY 156 ─────────────────────────────────────────────
add_executable(test_autonomy_e2e
    tests/test_autonomy_e2e.cpp
)
target_include_directories(test_autonomy_e2e PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    /usr/local/include
    /usr/local/include/vault_client
)
target_link_libraries(test_autonomy_e2e PRIVATE
    firewall_core
    GTest::gtest_main
    vault_client
    crypto_provider
    zmq
)
add_test(NAME test_autonomy_e2e COMMAND test_autonomy_e2e)
'''
    content = content.replace(anchor, anchor + insert, 1)
    fw_cmake.write_text(content)
    print(f'{OK} firewall CMakeLists: test_autonomy_e2e añadido')

print(f'\n{OK} CMakeLists parcheados correctamente')