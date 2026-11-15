from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.providers.basic_provider import BasicSimulator
from qiskit import transpile

'''
In order to satisfy the conditions: a + b = 5; b + c = 3; a + c = 2; a != b != c,
solving the linear system gives directly a unique solution:
        a = 2 -> a0 = 0, a1 = 1
        b = 3 -> b0 = 1, b1 = 1
        c = 0 -> c0 = 0, c1 = 0

from this we can understand that: the bits must match the exact pattern (a1 a0 b1 b0 c1 c0) = (1 0 1 1 0 0)

This brings us to the boolean condition: (b0 AND b1) AND (NOT(c0) AND NOT(c1)) AND (NOT(a0)) AND a1

We translated this boolean function in our circuit using X gates to invert the qubits that must be 0 (a0, c0, c1) and a multi-controlled gate
targeting the oracle ancilla qubit.

The grover algorithm is repeated 6 times, where we retrieved the optimal number of times by using the definition:
#G = pi/4 * (sqrt(N/M)) - 0.5 --> in this case M = 1, N = 64 -->  #G = 0.78 * 8 - 0.5 = 5.74 ~ 6
'''

# Define the Diffuser
def create_Diffuser(n_qubits):
    qc = QuantumCircuit(n_qubits, name="Diffuser")

    #Apply Hadamard and Pauli-X Gates on all the qubits
    qc.h(range(n_qubits))
    qc.x(range(n_qubits))

    #set the last qubit of the diffuser
    last_qubit = n_qubits-1
    control_qubit = list(range(last_qubit))

    #controlled Z-Gate on the last qubit
    qc.h(last_qubit)
    qc.mcx(control_qubit, last_qubit)
    qc.h(last_qubit)

    #Apply again Hadamard and Pauli-X Gates on all the qubits
    qc.x(range(n_qubits))
    qc.h(range(n_qubits))

    return qc.to_gate()

# Define the Oracle
def create_Oracle():
    qc = QuantumCircuit(9, name="Oracle")

    #Toffoli Gate on qubits 3,4 and 6
    qc.mcx([2,3],6, ctrl_state="11")

    #Toffoli Gate on qubits 5,6 and 8 with inverted controls
    qc.mcx([4,5],7, ctrl_state="00")

    #Pauli-X Gate on the first qubit
    qc.x(0)

    #Multicontrolled CNOT-Gate on qubits 1,2,7,8 and 9
    qc.mcx([0,1,6,7],8)

    #Z-Gate on the last qubit to phase flipping
    qc.z(8)

    #REVERSION OF THE GATES
    qc.mcx([0,1,6,7],8)
    qc.x(0)

    qc.mcx([4,5],7, ctrl_state="00")

    qc.mcx([2,3],6, ctrl_state="11")
    
    return qc.to_gate()

# Main Circuit Section

# Definition of number of EFFECTIVE and ANCILLA qubits
n_qubits = QuantumRegister(6, name= 'q_eff')
n_ancilla = QuantumRegister(3, name= 'ancilla')

# Overall Circuit
main_Circuit = QuantumCircuit(n_qubits, n_ancilla)

# Initialization with Hadarmard Gates
main_Circuit.h(n_qubits)
main_Circuit.barrier()

# Gate Creation
Diffuser_Gate = create_Diffuser(6)
Oracle_gate = create_Oracle()

# Oracle + Diffuser Section Repeated 6 times
for i in range(6):

    #Oracle application on all the 9 qubits
    main_Circuit.append(Oracle_gate, n_qubits[:]+n_ancilla[:])

    #Diffuser application only on the 6 effective qubits
    main_Circuit.append(Diffuser_Gate, n_qubits)
    main_Circuit.barrier()

# Final Measure Section   
c_reg = ClassicalRegister(6, name='c_out')
main_Circuit.add_register(c_reg)
main_Circuit.measure(n_qubits, c_reg)

# Execution of the circuit on the local simulator
sim = BasicSimulator()
shots = 100000

# Compilation of the circuit 
compile_Circuit = transpile(main_Circuit, backend=sim)

result = sim.run(compile_Circuit, shots=shots).result()

# Raw Counts
counts = result.get_counts()

# Sorting the results from the most frequent to the highly unprobable
sorted = dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

# Compute and print the probabilities
print("\nGrover Results:\n")
print("State\t| \tProbability")
print("-" * 25)

for state, frequency in sorted.items():
    probability = frequency / shots
    print(f"{state}\t| \t{probability:.4%}")

#Drawing of the circuit (On terminal and on an external file if remove the comment)
print(main_Circuit.draw('text'))
#main_Circuit.draw('mpl', filename='grover_es03_optional_2.png')