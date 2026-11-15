from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicProvider
from itertools import product
from qiskit.quantum_info import Statevector
import numpy as np
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import pandas as pd


def get_probabilities(num_qubits, counts):
    all_states = [''.join(state) for state in product('01', repeat=num_qubits)]
    total_shots = sum(counts.values())
    probabilities = [counts.get(state, 0) / total_shots for state in all_states]
    return probabilities

def Fidelity(psi, phi):
    F = np.abs(np.vdot(psi, phi))**2
    return float(np.clip(F, 0.0, 1.0))


#make a dictionary for each file
files = {
    "adder_small": "../qasm_files/adder_small.qasm",
    "adder_medium": "../qasm_files/adder_medium.qasm",
    "alu-bdd_288": "../qasm_files/alu-bdd_288.qasm",
    "linearsolver": "../qasm_files/linearsolver.qasm",
    "phaseest": "../qasm_files/phaseest.qasm"
}

#collect the different backends and optimization levels
backend_basic = BasicProvider().get_backend("basic_simulator")
backend_guadalupe = FakeGuadalupeV2()
basis_gates = ['id', 'ry', 'rx', 'rz', 'cx']
opt_levels = [0, 1, 2, 3]

results = []
#main for
for file in files.items():
    filename,path = file

    #create the circuit
    qc = QuantumCircuit.from_qasm_file(path=path)
    num_qubits = qc.num_qubits

    #simulation with state vector
    sv = Statevector(qc)
    prob_sv = sv.probabilities()

    #simulate with basic simulator
    qc_m = qc.copy()
    qc_m.measure_all()
    counts_basic = backend_basic.run(qc_m).result().get_counts()
    prob_basic = get_probabilities(num_qubits,counts_basic)

    fidelities_basis = []
    fidelities_fake = []
    for o in opt_levels:
        #using basis gates
        qc_basis_gates = transpile(qc,basis_gates=basis_gates,optimization_level=o)
        prob_basis = Statevector(qc_basis_gates).probabilities()
        fidelities_basis.append(Fidelity(prob_sv,prob_basis)) #compare with sv (without measuring)
        depth_basis = qc_basis_gates.depth()
        gates_counts_basis = list(qc_basis_gates.count_ops().items())

        results.append({
            'circuit':filename,
            'backend':'basis gates',
            'optimization':o,
            'depth':depth_basis,
            'gates counts':gates_counts_basis,
            'total gates':qc_basis_gates.size(),
            'fidelity_sv':fidelities_basis[o],
        })

        #using fake_guadalupe
        qc_fake = transpile(qc_m,backend=backend_guadalupe,optimization_level=o, seed_transpiler=42)
        counts_fake = backend_guadalupe.run(qc_fake).result().get_counts()
        prob_fake = get_probabilities(num_qubits,counts_fake)
        fidelities_fake.append(Fidelity(prob_basis,prob_fake)) #compare with basic simulator (with measuring)
        depth_fake = qc_fake.depth()
        gates_counts_fake = list(qc_fake.count_ops().items())

        results.append({
            'circuit':filename,
            'backend':'fake guadalupe',
            'optimization':o,
            'depth':depth_fake,
            'gates counts':gates_counts_fake,
            'total gates':qc_fake.size(),
            'fidelity_sv':fidelities_fake[o],
            })

df = pd.DataFrame(results)
df.to_csv('es01.csv',index=False)


