#!/usr/bin/env python3
"""
Create dummy ONNX model for testing ONNX Runtime integration.

Generates: dummy_embedder.onnx (10-d input → 32-d output)
Purpose: Verify ONNX Runtime C++ API working correctly

Via Appia Quality: Test infrastructure before real models
"""

import torch
import torch.nn as nn
import sys

class DummyEmbedder(nn.Module):
    """
    Simple neural network for testing ONNX Runtime.

    Architecture:
      Input (10-d) → Linear(64) → ReLU → Linear(32) → Tanh → Output (32-d)

    This mimics the structure of real embedders but with tiny dimensions.
    """
    def __init__(self, input_dim=10, output_dim=32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim),
            nn.Tanh()  # Normalize to [-1, 1]
        )

    def forward(self, x):
        return self.net(x)

def main():
    print("╔════════════════════════════════════════╗")
    print("║  Creating Dummy ONNX Model            ║")
    print("╚════════════════════════════════════════╝\n")

    # Create model
    print("Step 1: Initializing DummyEmbedder (10→32-d)...")
    model = DummyEmbedder(input_dim=10, output_dim=32)
    model.eval()
    print("  ✅ Model initialized\n")

    # Create dummy input for tracing
    print("Step 2: Creating dummy input tensor...")
    dummy_input = torch.randn(1, 10)
    print(f"  ✅ Input shape: {dummy_input.shape}\n")

    # Export to ONNX
    print("Step 3: Exporting to ONNX format...")
    torch.onnx.export(
        model,
        dummy_input,
        "dummy_embedder.onnx",
        input_names=['input'],
        output_names=['embedding'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'embedding': {0: 'batch_size'}
        },
        opset_version=14,  # Compatible with ONNX Runtime 1.17.1
        verbose=False
    )
    print("  ✅ Exported to: dummy_embedder.onnx\n")

    # Verify model
    print("Step 4: Verifying ONNX model...")
    try:
        import onnx
        onnx_model = onnx.load("dummy_embedder.onnx")
        onnx.checker.check_model(onnx_model)
        print("  ✅ Model verified (opset 14)\n")

        # Print model info
        print("Model Information:")
        print(f"  Input:  {onnx_model.graph.input[0].name} → shape (batch_size, 10)")
        print(f"  Output: {onnx_model.graph.output[0].name} → shape (batch_size, 32)")
        print(f"  Opset: {onnx_model.opset_import[0].version}")

    except ImportError:
        print("  ⚠️  onnx package not available for verification")
        print("  ℹ️  Model created, verification skipped")

    print("\n╔════════════════════════════════════════╗")
    print("║  Dummy Model Creation Complete ✅      ║")
    print("╚════════════════════════════════════════╝")

    return 0

if __name__ == "__main__":
    sys.exit(main())