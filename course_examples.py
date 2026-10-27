"""Additional course drawings; original eleven SPICE reference cases stay intact."""
from copy import deepcopy
from examples import get_examples, part, drawing


def get_course_examples():
    original={e['id']:e for e in get_examples()}
    def reuse(identifier,title):
        e=deepcopy(original[identifier]);e['title']=title;return e
    def amp(name,x,y,plus='',minus='Vm',out='Vout'):
        return dict(id=name,type='OPAMP',x=x,y=y,rotation=0,label1=plus,label2=minus,label3=out,v_min=-15,v_max=15,mode='feedback')
    inv=drawing([
        part('V1','V',1,160,180,90,'Vin1'),part('V2','V',2,160,440,90,'Vin2'),
        part('R1','R',10000,380,200),part('R2','R',20000,380,420),
        amp('U1',620,340),part('Rf','R',20000,620,540),part('RL','R',10000,900,460,90),
        part('OUT1','PORT',None,980,260),part('GND1','GROUND',None,160,620),
        part('GND2','GROUND',None,260,620),part('GND3','GROUND',None,460,280),
    ],[('V1:1','R1:1','vh'),('V2:1','R2:1','vh'),('R1:2','U1:2','hv',[(500,200),(500,360)]),
       ('R2:2','U1:2','hv',[(500,420),(500,360)]),('U1:1','GND3:1','hv',[(520,320),(520,260)]),
       ('U1:2','Rf:1','vh',[(500,360),(500,540)]),('Rf:2','U1:3','hv',[(820,540),(820,340)]),
       ('U1:3','RL:1','hv'),('RL:2','GND2:1','vh',[(900,600),(260,600)]),
       ('V1:2','GND1:1','vh'),('V2:2','GND2:1','vh'),('U1:3','OUT1:1','hv',[(860,340),(860,260)]),('OUT1:2','GND2:1','vh')])
    noninv=drawing([
        part('V1','V',1,160,180,90,'Vin1'),part('V2','V',3,160,440,90,'Vin2'),
        part('R1','R',10000,380,200),part('R2','R',10000,380,420),
        amp('U1',620,340,'Vp'),part('Rf','R',10000,660,540),part('Rg','R',10000,500,540,90),
        part('OUT1','PORT',None,980,260),part('GND1','GROUND',None,160,620),part('GND2','GROUND',None,260,620),
    ],[('V1:1','R1:1','vh'),('V2:1','R2:1','vh'),('R1:2','U1:1','hv',[(500,200),(500,320)]),
       ('R2:2','U1:1','hv',[(500,420),(500,320)]),('U1:2','Rg:1','hv',[(500,360)]),('Rg:2','GND2:1','vh'),
       ('U1:2','Rf:1','vh',[(580,360),(580,540)]),('Rf:2','U1:3','hv',[(820,540),(820,340)]),
       ('V1:2','GND1:1','vh'),('V2:2','GND2:1','vh'),('U1:3','OUT1:1','hv'),('OUT1:2','GND2:1','vh')])
    mixed=drawing([
        part('V1','V',12,160,340,90,'Vs'),part('R1','R',1000,420,200),
        part('R2','R',2000,820,400,90,'Va'),part('I1','I',.002,560,420,270,'','Va'),
        part('GND1','GROUND',None,160,620),
    ],[('V1:1','R1:1','vh'),('R1:2','R2:1','hv'),('I1:2','R2:1','vh'),
       ('R2:2','V1:2','hv',[(820,560),(160,560)]),('I1:1','V1:2','vh'),('V1:2','GND1:1','vh')])
    loaded=deepcopy(original['divider']['drawing'])
    loaded['items'].append(part('RL','R',2000,980,380,90))
    loaded['wires'] += [dict(id='wl1',a='R2:1',b='RL:1',bend='hv'),dict(id='wl2',a='R2:2',b='RL:2',bend='hv')]
    cascade=drawing([
        part('V1','V',1,140,300,90,'Vin'),amp('U1',400,240,minus='',out='Vbuf'),
        amp('U2',780,360,'Vbuf','Vm','Vout'),part('Rf','R',20000,820,540),part('Rg','R',10000,640,540,90),
        part('GND1','GROUND',None,140,640),part('GND2','GROUND',None,640,640),
        part('OUT1','PORT',None,1020,300),
    ],[('V1:1','U1:1','vh'),('V1:2','GND1:1','vh'),('U1:3','U1:2','vh',[(500,420),(300,420),(300,260)]),
       ('U1:3','U2:1','hv',[(600,240),(600,340)]),('U2:2','Rg:1','hv',[(640,380)]),('Rg:2','GND2:1','vh'),
       ('U2:2','Rf:1','vh',[(700,380),(700,540)]),('Rf:2','U2:3','hv',[(960,540),(960,360)]),
       ('U2:3','OUT1:1','hv'),('OUT1:2','GND2:1','vh')])
    def case(identifier,title,model,v,i,hand,equations):
        return dict(id=identifier,title=title,drawing=model,expected_v={'0':0,**v},expected_i=i,port=None,hand=hand,equations=equations)
    return [reuse('supernode','Supernode · floating source'),reuse('divider','Voltage divider and source transformation'),
        case('loaded_divider','Loaded voltage divider',loaded,{'Vs':12,'Va':6},
             {'V1':-.006,'R1':.006,'R2':.003,'RL':.003},
             ['R2 ∥ RL = 1000 Ω; Va = 12 × 1000/(1000 + 1000) = 6 V.'],[r'V_a=12\frac{R_2\parallel R_L}{R_1+R_2\parallel R_L}=6\ \mathrm{V}']),
        case('mixed_sources','Superposition · voltage and current sources',mixed,{'Vs':12,'Va':28/3},
             {'V1':-.008/3,'R1':.008/3,'R2':.014/3,'I1':.002},
             ['V1 alone contributes 8 V. I1 alone contributes 4/3 V. Va = 28/3 V.'],[r'\frac{V_a-12}{1000}+\frac{V_a}{2000}-0.002=0']),
        case('inverting_sum','Summing amplifier · inverting',inv,{'Vin1':1,'Vin2':2,'Vm':0,'Vout':-4},
             {'V1':-.0001,'V2':-.0001,'R1':.0001,'R2':.0001,'Rf':.0002,'RL':-.0004,'U1':.0006},
             ['Vout = −Rf(Vin1/R1 + Vin2/R2) = −4 V. Both input currents are zero.'],[r'V_{out}=-20000\left(\frac{1}{10000}+\frac{2}{20000}\right)=-4\ \mathrm{V}']),
        case('noninverting_sum','Summing amplifier · non-inverting',noninv,{'Vin1':1,'Vin2':3,'Vp':2,'Vm':2,'Vout':4},
             {'V1':.0001,'V2':-.0001,'R1':-.0001,'R2':.0001,'Rf':-.0002,'Rg':.0002,'U1':-.0002},
             ['Equal input resistors average the two signals to 2 V. Closed-loop gain is 2, so Vout = 4 V.'],[r'V_+=\frac{1/10000+3/10000}{1/10000+1/10000}=2\ \mathrm{V}',r'V_{out}=(1+10000/10000)V_+=4\ \mathrm{V}']),
        case('feedback_cascade','Supported feedback · follower then gain stage',cascade,{'Vin':1,'Vbuf':1,'Vm':1,'Vout':3},
             {'V1':0,'U1':0,'U2':-.0001,'Rf':-.0001,'Rg':.0001},
             ['U1 is a unity follower. U2 has its own passive negative-feedback loop and gain 3. The cascade is feed-forward between stages.'],[r'V_{buf}=V_{in}=1\ \mathrm{V}',r'V_{out}=(1+20000/10000)V_{buf}=3\ \mathrm{V}'])]
