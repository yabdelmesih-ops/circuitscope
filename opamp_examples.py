"""Fixed hand calculations for ideal amplifiers and unloaded outputs."""


def amplifier_examples(part, drawing):
    def amp():
        return dict(id='U1', type='OPAMP', x=620, y=340, rotation=0,
                    label1='', label2='Vm', label3='Vout', v_min=-15, v_max=15)
    def probe():
        return part('OUT1', 'PORT', None, 980, 280)
    feedback = [('U1:2','Rf:1','vh',[(480,360),(480,500)]),
                ('Rf:2','U1:3','hv',[(800,500),(800,340)])]
    probe_links = [('U1:3','OUT1:1','hv',[(860,340),(860,280)]),
                   ('OUT1:2','GND1:1','vh',[(1020,580),(160,580)])]
    inv = drawing([
        part('V1','V',1,160,440,90,'Vin'), part('Rin','R',10000,360,360),
        part('Rf','R',20000,620,500), amp(),
        part('RL','R',10000,900,460,90), probe(),
        part('GND1','GROUND',None,160,640), part('GND2','GROUND',None,460,280),
    ], [('V1:1','Rin:1','vh'),('Rin:2','U1:2','hv'),
        ('V1:2','GND1:1','vh'),('U1:1','GND2:1','hv',[(520,320),(520,260)]),
        ('U1:3','RL:1','hv'),('RL:2','GND1:1','vh',[(900,580),(160,580)])] + feedback + probe_links)
    noninv = drawing([
        part('V1','V',1,160,340,90,'Vin'), part('Rg','R',10000,400,500,90),
        part('Rf','R',20000,620,500), amp(), probe(),part('GND1','GROUND',None,160,640),
    ], [('V1:1','U1:1','vh',[(160,240),(520,240),(520,320)]),
        ('V1:2','GND1:1','vh'),('U1:2','Rg:1','hv',[(400,360)]),
        ('Rg:2','GND1:1','vh',[(400,580),(160,580)])] + feedback + probe_links)
    follower_amp = amp()
    follower_amp['label2'] = ''  # Minus and output are physically wired here.
    follower = drawing([
        part('V1','V',2,160,340,90,'Vin'), follower_amp, probe(),
        part('GND1','GROUND',None,160,640),
    ], [('V1:1','U1:1','vh',[(160,240),(520,240),(520,320)]),
        ('V1:2','GND1:1','vh'),('U1:3','U1:2','vh',[(800,460),(480,460),(480,360)])] + probe_links)
    unloaded = drawing([
        part('V1','V',12,200,360,90,'Vin'),part('R1','R',1000,500,240,0,'','Vout'),
        part('OUT1','PORT',None,840,340),part('GND1','GROUND',None,200,620),
    ], [('V1:1','R1:1','vh'),('R1:2','OUT1:1','hv'),
        ('V1:2','GND1:1','vh'),('OUT1:2','GND1:1','vh',[(880,540),(200,540)])])
    return [
        dict(id='inverting',title='Op amp · inverting amplifier (−2 V)', drawing=inv,
             description='A 1 V input, 10 kΩ input resistor and 20 kΩ feedback resistor give −2 V. Remove only RL for an open external output.',
             expected_v={'0':0,'Vin':1,'Vm':0,'Vout':-2},
             expected_i={'V1':-.0001,'Rin':.0001,'Rf':.0001,'RL':-.0002,'U1':.0003},
             port=dict(node1='Vout',node2='0',load='RL',voltage=-2,resistance=0),
             hand=['Negative feedback and grounded + give Vm = 0 V, but Vm is a separate electrical node from ground. Input currents into U1 are zero.',
                   'KCL: (0 − 1)/10000 + (0 − Vout)/20000 = 0, so Vout = −2 V.',
                   'With RL connected, 0.3 mA enters the amplifier output. With RL removed, 0.1 mA still flows through feedback. Ideal output resistance is zero; no finite Norton equivalent exists.'],
             equations=[r'V_{out}=-\frac{20000}{10000}(1)=-2\ \mathrm{V}',r'I_+=I_-=0']),
        dict(id='noninverting',title='Op amp · non-inverting amplifier (3 V)', drawing=noninv,
             description='The input drives +. A 10 kΩ / 20 kΩ feedback divider sets gain to 3, with no external load.',
             expected_v={'0':0,'Vin':1,'Vm':1,'Vout':3},
             expected_i={'V1':0,'Rg':.0001,'Rf':-.0001,'U1':-.0001},
             port=dict(node1='Vout',node2='0',load=None,voltage=3,resistance=0),
             hand=['Vm equals Vin = 1 V under linear negative feedback. Rg carries 0.1 mA to ground; the same current comes through Rf from the output.',
                   'No external output load is present, but the feedback divider still draws 0.1 mA. The ideal input draws zero current.'],
             equations=[r'V_{out}=\left(1+\frac{20000}{10000}\right)(1)=3\ \mathrm{V}']),
        dict(id='follower',title='Op amp · voltage follower (2 V, zero load current)',drawing=follower,
             description='Wire OUT directly to − and drive + with 2 V. The unloaded output stays at 2 V while its current is zero.',
             expected_v={'0':0,'Vin':2,'Vout':2},expected_i={'V1':0,'U1':0},
             port=dict(node1='Vout',node2='0',load=None,voltage=2,resistance=0),
             hand=['OUT and − share a real wire. + and − have equal voltage because of feedback, while the two input nodes remain separate.',
                   'With infinite input/probe resistance and no external load, every branch current is zero. A voltage can exist without load current.'],
             equations=[r'V_{out}=V_-=V_+=2\ \mathrm{V},\qquad I_{out}=0']),
        dict(id='openoutput',title='Open output · 12 V with no resistor current',drawing=unloaded,
             description='A 12 V source feeds a resistor ending at an unloaded output. The output probe draws no current.',
             expected_v={'0':0,'Vin':12,'Vout':12},expected_i={'V1':0,'R1':0},
             port=dict(node1='Vout',node2='0',load=None,voltage=12,resistance=1000),
             hand=['An open external output carries no load current. KCL at Vout forces the resistor current to zero.',
                   'I = 0 means the resistor drops 0 V, so Vout = Vin = 12 V. This output is not floating: the source and resistor determine its voltage.'],
             equations=[r'\frac{V_{out}-12}{1000}=0\quad\Rightarrow\quad V_{out}=12\ \mathrm{V}']),
    ]
