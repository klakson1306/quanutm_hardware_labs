from qubovert import boolean_var
from qubovert import QUBO
import numpy as np
from qubovert.sim import anneal_qubo

#parsing for the file txt
num_nodes = 0
edges = []
weights = []
with open("max_cut.txt") as f:
    for line in f:
        line = line.split()
        if len(line)>1:
            edges.append((int(line[0]),int(line[1])))
            weights.append(int(line[2]))
        else:
            num_nodes = int(line[0])

w = [[0 for _ in range(num_nodes)] for _ in range(num_nodes)]
for i in range(num_nodes):
    for j in range(num_nodes):
        if (i,j) in edges:
            index = edges.index((i,j))
            w[i][j] = weights[index]
        else:
            w[i][j] = 0 

nodes = []
model = QUBO()
for i in range(num_nodes):
    nodes.append(boolean_var(f'x_{i}'))

for i in range(num_nodes):
    for j in range(num_nodes):
        if w[i][j] != 0:
            model += w[i][j]*(2*nodes[i]*nodes[j] - nodes[i] - nodes[j])

solution = anneal_qubo(model)
print(solution)

