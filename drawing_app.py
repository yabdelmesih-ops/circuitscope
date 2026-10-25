"""Launch: py -m streamlit run drawing_app.py. Keep your engine.py beside it."""
from hashlib import sha256
import json
from pathlib import Path
import streamlit as st
from topology import compile_drawing, validate_for_solving, output_ports
from circuit_model import component_nodes, branch_nodes, branch_current, without_load
from teaching import build_lesson, circuit_signature, current_label, number, math_number
from examples import get_examples
from verification import verify_examples

st.set_page_config(page_title='CircuitScope Canvas', layout='wide')
st.title('CircuitScope — draw, solve, understand')
st.caption('DC circuits with resistors, independent sources and ideal feedback op amps. Add an Output probe to measure voltage without drawing load current. Values use Ω, V and A; ground is node 0.')
try:
    from engine import solve_circuit, get_voltages, thevenin
except (ImportError, ModuleNotFoundError) as error:
    st.error('Put your working engine.py beside drawing_app.py. It must define solve_circuit, get_voltages and thevenin, with no input() prompts.')
    st.code(str(error))
    st.stop()
if not hasattr(st.components, 'v2'):
    st.error('Update Streamlit: py -m pip install --upgrade streamlit')
    st.stop()
BASE = Path(__file__).parent
SAMPLE = json.loads((BASE / 'sample_drawing.json').read_text(encoding='utf-8'))
EMPTY_DRAWING = {'schema': 'circuitscope.canvas.v1', 'items': [], 'wires': []}
st.session_state.setdefault('canvas_seed', EMPTY_DRAWING)
st.session_state.setdefault('canvas_revision', 0)

def load_drawing(model):
    compile_drawing(model)
    st.session_state.canvas_seed = model
    st.session_state.canvas_revision += 1
    st.session_state.pop('analysis_result', None)
    st.session_state.question_kind = 'Node voltage'
    st.session_state.pop('question_node', None)
    st.session_state.pop('question_reference', None)
    st.session_state.pop('output_probe', None)
    st.session_state.pop('removed_load', None)
    st.session_state.teach_enabled = True

left, right = st.columns([1, 3])
with left:
    if st.button('Clear screen / New circuit'):
        load_drawing(EMPTY_DRAWING)
    if st.button('Load worked example'):
        load_drawing(SAMPLE)
with right:
    with st.expander('Open a saved drawing'):
        upload = st.file_uploader('CircuitScope drawing JSON', type='json')
        if upload:
            digest = sha256(upload.getvalue()).hexdigest()
            if digest != st.session_state.get('last_canvas_upload'):
                try:
                    document = json.loads(upload.getvalue())
                    if document.get('schema') != 'circuitscope.canvas.v1':
                        raise ValueError('Choose a project exported by this canvas.')
                    load_drawing(document)
                    st.session_state.last_canvas_upload = digest
                except (ValueError, TypeError, KeyError, AttributeError) as error:
                    st.error(f'Could not load drawing: {error}')

with st.expander('Example circuits and solver checks'):
    examples = get_examples()
    example_title = st.selectbox('Reference circuit', [e['title'] for e in examples])
    example = next(e for e in examples if e['title'] == example_title)
    st.caption(example['description'])
    if st.button('Load selected example'):
        load_drawing(example['drawing'])
    if st.checkbox('Show this example’s hand-calculated reference'):
        st.write(f'Reference for: {example_title}')
        for paragraph in example['hand']:
            st.write(paragraph)
        for equation in example['equations']:
            st.latex(equation)
        port = example['port']
        st.caption(f'Equivalent-circuit reference: port {port["node1"]} → {port["node2"]}; removed load: {port["load"] or "none"}.')
    if st.button('Run solver checks'):
        st.session_state.solver_check_results = verify_examples(solve_circuit, thevenin)
        st.session_state.solver_check_engine = sha256((BASE / 'engine.py').read_bytes()).hexdigest()
    rows = st.session_state.get('solver_check_results')
    if st.session_state.get('solver_check_engine') != sha256((BASE / 'engine.py').read_bytes()).hexdigest():
        rows = None
    if rows:
        if all(row['Result'] == 'PASS' for row in rows):
            st.success(f'All {len(rows)} reference circuits match their hand calculations and conservation checks.')
        else:
            st.warning('Some reference checks failed. See the details below.')
        st.dataframe(rows, hide_index=True)
        st.caption('These checks use your engine.py and fixed hand-calculated expectations. They do not modify your drawing. External SPICE comparison and real-browser checks remain separate.')

