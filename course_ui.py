"""Course examples and explicit, circuit-specific method walkthroughs."""
from math import isclose
from course_examples import get_course_examples
from course_methods import supernodes, superposition, feedback_paths, divider, transformation_candidates, transform_source, summing_amplifiers, operating_point
from circuit_model import component_nodes, branch_nodes
from topology import compile_drawing, output_ports
from teaching import circuit_signature
from diagram_import import netlist_to_drawing, preview_svg

METHODS=['Supernodes','Superposition','Source transformation','Voltage divider','Feedback loops','Summing amplifiers']


def verify_course_examples():
    rows=[]
    for e in get_course_examples():
        try:
            parts,_=compile_drawing(e['drawing']);v,i=operating_point(parts)
            checks=[isclose(v[n],expected,rel_tol=1e-8,abs_tol=1e-10) for n,expected in e['expected_v'].items()]
            checks += [isclose(i[n],expected,rel_tol=1e-8,abs_tol=1e-10) for n,expected in e['expected_i'].items()]
            checks += [abs(sum((int(branch_nodes(p)[0]==n)-int(branch_nodes(p)[1]==n))*i[p['name']] for p in parts))<1e-9 for n in v]
            rows.append(dict(Circuit=e['title'],Result='PASS' if all(checks) else 'FAIL',Checks=f'{sum(checks)}/{len(checks)}'))
        except (ValueError,KeyError,TypeError) as error:
            rows.append(dict(Circuit=e['title'],Result='FAIL',Details=str(error)))
    return rows


def render_course_examples(st, load_drawing):
    with st.expander('Circuits I method examples'):
        cases=get_course_examples()
        title=st.selectbox('Course example',[e['title'] for e in cases])
        chosen=next(e for e in cases if e['title']==title)
        st.caption('Save your drawing before loading an example. Methods work on your own supported circuits too.')
        if st.button('Load course example'):load_drawing(chosen['drawing'])
        if st.checkbox('Show course hand calculation'):
            for line in chosen['hand']:st.write(line)
            for equation in chosen['equations']:st.latex(equation)
        if st.button('Check course examples'):
            st.dataframe(verify_course_examples(),hide_index=True)


