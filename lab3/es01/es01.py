from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicProvider
from itertools import product
from qiskit.quantum_info import Statevector
import numpy as np
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import pandas as pd


def Classical_Fidelity(prob_P, prob_Q):
    """
    Calcola la corretta Classical Fidelity (Hellinger) 
    tra due vettori di probabilità.
    """
    p_array = np.array(prob_P)
    q_array = np.array(prob_Q)
    
    # Moltiplica le radici quadrate elemento per elemento e somma, poi eleva al quadrato
    F = np.sum(np.sqrt(p_array) * np.sqrt(q_array))**2
    
    return float(np.clip(F, 0.0, 1.0))


# Define function to obtain probabilities
def get_probabilities(num_qubits, counts):
    all_states = [''.join(state) for state in product('01', repeat=num_qubits)]
    total_shots = sum(counts.values())
    probabilities = [counts.get(state, 0) / total_shots for state in all_states]
    return probabilities

# Define function for fidelity calculation (given)
def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))


# make a dictionary for each file
files = {
    "adder_small": "../qasm_files/adder_small.qasm",
    "adder_medium": "../qasm_files/adder_medium.qasm",
    "alu-bdd_288": "../qasm_files/alu-bdd_288.qasm",
    "linearsolver": "../qasm_files/linearsolver.qasm",
    "phaseest": "../qasm_files/phaseest.qasm"
}

# collect the different backends and optimization levels
backend_basic = BasicProvider().get_backend("basic_simulator")
backend_guadalupe = FakeGuadalupeV2()
basis_gates = ['id', 'ry', 'rx', 'rz', 'cx']
opt_levels = [0, 1, 2, 3]

# List of final dictionaries results
results = []

# Main 'for' loop for each file
for file in files.items():
    filename,path = file

    # Create the circuit
    qc = QuantumCircuit.from_qasm_file(path=path)
    num_qubits = qc.num_qubits      # Obtain specific number of qubits

    # simulation with state vector
    sv = Statevector(qc)
    prob_sv = sv.data

    # Simulation with BasicProvider()
    qc_m = qc.copy()
    qc_m.measure_all()
    counts_basic = backend_basic.run(qc_m).result().get_counts()
    prob_basic = get_probabilities(num_qubits,counts_basic)


    fidelities_basis = []
    fidelities_fake = []
    for o in opt_levels:
        # Compilation with given Basis Gates
        qc_basis_gates = transpile(qc,basis_gates=basis_gates,optimization_level=o)
        prob_basis = Statevector(qc_basis_gates).data
        fidelities_basis.append(Fidelity(prob_sv,prob_basis))
        depth_basis = qc_basis_gates.depth()
        gates_counts_basis = list(qc_basis_gates.count_ops().items())

        results.append({
            'circuit':filename,
            'backend':'basis gates',
            'optimization':o,
            'depth':depth_basis,
            'gates counts':gates_counts_basis,
            'total gates':qc_basis_gates.size(),
            'fidelity':fidelities_basis[o],
        })

    for o in opt_levels:
        # Compilation with Fake_GuadalupeV2()
        qc_fake = transpile(qc_m,backend=backend_guadalupe,optimization_level=o)
        counts_fake = backend_guadalupe.run(qc_fake,shots=2012).result().get_counts()
        prob_fake = get_probabilities(num_qubits,counts_fake)
        fidelities_fake.append(Classical_Fidelity(prob_basic,prob_fake))
        depth_fake = qc_fake.depth()
        gates_counts_fake = list(qc_fake.count_ops().items())

        results.append({
            'circuit':filename,
            'backend':'fake guadalupe',
            'optimization':o,
            'depth':depth_fake,
            'gates counts':gates_counts_fake,
            'total gates':qc_fake.size(),
            'fidelity':fidelities_fake[o],
            })

# Printout of the results on the terminal window
current_group = None
for item in results:
    group_key = (item['circuit'], item['backend'])

    if group_key != current_group:
        if current_group is not None:
            print("\n" + "*" * 42 + "\n")
        current_group = group_key
        print(f"Circuit: {item['circuit']} | Backend: {item['backend']}")
        print("-" * 47)

    print(f"Optimization {item['optimization']} --> "f"Fidelity: {item['fidelity']:.6f}, "f"Gate Counts: {item['gates counts']} (Total: {item['total gates']}), "f"Depth: {item['depth']}")

# Export data on .csv file
df = pd.DataFrame(results)
df.to_csv('es01.csv', index= False)

