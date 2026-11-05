"""Optional independent protobuf decoding and fail-closed proof gate (v0.12).

The existing screened ONNX reader is hand-written.  The second path here uses
Google's maintained protobuf wire decoder with a *fixed* descriptor for the
small ONNX grammar understood by PCS.  Both paths must agree on all numerical
components that can affect a proof (operator DAG, shapes, and exact FP32 bits).

This is intentionally NOT an official onnx.checker, ONNX Runtime conformance,
formal verification, a secure sandbox, or a claim that two decoders have no
shared assumptions.  We never dynamically import model-supplied code.

This optional gate ABSTAINS when Google protobuf is not installed; the original
standard-library proof checker is preserved for independent replay, but may not
advertise the additional 'independently decoded' evidence.
"""
from __future__ import annotations

import hashlib
import struct
from functools import lru_cache
from .dense_nn import Unsupported, screen_onnx
from .relational_kernel import canonical

SCHEMA = 'pcs-dual-protobuf-decoder-v0.12'
GATE_SCHEMA = 'pcs-dual-decoder-proof-gate-v0.12'


@lru_cache(maxsize=1)
def _message_type():
    # Dynamically constructed descriptors require only protobuf; no generated
    # ONNX package, downloaded schemas, model-supplied plugins, or protoc.
    from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = 'pcs_onnx_screened_v12.proto'
    fd.package = 'pcs_screened'
    fd.syntax = 'proto2'
    T = descriptor_pb2.FieldDescriptorProto

    def msg(name):
        m = fd.message_type.add()
        m.name = name
        return m

    def field(m, name, number, typ, repeated=False, message=None, oneof=None, packed=False):
        f = m.field.add()
        f.name = name
        f.number = number
        f.label = T.LABEL_REPEATED if repeated else T.LABEL_OPTIONAL
        f.type = typ
        if message is not None:
            f.type_name = '.pcs_screened.' + message
        if oneof is not None:
            f.oneof_index = oneof
        if packed:
            f.options.packed = True
        return f

    op = msg('OperatorSetIdProto')
    field(op,'domain',1,T.TYPE_STRING)
    field(op,'version',2,T.TYPE_INT64)

    dim = msg('Dimension')
    field(dim,'dim_value',1,T.TYPE_INT64)
    field(dim,'dim_param',2,T.TYPE_STRING)
    field(dim,'denotation',3,T.TYPE_STRING)
    shape = msg('TensorShapeProto')
    field(shape,'dim',1,T.TYPE_MESSAGE,True,'Dimension')
    tt = msg('TensorType')
    field(tt,'elem_type',1,T.TYPE_INT32)
    field(tt,'shape',2,T.TYPE_MESSAGE,message='TensorShapeProto')
    tp = msg('TypeProto')
    tp.oneof_decl.add().name='value'
    field(tp,'tensor_type',1,T.TYPE_MESSAGE,message='TensorType',oneof=0)
    # Declare the alternative oneof tags so protobuf's last-member-wins
    # behavior can never silently match a preceding tensor_type.
    for n,tag in [('sequence_type',4),('map_type',5),('opaque_type',7),
                  ('sparse_tensor_type',8),('optional_type',9)]:
        # The actual alternatives are embedded messages.  This fixed grammar
        # treats them as opaque message payloads; they are never accepted.
        field(tp,n,tag,T.TYPE_MESSAGE,message='OpaqueType',oneof=0)
    opaque = msg('OpaqueType')
    field(opaque,'payload',99,T.TYPE_BYTES)

    vi = msg('ValueInfoProto')
    field(vi,'name',1,T.TYPE_STRING)
    field(vi,'type',2,T.TYPE_MESSAGE,message='TypeProto')
    field(vi,'doc_string',3,T.TYPE_STRING)

    tensor = msg('TensorProto')
    field(tensor,'dims',1,T.TYPE_INT64,True,packed=True)
    field(tensor,'data_type',2,T.TYPE_INT32)
    field(tensor,'float_data',4,T.TYPE_FLOAT,True,packed=True)
    field(tensor,'name',8,T.TYPE_STRING)
    field(tensor,'raw_data',9,T.TYPE_BYTES)
    field(tensor,'doc_string',12,T.TYPE_STRING)

    node = msg('NodeProto')
    field(node,'input',1,T.TYPE_STRING,True)
    field(node,'output',2,T.TYPE_STRING,True)
    field(node,'name',3,T.TYPE_STRING)
    field(node,'op_type',4,T.TYPE_STRING)
    field(node,'doc_string',6,T.TYPE_STRING)
    field(node,'domain',7,T.TYPE_STRING)

    graph = msg('GraphProto')
    field(graph,'node',1,T.TYPE_MESSAGE,True,'NodeProto')
    field(graph,'name',2,T.TYPE_STRING)
    field(graph,'initializer',5,T.TYPE_MESSAGE,True,'TensorProto')
    field(graph,'input',11,T.TYPE_MESSAGE,True,'ValueInfoProto')
    field(graph,'output',12,T.TYPE_MESSAGE,True,'ValueInfoProto')
    field(graph,'value_info',13,T.TYPE_MESSAGE,True,'ValueInfoProto')

    model = msg('ModelProto')
    field(model,'ir_version',1,T.TYPE_INT64)
    field(model,'producer_name',2,T.TYPE_STRING)
    field(model,'producer_version',3,T.TYPE_STRING)
    field(model,'domain',4,T.TYPE_STRING)
    field(model,'model_version',5,T.TYPE_INT64)
    field(model,'doc_string',6,T.TYPE_STRING)
    field(model,'graph',7,T.TYPE_MESSAGE,message='GraphProto')
    field(model,'opset_import',8,T.TYPE_MESSAGE,True,'OperatorSetIdProto')

    pool = descriptor_pool.DescriptorPool()
    pool.Add(fd)
    return message_factory.GetMessageClass(
        pool.FindMessageTypeByName('pcs_screened.ModelProto'))


