from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.qasm2 import dumps
from qiskit.quantum_info import Statevector
import matplotlib.pyplot as plt
'''
The circuit implemented in this code represents the application of the Grover algorithm used to find the state |11> from a uniform superposition
of 2 qubits.
The oracle is constructed from the first control-z gate applied to the second qubit, marking with a phase the state |11>;
Then the Diffuser is applied, composed by two hadamard gates (the dagger operator of the initialization), two x gates, the control z gate on the second qubit
and finally the same operations in reverse order before the control z gate: in this way the probability amplitude of the wanted state (the one we marked in the oracle)
is amplified.
At the end we measure the state, obtaining with the maximum probability in this case the wanted state |11>
'''

#create the circuit with 2 qubits (and 2 classical bits where to store the measurements of qbits)
qc = QuantumCircuit(2,2)

#the initial state is by default |00>

#applying the hadamard gate to both qubits
qc.h(0)
qc.h(1)

#applying a control-z gate (control qubit = 0, target qubit=1)
qc.cz(0,1)

#applying the hadamard gate to both qubits
qc.h(0)
qc.h(1)

#applying the x gate to both qubits
qc.x(0)
qc.x(1)

qc.cz(0,1)

#applying the x gate to both qubits
qc.x(0)
qc.x(1)

#applying the hadamard gate to both qubits
qc.h(0)
qc.h(1)

#print the statevector before measuring the qubits
sv = Statevector(qc)
print(sv)

#measuring both qubits, sotring the result in classical bits 0 and 1
qc.measure(0,0)
qc.measure(1,1)

#using the basic simulator to simulate the circuit and retrieve the output
backend = BasicSimulator()
transpiled = transpile(qc,backend)
job = backend.run(transpiled,shots=1024)
result = job.result()
counts = result.get_counts(qc)
print("Counts: " , counts)

#finally generate the file representing the circuit in openqasm
qasm_str = dumps(qc)
with open('es03_qasm.qasm','w') as f:
    f.write(qasm_str)
    f.close()

#print the circuit on the terminal
print(qc.draw())




