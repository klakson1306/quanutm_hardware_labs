from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator

'''
since we are searching for 1 item out of 4 (using 2 qubits), the initial uniform superposition vector starts at an angle of 30 degrees from the 
perpendicular axis of the unmarked states. each grover iteration rotates the state vector by exactly 2 times this initial angle, so by 60 degrees.
by using a single iteration, the vector is rotated to 30 + 60 = 90 degrees, perfectly aligning with the marked state axis and giving a 100% probability of 
measuring it. by applying a second iteration, geometrically in the two-dimensional space spanned by the correct vector and the perpendicular one, we rotate 
it by another 60 degrees, so the final angle becomes 150 degrees. At this position, the probability of measuring the marked state is sin(150)^2 = 1/4, and 
the probability for the unmarked states is cos(150)^2 = 3/4 (which is exactly 1/4 for each of the 3 wrong states). therefore, the projections on the bases
result once again in a complete uniform superposition of all the possible combinations, just with different relative phases.
'''


qc = QuantumCircuit(2)


qc.h(0)
qc.h(1)

#oracle for |00>
qc.x(0)
qc.x(1)
qc.cz(0,1)
qc.x(0)
qc.x(1)

#diffuser
qc.h(0)
qc.h(1)
qc.x(0)
qc.x(1)
qc.cz(0,1)
qc.x(0)
qc.x(1)
qc.h(0)
qc.h(1)

#measure
qc.measure_all()


#retrieve the results
backend = BasicSimulator()
transpiled = transpile(qc,backend)
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
