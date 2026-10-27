"""DC methods explained from the actual compiled circuit, not a drawing guess."""
from copy import deepcopy
from math import isclose
from circuit_model import component_nodes, branch_nodes, branch_current, opamp_mode, validate_opamps
from engine import solve_circuit
from teaching import symbol, math_number, current_symbol, join_terms, known_from_sources


def operating_point(parts, *, check_rails=True):
    _, index, sources, solution = solve_circuit(parts, check_rails=check_rails)
    voltages = {'0': 0., **{n: float(solution[i]) for n, i in index.items()}}
    currents = {p['name']: branch_current(p, voltages, index, sources, solution) for p in parts}
    return voltages, currents


def supernodes(parts):
    """Floating ideal voltage-source chains form supernodes; op-amp equality doesn't."""
    graph = {}
    for p in parts:
        if p['type'] == 'V':
            a, b = component_nodes(p)
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    result, seen = [], set()
    for start in graph:
        if start in seen:
            continue
        group, todo = set(), [start]
        while todo:
            n = todo.pop()
            if n not in group:
                group.add(n); todo.extend(graph[n]-group)
        seen.update(group)
        if '0' in group or len(group) < 2:
            continue
        sources = [p for p in parts if p['type'] == 'V' and p['node1'] in group and p['node2'] in group]
        terms, boundary = [], []
        for p in parts:
            a, b = branch_nodes(p)
            if (a in group) == (b in group):
                continue
            boundary.append(p['name'])
            sign, inside, outside = (1, a, b) if a in group else (-1, b, a)
            if p['type'] == 'R':
                terms.append((1, r'\frac{'+symbol(inside)+'-'+symbol(outside)+'}{'+math_number(p['value'])+'}'))
            elif p['type'] == 'I':
                value = sign*p['value']
                if value:
                    terms.append((1 if value > 0 else -1, math_number(abs(value))))
            else:
                terms.append((sign, current_symbol(p['name'])))
        result.append(dict(nodes=sorted(group), sources=[p['name'] for p in sources], boundary=boundary,
            kcl=join_terms(terms)+' = 0', constraints=[symbol(p['node1'])+'-'+symbol(p['node2'])+' = '+math_number(p['value']) for p in sources]))
    return result


def superposition(parts, node1, node2='0', *, branch=None):
    if any(p['type'] == 'OPAMP' and opamp_mode(p) == 'open_loop' for p in parts):
        raise ValueError('Superposition requires a linear circuit. Open-loop comparators cannot be superposed.')
    sources = [p for p in parts if p['type'] in ('V', 'I')]
    if not sources:
        raise ValueError('Add at least one independent voltage or current source.')
    def read(circuit, check_rails):
        voltages, currents = operating_point(circuit, check_rails=check_rails)
        if branch:
            if branch not in currents:
                raise ValueError('Select an existing component current.')
            return currents[branch]
        if node1 not in voltages or node2 not in voltages:
            raise ValueError('Choose two connected circuit nodes.')
        return voltages[node1]-voltages[node2]
    full = read(parts, True)
    rows = []
    for source in sources:
        circuit = deepcopy(parts)
        disabled = []
        for p in circuit:
            if p['type'] in ('V', 'I') and p['name'] != source['name']:
                p['value'] = 0
                disabled.append(p['name']+(' → short' if p['type']=='V' else ' → open'))
        # Contributions are linear mathematical terms, not separately clipped
        # physical operating points. The full result above is checked for rails.
        value = read(circuit, False)
        rows.append(dict(source=source['name'], value=value, disabled=disabled, components=circuit))
    total = sum(r['value'] for r in rows)
    return dict(rows=rows, full=full, total=total, residual=total-full,
                agrees=isclose(total, full, rel_tol=1e-8, abs_tol=1e-10), unit='A' if branch else 'V')


