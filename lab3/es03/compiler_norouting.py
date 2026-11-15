from qiskit import QuantumCircuit
from qiskit.circuit.library import RZGate,RXGate,RYGate,XGate
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import numpy as np
from collections import deque
import random, math

backend = FakeGuadalupeV2()
coupling_map = backend.configuration().coupling_map
native_gates = backend.configuration().basis_gates


#optimization functions

def same_gate(qc: QuantumCircuit) -> QuantumCircuit:
    """Cancel adjacent self-inverse gates and merge adjacent rotations on the same qubits."""
    new_qc = QuantumCircuit(qc.num_qubits, qc.num_clbits)
    self_inverse_gates = {'cx', 'x', 'h', 'swap'}
    rotation_map = {'rz': RZGate, 'rx': RXGate, 'ry': RYGate}

    stack = []

    for gate in qc.data:
        op, qubits, clbits = gate.operation, gate.qubits, gate.clbits
        name = op.name

        if not stack:
            stack.append((op, qubits, clbits))
            continue

        prev_op, prev_qubits, prev_clbits = stack[-1]
        prev_name = prev_op.name

        # 1. Cancel adjacent identical self-inverse gates (e.g., CX * CX = I, X * X = I)
        if name in self_inverse_gates and name == prev_name and qubits == prev_qubits:
            print(f"Found self-canceling pair of {name}!")
            stack.pop()

        # 2. Merge adjacent rotation gates of the same type on the SAME qubit
        elif name in rotation_map and name == prev_name and qubits == prev_qubits:
            new_angle = prev_op.params[0] + op.params[0]
            print(f"Found adjacent {name} rotations on same qubit! Merging...")
            stack.pop()
            if not np.isclose(new_angle % (2 * np.pi), 0.0, atol=1e-9):
                merged_op = rotation_map[name](new_angle)
                stack.append((merged_op, qubits, clbits))

        # 3. Combine two adjacent SX gates on the same qubit into a single X gate (SX * SX = X)
        elif name == 'sx' and prev_name == 'sx' and qubits == prev_qubits:
            print("Found two adjacent sx gates! Replacing with x...")
            stack.pop()
            stack.append((XGate(), qubits, clbits))

        else:
            stack.append((op, qubits, clbits))

    for op, qubits, clbits in stack:
        new_qc.append(op, qubits, clbits)

    return new_qc

def bfs_shortest_path(coupling_map: list, start: int, target: int) -> list:
    queue = deque([[start]])
    visited = {start}
    
    while queue:
        path = queue.popleft()
        node = path[-1]

        if node == target:
            return path
            
        for edge in coupling_map:
            if edge[0] == node and edge[1] not in visited:
                visited.add(edge[1])
                queue.append(path + [edge[1]])
                
    return []

def s_matrix(coupling_map: list, num_qubits_phys: int):
    s = np.zeros((num_qubits_phys, num_qubits_phys))
    for i in range(num_qubits_phys):
         for j in range(num_qubits_phys):
              if i != j:
                s[i][j] = len(bfs_shortest_path(coupling_map,i,j)) - 2
    return s

def e_t_matrices(num_qubits_phys: int):

    e = np.full((num_qubits_phys, num_qubits_phys), np.inf)
    t = np.full((num_qubits_phys, num_qubits_phys), np.inf)
    np.fill_diagonal(e, 0.0)
    np.fill_diagonal(t, 0.0)

    properties = backend.properties()
    for gate in properties.gates:
        if gate.gate == 'cx':
            u, v = gate.qubits[0], gate.qubits[1]
            
            for param in gate.parameters:
                if param.name == 'gate_length':
                    t[u][v] = 3*param.value
                if param.name == 'gate_error':
                    e[u][v] = 3*param.value

    for k in range(num_qubits_phys):
        for i in range(num_qubits_phys):
            for j in range(num_qubits_phys):
                if e[i][k] + e[k][j] < e[i][j]:
                    e[i][j] = e[i][k] + e[k][j]
                if t[i][k] + t[k][j] < t[i][j]:
                    t[i][j] = t[i][k] + t[k][j]

    return e, t

