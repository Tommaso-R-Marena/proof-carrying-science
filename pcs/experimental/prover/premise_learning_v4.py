"""Checked trajectory intake and recoverable grounded imitation/RL updates.

Only explicit training tasks enter gradient updates. This module does not rank
or select checkpoints using final evaluation answers.
"""
from pathlib import Path
import hashlib
import json
import time
import torch
from .induction_ir import digest
from .premise_policy_v4 import PremisePolicy, save_training_checkpoint, load_training_checkpoint

ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def collect_checked_training(env, tasks, *, limit=6):
    """Recreate every observation/action option and independently check terminals."""
    if not tasks or any(t.get("split") != "train" for t in tasks):
        raise ValueError("evaluation firewall: only training tasks may be collected")
    for task in tasks:
        if task.get("license") not in {"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"}:
            raise ValueError("explicit licensed training provenance required")
        source = task.get("source")
        if type(source) is str:
            if not source or len(source) > 4096:
                raise ValueError("bounded nonempty training source required")
        elif type(source) is dict:
            required = {"repository", "module", "base_revision", "source_file", "source_sha256", "authorship"}
            forbidden = {"kernel", "verified", "checker_result", "authority", "success", "reward"}
            if not required <= set(source) or forbidden & set(source) or len(json.dumps(source)) > 16384:
                raise ValueError("bounded source provenance required, without checker claims")
            if any(type(source[key]) is not str or not source[key] for key in required):
                raise ValueError("explicit source identity fields required")
            for key, length in [("base_revision", 40), ("source_sha256", 64)]:
                if len(source[key]) != length or any(c not in "0123456789abcdef" for c in source[key]):
                    raise ValueError("exact source revision/digest required")
        else:
            raise ValueError("explicit licensed training provenance required")
    episodes = []
    for task in tasks:
        statement = task["statement"]
        state = env.start(statement)
        actions = []; records = []
        for action in task["actions"]:
            options = env.options(state, limit=limit)
            if action not in options:
                raise ValueError("training action outside receiver option set: " + str(action))
            observed = env.step(statement, actions, action)
            if not observed["valid"]:
                raise ValueError("invalid training action")
            records.append({"state": state, "options": options, "chosen": options.index(action), "action": action,
                            "next_state": observed["state"], "goal_sha256": digest(statement)})
            actions.append(action); state = observed["state"]
        if not records or state["goals"]:
            raise ValueError("training path does not close original theorem")
        first = env.verify(statement, actions)
        second = env.verify(statement, actions)
        stable = ["statement", "proof", "kernel", "goal_sha256", "catalog_sha256", "source_sha256"]
        if not first.get("kernel") or any(first.get(key) != second.get(key) for key in stable):
            raise ValueError("independent training replay differs")
        # Receipts are also retained intact: do not infer proof from this flag.
        episodes.append({"id": task["id"], "split": "train", "statement": statement,
                         "goal_sha256": digest(statement), "actions": actions, "records": records,
                         "receipt": first, "independent_receipt": second,
                         "source": task["source"], "license": task["license"]})
    return episodes


def transitions(episodes):
    result = []
    for episode in episodes:
        if episode.get("split") != "train" or not episode.get("independent_receipt"):
            raise ValueError("only checked training episodes may enter imitation")
        for index, record in enumerate(episode["records"]):
            if record["action"] != record["options"][record["chosen"]] or record["goal_sha256"] != episode["goal_sha256"]:
                raise ValueError("training action/goal binding differs")
            result.append((record["state"], record["options"], record["chosen"], len(episode["records"]) - index))
    if not result:
        raise ValueError("no verified training transitions")
    return result


def train_supervised(model, episodes, *, epochs=20, seed=71, optimizer=None, start_epoch=0, restore_rng=False):
    if type(epochs) is not int or type(start_epoch) is not int or not 0 <= start_epoch < epochs <= 1000:
        raise ValueError("bounded nonempty training epoch interval required")
    examples = transitions(episodes)
    if not restore_rng:
        torch.manual_seed(seed)
    elif optimizer is None:
        raise ValueError("RNG/optimizer resume must be explicit")
    optimizer = optimizer or torch.optim.Adam(model.parameters(), lr=.003)
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    started = time.monotonic(); losses = []
    model.train()
    for epoch in range(start_epoch, epochs):
        total = 0.
        for index in torch.randperm(len(examples)).tolist():
            state, options, label, remaining = examples[index]
            logits, value, uncertainty = model(state, options)
            loss = torch.nn.functional.cross_entropy(logits[None], torch.tensor([label], device=logits.device))
            loss = loss + .03 * (value - 1 / remaining).square() + .01 * uncertainty.square()
            optimizer.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
            total += float(loss.detach())
        losses.append(total / len(examples))
    return optimizer, {"examples": len(examples), "epochs_completed": epochs - start_epoch, "next_epoch": epochs,
                       "seed": seed, "losses": losses, "wall_seconds": time.monotonic() - started,
                       "changed_parameters": [n for n, p in model.named_parameters() if not torch.equal(p.detach(), before[n])],
                       "training_data_sha256": digest(episodes)}


