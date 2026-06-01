"""
The Tree of Life and Quantum Taxonomy - The Shape of Thought
=============================================================
Species counts across the tree of life encoded by divergence time on 6 qubits.
Does the QFT sort kingdoms? Or does our categorisation need amending?

Three runs: Animals only, Plants only, All kingdoms mixed.
Encoding: taxonomic group -> divergence time (MYA) -> log bin -> quantum state
The spectrum is TIME, measured in millions of years.

Experiment #5 in the Shape of Thought quantum series.
"""

import argparse
import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator

from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

N_QUBITS = 6
N_BINS = 2 ** N_QUBITS  # 64
TIME_MIN = 50.0     # MYA - youngest divergence we track
TIME_MAX = 3500.0   # MYA - oldest (archaea/bacteria)
LOG_MIN = np.log10(TIME_MIN)
LOG_MAX = np.log10(TIME_MAX)
BIN_WIDTH_LOG = (LOG_MAX - LOG_MIN) / N_BINS
DEFAULT_SHOTS = 8192
SEED = 42

OUTPUT_DIR = Path(__file__).parent

# ---- Tree of Life Data ---------------------------------------------------
# (group_name, species_count, divergence_mya, kingdom)
# Sources: Catalogue of Life, IUCN, Our World in Data, Royal Society
# Divergence times: molecular clock estimates, rounded

TREE_OF_LIFE = [
    # ANIMALIA - 32 phyla, major ones listed
    ("Porifera (sponges)", 8500, 600, "Animalia"),
    ("Ctenophora (comb jellies)", 200, 580, "Animalia"),
    ("Cnidaria (jellyfish/coral)", 11000, 580, "Animalia"),
    ("Placozoa", 3, 600, "Animalia"),
    ("Acoelomorpha", 400, 560, "Animalia"),
    ("Platyhelminthes (flatworms)", 20000, 550, "Animalia"),
    ("Gastrotricha", 800, 540, "Animalia"),
    ("Rotifera", 2200, 540, "Animalia"),
    ("Nematoda (roundworms)", 25000, 600, "Animalia"),
    ("Nematomorpha", 360, 540, "Animalia"),
    ("Priapulida", 20, 535, "Animalia"),
    ("Kinorhyncha", 250, 535, "Animalia"),
    ("Loricifera", 35, 535, "Animalia"),
    ("Bryozoa", 6000, 480, "Animalia"),
    ("Brachiopoda", 400, 530, "Animalia"),
    ("Phoronida", 15, 530, "Animalia"),
    ("Annelida (segmented worms)", 17000, 530, "Animalia"),
    ("Mollusca (snails/octopi)", 85000, 540, "Animalia"),
    ("Arthropoda (insects/spiders)", 1200000, 530, "Animalia"),
    ("Onychophora (velvet worms)", 200, 530, "Animalia"),
    ("Tardigrada (water bears)", 1300, 530, "Animalia"),
    ("Echinodermata (starfish)", 7000, 530, "Animalia"),
    ("Hemichordata", 130, 530, "Animalia"),
    ("Chordata (vertebrates)", 66000, 530, "Animalia"),
    ("Chaetognatha (arrow worms)", 130, 540, "Animalia"),
    ("Xenacoelomorpha", 450, 560, "Animalia"),

    # PLANTAE - 14 divisions
    ("Chlorophyta (green algae)", 8000, 1000, "Plantae"),
    ("Charophyta", 4000, 700, "Plantae"),
    ("Marchantiophyta (liverworts)", 9000, 470, "Plantae"),
    ("Anthocerotophyta (hornworts)", 300, 470, "Plantae"),
    ("Bryophyta (mosses)", 12000, 470, "Plantae"),
    ("Lycopodiophyta (club mosses)", 1300, 410, "Plantae"),
    ("Polypodiophyta (ferns)", 10500, 360, "Plantae"),
    ("Cycadophyta (cycads)", 340, 280, "Plantae"),
    ("Ginkgophyta (ginkgo)", 1, 270, "Plantae"),
    ("Coniferophyta (conifers)", 630, 310, "Plantae"),
    ("Gnetophyta", 80, 250, "Plantae"),
    ("Magnoliophyta (flowering plants)", 260000, 140, "Plantae"),

    # FUNGI - 8 phyla
    ("Chytridiomycota", 1000, 660, "Fungi"),
    ("Blastocladiomycota", 200, 600, "Fungi"),
    ("Neocallimastigomycota", 20, 500, "Fungi"),
    ("Zoopagomycota", 200, 500, "Fungi"),
    ("Mucoromycota", 1000, 500, "Fungi"),
    ("Glomeromycota", 300, 460, "Fungi"),
    ("Ascomycota (sac fungi)", 83000, 400, "Fungi"),
    ("Basidiomycota (mushrooms)", 34000, 400, "Fungi"),

    # SAR SUPERGROUP (former protists)
    ("Stramenopiles (diatoms/kelp)", 25000, 1200, "SAR"),
    ("Alveolata (dinoflagellates)", 30000, 1200, "SAR"),
    ("Rhizaria (forams/radiolarians)", 11000, 1200, "SAR"),

    # EXCAVATA
    ("Euglenozoa", 2000, 1500, "Excavata"),
    ("Metamonada", 500, 1500, "Excavata"),

    # AMOEBOZOA
    ("Amoebozoa (slime moulds)", 5000, 1500, "Amoebozoa"),

    # ARCHAEA
    ("Euryarchaeota", 8000, 3500, "Archaea"),
    ("Crenarchaeota", 2000, 3500, "Archaea"),
    ("Thaumarchaeota", 1500, 3000, "Archaea"),
    ("Asgard archaea", 500, 2500, "Archaea"),

    # BACTERIA (representative phyla)
    ("Proteobacteria", 200000, 3500, "Bacteria"),
    ("Firmicutes", 100000, 3500, "Bacteria"),
    ("Actinobacteria", 80000, 3000, "Bacteria"),
    ("Cyanobacteria", 5000, 2700, "Bacteria"),
    ("Bacteroidetes", 50000, 3000, "Bacteria"),
    ("Spirochaetes", 3000, 3000, "Bacteria"),
    ("Fusobacteria", 500, 3000, "Bacteria"),
    ("Deinococcus-Thermus", 200, 3000, "Bacteria"),
    ("Chloroflexi", 2000, 3200, "Bacteria"),
    ("Planctomycetes", 1000, 3000, "Bacteria"),
]


