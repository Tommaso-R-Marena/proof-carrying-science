"""Authored toy scientific retrieval data; no repository scientific source inputs.

Template families are allocated before example generation. Test families 10/11
are never used for vocabulary construction, optimization, or model selection.
"""
from __future__ import annotations

import hashlib
import json

KINDS = ("initial", "rate", "units", "objective", "result", "uncertainty")
SPLIT_FAMILIES = {"train": list(range(8)), "validation": [8, 9], "test": [10, 11]}

# Each column is an independently authored paired wording family, not a random
# partition of expansions of one template. All six intents occur in each family.
QUERY = {
"initial": "What amount does {e} start with?|Give the initial value for {e}.|What is the starting state of {e}?|How much {e} is present at time zero?|For {e}, identify the beginning amount.|Find the boundary value before {e} evolves.|What initial condition is assigned to {e}?|Which value seeds the trajectory of {e}?|Before evolution, how large is {e}?|What does the {e} trajectory begin at?|Which abundance was used to initialize {e}?|Recover the pre-evolution level for {e}.",
"rate": "How quickly does {e} change?|Give the rate law for {e}.|Which equation governs {e} over time?|How is the derivative of {e} defined?|For {e}, identify the evolution rule.|Find the kinetic relationship driving {e}.|What differential equation describes {e}?|Which formula determines the change in {e}?|What dynamics drive the motion of {e}?|How is the time variation of {e} calculated?|Recover the governing kinetics for {e}.|What expression gives the instantaneous slope of {e}?",
"units": "What units measure {e}?|Give the measurement units for {e}.|Which physical dimensions belong to {e}?|How is the scale of {e} expressed?|For {e}, identify the unit convention.|Find the dimensional label attached to {e}.|What unit is assigned to values of {e}?|Which measurement scale describes {e}?|How should a magnitude of {e} be labeled?|What dimensional convention applies to {e}?|Recover the dimensional annotation for {e}.|Which units accompany reported {e} values?",
"objective": "What loss is minimized for {e}?|Give the objective equation for {e}.|Which cost function is optimized for {e}?|How is the fitting target for {e} defined?|For {e}, identify the minimization criterion.|Find the optimization functional used for {e}.|What error measure is minimized for {e}?|Which formula scores the fit of {e}?|How is the penalty for fitting {e} calculated?|What scalar criterion guides the fit of {e}?|Recover the least squares expression for {e}.|What mathematical target is minimized when fitting {e}?",
"result": "What value was computed for {e}?|Give the numerical result for {e}.|Which final estimate was obtained for {e}?|What number did the solver report for {e}?|For {e}, identify the estimated endpoint.|Find the terminal numerical output for {e}.|What measured outcome is reported for {e}?|Which computed value summarizes {e}?|How large was {e} after the simulation?|What endpoint did the calculation return for {e}?|Recover the reported numerical outcome for {e}.|What value emerged from the calculation of {e}?",
"uncertainty": "What uncertainty and conditions apply to {e}?|Give the error range and conditions for {e}.|Which confidence bounds accompany {e}?|How precise is {e} under the stated conditions?|For {e}, identify the uncertainty interval.|Find the error bar and temperature for {e}.|What confidence interval is reported for {e}?|Which limits and conditions qualify {e}?|How much variability surrounds {e} at the test temperature?|What interval and operating conditions constrain {e}?|Recover the precision interval and measurement conditions for {e}.|Which confidence limits qualify the {e} estimate?",
}
SOURCE = {
"initial": "Initial condition for {e}: x(0) = {v}.|The starting amount of {e} is {v}.|At time zero, {e} has value {v}.|The trajectory of {e} begins with x0 = {v}.|Before evolution the {e} state is initialized to {v}.|Boundary data for {e}: initial value {v}.|The seed state used for {e} equals {v}.|The beginning condition of {e} is x(0) = {v}.|At the origin of time, {e} is set to {v}.|The prescribed initial magnitude of {e} is {v}.|Initialization sets the abundance of {e} to {v}.|The pre-evolution level of {e} was fixed at {v}.",
"rate": "Rate law for {e}: dx/dt = -{k} x.|The dynamics of {e} obey dx/dt = -{k} x.|Evolution equation for {e}: xprime = -{k} x.|The derivative of {e} is -{k} times its current value.|The kinetic equation driving {e} is dx/dt = -{k} x.|Time change in {e} follows xprime = -{k} x.|The governing differential law of {e} is dx/dt = -{k} x.|Instantaneous change of {e} is -{k} x.|For {e}, the time-dependent evolution satisfies dx/dt = -{k} x.|The motion rule for {e} specifies xprime = -{k} x.|The kinetics governing {e} satisfy dx/dt = -{k} x.|The instantaneous slope for {e} is -{k} times the current abundance.",
"units": "Units for {e} are millimoles per liter.|The measurement scale of {e} is mmol/L.|Values of {e} have concentration dimensions, mmol per liter.|The unit convention used for {e} is millimolar.|A magnitude of {e} is expressed in mmol L^-1.|The dimensional label of {e} is millimoles/liter.|The assigned unit of {e} is mmol/L.|Concentration of {e} is recorded in millimolar units.|The dimensional convention for {e} is mmol L^-1.|Measured {e} carries the label millimoles per liter.|The dimensional annotation attached to {e} is mmol/L.|Reported values of {e} are accompanied by millimolar concentration units.",
"objective": "Objective for {e}: minimize J = sum (prediction-observation)^2.|The fitting loss for {e} is the sum of squared residuals.|Cost function of {e}: J = sum (xhat-xobs)^2.|The target minimized for {e} is squared prediction error.|Optimization of {e} minimizes J = sum residual^2.|The optimization functional for {e} sums squared deviations.|The error criterion for {e} is sum (estimate-measurement)^2.|The formula scoring the fit of {e} is least squares.|The fitting penalty of {e} equals sum (xmodel-xdata)^2.|The scalar fit criterion for {e} is residual sum of squares.|For {e}, the least squares expression is J = sum (xhat-xobs)^2.|Fitting {e} minimizes the sum of squared prediction residuals.",
"result": "Numerical result for {e}: final estimate = {r}.|The solver computed {e} = {r} at the endpoint.|The final predicted value of {e} is {r}.|Numerical output reports {e} as {r}.|The estimated endpoint of {e} equals {r}.|Terminal calculation for {e} returns {r}.|The measured outcome of {e} is {r}.|The computed summary value for {e} is {r}.|After simulation, the magnitude of {e} was {r}.|The calculation returned endpoint {r} for {e}.|The reported numerical outcome for {e} equals {r}.|The value emerging from the calculation of {e} was {r}.",
"uncertainty": "Uncertainty for {e}: 95 percent interval [{lo}, {hi}] at 298 K.|Error range for {e} is [{lo}, {hi}], with temperature 298 K.|Confidence bounds for {e} are [{lo}, {hi}] under 298 K conditions.|Precision statement for {e}: 95 percent interval [{lo}, {hi}] at 298 K.|The uncertainty interval of {e} is [{lo}, {hi}] at temperature 298 K.|The error bar of {e} spans [{lo}, {hi}] at 298 K.|A confidence interval [{lo}, {hi}] qualifies {e} at 298 K.|The limits of {e} are [{lo}, {hi}] with operating temperature 298 K.|Variability around {e} spans [{lo}, {hi}] under the 298 K test.|The interval constraining {e} is [{lo}, {hi}] at 298 K.|Measurement precision for {e} is bounded by [{lo}, {hi}] at 298 K.|Confidence limits [{lo}, {hi}] qualify the estimate of {e} at 298 K.",
}


def build_benchmark():
    result = {}
    nouns = ["enzyme", "reactor", "population", "crystal", "fluid", "beam",
             "cell", "gas", "polymer", "sensor", "culture", "reservoir"]
    for split, families in SPLIT_FAMILIES.items():
        docs, queries = [], []
        for family in families:
            for system in range(2):
                entity = nouns[family] + (" alpha" if system == 0 else " beta")
                vals = dict(e=entity, v=2+family+system, k=0.1+system/10,
                            r=round(0.31+family/100+system/10, 2), lo=0.2+system/10, hi=0.5+system/10)
                for kind in KINDS:
                    ident = f"f{family}-{system}-{kind}"
                    docs.append({"id": ident, "text": SOURCE[kind].split("|")[family].format(**vals),
                                 "kind": kind, "family": family})
                    queries.append({"id": "q-"+ident, "text": QUERY[kind].split("|")[family].format(**vals),
                                    "positive_id": ident, "family": family, "kind": kind})
        # Every model receives this exact entire split source pool in this order.
        result[split] = {"queries": queries, "candidates": docs}
    return result


def dataset_sha256(data=None):
    raw = json.dumps(data or build_benchmark(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