with st.expander('Op-amp material · ideal rules and worked gains'):
    st.write('Place an Op amp from the inventory. Pin + is the non-inverting input, pin − is the inverting input, and OUT is the output. Connect output back to − directly or through resistors. Both ideal input currents are zero.')
    st.latex(r'I_+=I_-=0,\qquad V_+=V_-\quad\text{(negative feedback, linear operation)}')
    st.write('The equal input voltages are a feedback constraint, not a physical short. The amplifier adjusts its output using energy from its supplies. Supply pins are implicit here; select the amplifier to set its output limits (default −15 to +15 V).')
    st.write('Inverting amplifier: ground +, feed Vin through Rin to −, and put Rf from OUT to −. KCL at the − input gives the gain:')
    st.latex(r'\frac{0-V_{in}}{R_{in}}+\frac{0-V_{out}}{R_f}=0\quad\Rightarrow\quad V_{out}=-\frac{R_f}{R_{in}}V_{in}')
    st.write('Non-inverting amplifier: feed Vin to +, put Rg from − to ground and Rf from OUT to −. The feedback divider gives:')
    st.latex(r'V_{out}=\left(1+\frac{R_f}{R_g}\right)V_{in}')
    st.write('Voltage follower: wire OUT directly to − and drive +. Then Vout = Vin. An unloaded follower has zero output current while its output voltage can be nonzero.')
    st.write('Open output means no external load is attached. Feedback resistors may still carry current. An Output probe has infinite resistance and never joins its two terminals. A completely floating node has no uniquely defined voltage.')
    st.caption('Scope: ideal linear DC with direct or passive resistive negative feedback. No comparator, saturation waveform, frequency response, offset, bias current or current-limit simulation. Mixed positive/negative and active feedback networks are rejected. Output-limit checks do not model real supply headroom.')
    st.markdown('[Learning reference: MIT OpenCourseWare — Op Amps I](https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/22_op_amps1/)')

key = f'circuit_canvas_{st.session_state.canvas_revision}'
previous = st.session_state.get(key, {})
seed = previous.get('drawing', st.session_state.canvas_seed)
compile_error = None
try:
    components, labels = compile_drawing(seed)
except (ValueError, KeyError, TypeError) as error:
    components, labels, compile_error = [], {}, str(error)

# Ask the question before drawing, so numbers and visual notes update together.
active, step = None, 1
clicked_node = None
pick = previous.get('node_request')
if isinstance(pick, dict) and isinstance(pick.get('sequence'), int):
    token = (key, pick['sequence'], pick.get('revision'), pick.get('pin'))
    if token != st.session_state.get('last_node_request'):
        st.session_state.last_node_request = token
        st.session_state.pop('analysis_result', None)
        connected_nodes = {n for p in components for n in component_nodes(p)}
        if pick.get('revision') != seed.get('revision', 0):
            st.info('The drawing changed during that click. Click the node again to explain its current circuit.')
        elif labels.get(pick.get('pin')) not in connected_nodes:
            st.info('Connect that terminal or junction to a circuit component before explaining it.')
        else:
            clicked_node = labels[pick['pin']]
            st.session_state.question_kind = 'Node voltage'
            st.session_state.question_node = clicked_node
            st.session_state.question_reference = '0' if '0' in connected_nodes else next(iter(connected_nodes))
            st.session_state.teach_enabled = True