# ---- Encoding Pipeline ---------------------------------------------------

def time_to_bin(mya):
    if mya <= 0:
        return 0
    log_t = np.log10(mya)
    idx = int((log_t - LOG_MIN) / BIN_WIDTH_LOG)
    return max(0, min(N_BINS - 1, idx))

def bin_center_time(b):
    log_center = LOG_MIN + (b + 0.5) * BIN_WIDTH_LOG
    return 10 ** log_center

def get_kingdom_data(kingdom=None):
    if kingdom:
        data = [(name, count, mya, k) for name, count, mya, k in TREE_OF_LIFE if k == kingdom]
    else:
        data = list(TREE_OF_LIFE)
    results = []
    for name, count, mya, k in data:
        results.append({
            'name': name, 'species': count, 'mya': mya,
            'kingdom': k, 'bin': time_to_bin(mya),
        })
    return results


# ---- Amplitude Vectors ---------------------------------------------------

def build_amplitudes(taxa_data):
    counts = np.zeros(N_BINS)
    for t in taxa_data:
        counts[t['bin']] += t['species']
    if counts.sum() == 0:
        return np.zeros(N_BINS), counts
    amps = np.sqrt(counts / counts.sum())
    amps /= np.linalg.norm(amps)
    return amps, counts


# ---- Quantum Circuits ----------------------------------------------------

def build_circuits(amps, label, seed=SEED):
    circuits = {}

    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.initialize(amps)
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    circuits[f'{label}_direct'] = qc

    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.initialize(amps)
    qc.append(QFTGate(N_QUBITS), range(N_QUBITS))
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    circuits[f'{label}_qft'] = qc

    rng = np.random.default_rng(seed)
    shuffled = amps.copy()
    rng.shuffle(shuffled)
    qc = QuantumCircuit(N_QUBITS, N_QUBITS)
    qc.initialize(shuffled)
    qc.append(QFTGate(N_QUBITS), range(N_QUBITS))
    qc.measure(range(N_QUBITS), range(N_QUBITS))
    circuits[f'{label}_shuffled_qft'] = qc

    return circuits

def run_sim(circuits, shots=DEFAULT_SHOTS):
    sim = AerSimulator()
    pm = generate_preset_pass_manager(backend=sim, optimization_level=1)
    results = {}
    for name, qc in circuits.items():
        transpiled = pm.run(qc)
        result = sim.run(transpiled, shots=shots).result()
        results[name] = result.get_counts()
    return results


# ---- Analysis ------------------------------------------------------------

def counts_to_histogram(counts):
    hist = np.zeros(N_BINS)
    for bitstring, count in counts.items():
        idx = int(bitstring, 2)
        if idx < N_BINS:
            hist[idx] += count
    return hist

