"""Upload → optional API transcription → local editable review → explicit load."""
from hashlib import sha256
import json
import os
import re
from screenshot_import import analyze_image, reviewed_drawing, prepare_image, DEFAULT_MODEL, FIELDS
from diagram_import import preview_svg


def review_demo():
    def row(name,kind,a,b,value):
        return {**dict.fromkeys(FIELDS), 'name':name,'type':kind,'node1':a,'node2':b,'value':value}
    return dict(components=[row('V1','V','Vs','0',12),row('R1','R','Vs','Va',1000),row('R2','R','Va','0',2000)],
                notes=['Offline review demo: this predefined netlist is not a recognition result.'],uncertainties=[],unsupported=[])


def render_screenshot_import(st, load_drawing):
    with st.expander('Import a circuit screenshot'):
        st.write('Upload a clear circuit image, review its proposed connections and values, then load an editable drawing. Save your current drawing first.')
        st.caption('Optional AI transcription sends the image to OpenAI only when you press Analyze image with OpenAI. API billing applies. The app does not save your API key in circuit files. Clean DC diagrams work best; recognition can misread values, polarity and crossings.')
        upload=st.file_uploader('Circuit screenshot',type=['png','jpg','jpeg','webp'],key='circuit_screenshot')
        digest=sha256(upload.getvalue()).hexdigest() if upload is not None else None
        if upload is not None:
            try:
                image=prepare_image(upload.getvalue())
                st.image(image,caption='Original image for comparison',width='stretch')
                key=st.text_input('OpenAI API key',type='password',key='screenshot_api_key',help='Or configure OPENAI_API_KEY on the server. Do not share your key.')
                model=st.text_input('Vision model',value=DEFAULT_MODEL,key='screenshot_model')
                if st.button('Analyze image with OpenAI'):
                    st.session_state.pop('image_candidate',None)
                    try:
                        with st.spinner('Reading the circuit image…'):
                            result=analyze_image(upload.getvalue(),key or os.environ.get('OPENAI_API_KEY',''),model=model)
                        st.session_state.image_candidate=dict(payload=result,image_hash=digest)
                    except ValueError as error:
                        st.error(str(error))
            except ValueError as error:
                st.error(str(error))
        if st.button('Try import review demo (no API)'):
            st.session_state.image_candidate=dict(payload=review_demo(),image_hash=digest)
        candidate=st.session_state.get('image_candidate')
        if not candidate or candidate['image_hash']!=digest:
            return
        payload=candidate['payload']
        def plain(text):
            return re.sub(r'([\\`*_{}\[\]()#+.!<>|])',r'\\\1',text)
        for note in payload['notes']:
            st.info(plain(note))
        if payload['unsupported']:
            st.error('Unsupported elements: '+plain('; '.join(payload['unsupported'])))
            st.caption('This image cannot be imported faithfully. Crop or redraw a supported DC circuit and analyze again.')
            return
        for note in payload['uncertainties']:
            st.warning('Check in the original image: '+plain(note))
        st.markdown('**Review the proposed netlist**')
        st.caption('R: Ω; V: volts, positive at node1; I: amperes from node1 to node2. OPAMP: node1 +, node2 −, node3 OUT. Use node 0 for ground. Null values and op-amp settings must be filled before loading.')
        # Explicit types keep an all-null numeric column editable as numbers;
        # otherwise unknown op-amp limits can be inferred as a text column.
        columns={
            'name':st.column_config.TextColumn('Component ID',required=True),
            'type':st.column_config.SelectboxColumn('Type',options=['R','V','I','OPAMP','PORT'],required=True),
            'node1':st.column_config.TextColumn('Node 1',required=True),
            'node2':st.column_config.TextColumn('Node 2',required=True),
            'node3':st.column_config.TextColumn('OUT node (op amp)'),
            'value':st.column_config.NumberColumn('Value (Ω / V / A)',format='%.8g'),
            'mode':st.column_config.SelectboxColumn('Op-amp mode',options=['feedback','open_loop']),
            'v_min':st.column_config.NumberColumn('Output minimum (V)'),
            'v_max':st.column_config.NumberColumn('Output maximum (V)')}
        edited=st.data_editor(payload['components'],num_rows='dynamic',hide_index=True,column_config=columns,key='image_review_'+sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16])
        try:
            drawing=reviewed_drawing(edited)
        except (ValueError,KeyError,TypeError) as error:
            st.warning('Resolve before loading: '+str(error))
            return
        st.image(preview_svg(drawing),caption='Proposed editable drawing — wiring is explicit; crossings alone do not connect',width='stretch')
        signature=sha256(json.dumps(edited,sort_keys=True,default=str).encode()).hexdigest()[:20]
        approved=st.checkbox('I checked the values, source directions, reference node and every connection against the image',key='image_approved_'+signature)
        if st.button('Load reviewed circuit',disabled=not approved):
            load_drawing(drawing)
            st.success('Reviewed circuit loaded. You can move components, edit values and solve it below.')
