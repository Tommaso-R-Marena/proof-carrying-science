"""Authored numerical counterexamples and the admitted development-only workflow.

The tiny models and hand-computed answers are independent of the reconstruction
implementation. No final corpus source or reference annotation is used here.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from research.scientific_review_v4 import simulation as s
from research.scientific_review_v4 import workflow as w


def math(expression):
    return f'<math xmlns="{s.ML}">{expression}</math>'


def initial(symbol, expression):
    return f'<initialAssignment symbol="{symbol}">{math(expression)}</initialAssignment>'


def rule(symbol, expression):
    return f'<assignmentRule variable="{symbol}">{math(expression)}</assignmentRule>'


def model(*, assignments='', rules='', extra='', parameters='', concentration='1',
          rate='<apply><times/><ci>k</ci><ci>x</ci></apply>', k_constant='true'):
    return (f'<sbml xmlns="{s.NS}" level="2" version="4"><model id="m">'
            '<listOfCompartments><compartment id="c" size="1" constant="true"/></listOfCompartments>'
            f'<listOfSpecies><species id="x" compartment="c" initialConcentration="{concentration}" '
            'boundaryCondition="false" constant="false"/></listOfSpecies>'
            f'<listOfParameters><parameter id="k" value="1" constant="{k_constant}"/>'
            f'{parameters}</listOfParameters>'
            + (f'<listOfInitialAssignments>{assignments}</listOfInitialAssignments>' if assignments else '')
            + (f'<listOfRules>{rules}</listOfRules>' if rules else '')
            + extra + '<listOfReactions><reaction id="r" reversible="false">'
            '<listOfReactants><speciesReference species="x" stoichiometry="1"/></listOfReactants>'
            f'<kineticLaw>{math(rate)}</kineticLaw></reaction></listOfReactions>'
            '</model></sbml>').encode()


def project():
    config = {'format_version': 1, 'parameter_file': 'parameters.tsv', 'problems': [{
        'sbml_files': ['model.xml'], 'measurement_files': ['measurements.tsv'],
        'condition_files': ['conditions.tsv'], 'observable_files': ['observables.tsv']}]}
    return {
        'problem.json': json.dumps(config).encode(), 'model.xml': model(),
        'parameters.tsv': b'parameterId\tparameterScale\tlowerBound\tupperBound\tnominalValue\testimate\nk\tlin\t0\t10\t1\t1\n',
        'conditions.tsv': b'conditionId\ncondition\n',
        'observables.tsv': b'observableId\tobservableFormula\tnoiseFormula\nobs\tx\t1\n',
        'measurements.tsv': b'observableId\tsimulationConditionId\ttime\tmeasurement\nobs\tcondition\t0\t1\n',
    }


def test_parameter_initial_assignment_reaches_reaction_environment():
    runtime = s.ReactionRuntime(model(assignments=initial('k', '<cn>2</cn>')), {})
    assert runtime.parameters['k'] == 2
    assert runtime.environment(0, runtime.initial)['k'] == 2
    assert runtime.rhs(0, runtime.initial) == [-2]


def test_joint_initial_and_assignment_dependencies_exclude_stale_seed_values():
    raw = model(assignments=initial('k', '<cn>2</cn>') + initial('x', '<ci>q</ci>'),
                rules=rule('q', '<apply><times/><cn>2</cn><ci>k</ci></apply>'),
                parameters='<parameter id="q" value="1" constant="false"/>')
    runtime = s.ReactionRuntime(raw, {})
    assert runtime.initial == [4]
    assert runtime.environment(0, runtime.initial)['q'] == 4
    assert runtime.rhs(0, runtime.initial) == [-8]


def test_decimal80_initial_seed_retains_original_decimal_lexeme():
    literal = '1.0000000000000000000000000000000000000001'
    runtime = s.ReactionRuntime(model(concentration=literal), {})
    assert Decimal(runtime.initial_decimal80['x']) == Decimal(literal)


def test_decimal80_seed_uses_exact_amount_volume_fraction():
    raw = model().replace(b'size="1"', b'size="3"').replace(
        b'initialConcentration="1"', b'initialAmount="1"')
    runtime = s.ReactionRuntime(raw, {})
    with localcontext() as context:
        context.prec = 80
        assert Decimal(runtime.initial_decimal80['x']) == Decimal(1) / Decimal(3)


@pytest.mark.parametrize('literal,expected', [
    ('<cn>1.25</cn>', 1.25), ('<cn type="real" base="10">-2.5</cn>', -2.5),
    ('<cn type="integer">+2</cn>', 2), ('<cn type="rational">3<sep/>4</cn>', .75),
    ('<cn type="e-notation">1.25<sep/>2</cn>', 125),
])
def test_supported_mathml_constant_forms(literal, expected):
    assert s.math_value(ET.fromstring(math(literal)), {}) == expected


@pytest.mark.parametrize('literal', [
    '<cn base="2">10</cn>', '<cn type="hexdouble">12</cn>', '<cn units="second">1</cn>',
    '<cn type="integer">1.5</cn>', '<cn type="integer">1e2</cn>',
    '<cn type="rational">1</cn>', '<cn type="rational">1.2<sep/>2</cn>',
    '<cn type="rational">1<sep/>0</cn>', '<cn type="e-notation">2</cn>',
    '<cn type="e-notation">2<sep/>1.5</cn>', '<cn type="real">1<sep/>2</cn>',
    '<cn type="rational">1<sep/>2<sep/>3</cn>',
])
def test_unsupported_or_malformed_mathml_constants_fail_closed(literal):
    with pytest.raises((ValueError, ZeroDivisionError)):
        s.math_value(ET.fromstring(math(literal)), {})


@pytest.mark.parametrize('constant', ['true', None])
def test_original_assignment_parameter_must_be_mutable(constant):
    raw = model(rules=rule('k', '<cn>2</cn>'))
    if constant is None:
        raw = raw.replace(b' id="k" value="1" constant="true"', b' id="k" value="1"')
    with pytest.raises(ValueError):
        s.ReactionRuntime(raw, {})


def test_mutable_assignment_target_is_supported():
    runtime = s.ReactionRuntime(model(rules=rule('k', '<cn>2</cn>'), k_constant='false'), {})
    assert runtime.rhs(0, runtime.initial) == [-2]


def test_original_constant_species_cannot_acquire_assignment_semantics():
    raw = model(rules=rule('x', '<cn>2</cn>')).replace(
        b'boundaryCondition="false" constant="false"', b'boundaryCondition="false" constant="true"')
    with pytest.raises(ValueError):
        s.ReactionRuntime(raw, {})


@pytest.mark.parametrize('raw', [
    model(assignments=initial('x', '<cn>2</cn>') + initial('x', '<cn>3</cn>')),
    model(rules=rule('k', '<cn>2</cn>') + rule('k', '<cn>3</cn>'), k_constant='false'),
    model(assignments=initial('k', '<cn>2</cn>'), rules=rule('k', '<cn>3</cn>'), k_constant='false'),
])
def test_duplicate_or_conflicting_assignment_targets_are_unsupported(raw):
    with pytest.raises(ValueError):
        s.ReactionRuntime(raw, {})


@pytest.mark.parametrize('change', [
    lambda raw: raw.replace(b'<model id="m">', b'<model id="m"/><model id="other">'),
    lambda raw: raw.replace(b'<model id="m">', b'<model xmlns="urn:foreign" id="m">'),
    lambda raw: raw.replace(b'</model>', b'<listOfInitialAssignments/><listOfInitialAssignments/></model>'),
    lambda raw: raw.replace(b'</model>', b'<listOfRules/><listOfRules/></model>'),
    lambda raw: raw.replace(b'</model>', ('<listOfInitialAssignments xmlns="urn:foreign">'
        + initial('x', '<cn>2</cn>') + '</listOfInitialAssignments></model>').encode()),
    lambda raw: raw.replace(b'</model>', ('<listOfReactions><listOfInitialAssignments>'
        + initial('x', '<cn>2</cn>') + '</listOfInitialAssignments></listOfReactions></model>').encode()),
])
def test_model_container_namespace_count_and_semantic_placement_are_checked(change):
    with pytest.raises(ValueError):
        s.ReactionRuntime(change(model()), {})


@pytest.mark.parametrize('metadata', ['notes', 'annotation'])
def test_embedded_metadata_assignments_are_inert_or_rejected(metadata):
    raw = model(extra=f'<{metadata}><listOfInitialAssignments>{initial("x", "<cn>2</cn>")}'
                f'</listOfInitialAssignments></{metadata}>')
    try:
        runtime = s.ReactionRuntime(raw, {})
    except ValueError:
        return
    assert runtime.initial == [1]
    assert runtime.rhs(0, runtime.initial) == [-1]


def test_sbml_time_cannot_be_shadowed_by_named_parameter():
    expression = ('<apply><plus/><ci>__time__</ci>'
                  '<csymbol definitionURL="http://www.sbml.org/sbml/symbols/time">time</csymbol></apply>')
    runtime = s.ReactionRuntime(model(parameters='<parameter id="__time__" value="17" constant="true"/>',
                                    rules=rule('k', expression), k_constant='false'), {})
    assert runtime.environment(2, runtime.initial)['__time__'] == 17
    assert runtime.rhs(2, runtime.initial) == [-19]


@pytest.mark.parametrize('path', ['parameters.tsv', 'conditions.tsv', 'observables.tsv'])
def test_reconstruction_rejects_duplicate_declared_ids_before_dictionary_creation(path):
    files = project()
    files[path] += files[path].splitlines(keepends=True)[1]
    assert s.reconstruct(files)['status'] == 'UNKNOWN'


@pytest.mark.parametrize('column', ['typo', 'c'])
def test_unknown_or_compartment_condition_columns_do_not_silently_disappear(column):
    files = project()
    files['conditions.tsv'] = f'conditionId\t{column}\ncondition\t2\n'.encode()
    assert s.reconstruct(files)['status'] == 'UNKNOWN'


def test_external_noise_and_calibration_parameter_rows_do_not_override_model_symbols():
    files = project()
    files['parameters.tsv'] += b'extra_noise\tlin\t0\t10\t2\t1\ncalibration\tlin\t0\t10\t3\t1\n'
    result = s.reconstruct(files)
    assert result['status'] == 'REPRODUCED_COMPUTATION', result['evidence']


def test_compartment_parameter_override_is_explicitly_unsupported():
    files = project()
    files['parameters.tsv'] += b'c\tlin\t0.1\t10\t2\t1\n'
    assert s.reconstruct(files)['status'] == 'UNKNOWN'


@pytest.mark.parametrize('scale', ['log', 'log10'])
def test_log_scale_parameters_require_positive_untransformed_bounds_and_nominal(scale):
    files = {'parameters.tsv': ('parameterId\tparameterScale\tlowerBound\tupperBound\tnominalValue\n'
                               f'k\t{scale}\t-1\t2\t1\n').encode()}
    check, = [value for value in w.analyze(files)['checks'] if value['checker'] == 'parameter_domain']
    assert check['checker'] == 'parameter_domain'
    assert check['status'] == 'REFUTED'


def test_exact_rss_survives_binary64_projection_overflow():
    large = w.number('9' * 91 + 'e64')
    result = w.residual_statistics([{'measurement': large, 'simulation': Fraction(0),
                                    'row': {'observableId': 'obs', 'simulationConditionId': 'c'}}])
    assert Fraction(result['rss_exact']) == large * large
    assert result['rss_float'] is None
    assert result['rss_float_projection']['status'] == 'OUT_OF_RANGE'


def test_prediction_join_uses_metadata_and_not_row_position():
    base = {'observableId': 'obs', 'simulationConditionId': 'c', 'time': '1'}
    measurements = [{**base, 'datasetId': 'first', 'measurement': '2'},
                    {**base, 'datasetId': 'second', 'measurement': '5'}]
    predictions = [{**base, 'datasetId': 'second', 'simulation': '4'},
                   {**base, 'datasetId': 'first', 'simulation': '2'}]
    pairs, columns = w.join_predictions(measurements, predictions)
    assert 'datasetId' in columns
    assert [pair['simulation'] for pair in pairs] == [2, 4]
    assert w.residual_statistics(pairs)['rss_exact'] == '1'


def test_distinct_predictions_with_identical_complete_identity_are_ambiguous():
    base = {'observableId': 'obs', 'simulationConditionId': 'c', 'time': '1', 'datasetId': 'd'}
    with pytest.raises(ValueError):
        w.join_predictions([{**base, 'measurement': '2'}],
                           [{**base, 'simulation': '2'}, {**base, 'simulation': '3'}])


def development_files():
    directory = Path(__file__).parents[1] / 'fixtures/development/fiedler2016/petab/v1'
    return {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}


def test_admitted_development_provided_prediction_rss_is_exact():
    checks = w.analyze(development_files())['checks']
    result, = [check for check in checks if check['checker'] == 'provided_prediction_residuals']
    assert result['status'] == 'REPRODUCED_COMPUTATION'
    assert result['evidence']['observations'] == 72
    assert result['evidence']['rss_exact'] == (
        '40814069238626533672588417454406577989/'
        '4000000000000000000000000000000000000')
    assert result['evidence']['simulation_reexecution'] == 'NOT_PERFORMED'


def test_admitted_development_source_is_actually_reconstructed_with_two_solvers():
    files = development_files()
    result = s.reconstruct(files)
    assert result['status'] == 'REPRODUCED_COMPUTATION', result['evidence']
    evidence = result['evidence']
    assert evidence['measurements'] == 72
    assert len(evidence['conditions']) == 3
    assert evidence['maximum_observable_solver_difference'] < 1e-5
    assert evidence['provided_prediction_max_absolute_difference'] < 1e-5
    assert all(set(condition['rhs_calls']) == {'Radau', 'BDF'} for condition in evidence['conditions'])
    assert all(min(condition['rhs_calls'].values()) > 0 for condition in evidence['conditions'])
    assert all(len(condition['structural_projection_sha256']) == 64 for condition in evidence['conditions'])
    assert any(source['path'] == 'model.xml' and source['sha256'] == hashlib.sha256(files['model.xml']).hexdigest()
               for source in result['sources'])
    assert evidence['Python_SBML_refinement'] == 'OPEN'
    assert result['scientific_meaning'] == 'OPEN'
    assert result['empirical_validity'] == 'NOT_ESTABLISHED'
