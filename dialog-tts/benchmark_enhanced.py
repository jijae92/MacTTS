#!/usr/bin/env python3
"""
Benchmark script to compare original vs enhanced Dialog TTS performance.
"""

import time
import sys
from pathlib import Path

# Add dialog-tts to path
sys.path.insert(0, str(Path(__file__).parent))

from dialog_tts import DialogTTSEngine
from dialog_tts_enhanced import CachedDialogTTSEngine
from dialog_tts import load_speaker_map


def benchmark_original(script_path: Path, speaker_map: dict, output_path: Path):
    """Benchmark original DialogTTSEngine."""
    print("\n" + "="*60)
    print("ORIGINAL Dialog TTS Engine")
    print("="*60)

    engine = DialogTTSEngine(
        engine='edge',
        sample_rate=24000,
        stereo=True
    )

    start = time.time()
    result = engine.synthesize_dialog(
        script_path=script_path,
        speaker_map=speaker_map,
        output_path=output_path,
        gap_ms=250,
        xfade_ms=20,
        breath_ms=80,
        normalize_dbfs=-1.0
    )
    elapsed = time.time() - start

    print(f"\n⏱  Total time: {elapsed:.2f}s")
    return elapsed


def benchmark_enhanced(
    script_path: Path,
    speaker_map: dict,
    output_path: Path,
    workers: int = 3,
    use_cache: bool = False,
    lufs: float = None
):
    """Benchmark enhanced CachedDialogTTSEngine."""
    print("\n" + "="*60)
    print(f"ENHANCED Dialog TTS Engine (workers={workers}, cache={use_cache}, lufs={lufs})")
    print("="*60)

    engine = CachedDialogTTSEngine(
        engine='edge',
        sample_rate=24000,
        stereo=True,
        max_workers=workers,
    )

    if not use_cache:
        engine.cache_enabled = False

    start = time.time()
    result = engine.synthesize_dialog_parallel(
        script_path=script_path,
        speaker_map=speaker_map,
        output_path=output_path,
        gap_ms=250,
        xfade_ms=20,
        breath_ms=80,
        normalize_dbfs=-1.0,
        lufs_target=lufs,
    )
    elapsed = time.time() - start

    print(f"\n⏱  Total time: {elapsed:.2f}s")
    return elapsed


def main():
    """Run benchmarks."""
    # Setup
    script_path = Path("samples/dialog.txt")
    if not script_path.exists():
        print(f"Error: Sample script not found: {script_path}")
        return 1

    # Load speaker config
    speaker_map = {
        'A': {
            'voice_name': 'SunHi',
            'rate_wpm': 180,
            'gain_db': 0.0,
            'pan': -0.3,
            'aliases': []
        },
        'B': {
            'voice_name': 'InJoon',
            'rate_wpm': 170,
            'gain_db': 0.0,
            'pan': 0.3,
            'aliases': []
        }
    }

    from dialog_tts import SpeakerConfig
    speaker_map = {
        k: SpeakerConfig(v, engine='edge')
        for k, v in speaker_map.items()
    }

    output_dir = Path("output/benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Benchmark 1: Original engine
    try:
        results['original'] = benchmark_original(
            script_path,
            speaker_map,
            output_dir / "original.wav"
        )
    except Exception as e:
        print(f"Original engine failed: {e}")
        results['original'] = None

    # Benchmark 2: Enhanced engine (no cache, 1 worker)
    try:
        results['enhanced_1worker'] = benchmark_enhanced(
            script_path,
            speaker_map,
            output_dir / "enhanced_1worker.wav",
            workers=1,
            use_cache=False
        )
    except Exception as e:
        print(f"Enhanced 1 worker failed: {e}")
        results['enhanced_1worker'] = None

    # Benchmark 3: Enhanced engine (no cache, 3 workers)
    try:
        results['enhanced_3workers'] = benchmark_enhanced(
            script_path,
            speaker_map,
            output_dir / "enhanced_3workers.wav",
            workers=3,
            use_cache=False
        )
    except Exception as e:
        print(f"Enhanced 3 workers failed: {e}")
        results['enhanced_3workers'] = None

    # Benchmark 4: Enhanced engine (with cache, 3 workers) - run twice to show cache benefit
    try:
        # First run (cache miss)
        results['enhanced_cache_miss'] = benchmark_enhanced(
            script_path,
            speaker_map,
            output_dir / "enhanced_cache_miss.wav",
            workers=3,
            use_cache=True
        )

        # Second run (cache hit)
        results['enhanced_cache_hit'] = benchmark_enhanced(
            script_path,
            speaker_map,
            output_dir / "enhanced_cache_hit.wav",
            workers=3,
            use_cache=True
        )
    except Exception as e:
        print(f"Enhanced cache failed: {e}")
        results['enhanced_cache_miss'] = None
        results['enhanced_cache_hit'] = None

    # Benchmark 5: Enhanced with LUFS normalization
    try:
        results['enhanced_lufs'] = benchmark_enhanced(
            script_path,
            speaker_map,
            output_dir / "enhanced_lufs.wav",
            workers=3,
            use_cache=True,
            lufs=-16.0
        )
    except Exception as e:
        print(f"Enhanced LUFS failed: {e}")
        results['enhanced_lufs'] = None

    # Summary
    print("\n" + "="*60)
    print("BENCHMARK RESULTS")
    print("="*60)

    for name, elapsed in results.items():
        if elapsed:
            if results['original']:
                speedup = results['original'] / elapsed
                print(f"{name:30s}: {elapsed:6.2f}s  ({speedup:4.2f}x)")
            else:
                print(f"{name:30s}: {elapsed:6.2f}s")
        else:
            print(f"{name:30s}: FAILED")

    print("\nKey findings:")
    if results.get('enhanced_3workers') and results.get('original'):
        speedup = results['original'] / results['enhanced_3workers']
        print(f"  • Parallel synthesis (3 workers) is {speedup:.1f}x faster")

    if results.get('enhanced_cache_hit') and results.get('enhanced_cache_miss'):
        speedup = results['enhanced_cache_miss'] / results['enhanced_cache_hit']
        print(f"  • Caching provides {speedup:.1f}x speedup on repeated synthesis")

    if results.get('enhanced_lufs') and results.get('enhanced_3workers'):
        overhead = results['enhanced_lufs'] - results['enhanced_3workers']
        print(f"  • LUFS normalization adds ~{overhead:.1f}s overhead")

    print(f"\nOutput files saved to: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
