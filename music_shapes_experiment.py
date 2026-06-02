"""
Music Shapes and Quantum Emotion - The Shape of Thought
=======================================================
Melodies from different traditions and moods encoded as MIDI pitch
distributions on 6 qubits. Does the QFT hear the tradition? The mood?

Experiment #8 in the Shape of Thought quantum series.
"""

import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

N_QUBITS = 6
N_BINS = 64
SHOTS = 8192
MIDI_MIN, MIDI_MAX = 36, 96
OUTPUT_DIR = Path(__file__).parent

MELODIES = {
    # Traditions
    'Twinkle Twinkle': {'tradition': 'Western nursery', 'mood': 'happy',
        'notes': [60,60,67,67,69,69,67,65,65,64,64,62,62,60,
                  67,67,65,65,64,64,62,67,67,65,65,64,64,62,
                  60,60,67,67,69,69,67,65,65,64,64,62,62,60]},
    'Bach Invention No.1': {'tradition': 'Baroque', 'mood': 'neutral',
        'notes': [60,62,64,60,67,72,71,72,74,72,71,69,67,65,64,62,
                  60,62,64,65,67,69,71,72,74,76,77,76,74,72,71,69,
                  67,65,64,62,60,64,67,72,74,72,71,69,67,65,64,62,
                  60,55,57,59,60,62,64,65,67,69,71,72,74,76,77,79]},
    'Amazing Grace': {'tradition': 'Pentatonic', 'mood': 'solemn',
        'notes': [60,65,69,67,69,72,69,67,65,60,65,69,67,69,72,
                  74,72,69,67,65,60,65,69,67,69,72,69,67,65,60]},
    'Blues in C': {'tradition': 'Blues', 'mood': 'melancholy',
        'notes': [60,63,65,66,67,70,72,70,67,66,65,63,60,
                  60,63,65,66,67,70,72,75,72,70,67,66,65,63,60,
                  60,63,65,66,67,65,63,60,58,55,53,51,48]},
    'Raga Yaman': {'tradition': 'Indian', 'mood': 'devotional',
        'notes': [60,64,66,67,69,73,75,72,75,73,69,67,66,64,60,
                  60,64,66,67,69,73,75,72,75,73,69,67,66,64,60,
                  48,52,54,55,57,61,63,60,63,61,57,55,54,52,48]},
    'Sakura': {'tradition': 'Japanese', 'mood': 'wistful',
        'notes': [64,65,69,64,65,69,71,72,71,69,65,64,
                  69,71,72,71,69,65,64,65,62,60,
                  64,65,69,64,65,69,71,72,71,69,65,64]},

    # Happy vs Sad
    'Ode to Joy': {'tradition': 'Classical', 'mood': 'happy',
        'notes': [64,64,65,67,67,65,64,62,60,60,62,64,64,62,62,
                  64,64,65,67,67,65,64,62,60,60,62,64,62,60,60]},
    'Moonlight Sonata': {'tradition': 'Classical', 'mood': 'sad',
        'notes': [61,64,68,61,64,68,61,64,68,61,64,68,
                  61,63,68,61,63,68,60,63,68,60,63,68,
                  59,63,67,59,63,67,59,62,68,59,62,68]},
    'When The Saints': {'tradition': 'Spiritual', 'mood': 'happy',
        'notes': [60,64,65,67,60,64,65,67,60,64,65,67,
                  65,64,60,64,62,64,65,64,60,60,62,
                  64,64,62,60,62,60,57,60]},
    'Danny Boy': {'tradition': 'Irish', 'mood': 'sad',
        'notes': [60,65,67,69,72,74,72,69,67,69,72,67,65,
                  60,62,64,65,67,65,64,62,60,57,55,
                  60,65,67,69,72,74,76,77,76,74,72]},
    'Happy Birthday': {'tradition': 'Folk', 'mood': 'happy',
        'notes': [60,60,62,60,65,64,60,60,62,60,67,65,
                  60,60,72,69,65,64,62,70,70,69,65,67,65]},
    'Taps': {'tradition': 'Military bugle', 'mood': 'sad',
        'notes': [60,60,65,60,65,67,60,65,67,60,65,67,
                  65,67,72,67,72,65,67,65,60,60,65]},
    'Wedding March': {'tradition': 'Classical', 'mood': 'happy',
        'notes': [67,67,67,72,72,71,69,67,67,65,64,65,67,
                  67,67,67,72,72,71,69,67,67,65,64,65,67,
                  72,74,76,77,76,74,72]},
    'Chopin Funeral March': {'tradition': 'Classical', 'mood': 'sad',
        'notes': [56,56,56,56,63,62,62,61,61,60,60,63,
                  56,56,56,56,63,62,62,61,61,60,60,56,
                  56,56,56,63,62,61,60,56]},
}


def encode_melody(notes):
    notes = np.array(notes)
    notes = notes[(notes >= MIDI_MIN) & (notes < MIDI_MAX)]
    counts = np.zeros(N_BINS)
    bin_width = (MIDI_MAX - MIDI_MIN) / N_BINS
    for n in notes:
        b = int((n - MIDI_MIN) / bin_width)
        b = max(0, min(N_BINS - 1, b))
        counts[b] += 1
    shifted = counts + 0.01
    amps = np.sqrt(shifted / shifted.sum())
    amps /= np.linalg.norm(amps)
    return amps, counts, notes


def run_qft(amps):
    sim = AerSimulator()
    pm = generate_preset_pass_manager(backend=sim, optimization_level=1)
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.initialize(amps)
    qc.append(QFTGate(N_QUBITS), range(N_QUBITS))
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    result = sim.run(pm.run(qc), shots=SHOTS).result()
    hist = np.zeros(N_BINS)
    for bs, ct in result.get_counts().items():
        hist[int(bs, 2)] += ct
    return hist


def main():
    uniform = SHOTS / N_BINS
    results = {}

    print("=" * 60)
    print("  MUSIC SHAPES AND QUANTUM EMOTION")
    print("  The Shape of Thought - Experiment #8")
    print("=" * 60)

    for name, data in MELODIES.items():
        amps, counts, notes = encode_melody(data['notes'])
        hist = run_qft(amps)
        top_k = [(int(k), round(float(hist[k] / uniform), 1))
                 for k in np.argsort(hist)[-5:][::-1] if k > 0]

        results[name] = {
            'tradition': data['tradition'],
            'mood': data['mood'],
            'n_notes': len(notes),
            'unique_pitches': len(set(notes)),
            'range': int(notes.max() - notes.min()),
            'mean_pitch': round(float(notes.mean()), 1),
            'top_k': top_k,
        }
        icon = 'H' if data['mood'] == 'happy' else 'S' if data['mood'] == 'sad' else '-'
        print(f"  [{icon}] {name:30s} k={top_k[:3]}")

    print("\n  HAPPY vs SAD:")
    for mood in ['happy', 'sad']:
        entries = {n: r for n, r in results.items() if r['mood'] == mood}
        third_ks = [r['top_k'][2][0] for r in entries.values() if len(r['top_k']) > 2]
        print(f"    {mood.upper()}: third k = {third_ks}")

    json_path = OUTPUT_DIR / 'music_results.json'
    json_path.write_text(json.dumps({
        'experiment': 'Music Shapes and Quantum Emotion',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'results': results,
    }, indent=2))
    print(f"\n  Saved {json_path}")


if __name__ == '__main__':
    main()
