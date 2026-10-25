# Guided practice

Guided practice turns the reference circuits into predict-then-check exercises. A question loads a circuit, the learner enters a signed answer with a unit, and the app gives feedback and hints before revealing the worked solution.

## Questions

| Question | Skill practiced |
|---|---|
| Voltage divider | Series current and node voltage |
| Current-source node | KCL and Ohm's law |
| Floating voltage source | Supernode KCL with a source constraint |
| Signed branch current | Current reference direction |
| Open-port voltage | Removing the bridge load and subtracting node voltages |
| Port resistance | Deactivating the independent source and combining resistors |
| Feedback amplifier | Zero input current, input equality and KCL |
| Unloaded output | Voltage with zero load current |
| Open-loop comparator | Comparing inputs and selecting the configured output level |

## Using it

Open **Guided practice · predict, check, explain**, choose a question and click **Start practice question**. This replaces the current drawing, so save any circuit first.

- Enter the number and unit separately, for example `-2.4` with **mA** or `-0.0024` with **A**. Scientific notation is accepted. Expressions and units typed into the number field are not.
- **Check my answer** gives feedback without revealing a wrong answer. If the magnitude is right but the sign is wrong, the feedback says so.
- **Show next hint** reveals one hint at a time, two per question.
- A correct answer, or **Reveal worked answer**, shows the hand calculation. Revealing alone does not mark a question correct; a later correct submission does.

Answers within 0.5% relative error, or 10⁻⁹ absolute in the base unit, are accepted. Invalid or nonfinite entries don't count as attempts. Progress is kept only for the current session.

## Keeping the answer key valid

Moving or rotating parts keeps the question gradable, because connections are unchanged. Changing a value, a connection, a node name or an amplifier setting disables grading for that question, since the answer key no longer describes the circuit. Start the question again to reload it, or keep experimenting with **Solve drawing**. Loading another drawing or clearing the canvas ends the active question.

## Implementation

- **`practice.py`** defines each question with a fixed, hand-derived answer key and two hints. `grade_answer()` converts the chosen unit to V, A or Ω, rejects nonfinite input, and compares the signed result with the key. It never calls the solver to produce an answer.
- **`practice_ui.py`** handles loading, hints, form submission, worked answers and session progress. Before grading, it compares a signature of the compiled netlist against the question's signature. Coordinates and wire corners don't enter that signature, so only electrical changes invalidate the key.

The test suite independently solves all nine exercise circuits to cross-check their fixed keys. Streamlit integration tests and the browser suite cover hints, unit handling, explicit reveal, signed-current feedback, progress, and rejection of a stale key after the circuit is edited.