def detect_peaks(hist, shots):
    uniform = shots / N_BINS
    peaks_idx, props = find_peaks(hist, height=uniform * 1.5, distance=3, prominence=shots * 0.008)
    return [
        {'bin': int(i), 'time_mya': round(bin_center_time(i), 1),
         'count': int(hist[i]), 'ratio': round(hist[i] / uniform, 2)}
        for i in peaks_idx
    ]

def find_density_peaks(bin_counts):
    smoothed = gaussian_filter1d(bin_counts.astype(float), sigma=1.0)
    peaks_idx, _ = find_peaks(smoothed, height=max(smoothed) * 0.05, distance=3, prominence=max(smoothed) * 0.03)
    return [
        {'bin': int(i), 'time_mya': round(bin_center_time(i), 1),
         'density': round(bin_counts[i], 0)}
        for i in peaks_idx
    ]

def analyse_run(results, shots, bin_counts, label):
    analysis = {}
    for name in [f'{label}_direct', f'{label}_qft', f'{label}_shuffled_qft']:
        if name not in results:
            continue
        hist = counts_to_histogram(results[name])
        peaks = detect_peaks(hist, shots)
        uniform = np.full(N_BINS, shots / N_BINS)
        chi2 = float(np.sum((hist - uniform)**2 / uniform))
        analysis[name] = {
            'histogram': hist.tolist(), 'peaks': peaks, 'chi_squared': round(chi2, 1),
        }
    analysis['density_peaks'] = find_density_peaks(bin_counts)
    return analysis


# ---- Visualisation -------------------------------------------------------

KINGDOM_COLOURS = {
    'Animalia': '#cc4444', 'Plantae': '#44aa44', 'Fungi': '#aa8844',
    'SAR': '#4488cc', 'Excavata': '#cc88cc', 'Amoebozoa': '#88cccc',
    'Archaea': '#ff8800', 'Bacteria': '#ffaa44',
}

def time_to_colour(mya):
    t = (np.log10(max(50, min(3500, mya))) - LOG_MIN) / (LOG_MAX - LOG_MIN)
    r = 0.3 + 0.5 * t
    g = 0.5 * (1 - abs(2 * t - 1))
    b = 0.3 + 0.5 * (1 - t)
    return (r, g, b)

def plot_kingdom_spectrum(all_data, bin_counts_dict, filename):
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    kingdoms_to_plot = [
        ('animalia', 'Animals - Species by Divergence Time'),
        ('plantae', 'Plants - Species by Divergence Time'),
        ('all', 'All Kingdoms - Species by Divergence Time'),
    ]

    for ax, (kingdom, title) in zip(axes, kingdoms_to_plot):
        counts = bin_counts_dict[kingdom.lower() if kingdom != 'all' else 'all']
        colors = [time_to_colour(bin_center_time(b)) for b in range(N_BINS)]
        ax.bar(range(N_BINS), counts, color=colors, edgecolor='#333', linewidth=0.3)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel('Species count', fontsize=10)

        era_marks = [
            (140, 'Cretaceous\n(flowers)'), (530, 'Cambrian\n(animals)'),
            (470, 'Ordovician\n(land plants)'), (2700, 'Archean\n(cyanobacteria)'),
        ]
        for mya, label in era_marks:
            b = time_to_bin(mya)
            if 0 <= b < N_BINS:
                ax.axvline(x=b, color='#aaa', linestyle=':', alpha=0.4)
                ax.text(b, ax.get_ylim()[1] * 0.85, label, fontsize=7, ha='center', color='#666')

    axes[-1].set_xlabel('Log-time bins (50 MYA - 3,500 MYA, recent -> ancient)', fontsize=11)
    fig.suptitle('Tree of Life: Where Species Concentrate in Evolutionary Time', fontsize=14)
    plt.tight_layout()
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")

def plot_qft_contrast(analysis_dict, shots, filename):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    uniform = shots / N_BINS

    for ax, (label, title, color) in zip(axes, [
        ('animalia', 'Animals QFT', '#cc4444'),
        ('plantae', 'Plants QFT', '#44aa44'),
        ('all', 'All Kingdoms QFT', '#8844cc'),
    ]):
        qft_key = f'{label}_qft'
        if qft_key in analysis_dict:
            hist = np.array(analysis_dict[qft_key]['histogram'])
            ax.bar(range(1, N_BINS), hist[1:], color=color, edgecolor='#333', linewidth=0.3, alpha=0.8)
            ax.axhline(y=uniform, color='gray', linestyle='--', alpha=0.5)
            ax.set_title(title, fontsize=13)
            ax.set_xlabel('Frequency (k)', fontsize=11)

            top_k = np.argsort(hist[1:])[-3:] + 1
            for k in top_k:
                if hist[k] > uniform * 1.3:
                    ax.annotate(f'k={k}', xy=(k, hist[k]), xytext=(k + 3, hist[k] * 1.05),
                                arrowprops=dict(arrowstyle='->', color='#444'), fontsize=10, fontweight='bold')

    axes[0].set_ylabel('Measurement counts', fontsize=11)
    fig.suptitle('Does the QFT Sort Kingdoms?', fontsize=15, y=1.02)
    plt.tight_layout()
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {path}")