def render_methods(st, drawing, load_drawing):
    overlay=None
    with st.expander('Circuits I methods · explain this circuit'):
        try:parts,labels=compile_drawing(drawing)
        except (ValueError,KeyError,TypeError):
            st.info('Finish the connections and values before using a circuit method.');return None
        if not parts:
            st.info('Build a circuit or load a course example first.');return None
        method=st.selectbox('Circuit method',METHODS,key='course_method')
        nodes=sorted({n for p in parts for n in component_nodes(p)})
        names=[p['name'] for p in parts];resistors=[p['name'] for p in parts if p['type']=='R']
        request=[];extra=None
        if method=='Superposition':
            quantity=st.selectbox('Superposition quantity',['Voltage','Branch current'])
            if quantity=='Voltage':
                first=st.selectbox('Contribution first node',nodes,index=nodes.index('Va') if 'Va' in nodes else len(nodes)-1)
                second=st.selectbox('Contribution reference node',nodes,index=nodes.index('0') if '0' in nodes else 0)
                request=[first,second,None]
            else:request=[nodes[0],nodes[0],st.selectbox('Contribution component',names)]
            st.caption('Add signed voltages or currents, never powers. Inactive V sources become shorts; inactive I sources become opens. Feedback amplifiers remain active. Comparator circuits are nonlinear and are rejected.')
        elif method=='Voltage divider':
            if len(resistors)<2:st.info('Place at least two resistors.');return None
            request=[st.selectbox('Upper resistor',resistors),st.selectbox('Lower resistor',resistors,index=1),st.selectbox('Parallel load',['None']+resistors)]
        elif method=='Source transformation':
            # A probe on a series internal node makes that node externally
            # observable; such a source/resistor pair is not eligible.
            protected={n for pair in output_ports(drawing,labels).values() for n in pair}
            candidates=transformation_candidates(parts,protected)
            if not candidates:
                st.info('No eligible independent source/resistor pair. Use a voltage source in series with a resistor and no branch or probe at their private junction, or a current source in parallel with a resistor.');return None
            choice=st.selectbox('Source and resistor',[c['id']+' · '+c['kind'] for c in candidates])
            extra=next(c for c in candidates if c['id']+' · '+c['kind']==choice);request=[choice]
            st.caption('Equivalent only at the two outer terminals. Internal source/resistor currents, voltages and powers need not match. Loading the preview redraws the circuit; save the original first.')
        signature=circuit_signature(parts)
        if st.button('Explain selected method'):
            st.session_state.pop('method_result',None)
            try:
                if method=='Supernodes':result=supernodes(parts)
                elif method=='Superposition':result=superposition(parts,request[0],request[1],branch=request[2])
                elif method=='Feedback loops':
                    result=feedback_paths(parts);operating_point(parts)
                elif method=='Summing amplifiers':result=summing_amplifiers(parts)
                elif method=='Voltage divider':result=divider(parts,request[0],request[1],None if request[2]=='None' else request[2])
                else:
                    result=transform_source(parts,extra);result['candidate']=extra
                    # Include voltage probes, which are not solver branches.
                    probes=[dict(name=p['id'],type='PORT',node1=labels[p['id']+':1'],node2=labels[p['id']+':2']) for p in drawing['items'] if p['type']=='PORT']
                    result['drawing']=netlist_to_drawing(result['components']+probes)
                st.session_state.method_result=dict(signature=signature,method=method,request=request,result=result)
            except (ValueError,KeyError,TypeError) as error:st.error('Cannot use this method: '+str(error))
        stored=st.session_state.get('method_result')
        if not stored or (stored['signature'],stored['method'],stored['request'])!=(signature,method,request):return None
        result=stored['result']
        if method=='Supernodes':
            if not result:st.info('No floating voltage-source supernode. A source chain tied to ground fixes node voltages directly; ideal op-amp input equality does not merge input nodes.')
            for group in result:
                st.markdown('**Supernode: '+', '.join(group['nodes'])+'**')
                st.write('Enclose '+', '.join(group['sources'])+'. Source currents inside the boundary cancel when the node KCL equations are added.')
                st.latex(group['kcl'])
                for equation in group['constraints']:st.latex(equation)
                st.caption('Keep one independent source-voltage constraint per source. Internal resistors also cancel from the boundary KCL. Solve boundary equations and constraints together.')
            overlay=dict(nodes=sorted({n for g in result for n in g['nodes']}),parts=[p for g in result for p in g['sources']],label='Supernode boundaries') if result else None
        elif method=='Superposition':
            st.dataframe([{'Active source':r['source'],'Contribution ('+result['unit']+')':r['value'],'Other sources':'; '.join(r['disabled']) or 'none'} for r in result['rows']],hide_index=True)
            st.write(f"Contribution sum: {result['total']:.8g} {result['unit']} · Full circuit: {result['full']:.8g} {result['unit']} · Residual: {result['residual']:.3g} {result['unit']}")
            (st.success if result['agrees'] else st.warning)('Superposition contributions agree with the full linear solution.' if result['agrees'] else 'The contributions did not agree; inspect this circuit.')
            st.caption('Only the complete operating point is checked against configured op-amp limits. Individual contributions are unclipped linear terms and may not be realizable as separate physical rail-limited circuits.')
            source=st.selectbox('Preview one source contribution',[r['source'] for r in result['rows']])
            row=next(r for r in result['rows'] if r['source']==source)
            st.image(preview_svg(netlist_to_drawing(row['components'])),caption='Contribution preview: 0 V is a short; 0 A is an open. The main drawing stays unchanged.',width='stretch')
        elif method=='Voltage divider':
            st.latex(result['equation']);st.write(f"Effective lower resistance: {result['bottom']:.8g} Ω. V({result['mid']}) = {result['predicted']:.8g} V; full solver: {result['actual']:.8g} V.")
            st.caption('Endpoint voltages are fixed by grounded independent sources.' if result['known_endpoints'] else 'Endpoint voltages came from the full circuit solution. This is a local KCL identity, not a shortcut that determines unknown endpoint voltages.')
            overlay=dict(nodes=[result['mid']],parts=request[:2],label='Divider midpoint')
        elif method=='Feedback loops':
            if not result:st.info('No supported negative-feedback amplifier. Open-loop comparators do not impose input equality.')
            for path in result:
                st.write(f"{path['name']}: OUT ({path['output']}) → "+(' → '.join(path['path'])+' → ' if path['path'] else 'direct wire → ')+f"− ({path['minus']}).")
                st.caption('Zero input currents and V+ = V− apply to the checked linear DC operating point. This passive path check is not a frequency-domain stability or oscillation analysis. Positive/mixed feedback, hysteresis and closed-loop saturation remain unsupported.')
            overlay=dict(nodes=sorted({p[k] for p in result for k in ('minus','output')}),parts=[name for p in result for name in [p['name']]+p['path']],label='Supported feedback paths') if result else None
        elif method=='Summing amplifiers':
            if not result:st.info('No supported textbook summing network was recognized. Use the course examples, or solve the full circuit normally.')
            for amplifier in result:
                st.markdown('**'+amplifier['name']+' · '+amplifier['kind']+'**')
                st.latex(r'V_{out}=V_{ref}+R_f\sum_i\frac{V_{ref}-V_i}{R_i}' if amplifier['kind'].startswith('Inverting') else r'V_+=\frac{\sum_i V_i/R_i}{\sum_i 1/R_i},\quad V_{out}=(1+R_f/R_g)V_+')
                st.dataframe(amplifier['terms'],hide_index=True)
                st.write(f"Predicted Vout: {amplifier['predicted']:.8g} V · Full solver: {amplifier['actual']:.8g} V.")
                st.caption('Input-node voltages in this table come from the full solved circuit. The formula assumes the displayed resistor network and zero ideal amplifier input currents.')
            overlay=dict(nodes=[p['output'] for p in result],parts=[p['name'] for p in result],label='Summing amplifier output') if result else None
        else:
            c=result['candidate'];st.write(f"{c['kind']}: equivalent source = {c['value']:.8g} {'A from '+c['b']+' to '+c['a'] if c['kind']=='V to I' else 'V positive at '+c['a']}. Resistance is unchanged.")
            st.success(f"External-node DC voltages match. V({c['a']}) − V({c['b']}) = {result['port_voltage']:.8g} V.")
            st.image(preview_svg(result['drawing']),caption='Transformed circuit preview',width='stretch')
            if st.button('Load transformed circuit'):
                load_drawing(result['drawing']);st.rerun()
    return overlay
