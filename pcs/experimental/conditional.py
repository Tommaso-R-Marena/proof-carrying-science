"""Bounded, assumption-aware Boolean reasoning using reduced ordered BDDs.

This experimental checker is not registered PCS scientific authority. It gives
exact results within explicit Boolean interpretations, or a resource-limit result.
"""
from copy import deepcopy
import hashlib
import re

from pcs.canonical_json import canonicalize_jcs_bytes

TASK = 'pcs-conditional-boolean-task-v1'
RECEIPT = 'pcs-conditional-boolean-receipt-v1'
OPS = {'atom', 'true', 'false', 'not', 'and', 'or', 'implies'}
RESERVED = {'AND', 'OR', 'NOT', 'IMPLIES', 'TRUE', 'FALSE'}
MAX_VARIABLES, MAX_FORMULA_NODES, MAX_DEPTH = 24, 128, 12
DEFAULT_LIMITS = {'nodes': 4096, 'operations': 100000}


def digest(value):
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError('Unexpected conditional protocol fields')
    return value


def validate(value):
    exact(value, {'format', 'variables', 'source', 'candidate', 'assumptions'})
    names = value['variables']
    if value['format'] != TASK or type(names) is not list or len(names) > MAX_VARIABLES:
        raise ValueError('Declare at most 24 Boolean variables')
    if any(type(n) is not str or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,15}', n) or n in RESERVED for n in names):
        raise ValueError('Use uppercase Boolean names; logical keywords are reserved')
    if names != sorted(set(names)):
        raise ValueError('Variable names must be distinct and sorted')
    premises = value['assumptions']
    if type(premises) is not list or len(premises) > 8:
        raise ValueError('Declare at most eight assumptions')
    for formula in [value['source'], value['candidate'], *premises]:
        count = 0
        def visit(node, depth):
            nonlocal count
            count += 1
            if count > MAX_FORMULA_NODES or depth > MAX_DEPTH:
                raise ValueError('Formula complexity bound exceeded')
            if type(node) is not dict or type(node.get('op')) is not str or node['op'] not in OPS:
                raise ValueError('Unsupported Boolean formula')
            op = node['op']
            exact(node, {'op', 'symbol', 'args'} if op == 'atom' else {'op', 'body'} if op == 'not' else {'op', 'left', 'right'} if op in {'and', 'or', 'implies'} else {'op'})
            if op == 'atom' and (node['symbol'] not in names or type(node['args']) is not list or node['args']):
                raise ValueError('Unknown variable or nonzero arity')
            if op == 'not': visit(node['body'], depth + 1)
            elif op in {'and', 'or', 'implies'}:
                visit(node['left'], depth + 1); visit(node['right'], depth + 1)
        visit(formula, 0)
    return value


def evaluate(formula, assignment):
    op = formula['op']
    if op == 'atom': return assignment[formula['symbol']]
    if op in {'true', 'false'}: return op == 'true'
    if op == 'not': return not evaluate(formula['body'], assignment)
    a, b = evaluate(formula['left'], assignment), evaluate(formula['right'], assignment)
    return a and b if op == 'and' else a or b if op == 'or' else not a or b


class ResourceLimit(Exception):
    pass