if components:
    quantity = st.selectbox('Find', ['Node voltage', 'Open-circuit voltage', 'Branch current', 'Component power', 'Thevenin', 'Norton'], key='question_kind')
    nodes = sorted({n for p in components for n in component_nodes(p)})
    for widget_key in ('question_node', 'question_reference'):
        if st.session_state.get(widget_key) not in nodes:
            st.session_state.pop(widget_key, None)
    node1 = node2 = branch_name = load = None
    explain, probe_name = False, None
    if quantity in ('Branch current', 'Component power'):
        branch_name = st.selectbox('Component', [p['name'] for p in components])
    else:
        ports = output_ports(seed, labels) if quantity == 'Open-circuit voltage' else {}
        if ports:
            choices = list(ports) + ['Choose nodes manually']
            if st.session_state.get('output_probe') not in choices:
                st.session_state.pop('output_probe', None)
            selected_probe = st.selectbox('Output probe', choices, key='output_probe')
            if selected_probe in ports:
                probe_name = selected_probe
                node1, node2 = ports[probe_name]
                st.caption(f'{probe_name}: + at {node1}, − at {node2}. Infinite resistance; probe current = 0 A.')
        if probe_name is None:
            first, second = st.columns(2)
            default_node = 'Vout' if 'Vout' in nodes else 'Va' if 'Va' in nodes else next((n for n in nodes if n != '0'), nodes[0])
            node1 = first.selectbox('First node', nodes, index=0 if 'question_node' in st.session_state else nodes.index(default_node), key='question_node')
            node2 = second.selectbox('Second / reference node', nodes, index=0 if 'question_reference' in st.session_state else nodes.index('0') if '0' in nodes else 0, key='question_reference')
        if quantity in ('Node voltage', 'Open-circuit voltage'):
            explain = bool(st.checkbox('Teach me how this node works', value=False if 'teach_enabled' in st.session_state else True, key='teach_enabled'))
        if quantity in ('Thevenin', 'Norton', 'Open-circuit voltage'):
            loads = ['None'] + [p['name'] for p in components if p['type'] == 'R']
            if st.session_state.get('removed_load') not in loads:
                st.session_state.pop('removed_load', None)
            load = st.selectbox('Load to remove', loads, index=0 if 'removed_load' in st.session_state or quantity == 'Open-circuit voltage' else loads.index('R2') if 'R2' in loads else 0, key='removed_load')
            st.caption('Remove only the external load. Keep the feedback and voltage-divider resistors that belong to the circuit. None measures the existing circuit with no added load.')
    request = [quantity, node1, node2, branch_name, load, explain, probe_name]
    signature = circuit_signature(components)
    solve_pressed = st.button('Solve drawing', type='primary')
    if solve_pressed or clicked_node is not None:
        st.session_state.pop('analysis_result', None)
        try:
            validate_for_solving(components)
            metrics, captions, lesson, measurement = [], [], None, None
            if quantity in ('Node voltage', 'Open-circuit voltage'):
                load_name = None if load in (None, 'None') else load
                working = without_load(components, load_name)
                validate_for_solving(working)
                remaining_nodes = {n for p in working for n in component_nodes(p)}
                if node1 not in remaining_nodes or node2 not in remaining_nodes:
                    raise ValueError('Connect both output terminals to circuit nodes that remain after removing the load. A floating terminal has no defined voltage.')
                if explain:
                    _, index, sources, solution = solve_circuit(working)
                    lesson = build_lesson(working, node1, node2, index, sources, solution)
                    answer = lesson['answer']
                else:
                    voltages = get_voltages(working)
                    answer = voltages[node1] - voltages[node2]
                metrics.append((('Open-circuit output · ' if quantity == 'Open-circuit voltage' else '') + f'V({node1}) − V({node2})', f'{answer:.6g} V'))
                if quantity == 'Open-circuit voltage':
                    measurement = dict(node1=node1, node2=node2, voltage=answer, removedLoad=load_name, portId=probe_name)
                    captions.append(f'Probe current = 0 A. Removed external load: {load_name or "none"}. Internal/feedback currents can still flow. Voltage does not require current through the probe.')
            elif quantity in ('Thevenin', 'Norton'):
                if node1 == node2:
                    raise ValueError('Choose two different port nodes.')
                load_name = None if load == 'None' else load
                remaining = [p for p in components if p['name'] != load_name]
                validate_for_solving(remaining)
                remaining_nodes = {n for p in remaining for n in component_nodes(p)}
                if node1 not in remaining_nodes or node2 not in remaining_nodes:
                    raise ValueError('Choose port nodes that remain after removing the load.')
                voltage, resistance = thevenin(components, node1, node2, load_name)
                if quantity == 'Thevenin':
                    metrics.append(('Thevenin voltage', f'{voltage:.6g} V'))
                else:
                    if abs(resistance) < 1e-12:
                        raise ValueError('This ideal voltage port has zero resistance and no finite Norton current.')
                    metrics.append(('Norton current', f'{voltage / resistance:.6g} A'))
                metrics.append(('Equivalent resistance', f'{resistance:.6g} Ω'))
                captions.append(f'Port {node1} → {node2}. Removed load: {load_name or "none"}. All other components remain.')
            else:
                _, index, sources, solution = solve_circuit(components)
                voltages = {'0': 0.0, **{n: float(solution[i]) for n, i in index.items()}}
                part = next(p for p in components if p['name'] == branch_name)
                a, b = branch_nodes(part)
                voltage = voltages[a] - voltages[b]
                current = branch_current(part, voltages, index, sources, solution)
                metrics.append(('Current', f'{current:.6g} A') if quantity == 'Branch current' else ('Power', f'{voltage * current:.6g} W'))
                captions.append(f'Positive current: {a} → {b}. Positive power is absorbed.')
                if part['type'] == 'OPAMP':
                    captions.append('This is output current INTO the amplifier, not input current. Both input currents are zero. Output power uses the implicit supply/ground return; supply-pin currents are not simulated.')
            st.session_state.analysis_result = {'signature': signature, 'request': request, 'metrics': metrics, 'captions': captions, 'lesson': lesson, 'measurement': measurement}
        except Exception as error:
            st.error(f'Cannot solve this drawing: {error}')
            st.caption('Check loose pins, ground, node labels, and conflicting ideal voltage sources.')
    stored = st.session_state.get('analysis_result')
    if stored and stored['signature'] == signature and stored['request'] == request:
        active = stored
    if active and active['lesson']:
        steps = ['1 · Node', '2 · Current', '3 · KCL', '4 · Check']
        chosen = st.radio('Visual lesson', steps, index=1, horizontal=True)
        step = steps.index(chosen) if chosen in steps else 1
        st.caption('Purple highlights one electrical node. Numbered arrows show conventional current. Switch steps to see the reasoning.')

