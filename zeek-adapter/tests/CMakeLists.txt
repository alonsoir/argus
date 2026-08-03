# zeek-adapter/tests/CMakeLists.txt
#
# Sin framework de terceros a propósito: un main() con asserts que ctest ejecuta.
# El repo usa ctest (`make correlation-engine-test`); qué framework usa por dentro
# NO se ha medido (DAY 226). Si es GoogleTest y prefieres alinear, cámbialo aquí.

add_executable(test_to_row test_to_row.cpp)
target_link_libraries(test_to_row PRIVATE zeek_adapter_lib)
target_compile_options(test_to_row PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_test(NAME zeek_adapter_to_row COMMAND test_to_row)
