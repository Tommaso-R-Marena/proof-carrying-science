"""Deterministic tiny inputs; includes a serialized ONNX ModelProto with Identity node."""
from pathlib import Path
import struct, json
ROOT=Path(__file__).resolve().parent.parent/'samples'
ROOT.mkdir(parents=True,exist_ok=True)

def v(n):
    out=bytearray()
    while n >= 128:
        out.append((n & 127)|128);n >>= 7
    return bytes(out)+bytes([n])

def fld(number, value):
    if isinstance(value, int):return v((number<<3)|0)+v(value)
    if isinstance(value,str): value=value.encode()
    return v((number<<3)|2)+v(len(value))+value

def onnx_sample(missing=False,custom=False,stochastic=False,op="Identity"):
    inp='unknown' if missing else 'features'
    node=fld(1,inp)+fld(2,'prediction')+fld(4,'RandomNormal' if stochastic else op)
    if custom:node+=fld(7,'com.example.custom')
    # ValueInfoProto needs a TypeProto containing TensorProto type + shape.
    dim = fld(1,1)  # TensorShapeProto.Dimension.dim_value = 1
    tensor_shape = fld(1,dim)  # repeated Dimension dim = 1
    tensor_type = fld(1,1) + fld(2,tensor_shape)  # elem_type=FLOAT, shape
    type_proto = fld(1,tensor_type)
    inputvi=fld(1,'features')+fld(2,type_proto)
    outputvi=fld(1,'prediction')+fld(2,type_proto)
    graph=fld(1,node)+fld(2,'PCS_example')+fld(11,inputvi)+fld(12,outputvi)
    opset=fld(1,'')+fld(2,13)
    return fld(1,8)+fld(2,'PCS_test_fixture')+fld(7,graph)+fld(8,opset)

def safe_sample(values=(0.0, 1.0, -2.0, 3.5)):
    raw=b''.join(struct.pack('<f',x) for x in values)
    header=json.dumps({'example.weight':{'dtype':'F32','shape':[len(values)],'data_offsets':[0,len(raw)]}},separators=(',',':')).encode()
    return struct.pack('<Q',len(header))+header+raw

def pdb_line(serial,name,chain,resnum,x,y,z,res='GLY',element='C'):
    return f"ATOM  {serial:5d} {name:<4s} {res:>3s} {chain}{resnum:4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{20.0:6.2f}          {element:>2s}  \n"

if __name__=='__main__':
    (ROOT/'demo_identity.onnx').write_bytes(onnx_sample())
    (ROOT/'demo_relu_violation.onnx').write_bytes(onnx_sample(op='Relu'))
    (ROOT/'demo_weights.safetensors').write_bytes(safe_sample())
    (ROOT/'demo_protein.pdb').write_text(pdb_line(1,'CA','A',1,0,0,0)+pdb_line(2,'CA','A',5,6,0,0)+'END\n')
    (ROOT/'demo_reaction.sbml').write_text('<?xml version="1.0"?><sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2"><model id="reactions"><listOfSpecies><species id="A" compartment="c" initialAmount="10"/><species id="B" compartment="c" initialAmount="0"/></listOfSpecies><listOfReactions><reaction id="r1"><listOfReactants><speciesReference species="A"/></listOfReactants><listOfProducts><speciesReference species="B"/></listOfProducts><kineticLaw><math xmlns="http://www.w3.org/1998/Math/MathML"><cn>1</cn></math></kineticLaw></reaction></listOfReactions></model></sbml>')
    (ROOT/'demo_sequence.fasta').write_text('>PCS_example_protein\nMAVKLEDELGKD\n')
    for suffix,amount in [('balanced',2),('imbalanced',1)]:
        xml=f'<sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" xmlns:fbc="http://www.sbml.org/sbml/level3/version1/fbc/version2" level="3" version="2"><model id="water"><listOfSpecies><species id="H2" fbc:chemicalFormula="H2"/><species id="O2" fbc:chemicalFormula="O2"/><species id="H2O" fbc:chemicalFormula="H2O"/></listOfSpecies><listOfReactions><reaction id="water_synthesis"><listOfReactants><speciesReference species="H2" stoichiometry="2"/><speciesReference species="O2"/></listOfReactants><listOfProducts><speciesReference species="H2O" stoichiometry="{amount}"/></listOfProducts></reaction></listOfReactions></model></sbml>'
        (ROOT/f'demo_water_{suffix}.sbml').write_text(xml)
    (ROOT/'demo_damaged_graph.onnx').write_bytes(onnx_sample(missing=True))
    (ROOT/'demo_nan_weights.safetensors').write_bytes(safe_sample((0,float('nan'),2,3)))
    print('created',len(list(ROOT.iterdir())),'sample files')