class Diagram:
    def __init__(self, names, limits):
        self.names, self.limits = names, limits
        self.nodes, self.unique, self.memo = [], {}, {}
        self.operations = self.visits = self.witness_steps = 0

    def node(self, var, low, high):
        if low == high: return low
        key = (var, low, high)
        if key in self.unique: return self.unique[key]
        if len(self.nodes) >= self.limits['nodes']: raise ResourceLimit('nodes')
        result = len(self.nodes) + 2
        self.nodes.append(list(key)); self.unique[key] = result
        return result

    def apply(self, op, a, b):
        if self.operations >= self.limits['operations']: raise ResourceLimit('operations')
        self.operations += 1
        if a > b: a, b = b, a  # All three internal operations are commutative.
        key = (op, a, b)
        if key in self.memo: return self.memo[key]
        if a < 2 and b < 2:
            result = int(a and b) if op == 'and' else int(a or b) if op == 'or' else int(a != b)
        else:
            av = self.nodes[a-2][0] if a >= 2 else len(self.names)
            bv = self.nodes[b-2][0] if b >= 2 else len(self.names)
            var = min(av, bv)
            al, ah = self.nodes[a-2][1:] if av == var else (a, a)
            bl, bh = self.nodes[b-2][1:] if bv == var else (b, b)
            low = self.apply(op, al, bl); high = self.apply(op, ah, bh)
            result = self.node(var, low, high)
        self.memo[key] = result
        return result

    def compile(self, formula):
        self.visits += 1
        op = formula['op']
        if op == 'atom': return self.node(self.names.index(formula['symbol']), 0, 1)
        if op in {'true', 'false'}: return int(op == 'true')
        if op == 'not': return self.apply('xor', self.compile(formula['body']), 1)
        a = self.compile(formula['left']); b = self.compile(formula['right'])
        if op == 'implies': return self.apply('or', self.apply('xor', a, 1), b)
        return self.apply(op, a, b)

    def conjunction(self, roots):
        result = 1
        for root in roots: result = self.apply('and', result, root)
        return result

    def world(self, root):
        if root == 0: return None
        values = dict.fromkeys(self.names, False)
        while root >= 2:
            self.witness_steps += 1
            var, low, high = self.nodes[root-2]
            values[self.names[var]] = low == 0
            root = high if low == 0 else low
        assert root == 1
        return values

    def work(self):
        return {'bdd_nodes': len(self.nodes), 'apply_calls': self.operations,
                'ast_visits': self.visits, 'witness_steps': self.witness_steps}


def check(value, limits=None):
    value = validate(deepcopy(value))
    limits = deepcopy(DEFAULT_LIMITS if limits is None else limits)
    exact(limits, {'nodes', 'operations'})
    for field in limits:
        if type(limits[field]) is not int or not 1 <= limits[field] <= DEFAULT_LIMITS[field]:
            raise ValueError('Invalid symbolic work limit')
    manager = Diagram(value['variables'], limits)
    result = {'format': RECEIPT, 'checker': 'pcs-conditional-bdd/1', 'original_task': value,
              'task_sha256': digest(value), 'limits': limits, 'decision': None,
              'context_example': None, 'counterexample': None, 'unsat_core': None,
              'core_necessity_witnesses': None, 'diagram': None, 'limit_reached': None,
              'scope': 'Declared Boolean interpretations and explicit assumptions only',
              'pcs_authority': False, 'lean_kernel_checked': False}
    try:
        premises = []; context = 1
        for formula in value['assumptions']:
            premises.append(manager.compile(formula))
            context = manager.apply('and', context, premises[-1])
            if context == 0: break
        source = candidate = difference = None
        if context == 0:
            core = list(range(len(premises)))
            for i in list(core):
                remaining = [j for j in core if j != i]
                if manager.conjunction([premises[j] for j in remaining]) == 0: core = remaining
            necessities = []
            for i in core:
                world = manager.world(manager.conjunction([premises[j] for j in core if j != i]))
                assert world is not None
                necessities.append({'removed_assumption': i, 'assignment': world})
            result.update(decision='inconsistent_assumptions', unsat_core=core, core_necessity_witnesses=necessities)
        else:
            source = manager.compile(value['source']); candidate = manager.compile(value['candidate'])
            difference = manager.apply('and', context, manager.apply('xor', source, candidate))
            result['context_example'] = manager.world(context)
            world = manager.world(difference)
            if world is None: result['decision'] = 'equivalent_under_assumptions'
            else:
                truths = [evaluate(f, world) for f in value['assumptions']]
                a, b = evaluate(value['source'], world), evaluate(value['candidate'], world)
                assert all(truths) and a != b
                result.update(decision='counterexample', counterexample={'assignment': world,
                              'source_true': a, 'candidate_true': b, 'assumptions_true': truths})
        result['diagram'] = {'nodes': manager.nodes, 'source': source, 'candidate': candidate,
                             'context': context, 'difference': difference}
    except ResourceLimit as error:
        # Partial work never becomes an accepted result or contradictory context.
        for field in ['context_example', 'counterexample', 'unsat_core', 'core_necessity_witnesses', 'diagram']:
            result[field] = None
        result.update(decision='resource_limit', limit_reached=str(error))
    result['work'] = manager.work()
    result['receipt_sha256'] = digest(result)
    return result


