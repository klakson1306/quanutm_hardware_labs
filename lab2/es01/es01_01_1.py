from qiskit import QuantumCircuit, transpile
from qiskit.providers.basic_provider import BasicSimulator

qc = QuantumCircuit(2)


qc.h(0)
qc.h(1)

#oracle for |01>
qc.cz(1,0,ctrl_state='0')

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
