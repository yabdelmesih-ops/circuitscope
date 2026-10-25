"""Use the bundled engine in UI/lesson tests.

Independent expected numbers live in examples.py and opamp_examples.py;
verification compares this engine against those fixed hand calculations.
"""
from engine import solve_circuit, get_voltages, thevenin, open_circuit_voltage