def _bits(values):
    return [struct.pack('<f',float(x)).hex() for x in values]


def _from_custom(spec):
    """Numerical-semantic digest with every weight encoded as exact f32 bits."""
    return {
        'ir':spec['ir'], 'opset':spec['opset'],
        'input':[spec['input'],[1,spec['input_width']]],
        'output':[spec['output'],[1,spec['output_width']]],
        'weights':{k:{'shape':list(v['shape']),'bits':_bits(v['values'])}
                   for k,v in spec['weights'].items()},
        'nodes':[{'op':n['op'],'inputs':list(n['inputs']),'out':n['out']}
                 for n in spec['nodes']],
    }


def _from_protobuf(raw):
    Model=_message_type()
    msg=Model.FromString(raw)
    if not msg.HasField('graph') or not msg.HasField('ir_version'):
        raise ValueError('protobuf model graph/version absent')
    if len(msg.opset_import)!=1:
        raise ValueError('protobuf opset count')
    op=msg.opset_import[0]
    if not op.HasField('version'):
        raise ValueError('protobuf opset version absent')

    def vi(value):
        if not value.HasField('type') or value.type.WhichOneof('value')!='tensor_type':
            raise ValueError('protobuf value has no plain tensor type')
        ten=value.type.tensor_type
        if not ten.HasField('shape') or not ten.HasField('elem_type') or ten.elem_type!=1:
            raise ValueError('protobuf tensor shape/type absent')
        dims=[]
        for dim in ten.shape.dim:
            if not dim.HasField('dim_value') or dim.HasField('dim_param'):
                raise ValueError('protobuf symbolic/missing dimension')
            dims.append(int(dim.dim_value))
        return [value.name,dims]

    g=msg.graph
    if len(g.input)!=1 or len(g.output)!=1:
        raise ValueError('protobuf input/output count')
    weights={}
    for t in g.initializer:
        if t.name in weights:
            raise ValueError('duplicate protobuf initializer')
        dims=list(t.dims)
        if t.HasField('raw_data'):
            if len(t.raw_data)%4:
                raise ValueError('unaligned float32 weight bytes')
            bits=[t.raw_data[i:i+4].hex() for i in range(0,len(t.raw_data),4)]
        else:
            bits=_bits(t.float_data)
        weights[t.name]={'shape':dims,'bits':bits}
    return {
        'ir':int(msg.ir_version),'opset':int(op.version),
        'input':vi(g.input[0]),'output':vi(g.output[0]),
        'weights':weights,
        'nodes':[{'op':n.op_type,'inputs':list(n.input),'out':n.output[0] if len(n.output)==1 else None}
                 for n in g.node],
    }