def verify(receipt):
    receipt = deepcopy(receipt)
    if type(receipt) is not dict or 'original_task' not in receipt or 'limits' not in receipt:
        raise ValueError('Invalid conditional receipt')
    if digest(receipt) != digest(check(receipt['original_task'], receipt['limits'])):
        raise ValueError('Forged, stale or mismatched conditional receipt')
    return receipt['decision']


def parse_formula(text):
    if type(text) is not str or len(text.encode('utf-8')) > 4096:
        raise ValueError('Formula exceeds text budget')
    tokens = []; pos = 0
    while pos < len(text):
        if text[pos].isspace(): pos += 1; continue
        m = re.match(r'->|&&|\|\||[()!&|]|[A-Za-z][A-Za-z0-9_]*', text[pos:])
        if not m: raise ValueError('Invalid formula token at character ' + str(pos+1))
        token = m.group(); pos += len(token)
        token = {'&&':'AND', '&':'AND', '||':'OR', '|':'OR', '!':'NOT', '->':'IMPLIES'}.get(token, token)
        if token.upper() in RESERVED: token = token.upper()
        tokens.append(token)
        if len(tokens) > 512: raise ValueError('Formula token budget exceeded')
    index = 0
    def peek(): return tokens[index] if index < len(tokens) else None
    def take():
        nonlocal index
        token = peek(); index += 1; return token
    def balanced(op, items):
        if len(items) == 1: return items[0]
        middle = len(items)//2
        return {'op':op, 'left':balanced(op,items[:middle]), 'right':balanced(op,items[middle:])}
    def unary(depth):
        if depth > 32: raise ValueError('Formula nesting budget exceeded')
        token = take()
        if token == 'NOT': return {'op':'not', 'body':unary(depth+1)}
        if token == '(':
            node = implication(depth+1)
            if take() != ')': raise ValueError('Expected a closing parenthesis')
            return node
        if token in {'TRUE','FALSE'}: return {'op':token.lower()}
        if token is None or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,15}',token) or token in RESERVED:
            raise ValueError('Expected an uppercase variable, TRUE, FALSE or parenthesis')
        return {'op':'atom','symbol':token,'args':[]}
    def conjunction(depth):
        items = [unary(depth)]
        while peek() == 'AND': take(); items.append(unary(depth))
        return balanced('and',items)
    def disjunction(depth):
        items = [conjunction(depth)]
        while peek() == 'OR': take(); items.append(conjunction(depth))
        return balanced('or',items)
    def implication(depth):
        if depth > 32: raise ValueError('Formula nesting budget exceeded')
        node = disjunction(depth)
        if peek() == 'IMPLIES':
            take(); node = {'op':'implies','left':node,'right':implication(depth+1)}
        return node
    result = implication(0)
    if index != len(tokens): raise ValueError('Unexpected trailing formula token')
    return result


def from_text(source, candidate, assumptions=''):
    if type(assumptions) is not str or len(assumptions.encode('utf-8')) > 32768:
        raise ValueError('Assumption text exceeds byte budget')
    lines = [line.strip() for line in assumptions.splitlines() if line.strip()]
    if len(lines) > 8: raise ValueError('Declare at most eight assumptions, one per line')
    s, c, premises = parse_formula(source), parse_formula(candidate), [parse_formula(line) for line in lines]
    names = set()
    def collect(node):
        if node['op'] == 'atom': names.add(node['symbol'])
        elif node['op'] == 'not': collect(node['body'])
        elif node['op'] in {'and','or','implies'}: collect(node['left']); collect(node['right'])
    for f in [s,c,*premises]: collect(f)
    return validate({'format': TASK,'variables':sorted(names),'source':s,'candidate':c,'assumptions':premises})