def feedback_paths(parts):
    validate_opamps(parts)
    fixed = set(known_from_sources(parts))
    graph = {}
    for p in parts:
        if p['type'] == 'R':
            a, b = component_nodes(p)
            if a not in fixed and b not in fixed:
                graph.setdefault(a, []).append((b,p['name']))
                graph.setdefault(b, []).append((a,p['name']))
    result=[]
    for amp in parts:
        if amp['type'] != 'OPAMP' or opamp_mode(amp) != 'feedback':
            continue
        todo=[(amp['node3'],[])]; seen=set(); path=None
        while todo:
            node, route=todo.pop(0)
            if node==amp['node2']:
                path=route;break
            if node not in seen:
                seen.add(node);todo.extend((n,route+[name]) for n,name in graph.get(node,[]) if n not in seen)
        if path is None:
            raise ValueError('No supported passive negative-feedback path was found.')
        result.append(dict(name=amp['name'], plus=amp['node1'], minus=amp['node2'], output=amp['node3'], path=path))
    return result


def divider(parts, upper_name, lower_name, load_name=None):
    by_name={p['name']:p for p in parts}
    upper, lower=by_name[upper_name],by_name[lower_name]
    if upper_name==lower_name or upper['type']!='R' or lower['type']!='R' or upper['node1']==upper['node2'] or lower['node1']==lower['node2']:
        raise ValueError('Select two different resistors.')
    common=set(component_nodes(upper)) & set(component_nodes(lower))
    if len(common)!=1:
        raise ValueError('The divider resistors must share exactly one middle node.')
    mid=next(iter(common));high=next(n for n in component_nodes(upper) if n!=mid);low=next(n for n in component_nodes(lower) if n!=mid)
    resistance=lower['value']; allowed={upper_name,lower_name}
    if load_name:
        load=by_name[load_name]
        if load_name in allowed or load['type']!='R' or set(component_nodes(load))!={mid,low}:
            raise ValueError('The selected load must be a separate resistor across the lower resistor.')
        resistance=1/(1/resistance+1/load['value']);allowed.add(load_name)
    for p in parts:
        # Ideal amplifier inputs and probes draw no current. Its output does.
        nodes=(p['node3'],) if p['type']=='OPAMP' else component_nodes(p)
        if p['name'] not in allowed and mid in nodes:
            raise ValueError('Another branch loads the middle node. Select its parallel load if supported, or use full nodal analysis.')
    voltages,_=operating_point(parts)
    predicted=voltages[low]+(voltages[high]-voltages[low])*resistance/(upper['value']+resistance)
    return dict(mid=mid,high=high,low=low,bottom=resistance,predicted=predicted,actual=voltages[mid],
                known_endpoints=high in known_from_sources(parts) and low in known_from_sources(parts),
                equation=symbol(mid)+'='+symbol(low)+'+('+symbol(high)+'-'+symbol(low)+r')\frac{'+math_number(resistance)+'}{'+math_number(upper['value'])+'+'+math_number(resistance)+'}')


def transformation_candidates(parts, protected_nodes=()):
    result=[]
    uses={n:sum(component_nodes(p).count(n) for p in parts) for p in parts for n in component_nodes(p)}
    for source in parts:
        if source['type'] not in ('V','I') or source['node1']==source['node2']:
            continue
        for r in parts:
            if r['type']!='R' or r['node1']==r['node2']:
                continue
            shared=set(component_nodes(source))&set(component_nodes(r))
            if source['type']=='V' and len(shared)==1:
                inside=next(iter(shared))
                if uses[inside]!=2 or inside=='0' or inside in protected_nodes:
                    continue
                a=next(n for n in component_nodes(r) if n!=inside)
                b=next(n for n in component_nodes(source) if n!=inside)
                voltage=source['value']*(1 if source['node1']==inside else -1)
                result.append(dict(id=source['name']+' / '+r['name'],kind='V to I',source=source['name'],resistor=r['name'],a=a,b=b,inside=inside,value=voltage/r['value']))
            elif source['type']=='I' and len(shared)==2:
                result.append(dict(id=source['name']+' / '+r['name'],kind='I to V',source=source['name'],resistor=r['name'],a=source['node2'],b=source['node1'],inside=None,value=source['value']*r['value']))
    return result


