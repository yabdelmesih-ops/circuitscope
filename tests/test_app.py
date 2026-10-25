"""Exercise Python UI paths with a lightweight Streamlit API harness.

Does not verify real widget rendering or the browser custom-component transport.
"""
import json
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import patch
import reference_engine

ROOT=Path(__file__).resolve().parents[1]
class State(dict):
    def __getattr__(self,key): return self[key]
    def __setattr__(self,key,value): self[key]=value
class FakeStreamlit(types.ModuleType):
    def __init__(self, quantity):
        super().__init__('streamlit')
        self.quantity=quantity
        self.session_state=State(canvas_seed=json.loads((ROOT/'sample_drawing.json').read_text()))
        self.metrics=[]
        self.components=types.SimpleNamespace(v2=types.SimpleNamespace(component=self.register))
    def register(self, **args):
        assert 'export default' in args['js']
        def render(**kwargs):
            assert kwargs['height'] > 0
            return types.SimpleNamespace(drawing=kwargs['default']['drawing'])
        return render
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def __getattr__(self,name):
        return lambda *args,**kwargs: None
    def columns(self, sizes): return [self for _ in (range(sizes) if isinstance(sizes, int) else sizes)]
    def expander(self,*args,**kwargs): return self
    def file_uploader(self,*args,**kwargs): return None
    def button(self,label,**kwargs): return label=='Solve drawing'
    def selectbox(self,label,options,index=0,**kwargs):
        return self.quantity if label=='Find' else options[index]
    def metric(self,label,value): self.metrics.append((label,value))
    def error(self,message): raise AssertionError(message)
    def stop(self): raise AssertionError('Unexpected stop')

class AppTests(unittest.TestCase):
    def check_quantity(self,quantity,expected):
        fake=FakeStreamlit(quantity)
        with patch.dict(sys.modules,{'streamlit':fake,'engine':reference_engine}):
            runpy.run_path(str(ROOT/'drawing_app.py'))
        self.assertIn(expected,[v for _,v in fake.metrics])
    def test_voltage(self): self.check_quantity('Node voltage','7.2 V')
    def test_current(self): self.check_quantity('Branch current','-0.0072 A')
    def test_power(self): self.check_quantity('Component power','-0.0864 W')
    def test_thevenin(self): self.check_quantity('Thevenin','12 V')
    def test_norton(self): self.check_quantity('Norton','0.018 A')

if __name__=='__main__':unittest.main()
