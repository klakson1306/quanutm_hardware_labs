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

        #cancel adjacent identical self-inverse gates
        if name in self_inverse_gates and name == prev_name and qubits == prev_qubits:
            print(f"Found self-canceling pair of {name}!")
            stack.pop()

        # merge adjacent rotation gates of the same type on the same qubit
        elif name in rotation_map and name == prev_name and qubits == prev_qubits:
            new_angle = prev_op.params[0] + op.params[0]
            print(f"Found adjacent {name} rotations on same qubit! Merging...")
            stack.pop()
            if not np.isclose(new_angle % (2 * np.pi), 0.0, atol=1e-9):
                merged_op = rotation_map[name](new_angle)
                stack.append((merged_op, qubits, clbits))

        # combine two adjacent SX gates on the same qubit into a single X gate 
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

def find_neighbor(q_target: int) -> list:
  neighbor=[]
  for i in coupling_map:
    if i[0]==q_target:
      neighbor.append(i[1])
    elif i[1]==q_target and i[0] not in neighbor:
      neighbor.append(i[0])
  return neighbor

def cost_swap(nb: int, qb: int, qc: QuantumCircuit, d_matrix, idx_gate: int, mapping: list) -> float:
    mapping_copy = mapping.copy()
    idx_log_nb = mapping_copy.index(nb)
    idx_log_qb = mapping_copy.index(qb)
    mapping_copy[idx_log_nb], mapping_copy[idx_log_qb] = mapping_copy[idx_log_qb], mapping_copy[idx_log_nb]

    current_gate = qc.data[idx_gate]
    q_log_curr = [qc.find_bit(current_gate.qubits[0]).index,qc.find_bit(current_gate.qubits[1]).index]
    q_phys_a , q_phys_b = mapping_copy[q_log_curr[0]], mapping_copy[q_log_curr[1]]
    cost_f = d_matrix[q_phys_a][q_phys_b]

    w = 0.5
    window = 4
    cost_l = 0.0
    l = 0

    for gate in qc.data[idx_gate + 1:]:
        if gate.operation.name == 'cx':
            q_log_fut = [qc.find_bit(gate.qubits[0]).index,qc.find_bit(gate.qubits[1]).index]
            q_phys_a_fut, q_phys_b_fut = mapping_copy[q_log_fut[0]], mapping_copy[q_log_fut[1]]

            cost_l += d_matrix[q_phys_a_fut][q_phys_b_fut]
            l+=1

            if l == window:
                break

    if l > 0:
        cost_l = cost_l/l

    return cost_f + w*cost_l

def HA_routing(mapping_opt: list, qc: QuantumCircuit, d_matrix) -> QuantumCircuit:
  
    qc_routed = QuantumCircuit(backend.configuration().n_qubits, qc.num_qubits)
    idx_gate = 0
    for gate in qc.data:
        gate_name = gate.operation.name
        if gate_name=='cx':
            q_log = [qc.find_bit(gate.qubits[0]).index, qc.find_bit(gate.qubits[1]).index]
            qphy_A = mapping_opt[q_log[0]]
            qphy_B = mapping_opt[q_log[1]]

            last_swap = None

            while [qphy_A,qphy_B] not in coupling_map:
                neighbor_A = find_neighbor(qphy_A)
                neighbor_B = find_neighbor(qphy_B)
                best_cost = math.inf
                best_swap = None

                for i in neighbor_A:
                    if last_swap == {i,qphy_A}:
                        continue
                    cost = cost_swap(i,qphy_A,qc,d_matrix,idx_gate,mapping_opt)
                    if cost < best_cost:
                        best_cost = cost
                        best_swap = [i,qphy_A]
                for i in neighbor_B:
                    if last_swap == {i, qphy_B}:
                        continue
                    cost = cost_swap(i,qphy_B,qc,d_matrix,idx_gate,mapping_opt)
                    if cost < best_cost:
                        best_cost = cost
                        best_swap = [i,qphy_B]
                #Performing the swap
                qc_routed.cx(best_swap[0],best_swap[1])
                qc_routed.cx(best_swap[1],best_swap[0])
                qc_routed.cx(best_swap[0],best_swap[1])

                log_0 = mapping_opt.index(best_swap[0])
                log_1 = mapping_opt.index(best_swap[1])
                mapping_opt[log_0], mapping_opt[log_1] = mapping_opt[log_1], mapping_opt[log_0]
                qphy_A = mapping_opt[q_log[0]]
                qphy_B = mapping_opt[q_log[1]]

            qc_routed.cx(qphy_A, qphy_B)
        elif gate_name not in ['measure','barrier']:
            q_log = [qc.find_bit(gate.qubits[0]).index]
            qc_routed.append(gate.operation,[mapping_opt[q_log[0]]]) 

        idx_gate+=1
    
    return qc_routed