def transform_source(parts, candidate):
    # Re-derive to prevent stale/edited candidate dictionaries from changing a
    # different circuit. Protected-node restrictions are applied by the caller.
    matches=[c for c in transformation_candidates(parts) if c==candidate]
    if not matches:
        raise ValueError('This transformation no longer matches the circuit.')
    out=deepcopy(parts); by_name={p['name']:p for p in out}
    source=by_name[candidate['source']]; r=by_name[candidate['resistor']]
    a,b=candidate['a'],candidate['b']
    used={p['name'].lower() for p in out}|{n.lower() for p in out for n in component_nodes(p)}
    def unique(prefix):
        n=1
        while (prefix+str(n)).lower() in used:n+=1
        name=prefix+str(n);used.add(name.lower());return name
    if candidate['kind']=='V to I':
        source.update(name=unique('Ieq'),type='I',node1=b,node2=a,value=candidate['value'])
        r.update(node1=a,node2=b)
    else:
        inside=unique('ST')
        source.update(name=unique('Veq'),type='V',node1=a,node2=inside,value=candidate['value'])
        r.update(node1=inside,node2=b)
    before,_=operating_point(parts);after,_=operating_point(out)
    preserved=set(before)&set(after)
    if any(not isclose(before[n],after[n],rel_tol=1e-8,abs_tol=1e-9) for n in preserved):
        raise ValueError('The transformed circuit failed the external-node voltage check.')
    return dict(components=out,port_voltage=before[a]-before[b],preserved=sorted(preserved))


def summing_amplifiers(parts):
    """Recognize supported textbook summing networks, with solved input values."""
    voltages,_=operating_point(parts);result=[]
    for amp in parts:
        if amp['type']!='OPAMP' or opamp_mode(amp)!='feedback':continue
        plus,minus,out=component_nodes(amp)
        resistors=[p for p in parts if p['type']=='R' and p['node1']!=p['node2']]
        feedback=[p for p in resistors if set(component_nodes(p))=={minus,out}]
        if len(feedback)!=1:continue
        rf=feedback[0]
        inputs=[p for p in resistors if minus in component_nodes(p) and p is not rf]
        loads=[p for p in parts if p['type']!='R' and p['name']!=amp['name'] and minus in ((p['node3'],) if p['type']=='OPAMP' else component_nodes(p))]
        if len(inputs)>=2 and not loads:
            terms=[]
            for p in inputs:
                other=next(n for n in component_nodes(p) if n!=minus)
                terms.append(dict(name=p['name'],node=other,resistance=p['value'],voltage=voltages[other],contribution=rf['value']*(voltages[plus]-voltages[other])/p['value']))
            predicted=voltages[plus]+sum(t['contribution'] for t in terms)
            result.append(dict(name=amp['name'],kind='Inverting summing amplifier',terms=terms,predicted=predicted,actual=voltages[out],reference=voltages[plus],rf=rf['value'],output=out))
        plus_inputs=[p for p in resistors if plus in component_nodes(p)]
        plus_loads=[p for p in parts if p['type']!='R' and p['name']!=amp['name'] and plus in ((p['node3'],) if p['type']=='OPAMP' else component_nodes(p))]
        rg=[p for p in inputs if set(component_nodes(p))=={minus,'0'}]
        if len(plus_inputs)>=2 and not plus_loads and len(inputs)==1 and len(rg)==1:
            terms=[];g=sum(1/p['value'] for p in plus_inputs)
            gain=1+rf['value']/rg[0]['value']
            for p in plus_inputs:
                other=next(n for n in component_nodes(p) if n!=plus)
                terms.append(dict(name=p['name'],node=other,resistance=p['value'],voltage=voltages[other],contribution=gain*voltages[other]/p['value']/g))
            result.append(dict(name=amp['name'],kind='Non-inverting summing amplifier',terms=terms,predicted=sum(t['contribution'] for t in terms),actual=voltages[out],reference=0.,gain=gain,output=out))
    return result
