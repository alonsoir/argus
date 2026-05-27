# 📋 CHECKLIST REVISIÓN DÍA 36

## [ ] CÓDIGO GENERADO POR IA - COMPRENSIÓN REQUERIDA
- [ ] He leído y comprendo cada archivo
- [ ] Entiendo el propósito de cada componente
- [ ] Sé cómo modificar parámetros clave
- [ ] Conozco las limitaciones del enfoque sintético

## [ ] CONVENCIONES C++20 DEL PROYECTO
- [ ] Smart pointers usados correctamente
- [ ] RAII para manejo de recursos
- [ ] Const-correctness
- [ ] Manejo de errores con excepciones
- [ ] No raw loops (usar algoritmos STL)

## [ ] USO CORRECTO DE DIMENSIONALITYREDUCER
- [ ] API train/transform/save/load usada correctamente
- [ ] Dimensiones correctas (384→128, etc.)
- [ ] Validación de varianza implementada
- [ ] Manejo de errores en operaciones FAISS

## [ ] MANEJO ADECUADO DE ERRORES
- [ ] Validación de entrada/salida
- [ ] Mensajes de error claros
- [ ] Recursos liberados en excepciones
- [ ] Logging adecuado

## [ ] DOCUMENTACIÓN VIA APPIA QUALITY
- [ ] README.md completo y claro
- [ ] Comentarios en código explicativos
- [ ] Propósito y limitaciones documentados
- [ ] Instrucciones de ejecución paso a paso

## [ ] COMPILACIÓN EN DEBIAN 12
- [ ] Dependencias verificadas
- [ ] Compila sin warnings con -Wall -Wextra
- [ ] Script de compilación funciona
- [ ] Tests unitarios compilan y ejecutan

## [ ] NO USAMOS CÓDIGO QUE NO PASE:

### [ ] Compila limpio (sin warnings)
g++ -std=c++20 -Wall -Wextra -Werror -O2 synthetic_data_generator.cpp -o test_compile

### [ ] Test unitario PASS
./run_tests  # Todos los tests deben pasar

### [ ] Test contra golden dataset
# Verificar que golden dataset tiene estadísticas correctas

### [ ] Performance razonable
# <5 segundos para 20K eventos sintéticos

## [ ] ENTENDIMIENTO COMPLETO
No ejecutaremos código que no entendemos.
Cada línea debe tener sentido.
Si no entendemos algo → preguntamos o reescribimos esa parte.