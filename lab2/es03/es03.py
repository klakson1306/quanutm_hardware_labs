from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.circuit.library import MCMTGate,ZGate

'''
In order to satisfy the condition: a + b = 4; a != b,
It means that either a = 1 and b = 3 or viceversa.
so the two values can be:   1. a0 = 1, a1 = 0, b0 = 1, b1 = 1 
                            2. a0 = 1, a1 = 1, b0 = 1, b1 = 0

from this we can understand that: the first bit of both values must be always 1
                                  the second bits of the two values must be different a1 != b1

This brings us to the boolean condition:  (a0 AND b0) AND (a1 XOR b1)

We translated this boolean function in our circuit using 3 ancilla qubits to store intermediate and final results.
The AND are converted in Toffoli gates.
The XOR is converted in two subsequential CNOT on the same target qubit, changing the control.

The grover algorithm is repeated 2 times, where we retrieved the optimal number of times by using the definition:
#G = pi/4 * (sqrt(N/M)) - 0.5 --> in this case M = 2, N = 16 -->  #G = 0.78 * 2.82 - 0.5 = 1.69 ~ 2
'''

#define blocks 
def uniform_superposition(qc: QuantumCircuit, n: int) -> None:
    for i in range(n):
        qc.h(i)
    return 

def oracle(qc: QuantumCircuit) -> None:
    qc.ccx(0,1,4)
    qc.cx(2,5)
    qc.cx(3,5)
    qc.ccx(4,5,6)
    qc.z(6)
    qc.ccx(4,5,6)
    qc.cx(3,5)
    qc.cx(2,5)
    qc.ccx(0,1,4)
    return

def diffuser(qc: QuantumCircuit, n: int) -> None:
    #in this case the initialization (set of H) is the inverse of itself -> H^-1 = H
    uniform_superposition(qc,n)
    for i in range(n):
        qc.x(i)
    #create the 3-control Z gate
    c3z = MCMTGate(ZGate(),num_ctrl_qubits=3,num_target_qubits=1)
    qc.compose(c3z,qubits=[0,1,2,3],inplace=True)
    for i in range(n):
        qc.x(i)
    uniform_superposition(qc,n)
    return

qc = QuantumCircuit(7,4)

#initialize
uniform_superposition(qc=qc,n=4)

#run the grover algorithm (2 iterations in this case)
for i in range(2):
    oracle(qc)
    diffuser(qc,4)

qc.measure([0,1,2,3],[0,2,1,3]) #not following the standard order of clbits, so that the result can be seen as (a1a0 b1b0)

#retrieve the results
backend = BasicSimulator()
transpiled = transpile(qc,backend=backend)
job = backend.run(transpiled,shots=100000)
result = job.result()
counts = result.get_counts(qc)
counts = dict(sorted(counts.items(),key=lambda item: item[1], reverse=True))
#print out the results
print("State\t| \tProbability")
print("-" * 25)
for state, frequency in counts.items():
    probability = frequency / 100000
    print(f"{state}\t| \t{probability:.4%}")
print(qc.draw('text'))



