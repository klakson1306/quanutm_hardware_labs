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

