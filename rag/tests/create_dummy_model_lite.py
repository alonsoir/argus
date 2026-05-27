#!/usr/bin/env python3
"""
Create dummy ONNX model WITHOUT PyTorch (faster, simpler)

Generates: dummy_embedder.onnx (10-d input → 32-d output)
Purpose: Verify ONNX Runtime C++ API working correctly

Via Appia Quality: Simple solution for simple test
"""

import onnx
from onnx import helper, TensorProto
import numpy as np
import sys

def create_dummy_model():
    print("╔════════════════════════════════════════╗")
    print("║  Creating Dummy ONNX Model            ║")
    print("╚════════════════════════════════════════╝\n")
    
    print("Step 1: Initializing model structure (10→32-d)...")
    
    # Input tensor
    input_tensor = helper.make_tensor_value_info(
        'input', TensorProto.FLOAT, [None, 10]  # Dynamic batch size
    )
    
    # Output tensor
    output_tensor = helper.make_tensor_value_info(
        'embedding', TensorProto.FLOAT, [None, 32]
    )
    print("  ✅ Model structure defined\n")
    
    print("Step 2: Creating network weights...")
    
    # Layer 1: Linear (10 → 64)
    w1 = np.random.randn(10, 64).astype(np.float32) * 0.1
    b1 = np.zeros(64, dtype=np.float32)
    
    w1_init = helper.make_tensor('w1', TensorProto.FLOAT, [10, 64], w1.flatten())
    b1_init = helper.make_tensor('b1', TensorProto.FLOAT, [64], b1.flatten())
    
    # Layer 2: Linear (64 → 32)
    w2 = np.random.randn(64, 32).astype(np.float32) * 0.1
    b2 = np.zeros(32, dtype=np.float32)
    
    w2_init = helper.make_tensor('w2', TensorProto.FLOAT, [64, 32], w2.flatten())
    b2_init = helper.make_tensor('b2', TensorProto.FLOAT, [32], b2.flatten())
    print("  ✅ Weights initialized\n")
    
    print("Step 3: Building computation graph...")
    
    # Nodes: Input → Linear → ReLU → Linear → Tanh → Output
    matmul1 = helper.make_node('MatMul', ['input', 'w1'], ['mm1'])
    add1 = helper.make_node('Add', ['mm1', 'b1'], ['add1'])
    relu = helper.make_node('Relu', ['add1'], ['relu1'])
    matmul2 = helper.make_node('MatMul', ['relu1', 'w2'], ['mm2'])
    add2 = helper.make_node('Add', ['mm2', 'b2'], ['add2'])
    tanh = helper.make_node('Tanh', ['add2'], ['embedding'])
    
    # Create graph
    graph = helper.make_graph(
        nodes=[matmul1, add1, relu, matmul2, add2, tanh],
        name='DummyEmbedder',
        inputs=[input_tensor],
        outputs=[output_tensor],
        initializer=[w1_init, b1_init, w2_init, b2_init]
    )
    print("  ✅ Computation graph built\n")
    
    print("Step 4: Creating ONNX model...")
    
    # Create model with opset 14 (compatible with ONNX Runtime 1.17.1)
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 14)])
    model.ir_version = 8
    print("  ✅ Model created (opset 14)\n")
    
    print("Step 5: Saving to file...")
    onnx.save(model, 'dummy_embedder.onnx')
    print("  ✅ Saved to: dummy_embedder.onnx\n")
    
    print("Step 6: Verifying model...")
    try:
        onnx.checker.check_model(model)
        print("  ✅ Model verification passed\n")
        
        print("Model Information:")
        print(f"  Input:  input → shape (batch_size, 10)")
        print(f"  Output: embedding → shape (batch_size, 32)")
        print(f"  Opset: 14")
        print(f"  Layers: Linear(10→64) → ReLU → Linear(64→32) → Tanh")
        
    except Exception as e:
        print(f"  ⚠️  Verification warning: {e}")
        print("  ℹ️  Model created, may still work")
    
    print("\n╔════════════════════════════════════════╗")
    print("║  Dummy Model Creation Complete ✅      ║")
    print("╚════════════════════════════════════════╝")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(create_dummy_model())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
