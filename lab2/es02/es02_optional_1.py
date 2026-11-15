from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator

'''
In this code is implemented the quantum adder following the Takahashi advanced structure.

The correspondance between bit values and qubits is different w.r.t. the es02 (made by ourselves), and follow this order:

Values: a1a0, b1b0

Each bit corresponds to the qubits numbered in the order:
0 -> b0                     
1 -> a0
2 -> b1
3 -> a1
4 -> ancilla

The result is read in this way:
0 -> s0
2 -> s1
4 -> s2
'''

backend = BasicSimulator()


# TEST SECTION (uncomment to see the test's results)
'''
print('start testing:\n')
for a in range(4):
    for b in range(4):
        a0 = a & 1
        a1 = (a >> 1) & 1
        b0 = b & 1
        b1 = (b >> 1) & 1
        
        qc = QuantumCircuit(6, 3)
        
        if a0 == 1: qc.x(0)
        if b0 == 1: qc.x(1)
        if a1 == 1: qc.x(3)
        if b1 == 1: qc.x(4)
        

        qc.ccx(0, 1, 2)
        qc.ccx(3, 4, 5)
        qc.cx(3, 4)
        qc.ccx(2, 4, 5)
        qc.cx(2, 4)
        qc.ccx(0, 1, 2)
        qc.cx(0, 1)
        
        
        qc.measure(1, 0)
        qc.measure(4, 1)
        qc.measure(5, 2)
        
        
        transpiled = transpile(qc, backend=backend)
        job = backend.run(transpiled, shots=1024)
        result = job.result()
        counts = result.get_counts(qc)
        
        measured_str = max(counts, key=counts.get)
        measured_sum = int(measured_str, 2)
        expected_sum = a + b
        
        a_str = f"{a1}{a0}"
        b_str = f"{b1}{b0}"
        
        if measured_sum == expected_sum:
            print(f"ok: input {a_str} + {b_str} = {measured_str}")
        else:
            print(f"errore: input {a_str} + {b_str} = {measured_str}")
'''

#ASSIGNMENT SECTION
qc = QuantumCircuit(5,3)


#prepare the input qubit 01 + 11 as requested in the assignment
qc.x(1)
qc.x(0)
qc.x(2)


#step 1
qc.cx(3,2)

#step 2
qc.cx(3,4)

#step 3
qc.ccx(0,1,3)
qc.ccx(2,3,4)

#step 4
qc.cx(3,2)
qc.ccx(0,1,3)

#step 5
#nothing

#step 6
qc.cx(1,0)
qc.cx(3,2)

qc.measure([0,2,4],[0,1,2])


transpiled = transpile(qc,backend=backend)
job = backend.run(transpiled,shots=1024)
result = job.result()
counts = result.get_counts(qc)
#print("Counts: " , counts)
print(f'Result of the operation 01 + 11: {max(counts, key=counts.get)}')  #retrieve the result based on the number of shots that yielded that value