def crosscheck(raw:bytes)->dict:
    """Return AGREE only for exact screened numerical-semantic agreement.

    Never silently fallback to the original parser if protobuf is missing.
    This is an empirical two-decoder check and NOT a proof of protobuf soundness.
    """
    result={'schema':SCHEMA,'status':'NOT_RUN',
            'official_onnx_checker':'NOT_RUN',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'external_runtime_equivalence':'NOT_ESTABLISHED'}
    try:
        from google.protobuf import __version__ as protobuf_version
    except ImportError:
        return dict(result,reason='Independent Google protobuf decoder unavailable')
    try:
        if type(raw) is not bytes:
            raise ValueError('Immutable model bytes required')
        screened=screen_onnx(raw)
        manual=_from_custom(screened)
        other=_from_protobuf(raw)
        if manual!=other:
            return dict(result,status='DISAGREEMENT',model_sha256=hashlib.sha256(raw).hexdigest(),
                        reason='Independent protobuf decoding disagrees with screened mathematical model')
        digest=hashlib.sha256(canonical(manual)).hexdigest()
        return dict(result,status='AGREE',model_sha256=hashlib.sha256(raw).hexdigest(),
                    semantic_digest_sha256=digest,
                    protobuf_version=protobuf_version,
                    scope='restricted two-decoder numerical-semantic agreement; not an official ONNX validator or proof kernel')
    except (ValueError,TypeError,KeyError,UnicodeError,OverflowError,ArithmeticError,MemoryError,
            Unsupported) as exc:
        return dict(result,status='DISAGREEMENT',reason=type(exc).__name__+': '+str(exc)[:160])
    except Exception as exc:
        # e.g. google.protobuf.message.DecodeError, no trusted fallback.
        return dict(result,status='DISAGREEMENT',reason=type(exc).__name__+': '+str(exc)[:160])


class DualDecoderAssuranceGate:
    """Requires *both* mathematical proofs AND independent protobuf agreement."""
    __slots__=('__gate','__review')

    def __init__(self, old:bytes,new:bytes,real_bundle:dict,direct_bundle:dict,
                 policy:dict, trusted_policy_sha256:str):
        from .dual_envelope_v10 import DualAssuranceGate
        self.__gate=None
        self.__review={'schema':GATE_SCHEMA,'status':'OPEN',
                       'deployment_authorization':'NOT_ESTABLISHED',
                       'lean_kernel_verification':'NOT_ESTABLISHED',
                       'official_onnx_runtime_equivalence':'NOT_ESTABLISHED'}
        try:
            old=bytes(old);new=bytes(new)
            oldcheck=crosscheck(old);newcheck=crosscheck(new)
            if oldcheck['status']!='AGREE' or newcheck['status']!='AGREE':
                self.__review=dict(self.__review,reason='Independent ONNX decoding not established',
                                   original_decoder_status=oldcheck['status'],
                                   updated_decoder_status=newcheck['status'])
                return
            gate=DualAssuranceGate(old,new,real_bundle,direct_bundle,policy,trusted_policy_sha256)
            review=gate.review()
            if review['status']!='PROVED_CONDITIONALLY':
                self.__review=dict(self.__review,reason='Mathematical proof gate rejected evidence',
                                   original_decoder_status='AGREE',updated_decoder_status='AGREE',
                                   mathematical_status=review['status'])
                return
            self.__gate=gate
            self.__review=dict(self.__review,status='PROVED_CONDITIONALLY',
                               old_model_sha256=oldcheck['model_sha256'],
                               new_model_sha256=newcheck['model_sha256'],
                               original_semantic_digest=oldcheck['semantic_digest_sha256'],
                               updated_semantic_digest=newcheck['semantic_digest_sha256'],
                               policy_sha256=review['policy_sha256'],
                               verified_regions=review['region_count'],
                               checked_fp32_partition_leaves=review['checked_fp32_partition_leaves'],
                               scope='independent protobuf/handwritten decoder agreement + two Python proof routes')
        except (TypeError,ValueError,MemoryError,OverflowError) as exc:
            self.__review=dict(self.__review,reason=type(exc).__name__+': '+str(exc)[:160])

    def review(self)->dict:
        return dict(self.__review)

    def admit(self,words:list[str])->dict:
        if self.__gate is None:
            return {'status':'ABSTAIN','reason':'Independent dual decoding or proof gate unavailable'}
        return self.__gate.admit(words)

    def reference_infer(self,words:list[str])->dict:
        if self.__gate is None:
            return {'status':'ABSTAIN','reason':'Independent dual decoding or proof gate unavailable'}
        return self.__gate.reference_infer(words)