def d_matrix(s_matrix,e_matrix,t_matrix, a1 = 0.33, a2 = 0.33, a3 = 0.33):
    s,e,t = s_matrix/np.max(s_matrix), e_matrix/np.max(e_matrix), t_matrix/np.max(t_matrix)
    return (a1*s)+(a2*e)+(a3*t)

def cost_function(mapping, d_matrix, qc: QuantumCircuit):
    cost = 0

    for gate in qc.data:
        if gate.operation.name in ['measure','barrier']:
            continue

    idx_log = [qc.find_bit(q).index for q in gate.qubits]

    if len(idx_log) == 2:
        idx_phys_1 = mapping[idx_log[0]]
        idx_phys_2 = mapping[idx_log[1]]
        cost += d_matrix[idx_phys_1][idx_phys_2]
    if len(idx_log) == 3:
            idx_phys_1 = mapping[idx_log[0]]
            idx_phys_2 = mapping[idx_log[1]]
            idx_phys_3 = mapping[idx_log[2]]
            cost += d_matrix[idx_phys_1][idx_phys_2]
            cost += d_matrix[idx_phys_1][idx_phys_3]
            cost += d_matrix[idx_phys_2][idx_phys_3]
    
    return cost

def find_neighbor_mapping(mapping: list) -> list:
    copy = mapping.copy()
    random.shuffle(copy)
    return copy

def opt_mapping(initial_map: list, d_matrix, qc: QuantumCircuit, t_init=10.0, t_f=0.01, delta=0.95) -> list:
    curr_mapping = initial_map
    opt_mapping = initial_map
    curr_cost = cost_function(curr_mapping, d_matrix, qc)
    opt_cost = curr_cost
    t = t_init
    while t >= t_f:
        neigh_mapping = find_neighbor_mapping(curr_mapping)
        neigh_cost = cost_function(neigh_mapping,d_matrix,qc)
        if neigh_cost < opt_cost:
            opt_cost = neigh_cost
            opt_mapping = neigh_mapping

        if neigh_cost < curr_cost:
            curr_cost = neigh_cost
            curr_mapping = neigh_mapping

        else:
            acceptance_probability = math.exp((curr_cost - neigh_cost) / t)
            if random.random() < acceptance_probability:
                curr_cost = neigh_cost
                curr_mapping = neigh_mapping
        t = t * delta

    return opt_mapping

def check_mapping(idx: list) -> bool:
    return idx in coupling_map

def check_gate(gate: str) -> bool:
    return gate in native_gates

def from_h(qc: QuantumCircuit,idx: int):
    qc.rz(np.pi/2,idx)
    qc.sx(idx)
    qc.rz(np.pi/2,idx)
    return

def from_u3(qc: QuantumCircuit, angles: list ,idx: int):
    qc.rz(angles[2],idx)
    qc.sx(idx)
    qc.rz(angles[0],idx)
    qc.rz(np.pi,idx)
    qc.sx(idx)
    qc.rz(angles[1],idx)
    qc.rz(np.pi,idx)

def swap(mapping: list, path: list, qc: QuantumCircuit):
    for i in range(len(path)-2):
        a = path[i]
        b = path[i+1]
        qc.cx(a,b)
        qc.cx(b,a)
        qc.cx(a,b)

        for idx in range(len(mapping)):
            if mapping[idx] == a:
                mapping[idx] = b
            elif mapping[idx] == b:
                mapping[idx] = a

