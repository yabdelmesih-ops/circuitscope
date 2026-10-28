# CircuitScope

A Python project for drawing and solving DC circuits while studying Circuits I.
The interface uses Streamlit and a JavaScript canvas; NumPy solves the circuit equations.

Build circuits with resistors, independent voltage/current sources and ideal op amps.
Find node voltages, branch currents, signed power and linear Thévenin/Norton equivalents.
The app also shows KCL explanations and supported Circuits I methods.

From this folder, run:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run drawing_app.py
```

- [User guide](docs/USER_GUIDE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [SPICE validation and tests](docs/VALIDATION.md)

This is a DC learning model. It does not simulate AC, transients or real amplifier dynamics.
