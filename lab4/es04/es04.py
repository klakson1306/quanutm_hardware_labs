from qubovert import boolean_var
from qubovert import QUBO
import numpy as np
from qubovert.sim import anneal_qubo
import pandas as pd

df = pd.read_csv('./guests.csv',header=0,index_col=0)
num_tables = 4
num_guests = len(df)
seats_table = num_guests // num_tables

variables = [[boolean_var(name=f'x_{k}_{df.columns[i]}') for i in range(num_guests)]
             for k in range(num_tables)] #x_ki where k is the table number and i is the guest

#write the function to minimize
cost_f = QUBO()
for k in range(num_tables):
    for i in range(num_guests):
        for j in range(i+1,num_guests):
            cost_f-= variables[k][i]*variables[k][j]*df.values[i][j]

#the first constraint (each table must have 5 seats)
costraint_1 = QUBO()
for k in range(num_tables):
    sub = QUBO()
    sub-=seats_table
    for i in range(num_guests):
        sub+= variables[k][i]
    sub = sub**2
    costraint_1+=sub

#the second constraint (each guest must be in 1 and only 1 table)
costraint_2 = QUBO()
for i in range(num_guests):
    sub = QUBO()
    sub-=1
    for k in range(num_tables):
        sub+=variables[k][i]
    sub = sub**2
    costraint_2+=sub


p1,p2 = 10,10 #TO DO modify the weights of the constraints
model = cost_f + p1*costraint_1 + p2*costraint_2
solution = anneal_qubo(model, num_anneals=100).best.state
p_guests = costraint_2.value(solution)
p_table = costraint_1.value(solution)
score = -cost_f.value(solution)

print(f'Penalty guests: {p_guests}\nPenaly tables: {p_table}\nScore cost function: {score}')
for k in range(num_tables):
    seated = [df.columns[i] for i in range(num_guests) if solution[f'x_{k}_{df.columns[i]}'] == 1]
    print(f"Tavolo {k} ({len(seated)}): {seated}")