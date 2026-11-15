from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.qasm2 import dumps
from qiskit.quantum_info import Statevector
import matplotlib.pyplot as plt

'''
The following circuit performs the same Grover algorithm as in the es03.py file, but this time the control-z gate perfomed by the diffuser
is applied by exploiting the identity HXH = Z.
So instead of having a control-z gate in the diffuser, a control-x gate is applied to the second qubit, with an hadamard before and after it.
'''

#create the circuit
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

#equivalent to a control z gate on qubit 1
qc.h(1)
qc.cx(0,1)
qc.h(1)

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
with open('es03_qasm_optional.qasm','w') as f:
    f.write(qasm_str)
    f.close()

#print the circuit on the terminal
print(qc.draw())




