from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicProvider
from itertools import product
import numpy as np
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import pandas as pd
from compiler_basic import my_compiler_basic
from qiskit.quantum_info import Statevector

backend_fake = FakeGuadalupeV2()
backend_basic = BasicProvider().get_backend("basic_simulator")


files = {
    "adder_small": "../qasm_files/adder_small.qasm",
    "adder_medium": "../qasm_files/adder_medium.qasm",
    "alu-bdd_288": "../qasm_files/alu-bdd_288.qasm",
    "linearsolver": "../qasm_files/linearsolver.qasm",
    "phaseest": "../qasm_files/phaseest.qasm"
}

def get_probabilities(num_qubits, counts):
    all_states = [''.join(state) for state in product('01', repeat=num_qubits)]
    total_shots = sum(counts.values())
    probabilities = [counts.get(state, 0) / total_shots for state in all_states]
    return probabilities

def Classical_Fidelity(prob_P, prob_Q):
    p_array = np.array(prob_P)
    q_array = np.array(prob_Q)
    
    F = np.sum(np.sqrt(p_array) * np.sqrt(q_array))**2
    
    return float(np.clip(F, 0.0, 1.0))

def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))

def format_ops(ops_dict):
    """Formats a count_ops dictionary into a compact 'gate: count' string."""
    return ", ".join(f"{k}: {v}" for k, v in sorted(ops_dict.items()) if k not in ("measure", "barrier"))

def print_circuit_comparison(name, qc_orig, qc_qiskit, qc_custom, fid_qiskit, fid_custom):
    ops_orig = dict(qc_orig.count_ops())
    ops_qiskit = dict(qc_qiskit.count_ops())
    ops_custom = dict(qc_custom.count_ops())

    # collect all gate names across the 3 circuits (excluding measure/barrier for clarity, shown at bottom)
    all_gates = sorted(
        set(ops_orig.keys()) | set(ops_qiskit.keys()) | set(ops_custom.keys())
    )

    print("\n" + "=" * 78)
    print(f" CIRCUIT: {name.upper()} ({qc_orig.num_qubits} logical qubits)")
    print("=" * 78)
    print(f"{'Metric / Gate':<20} | {'Original (QASM)':>16} | {'Qiskit (Opt=0)':>16} | {'My Basic Compiler':>17}")
    print("-" * 78)

    for gate in all_gates:
        c_orig = ops_orig.get(gate, 0)
        c_qisk = ops_qiskit.get(gate, 0)
        c_cust = ops_custom.get(gate, 0)
        print(f"  {gate:<18} | {c_orig:>16} | {c_qisk:>16} | {c_cust:>17}")

    print("-" * 78)
    print(f"{'Total Gates':<20} | {qc_orig.size():>16} | {qc_qiskit.size():>16} | {qc_custom.size():>17}")
    print(f"{'Circuit Depth':<20} | {qc_orig.depth():>16} | {qc_qiskit.depth():>16} | {qc_custom.depth():>17}")
    print(f"{'Fidelity vs Ideal':<20} | {'1.000000 (Ref)':>16} | {fid_qiskit:>16.6f} | {fid_custom:>17.6f}")
    print("=" * 78)

summary_rows = []


for item in files.items():

    #retrieve filenames, paths and the circuits (both compiled and not compiled) with the number of qubits
    name,path = item
    qc = QuantumCircuit.from_qasm_file(path)
    sv_ideal = Statevector(qc).data
    num_clbits = qc.num_qubits
    qc_custom = my_compiler_basic(qc)
    num_qubits = qc_custom.num_qubits

    #compile with the basic simulator (noisless reference)
    qc_m = qc.copy()
    qc_m .measure_all()
    counts_basic = backend_basic.run(qc_m).result().get_counts()
    prob_basic = get_probabilities(num_qubits,counts_basic)

    #compile with the native transpiler of fakeguadalupe (original reference)
    qc_fake = transpile(qc_m,backend=backend_fake, optimization_level=0, seed_transpiler=42)
    counts_fake = backend_fake.run(qc_fake).result().get_counts()
    prob_fake = get_probabilities(num_qubits=num_qubits,counts=counts_fake)
    fid_fake = Classical_Fidelity(prob_basic,prob_fake)
    ops_fake = dict(qc_fake.count_ops())

    #compile with custom compiler_basic made by us
    counts_custom = backend_fake.run(qc_custom).result().get_counts()
    prob_custom = get_probabilities(num_qubits=num_qubits,counts=counts_custom)
    fid_custom = Classical_Fidelity(prob_basic, prob_custom)
    ops_custom = dict(qc_custom.count_ops())

    final_mapping = {}
    for inst, qargs, cargs in qc_custom.data:
        if inst.name == 'measure':
            phys_bit = qc_custom.find_bit(qargs[0]).index
            class_bit = qc_custom.find_bit(cargs[0]).index
            final_mapping[class_bit] = phys_bit
    active_qubits = [final_mapping[i] for i in range(num_clbits)]
    n_qubits_effettivi = qc_custom.num_qubits
    qc_ideal_match = QuantumCircuit(n_qubits_effettivi)
    qc_ideal_match.compose(qc, qubits=active_qubits, inplace=True)
    sv_ideal_match = Statevector(qc_ideal_match).data
    qc_opt_no_meas = qc_custom.copy()
    qc_opt_no_meas.remove_final_measurements()
    sv_opt_match = Statevector(qc_opt_no_meas).data
    
    fid_custom_logical = Fidelity(sv_ideal_match, sv_opt_match)

    print_circuit_comparison(name, qc, qc_fake, qc_custom, fid_fake, fid_custom)

    summary_rows.append({
        "Circuit": name,
        "Qiskit Depth": qc_fake.depth(),
        "My Depth": qc_custom.depth(),
        "Qiskit CX": ops_fake.get("cx", 0),
        "My CX": ops_custom.get("cx", 0),
        "Qiskit Gates": format_ops(ops_fake),
        "My Gates": format_ops(ops_custom),
        "Qiskit Fid": round(fid_fake, 6),
        "My Fid": round(fid_custom, 6),
        "My Fid Logic": round(fid_custom_logical, 6)
    })

print("\n\n" + "#" * 105)
print(" OVERALL SUMMARY TABLE")
print("#" * 105)
df_summary = pd.DataFrame(summary_rows)
print(df_summary.to_string(index=False))
print("#" * 105)