# normal functions
def translate_to_native(qc_routed: QuantumCircuit) -> QuantumCircuit:
    """translate all the gates in the native ones"""
    qc_compiled = QuantumCircuit(qc_routed.num_qubits, qc_routed.num_clbits)
    
    for gate in qc_routed.data:
        gate_name = gate.operation.name
        params = gate.operation.params
        
        idx_phys = [qc_routed.find_bit(q).index for q in gate.qubits]
        
        if len(idx_phys) == 1:
            qa = idx_phys[0]
            if check_gate(gate_name):
                qc_compiled.append(gate.operation, [qa])
            elif gate_name == 'h':
                from_h(qc_compiled, qa)
            elif gate_name == 't':
                qc_compiled.rz(np.pi/4, qa)
            elif gate_name == 'tdg':
                qc_compiled.rz(-np.pi/4, qa)
            elif gate_name == 's':
                qc_compiled.rz(np.pi/2, qa)
            elif gate_name == 'u3':
                from_u3(qc_compiled, params, qa)
        
        elif len(idx_phys) == 2:
            qc_compiled.append(gate.operation, idx_phys)
            
    return qc_compiled


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

def explode_ccx(qc: QuantumCircuit) -> QuantumCircuit:
    qc_exp = QuantumCircuit(qc.num_qubits, qc.num_clbits)
    
    for gate in qc.data:
        if gate.operation.name == 'ccx':
            qa = qc.find_bit(gate.qubits[0]).index
            qb = qc.find_bit(gate.qubits[1]).index
            qt = qc.find_bit(gate.qubits[2]).index
            
            qc_exp.h(qt)
            qc_exp.cx(qb, qt)
            qc_exp.tdg(qt)
            qc_exp.cx(qa, qt)
            qc_exp.t(qt)
            qc_exp.cx(qb, qt)
            qc_exp.tdg(qt)
            qc_exp.cx(qa, qt)
            qc_exp.t(qt)
            qc_exp.t(qb)
            qc_exp.h(qt)
            qc_exp.cx(qa, qb)
            qc_exp.t(qa)
            qc_exp.tdg(qb)
            qc_exp.cx(qa, qb)
        else:
            qc_exp.append(gate)
            
    return qc_exp
    
def my_compiler_opt(qc: QuantumCircuit) -> QuantumCircuit:
    num_qubits_log = qc.num_qubits
    num_qubits_phys = backend.configuration().n_qubits
    initial_mapping = list(range(num_qubits_phys)) #trivial mapping, the index is the logical index and the entry is the physical index

    #first we clean eventual duplicate gates and explode ccx
    qc = explode_ccx(qc)
    qc = same_gate(qc=qc)
    #find the s,e,t and d matrix
    s = s_matrix(coupling_map,num_qubits_phys)
    e,t = e_t_matrices(num_qubits_phys)
    a1,a2,a3 = 0.7,0.3,0
    d = d_matrix(s,e,t,a1,a2,a3)
    #find the optimal mapping
    mapping = opt_mapping(initial_mapping,d,qc,100,0.001,0.99)
    print(f'Optimized mapping: {mapping}\nParameters for D matrix: a1 = {a1}, a2 = {a2}, a3 = {a3}')

    #here the routing part,
    qc_routed = HA_routing(mapping,qc,d)
    qc_compiled = translate_to_native(qc_routed)

    #again we check the same gates
    qc_compiled = same_gate(qc_compiled)

    #measuring respecting the trivial mapping for the fidelity
    for idx in range(num_qubits_log):
        qc_compiled.measure(mapping[idx],idx)

    return qc_compiled