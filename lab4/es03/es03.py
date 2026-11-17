from qubovert import boolean_var
from qubovert import QUBO
import numpy as np
from qubovert.sim import anneal_qubo


num_obj = None
w = None
pref_weight = []
i = 0
with open("objects.txt") as f:
    for line in f:
        line = line.split()
        if i!=0:
            pref_weight.append((int(line[0]),int(line[1])))
        else:
            num_obj,w = int(line[0]), int(line[1])
        i+=1

#matrix containing each row the object and 2 columns, the first is the preference, the second is the weight
stats = np.zeros((num_obj,2),dtype=int)
for i in range(num_obj):
    for j in range(2):
        if j%2 == 0:
            stats[i][j] = pref_weight[i][0]
        else:
            stats[i][j] = pref_weight[i][1]


objects = [boolean_var(f'x_{i}') for i in range(num_obj)]

#define the function of the preference (maximize it, so put a - sign)
preference = QUBO()
for i in range(num_obj):
    preference -= stats[i][0]*objects[i]

#define the function for the weight
max_s = w #in this case the minimum value of the xi is 0, so max value of s is w

num_s = 0
while 2**(num_s)<w:
    num_s+=1
slack = [boolean_var(f's_{i}') for i in range(num_s)]

weight = QUBO()
weight-=w
for i in range(num_obj):
    weight+= stats[i][1]*objects[i]
for j in range(num_s):
    weight+=(2**j)*slack[j]
weight = weight**2

#we need to calculate the costraint, we need the average value of the cost function
p = sum(stats[:,0])
print(p)
model = QUBO()
model+= preference + p*weight
solution = anneal_qubo(model,num_anneals=100)
print(solution.best)
