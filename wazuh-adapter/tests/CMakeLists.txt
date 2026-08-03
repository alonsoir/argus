# wazuh-adapter/tests/CMakeLists.txt
#
# Sin framework de terceros a propósito: un main() con asserts que ctest ejecuta (mismo
# patrón que suricata/zeek-adapter). Vectores = líneas reales del snapshot day240.

add_executable(test_to_row test_to_row.cpp)
target_link_libraries(test_to_row PRIVATE wazuh_adapter_lib)
target_compile_options(test_to_row PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_test(NAME wazuh_adapter_to_row COMMAND test_to_row)