# ---- Main ----------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Tree of Life Quantum Taxonomy')
    parser.add_argument('--shots', type=int, default=DEFAULT_SHOTS)
    parser.add_argument('--hardware', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("  TREE OF LIFE AND QUANTUM TAXONOMY")
    print("  The Shape of Thought - Experiment #5")
    print("=" * 60)

    # Build data for three runs
    runs = {}
    bin_counts_dict = {}

    for label, kingdom in [('animalia', 'Animalia'), ('plantae', 'Plantae'), ('all', None)]:
        data = get_kingdom_data(kingdom)
        total_species = sum(d['species'] for d in data)
        amps, counts = build_amplitudes(data)
        occupied = int(np.sum(counts > 0))
        print(f"\n  {label}: {len(data)} taxa, {total_species:,} species, {occupied}/{N_BINS} bins occupied")
        runs[label] = {'data': data, 'amps': amps, 'counts': counts}
        bin_counts_dict[label] = counts

    # Build and run circuits
    all_circuits = {}
    for label in ['animalia', 'plantae', 'all']:
        circuits = build_circuits(runs[label]['amps'], label)
        all_circuits.update(circuits)

    print(f"\n  Running simulator ({args.shots:,} shots per circuit)...")
    raw_results = run_sim(all_circuits, args.shots)

    # Analyse each run
    all_analysis = {}
    for label in ['animalia', 'plantae', 'all']:
        analysis = analyse_run(raw_results, args.shots, runs[label]['counts'], label)
        all_analysis.update(analysis)
        all_analysis[f'{label}_density_peaks'] = analysis['density_peaks']

    # Plots
    print("\n  Generating plots...")
    plot_kingdom_spectrum(TREE_OF_LIFE, bin_counts_dict, 'life_spectrum.png')
    plot_qft_contrast(all_analysis, args.shots, 'life_qft_contrast.png')

    # Results
    print("\n8. Saving results...")
    results_json = {
        'experiment': 'Tree of Life and Quantum Taxonomy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'parameters': {'n_qubits': N_QUBITS, 'time_range_mya': [TIME_MIN, TIME_MAX], 'scale': 'logarithmic'},
    }

    for label in ['animalia', 'plantae', 'all']:
        qft_key = f'{label}_qft'
        shuf_key = f'{label}_shuffled_qft'
        results_json[label] = {
            'n_taxa': len(runs[label]['data']),
            'total_species': sum(d['species'] for d in runs[label]['data']),
            'density_peaks': all_analysis.get(f'{label}_density_peaks', []),
            'qft_peaks': all_analysis.get(qft_key, {}).get('peaks', []),
            'shuffled_qft_peaks': all_analysis.get(shuf_key, {}).get('peaks', []),
            'chi_squared_qft': all_analysis.get(qft_key, {}).get('chi_squared', 0),
        }

    json_path = OUTPUT_DIR / 'life_spectrum_results.json'
    json_path.write_text(json.dumps(results_json, indent=2))
    print(f"  Saved {json_path}")

    # Summary
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    for label in ['animalia', 'plantae', 'all']:
        print(f"\n  {label.upper()}:")
        print(f"    Density peaks:")
        for p in all_analysis.get(f'{label}_density_peaks', []):
            print(f"      {p['time_mya']:.0f} MYA ({p['density']:.0f} species)")
        qft_key = f'{label}_qft'
        print(f"    QFT peaks:")
        for p in all_analysis.get(qft_key, {}).get('peaks', []):
            if p['bin'] > 0:
                print(f"      k={p['bin']}: {p['count']} counts ({p['ratio']}x uniform)")
        shuf_key = f'{label}_shuffled_qft'
        shuf_peaks = [p for p in all_analysis.get(shuf_key, {}).get('peaks', []) if p['bin'] > 0]
        print(f"    Shuffled QFT peaks: {len(shuf_peaks)} (control)")

    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
