from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicProvider
from itertools import product
import numpy as np
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import pandas as pd
import random

# import both compilers
from compiler_basic import my_compiler_basic
from compiler import my_compiler_opt

random.seed(42)

backend_fake = FakeGuadalupeV2()
backend_basic = BasicProvider().get_backend("basic_simulator")

files = {
    "adder_small": "../qasm_files/adder_small.qasm",
    "adder_medium": "../qasm_files/adder_medium.qasm",
    "alu-bdd_288": "../qasm_files/alu-bdd_288.qasm",
    "linearsolver": "../qasm_files/linearsolver.qasm",
    "phaseest": "../qasm_files/phaseest.qasm"
}

def get_probabilities(num_clbits, counts):
    all_states = [''.join(state) for state in product('01', repeat=num_clbits)]
    total_shots = sum(counts.values())
    return [counts.get(state, 0) / total_shots for state in all_states]

def Classical_Fidelity(prob_P, prob_Q):

    p_array = np.array(prob_P)
    q_array = np.array(prob_Q)
    
    F = np.sum(np.sqrt(p_array) * np.sqrt(q_array))**2
    
    return float(np.clip(F, 0.0, 1.0))

def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))

def format_ops(ops_dict):
    return ", ".join(f"{k}: {v}" for k, v in sorted(ops_dict.items()) if k not in ("measure", "barrier"))

def print_circuit_comparison(name, qc_orig, qc_qiskit, qc_basic, qc_opt, f_qiskit, f_basic, f_opt):
    o_orig, o_qiskit, o_basic, o_opt = [dict(q.count_ops()) for q in (qc_orig, qc_qiskit, qc_basic, qc_opt)]
    all_gates = sorted(set(o_orig) | set(o_qiskit) | set(o_basic) | set(o_opt))
    
    print("\n" + "=" * 98)
    print(f" CIRCUIT: {name.upper()} ({qc_orig.num_qubits} logical qubits)")
    print("=" * 98)
    print(f"{'Metric / Gate':<16} | {'Original':>12} | {'Qiskit (Lvl 0)':>16} | {'My Basic':>15} | {'My Optimized':>17}")
    print("-" * 98)

    for gate in all_gates:
        if gate in ['measure', 'barrier']: continue
        print(f"  {gate:<14} | {o_orig.get(gate,0):>12} | {o_qiskit.get(gate,0):>16} | {o_basic.get(gate,0):>15} | {o_opt.get(gate,0):>17}")

    print("-" * 98)
    print(f"{'Total Gates':<16} | {qc_orig.size():>12} | {qc_qiskit.size():>16} | {qc_basic.size():>15} | {qc_opt.size():>17}")
    print(f"{'Circuit Depth':<16} | {qc_orig.depth():>12} | {qc_qiskit.depth():>16} | {qc_basic.depth():>15} | {qc_opt.depth():>17}")
    print(f"{'Fidelity':<16} | {'1.000000':>12} | {f_qiskit:>16.6f} | {f_basic:>15.6f} | {f_opt:>17.6f}")
    print("=" * 98)

summary_rows = []

for name, path in files.items():
    qc = QuantumCircuit.from_qasm_file(path)
    qc.remove_final_measurements()
    
    # the number of classical bits is the true measure of logical states
    num_clbits = qc.num_qubits 

    #reference
    qc_m = qc.copy()
    qc_m.measure_all()
    prob_basic = get_probabilities(num_clbits, backend_basic.run(qc_m).result().get_counts())

    #  qiskit compiler
    qc_qiskit = transpile(qc_m, backend=backend_fake, optimization_level=0, seed_transpiler=42)
    prob_qiskit = get_probabilities(num_clbits, backend_fake.run(qc_qiskit,shots=2012).result().get_counts())
    fid_qiskit = Classical_Fidelity(prob_basic, prob_qiskit)

    # custom basic compiler
    qc_basic = my_compiler_basic(qc)
    prob_basic_fake = get_probabilities(num_clbits, backend_fake.run(qc_basic, shots=2012).result().get_counts())
    fid_basic = Classical_Fidelity(prob_basic, prob_basic_fake)

    # custom optimized compiler
    qc_opt = my_compiler_opt(qc)
    prob_opt_fake = get_probabilities(num_clbits, backend_fake.run(qc_opt,shots=2012).result().get_counts())
    fid_opt = Classical_Fidelity(prob_basic, prob_opt_fake)

    print_circuit_comparison(name, qc, qc_qiskit, qc_basic, qc_opt, fid_qiskit, fid_basic, fid_opt)

    ops_basic = dict(qc_basic.count_ops())
    ops_opt = dict(qc_opt.count_ops())
    
    cx_basic = ops_basic.get("cx", 0)
    cx_opt = ops_opt.get("cx", 0)
    
    cx_reduction = ((cx_basic - cx_opt) / cx_basic * 100) if cx_basic > 0 else 0.0
    depth_reduction = ((qc_basic.depth() - qc_opt.depth()) / qc_basic.depth() * 100) if qc_basic.depth() > 0 else 0.0
    fid_improvement = fid_opt - fid_basic

    summary_rows.append({
        "Circuit": name,
        "Qiskit CX": dict(qc_qiskit.count_ops()).get("cx", 0),
        "Basic CX": cx_basic,
        "Opt CX": cx_opt,
        "CX Reduced %": f"{cx_reduction:.1f}%",
        "Basic Depth": qc_basic.depth(),
        "Opt Depth": qc_opt.depth(),
        "Depth Reduced %": f"{depth_reduction:.1f}%",
        "Qiskit Fid": round(fid_qiskit, 4),
        "Basic Fid": round(fid_basic, 4),
        "Opt Fid": round(fid_opt, 4),
        "Fid Gain": f"+{fid_improvement:.4f}"
    })

print("\n\n" + "#" * 120)
print(" FINAL OPTIMIZATION STATS COMPARED TO BASIC COMPILER")
print("#" * 120)
df_summary = pd.DataFrame(summary_rows)
print(df_summary.to_string(index=False))
print("#" * 120)