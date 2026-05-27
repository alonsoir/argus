#include <iostream>
#include <cstdlib>

int main() {
    std::cout << "Test 1: Ejecutando ipset con system()..." << std::endl;
    
    std::string cmd = "ipset list test_ipset -n > /dev/null 2>&1";
    std::cout << "Comando: " << cmd << std::endl;
    
    int ret = system(cmd.c_str());
    std::cout << "Return code: " << ret << std::endl;
    
    if (ret == 0) {
        std::cout << "Set existe" << std::endl;
    } else {
        std::cout << "Set NO existe (esperado)" << std::endl;
    }
    
    std::cout << "Test 2: Creando set..." << std::endl;
    cmd = "ipset create test_ipset hash:ip 2>&1";
    std::cout << "Comando: " << cmd << std::endl;
    
    ret = system(cmd.c_str());
    std::cout << "Return code: " << ret << std::endl;
    
    std::cout << "Test 3: Verificando set existe..." << std::endl;
    cmd = "ipset list test_ipset -n > /dev/null 2>&1";
    ret = system(cmd.c_str());
    std::cout << "Return code: " << ret << std::endl;
    
    std::cout << "Test 4: Destruyendo set..." << std::endl;
    cmd = "ipset destroy test_ipset 2>&1";
    ret = system(cmd.c_str());
    std::cout << "Return code: " << ret << std::endl;
    
    std::cout << "✅ Test completado!" << std::endl;
    return 0;
}