class MathlibRLEnvironment:
    """Versioned sequential adapter; rewards are reconstructed from real Lean."""
    def __init__(self, env, *, limit=6, max_steps=16):
        if type(max_steps) is not int or not 1 <= max_steps <= 24 or type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("bounded real Lean episode limits required")
        self.env, self.limit, self.max_steps = env, limit, max_steps
        self.goal = None
        self.actions = []
        self.state = None
        self.done = True
        self.steps = 0

    def reset(self, statement):
        self.goal = statement; self.goal_sha256 = digest(statement)
        self.actions = []; self.steps = 0; self.state = self.env.start(statement); self.done = False
        return self.state

    def candidates(self):
        if self.done:
            raise ValueError("terminal RL episode")
        return self.env.options(self.state, limit=self.limit)

    def step(self, action):
        if self.done or digest(self.goal) != self.goal_sha256:
            raise ValueError("terminal or changed RL theorem")
        options = self.candidates()
        if action not in options:
            raise ValueError("action outside receiver grammar")
        previous_goals = len(self.state["goals"])
        self.steps += 1
        try:
            observed = self.env.step(self.goal, self.actions, action)
        except RuntimeError as error:
            self.done = True
            return self.state, -.2, True, {"status": "resource_exhaustion", "receipt": None, "error": str(error)[-1000:]}
        receipt = None
        if observed["valid"]:
            self.actions.append(action); self.state = observed["state"]
            if observed["closed"]:
                self.done = True
                try:receipt = self.env.verify(self.goal, self.actions)
                except RuntimeError as error:
                    return self.state, -.2, True, {"status":"verification_failed","receipt":None,"error":str(error)[-1000:]}
        if not observed["valid"]:
            self.done = True
        exhausted = self.steps >= self.max_steps
        self.done = self.done or exhausted
        reward = 1.0 if receipt is not None else (-.2 if not observed["valid"] else -.015 + .02 * max(0, previous_goals - len(self.state["goals"])))
        status = "verified" if receipt is not None else "invalid" if not observed["valid"] else "exhausted" if exhausted else "open"
        return self.state, reward, self.done, {"status": status, "receipt": receipt, "error": observed.get("error")}


def actor_critic(model, environment, tasks, *, episodes=8, seed=83, on_episode=None):
    if not tasks or type(episodes) is not int or not 1 <= episodes <= 64 or any(t.get("split") != "train" for t in tasks):
        raise ValueError("evaluation firewall: bounded RL may use training tasks only")
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=.0005)
    before = digest({k: v.detach().tolist() for k, v in model.state_dict().items()})
    started = time.monotonic(); results = []
    for index in range(episodes):
        task = tasks[index % len(tasks)]; state = environment.reset(task["statement"])
        logps, values, rewards, entropies, trace = [], [], [], [], []
        model.train()
        for _ in range(environment.max_steps):
            options = environment.candidates()
            logits, value, _ = model(state, options)
            distribution = torch.distributions.Categorical(logits=logits)
            selected = distribution.sample(); action = options[int(selected)]
            next_state, reward, done, response = environment.step(action)
            logps.append(distribution.log_prob(selected)); values.append(value); rewards.append(reward); entropies.append(distribution.entropy())
            trace.append({"state": state, "action": action, "reward": reward, "status": response["status"]})
            state = next_state
            if done:
                break
        replay=None
        if response['status']=='verified':
            try:replay=environment.env.verify(task['statement'],environment.actions)
            except RuntimeError as error:
                # Extra admission replay is eligibility, before the gradient.
                # Retain the primary proof but never train a positive label
                # when the declared independent gate could not finish.
                response={**response,'status':'independent_replay_failed','error':str(error)[-1000:]}
                rewards[-1]=-.2;trace[-1]['reward']=-.2;trace[-1]['status']=response['status']
        returns = []; total = 0.
        for reward in reversed(rewards):
            total = reward + .97 * total; returns.insert(0, total)
        loss = sum(-log * (value.new_tensor(ret) - value.detach()) + .5 * (value - ret).square() - .002 * entropy
                   for log, value, ret, entropy in zip(logps, values, returns, entropies)) / len(logps)
        optimizer.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
        results.append({"task": task["id"], "goal_sha256": digest(task["statement"]), "status": response["status"],
                        "trace": trace, "receipt": response["receipt"], "independent_receipt": replay, "error":response.get('error'), "loss": float(loss.detach())})
        if on_episode is not None:on_episode(model,optimizer,results)
    after = digest({k: v.detach().tolist() for k, v in model.state_dict().items()})
    return optimizer, {"algorithm": "sequential-actual-Mathlib-actor-critic-v4", "seed": seed,
                       "before": before, "after": after, "weights_changed": before != after,
                       "wall_seconds": time.monotonic() - started, "episodes": results}