editor = st.components.v2.component(
    name='circuitscope_drawing',
    html=(BASE / 'canvas' / 'editor.html').read_text(encoding='utf-8'),
    css=(BASE / 'canvas' / 'editor.css').read_text(encoding='utf-8').replace('}', '}\n'),
    js=(BASE / 'canvas' / 'editor.js').read_text(encoding='utf-8'),
)
lesson = active['lesson'] if active else None
result = editor(
    data={'drawing': seed, 'node_map': labels, 'lesson': {**lesson, 'step': step} if lesson else None, 'measurement': active.get('measurement') if active else None},
    default={'drawing': seed, 'node_request': None}, key=key,
    on_drawing_change=lambda: None, on_node_request_change=lambda: None,
    height=820, width='stretch',
)
drawing = result.drawing
st.download_button('Save drawing JSON', json.dumps(drawing, indent=2), file_name='circuitscope-drawing.json', mime='application/json')
if compile_error:
    st.warning(compile_error)
    st.stop()
if not components:
    st.info('Place a source and a resistor, then connect their terminals to ground.')
    st.stop()

if active:
    for label, value in active['metrics']:
        st.metric(label, value)
    for caption in active['captions']:
        st.caption(caption)
    if lesson:
        st.subheader(f'Why node {lesson["node"]} has this voltage')
        if step == 0:
            st.write(f'Node {lesson["node"]} is {number(lesson["node_voltage"])} V relative to ground. Every highlighted wire belongs to that same node.')
            st.write(f'Your requested difference is {number(lesson["node_voltage"])} − ({number(lesson["reference_voltage"])}) = {number(lesson["answer"])} V.')
            st.caption('Voltage is a difference in electric potential; current is the rate at which charge flows.')
        elif step == 1:
            st.dataframe([{'Branch': b['name'], 'Current': b['label'], 'At this node': 'leaves' if b['outward'] > 0 else 'enters' if b['outward'] < 0 else 'no net transfer', 'Signed current (A)': b['current']} for b in lesson['incident']], hide_index=True)
            st.write('R/V/I positive current is pin 1 → pin 2. Op-amp positive current enters OUT; both input currents are zero. Arrows show the actual conventional current direction.')
        elif step == 2:
            st.write('Choose currents leaving this node as positive, then apply Kirchhoff’s current law:')
            st.latex(lesson['kcl'])
            st.caption('Voltages are in volts, resistances in ohms, and each term is a current in amperes. Unknowns stay symbolic until the equations are solved.')
            for item in lesson['algebra']:
                st.write(item['text'])
                if item['latex']:
                    st.latex(item['latex'])
            if lesson['node'] == '0':
                st.caption('Ground is defined as 0 V. Its KCL follows from the other node equations; it is not an extra independent equation.')
            with st.expander('See the full set of simultaneous equations'):
                for equation in lesson['equations']:
                    st.write(equation['label'])
                    st.latex(equation['latex'])
        else:
            st.write(f'Current entering: {current_label(lesson["incoming"])}. Current leaving: {current_label(lesson["outgoing"])}.')
            st.latex(r'\sum I_{\mathrm{out}}-\sum I_{\mathrm{in}}=' + math_number(lesson['residual']) + r'\ \mathrm{A}')
            if lesson['balanced']:
                st.success('The currents balance within numerical precision: charge is conserved at this node.')
            else:
                st.warning('The computed currents do not balance within the check tolerance.')
            st.caption('Changing one resistance can change several node voltages and branch currents. The whole connected circuit determines the split.')
        st.caption('Learning reference: [OpenStax, University Physics Volume 2, §10.3](https://openstax.org/books/university-physics-volume-2/pages/10-3-kirchhoffs-rules).')
else:
    st.caption('Choose Explain node in the inventory and click a wire or terminal for a visual lesson. You can also choose a question above and click Solve drawing. Circuit edits hide old answers until you solve again.')
with st.expander('See what the drawing sends to your solver'):
    st.dataframe(components, hide_index=True)
    st.caption('R/V/I use name/type/node1/node2/value. Op amps use node1 (+), node2 (−), node3 (OUT), v_min/v_max. Output probes add no solver branch. Positions do not enter the equations.')
