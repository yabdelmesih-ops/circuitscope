from copy import deepcopy
from io import BytesIO
import json
import unittest
from urllib.error import HTTPError
from PIL import Image
from screenshot_import import *
from screenshot_ui import review_demo
from topology import compile_drawing
from engine import get_voltages


def image_bytes():
    out=BytesIO();Image.new('RGBA',(20,20),(0,0,0,0)).save(out,format='PNG');return out.getvalue()


class ScreenshotImportTests(unittest.TestCase):
    def test_request_uses_inline_image_strict_schema_and_no_stored_response(self):
        r=build_request(image_bytes())
        self.assertFalse(r['store']);self.assertTrue(r['text']['format']['strict'])
        self.assertTrue(r['input'][0]['content'][1]['image_url'].startswith('data:image/jpeg;base64,'))
        from jsonschema import Draft202012Validator
        Draft202012Validator(EXTRACTION_SCHEMA).validate(review_demo())

    def test_invalid_files_and_oversize_input_are_rejected_before_network(self):
        for data in [b'',b'not an image',b'x'*(8*1024*1024+1)]:
            with self.assertRaises(ValueError):prepare_image(data)
        with self.assertRaises(ValueError):build_request(image_bytes(),model='https://other.example')

    def test_transport_contract_parses_without_a_real_key_or_network(self):
        class Response(BytesIO):pass
        calls=[]
        def transport(request,timeout):
            calls.append((request.full_url,request.get_header('Authorization'),timeout))
            return Response(json.dumps(dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(review_demo()))])])).encode())
        payload=analyze_image(image_bytes(),'test-key',transport=transport)
        self.assertEqual(calls,[('https://api.openai.com/v1/responses','Bearer test-key',120)])
        self.assertEqual(payload,review_demo())
        self.assertNotIn('test-key',json.dumps(payload))

    def test_refusal_incomplete_and_bad_json_do_not_become_drawings(self):
        for response in [dict(status='incomplete'),dict(status='completed',output=[dict(content=[dict(type='refusal')])]),dict(status='completed',output=[dict(content=[dict(type='output_text',text='not json')])])]:
            with self.assertRaises(ValueError):parse_response(response)

    def test_api_error_hides_response_and_key(self):
        def failed(request,timeout):raise HTTPError(API_URL,401,'secret response',{},None)
        with self.assertRaisesRegex(ValueError,'HTTP 401') as error:analyze_image(image_bytes(),'private-key',transport=failed)
        self.assertNotIn('private-key',str(error.exception));self.assertNotIn('secret response',str(error.exception))

    def test_invalid_key_is_rejected_without_echoing_it_or_calling_network(self):
        calls=[]
        with self.assertRaises(ValueError) as error:
            analyze_image(image_bytes(),'private-key\r\nInjected: value',transport=lambda *args,**kwargs:calls.append(args))
        self.assertEqual(calls,[]);self.assertNotIn('private-key',str(error.exception))

    def test_review_reconstructs_real_connections_and_preserves_negative_sources(self):
        rows=review_demo()['components'];drawing=reviewed_drawing(rows)
        p,_=compile_drawing(drawing);self.assertAlmostEqual(get_voltages(p)['Va'],8)
        rows[0]['value']=-12;p,_=compile_drawing(reviewed_drawing(rows));self.assertAlmostEqual(get_voltages(p)['Va'],-8)

    def test_unknown_values_modes_and_supply_limits_require_explicit_review(self):
        rows=review_demo()['components'];rows[0]['value']=None
        with self.assertRaisesRegex(ValueError,'finite value'):reviewed_drawing(rows)
        amp={**dict.fromkeys(FIELDS),'name':'U1','type':'OPAMP','node1':'Va','node2':'Vm','node3':'Vout'}
        rows=review_demo()['components']+[amp]
        with self.assertRaisesRegex(ValueError,'explicitly'):reviewed_drawing(rows)
        amp['mode']='feedback'
        with self.assertRaisesRegex(ValueError,'minimum and maximum'):reviewed_drawing(rows)

    def test_invalid_values_nodes_duplicate_names_and_unsupported_parts_rejected(self):
        for key,value in [('value',float('nan')),('value',True),('node1','<script>'),('name','R1'),('type','CAPACITOR')]:
            rows=review_demo()['components'];rows[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises((ValueError,TypeError)):reviewed_drawing(rows)
        rows=review_demo()['components']
        for r in rows:
            for key in ('node1','node2'):
                if r[key]=='0':r[key]='G'
        with self.assertRaisesRegex(ValueError,'reference'):reviewed_drawing(rows)
