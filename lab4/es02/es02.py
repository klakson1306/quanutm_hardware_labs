from qubovert import boolean_var
from qubovert import QUBO
import numpy as np
from qubovert.sim import anneal_qubo



num_nodes = None
num_colors = None
edges = []
i = 0
with open("graph_coloring.txt") as f:
    for line in f:
        line = line.split()
        if i!=0:
            edges.append((int(line[0]),int(line[1])))
        else:
            num_nodes,num_colors = int(line[0]), int(line[1])
        i+=1

#the number of rows are the nodes
#the number of columns are the colors
variables = [[0 for _ in range(num_colors)] for _ in range(num_nodes)]
for i in range(num_nodes):
    for j in range(num_colors):
        variables[i][j] = boolean_var(f'x_{i}{j}')

model = QUBO()
for j in range(num_nodes):
    model_round = QUBO()
    model_round += 1
    for i in range(num_colors):
        model_round += -variables[j][i]

    model_round = model_round**2
    model += model_round

for edge in edges:
    i,j = edge[0],edge[1]
    for c in range(num_colors):
        model += variables[i][c]*variables[j][c]

solution = anneal_qubo(model,num_anneals=100)
print(solution.best)
print(model.is_solution_valid(solution))