def from_ccx(qa_log: int, qb_log: int, qt_log: int, qc: QuantumCircuit, mapping: list):
    
    qa = mapping[qa_log]
    qb = mapping[qb_log]
    qt = mapping[qt_log]

    from_h(qc,qt)
    
    if check_mapping([qb,qt]):
        qc.cx(qb,qt)
    else:
        path = bfs_shortest_path(coupling_map,qb,qt)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qb,qt)
    
    qc.rz(-np.pi/4,qt)
    
    if check_mapping([qa,qt]):
            qc.cx(qa,qt)
    else:
        path = bfs_shortest_path(coupling_map,qa,qt)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qa,qt)
    
    qc.rz(np.pi/4,qt)

    if check_mapping([qb,qt]):
            qc.cx(qb,qt)
    else:
        path = bfs_shortest_path(coupling_map,qb,qt)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qb,qt)

    qc.rz(-np.pi/4,qt)

    if check_mapping([qa,qt]):
                qc.cx(qa,qt)
    else:
        path = bfs_shortest_path(coupling_map,qa,qt)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qa,qt)

    qc.rz(np.pi/4,qt)
    qc.rz(np.pi/4,qb)
    from_h(qc,qt)

    if check_mapping([qa,qb]):
                qc.cx(qa,qb)
    else:
        path = bfs_shortest_path(coupling_map,qa,qb)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qa,qb)

    qc.rz(np.pi/4,qa)
    qc.rz(-np.pi/4,qb)

    if check_mapping([qa,qb]):
                    qc.cx(qa,qb)
    else:
        path = bfs_shortest_path(coupling_map,qa,qb)
        swap(mapping,path,qc)
        qa, qb, qt = mapping[qa_log], mapping[qb_log], mapping[qt_log]
        qc.cx(qa,qb)


    
def my_compiler_opt(qc: QuantumCircuit) -> QuantumCircuit:
    num_qubits_log = qc.num_qubits
    num_qubits_phys = backend.configuration().n_qubits
    initial_mapping = list(range(num_qubits_phys)) #trivial mapping, the index is the logical index and the entry is the physical index

    #first we clean eventual duplicate gates
    qc = same_gate(qc=qc)
    #find the s,e,t and d matrix
    s = s_matrix(coupling_map,num_qubits_phys)
    e,t = e_t_matrices(num_qubits_phys)
    a1,a2,a3 = 0.7,0.3,0
    d = d_matrix(s,e,t,a1,a2,a3)
    #find the optimal mapping
    mapping = opt_mapping(initial_mapping,d,qc)
    print(f'Optimized mapping: {mapping}\nParameters for D matrix: a1 = {a1}, a2 = {a2}, a3 = {a3}')

    qc_compiled = QuantumCircuit(num_qubits_phys, num_qubits_log)

    for gate in qc.data:
        gate_name = gate.operation.name
        idx_log = [qc.find_bit(q).index for q in gate.qubits]
        params = gate.operation.params

        #check number of qubits
        match len(idx_log):
            case 1:
                qa = mapping[idx_log[0]]
                if check_gate(gate_name):
                    qc_compiled.append(gate.operation,[qa])
                elif gate_name=='h':
                    from_h(qc_compiled,qa)
                elif gate_name=='t':
                    qc_compiled.rz(np.pi/4,qa)
                elif gate_name=='tdg':
                    qc_compiled.rz(-np.pi/4,qa)
                elif gate_name=='s':
                    qc_compiled.rz(np.pi/2,qa)
                elif gate_name=='u3':
                    from_u3(qc_compiled,params,qa)
                else:
                    print('********** 1-Qubit Gate non implemented ************')
            case 2:
                if check_gate(gate_name):
                    qa = mapping[idx_log[0]]
                    qb = mapping[idx_log[1]]
                    if check_mapping([qa,qb]):
                        qc_compiled.append(gate.operation,[qa,qb])
                    else:
                        path = bfs_shortest_path(coupling_map,qa,qb)
                        swap(mapping,path,qc_compiled)
                        qc_compiled.append(gate.operation,[mapping[idx_log[0]],mapping[idx_log[1]]])
                else:
                    print('********** 2-Qubit Gate non implemented ************')
            case 3:
                if gate_name=='ccx':
                    from_ccx(idx_log[0],idx_log[1],idx_log[2],qc_compiled,mapping)
                else:
                    print('********* 3-Qubit Gate not implemented ************')

    #again we check the same gates
    qc_compiled = same_gate(qc_compiled)

    #measuring respecting the trivial mapping for the fidelity
    for idx in range(num_qubits_log):
        qc_compiled.measure(mapping[idx],idx)

    return qc_compiled