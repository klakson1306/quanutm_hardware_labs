from qiskit import QuantumCircuit
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
import numpy as np
from collections import deque

backend = FakeGuadalupeV2()
coupling_map = backend.configuration().coupling_map
native_gates = backend.configuration().basis_gates

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


    
def my_compiler_basic(qc: QuantumCircuit) -> QuantumCircuit:
    num_qubits_log = qc.num_qubits
    num_qubits_phys = backend.configuration().n_qubits
    mapping = [i if i < num_qubits_log else None for i in range(num_qubits_phys)] #trivial mapping, the index is the logical index and the entry is the physical index

    qc_compiled = QuantumCircuit(num_qubits_log, num_qubits_log)

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


    for idx in range(num_qubits_log):
        qc_compiled.measure(mapping[idx],idx)

    return qc_compiled