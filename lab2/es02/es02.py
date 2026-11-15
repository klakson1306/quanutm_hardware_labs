from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator

'''
The two values (2-bit each) are mapped in the following way:
Values: a1a0, b1b0

Each bit corresponds to the qubits numbered in the order:
0 -> a0
1 -> b0
2 -> ancilla
3 -> a1
4 -> b1
5 -> ancilla

The result is read in this way:
1 -> s0
4 -> s1
5 -> s2

'''

backend = BasicSimulator()


# TEST SECTION (uncomment to see the test's results)

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


#ASSIGNMENT SECTION
qc = QuantumCircuit(6,3)


#prepare the input qubit 01 + 11 as requested in the assignment
qc.x(0)
qc.x(1)
qc.x(4)


qc.ccx(0,1,2) #performs the carry between the least significant bits and store the result on qubit2 (first ancilla qubit)

qc.ccx(3,4,5) #performs the carry between the most significant bits and store the result on qubit5
qc.cx(3,4) #performs the sum between the most significant bits and store the result on qubit4 (overwriting the b1 value)
qc.ccx(2,4,5) # adding the eventual carry of the least significant bits to the current sum of the most significant bits 
qc.cx(2,4) #adding the eventual carry of the least significant bits to the result of the sum of the most significant bits
qc.ccx(0,1,2)#reset the ancilla for c1
qc.cx(0,1) #performs the sum between the least significant bits and store the result on qubit1 (overwriting the b0 value)



qc.measure(1,0)
qc.measure(4,1)
qc.measure(5,2)

transpiled = transpile(qc,backend=backend)
job = backend.run(transpiled,shots=1024)
result = job.result()
counts = result.get_counts(qc)
#print("Counts: " , counts)
print(f'Result of the operation 01 + 11: {max(counts, key=counts.get)}')  #retrieve the result based on the number of shots that yielded that value

