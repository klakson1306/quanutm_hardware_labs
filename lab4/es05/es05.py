from qubovert import boolean_var
from qubovert import QUBO
import numpy as np
from qubovert.sim import anneal_qubo
import pandas as pd


num_var = None
num_clauses = None
clauses = []
with open('./clauses.txt') as f:
    first = True
    for line in f:
        line = line.split()
        if first:
            num_var,num_clauses = int(line[0]),int(line[1])
            first = False
            continue
        clauses.append([int(line[0]),int(line[1]),int(line[2])])

#constraint expression built in notes, here insert the explanation maybe
#i must create an expression for each clause, and the final function to optimize will be the sum of these expressions
def create_expr(clause: list,variables: list,y: boolean_var):
    var1,var2,var3 = variables[abs(clause[0])-1],variables[abs(clause[1])-1],variables[abs(clause[2])-1]
    expr = QUBO()
    expr += 1
    if clause[0] < 0:
        var1 = 1 - var1
    if clause[1] < 0:
        var2 = 1 - var2
    if clause[2] < 0:
        var3 = 1 - var3
    expr += -var1-var2 -var3 +var1*var2 +var2*var3 +var3*var1 +y*(2 - var1 -var2 -var3)
    return expr 


variables = []
for i in range(num_var):
    variables.append(boolean_var(name=f'x_{i}'))
s_variables = []
for j in range(num_clauses):
    s_variables.append(boolean_var(name=f'y_{j}'))

f = QUBO()
for i,clause in enumerate(clauses):
    f+= create_expr(clause=clause,variables=variables,y=s_variables[i])

solution = anneal_qubo(f,num_anneals=100).best.state
print(solution)
score = f.value(solution)
print(f'Score of the cost function: {score}')

num_satisfied = 0
for clause in clauses:
    sat = False
    for var in clause:
        val = solution[f'x_{abs(var)-1}']
        if (val == 1 and var > 0) or (val == 0 and var < 0):
            sat = True
    if sat:
        num_satisfied+=1
print(f'Number of satisfied clauses: {num_satisfied}/{num_clauses}')
