#!/usr/bin/env python3
"""
Fix ONNX Model Opset - Day 34

Regenera los modelos ONNX con opset 14 (IR version 9)
para compatibilidad con ONNX Runtime C++ v1.17.1
"""

import torch
import torch.nn as nn
import numpy as np

class ChronosEmbedder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(83, 256)
        self.fc2 = nn.Linear(256, 512)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.tanh(self.fc2(x))
        return x

class SBERTEmbedder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(83, 192)
        self.fc2 = nn.Linear(192, 384)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.tanh(self.fc2(x))
        return x

class AttackEmbedder(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(83, 128)
        self.fc2 = nn.Linear(128, 256)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.tanh(self.fc2(x))
        return x

def export_model(model, output_path, model_name, output_dim):
    """Export model to ONNX with opset 14 using legacy exporter"""
    model.eval()
    dummy_input = torch.randn(1, 83)

    print(f"\n{'='*60}")
    print(f"Exporting: {model_name}")
    print('='*60)

    # Export with opset 14 (IR version 9) using LEGACY exporter
    # dynamo=False forces the old exporter that supports opset 14
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,  # ← Key change: 14 instead of 18
        do_constant_folding=True,
        input_names=['features'],
        output_names=['embedding'],
        dynamic_axes={
            'features': {0: 'batch_size'},
            'embedding': {0: 'batch_size'}
        },
        dynamo=False  # ← CRITICAL: Use legacy exporter for opset < 18
    )

    print(f"  ✅ Model exported: {output_path}")
    print(f"  Opset version: 14 (IR version 9)")
    print(f"  Output dimension: {output_dim}")

    # Verify with onnx
    try:
        import onnx
        model_onnx = onnx.load(output_path)
        onnx.checker.check_model(model_onnx)
        print(f"  ✅ ONNX model validated")

        # Show IR version
        ir_version = model_onnx.ir_version
        print(f"  IR version: {ir_version}")
    except ImportError:
        print("  ⚠️  onnx package not installed (validation skipped)")
    except Exception as e:
        print(f"  ⚠️  Validation warning: {e}")

def main():
    print("╔════════════════════════════════════════════════════════╗")
    print("║  ML Defender - Fix Model Opset (Day 34)              ║")
    print("╚════════════════════════════════════════════════════════╝")
    print("\nRegenerating models with opset 14 (IR version 9)...")
    print("This fixes compatibility with ONNX Runtime C++ v1.17.1\n")

    # Chronos Embedder (83 → 512-d)
    chronos = ChronosEmbedder()
    export_model(chronos, "chronos_embedder.onnx", "Chronos (Time Series)", 512)

    # SBERT Embedder (83 → 384-d)
    sbert = SBERTEmbedder()
    export_model(sbert, "sbert_embedder.onnx", "SBERT (Semantic)", 384)

    # Attack Embedder (83 → 256-d)
    attack = AttackEmbedder()
    export_model(attack, "attack_embedder.onnx", "Attack (Patterns)", 256)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("  ✅ chronos_embedder.onnx - 512-d (opset 14)")
    print("  ✅ sbert_embedder.onnx   - 384-d (opset 14)")
    print("  ✅ attack_embedder.onnx  - 256-d (opset 14)")
    print("\n" + "="*60)
    print("✅ ALL MODELS REGENERATED")
    print("="*60)
    print("\nNext steps:")
    print("  1. Backup old models (already done as *.bak)")
    print("  2. Test C++ inference: ./test_real_embedders")
    print("  3. If working, proceed to Fase 3")

if __name__ == "__main__":
    main()