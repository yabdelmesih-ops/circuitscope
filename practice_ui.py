"""Guided practice UI, separate from circuit solving and canvas interaction."""
from practice import get_exercises, drawing_signature, grade_answer, UNITS


def render_practice(st, load_drawing):
    with st.expander('Guided practice · predict, check, explain'):
        exercises = get_exercises()
        selected = st.selectbox('Practice question', [q['title'] for q in exercises], key='practice_choice')
        question = next(q for q in exercises if q['title'] == selected)
        st.caption('Start loads a reference circuit. Save your drawing first. Hints and checking stay separate from Solve drawing; you can still use the solver whenever you want.')
        if st.button('Start practice question'):
            load_drawing(question['drawing'])
            st.session_state.practice_active = dict(id=question['id'], hints=0, revealed=False, feedback=None)
            st.session_state.pop('practice_answer', None)
            st.session_state.pop('practice_unit', None)
            st.session_state.question_node = question['node']
            st.session_state.question_reference = '0'
            if question['id'] == 'branch_direction':
                st.session_state.question_kind = 'Branch current'
                st.session_state.question_branch = 'R3'
            elif question['id'].startswith('bridge_'):
                st.session_state.question_kind = 'Thevenin'
                st.session_state.question_reference = 'Vb'
                st.session_state.removed_load = 'R5'
            elif question['id'] == 'open_output':
                st.session_state.question_kind = 'Open-circuit voltage'
        active = st.session_state.get('practice_active')
        if not active:
            st.write('Choose a question and press Start practice question.')
            return
        # Changing the selector previews the next question; it never silently
        # changes the answer key for the drawing already loaded.
        q = next(q for q in exercises if q['id'] == active['id'])
        st.markdown(f"**Current question: {q['title']}**")
        st.write(q['prompt'])
        canvas_key = f"circuit_canvas_{st.session_state.canvas_revision}"
        drawing = st.session_state.get(canvas_key, {}).get('drawing', st.session_state.canvas_seed)
        try:
            matches = drawing_signature(drawing) == q['signature']
        except (ValueError, KeyError, TypeError):
            matches = False
        if not matches:
            st.warning('The circuit changed. This practice answer key no longer applies. Select this question and press Start practice question to reload it, or keep exploring with Solve drawing.')
            return
        progress = st.session_state.setdefault('practice_progress', {})
        record = progress.setdefault(q['id'], dict(attempts=0, correct=False, revealed=False))
        st.caption('Answers accept 0.5% relative rounding error. Enter a signed number and choose its unit. Progress lasts for this live session.')
        with st.form('practice_attempt'):
            text = st.text_input('Your predicted answer', key='practice_answer', placeholder='Enter a number')
            choices = list(UNITS[q['unit']])
            unit = st.selectbox('Answer unit', choices, index=choices.index(q.get('default_unit', q['unit'])), key='practice_unit')
            submitted = st.form_submit_button('Check my answer')
        if submitted:
            try:
                correct, message = grade_answer(q, text, unit)
                record['attempts'] += 1
                if correct:
                    record['correct'] = True
                    active['revealed'] = True
                active['feedback'] = (correct, message)
            except ValueError as error:
                active['feedback'] = (False, str(error))
        if active['feedback']:
            correct, message = active['feedback']
            (st.success if correct else st.info)(message)
        if st.button('Show next hint', disabled=active['hints'] >= len(q['hints'])):
            active['hints'] += 1
        for i, hint in enumerate(q['hints'][:active['hints']], 1):
            st.write(f'Hint {i}: {hint}')
        if st.button('Reveal worked answer'):
            active['revealed'] = True
            record['revealed'] = True
        if active['revealed']:
            st.markdown('**Worked answer**')
            st.write(q['solution'])
            st.caption('The solver controls are prepared for this question. Use Solve drawing to compare the result; voltage questions also offer current arrows and KCL. Changing those controls does not change this practice prompt.')
        solved = sum(bool(row['correct']) for row in progress.values())
        st.caption(f"Practice progress: {solved}/{len(exercises)} questions answered correctly · This question: {record['attempts']} checked attempts. Revealing an answer does not count as a correct attempt.")
