"""Exploratory training-only covariance diagnostic; never a held-out evaluation.

The primary experiment is unchanged. This module adds 0.48 to the existing 0.02
JEPA covariance coefficient, fits the same training examples, and measures only
training embeddings. It launches no Lean process and grants no proof authority.
The caller trusts the provenance of the local training archive/checkpoints;
recomputed hashes do not establish independent custody or validate their labels.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import torch

from pcs.jsonio import strict_json_loads
from .experiment import configure, fit
from .model import ProofJEPA

BASE_COVARIANCE_COEFFICIENT = .02
EXTRA_COVARIANCE_COEFFICIENT = .48
MAX_TRAINING_BYTES = 64_000_000


class CovarianceDiagnostic(ProofJEPA):
    """Same model/predictive objective, with the explicit extra regularizer."""

    def predictive_loss(self, transitions, proof_guided=False):
        loss = super().predictive_loss(transitions, proof_guided=proof_guided)
        if len(transitions) > 1:
            z = torch.stack([self.encode(record['state']) for record in transitions])
            centered = z - z.mean(0)
            covariance = centered.T @ centered / (len(transitions) - 1)
            offdiagonal = covariance - torch.diag(torch.diagonal(covariance))
            loss = loss + EXTRA_COVARIANCE_COEFFICIENT * offdiagonal.square().sum() / self.width
        return loss


@torch.no_grad()
def embedding_statistics(model, records):
    """Finite observed statistics, not a general non-collapse guarantee."""
    if len(records) < 2:
        raise ValueError('at least two completed-proof training states required')
    z = torch.stack([model.encode(record['state']) for record in records])
    centered = z - z.mean(0)
    covariance = centered.T @ centered / (len(z) - 1)
    offdiagonal = covariance - torch.diag(torch.diagonal(covariance))
    return {
        'states': len(records),
        'embedding_mean_std': float(z.std(0, unbiased=False).mean()),
        'participation_dimension': float(torch.trace(covariance).square() /
                                         (covariance.square().sum() + 1e-12)),
        'off_diagonal_covariance_penalty': float(offdiagonal.square().sum() / model.width),
    }


def run(run_directory, output, *, seeds=(17, 31), epochs=6):
    """Read only training.json.gz and specified JEPA baseline checkpoints.

    No task/test/results/selection file is read. No checkpoint is written,
    selected, promoted or tested. This diagnostic is outside the primary seven
    methods. Results are exploratory even when regularization increases rank.
    """
    root, output = Path(run_directory), Path(output)
    if output.exists():
        raise ValueError('refuse diagnostic evidence overwrite')
    if (not seeds or len(set(seeds)) != len(seeds) or
            any(type(seed) is not int or not 0 <= seed < 2**31 for seed in seeds) or
            type(epochs) is not int or not 1 <= epochs <= 200):
        raise ValueError('invalid bounded diagnostic configuration')
    training_path = root / 'training.json.gz'
    with gzip.open(training_path, 'rb') as stream:
        raw = stream.read(MAX_TRAINING_BYTES + 1)
    if len(raw) > MAX_TRAINING_BYTES:
        raise ValueError('training archive exceeds decompressed byte bound')
    corpus = strict_json_loads(raw.decode('utf-8'))
    if (type(corpus) is not dict or corpus.get('format') != 'pcs-proof-jepa-transition-corpus-v1'
            or corpus.get('authority') != 'NONE'):
        raise ValueError('unsupported training archive')
    records = corpus['transitions']
    if not records or any(record.get('split') != 'train' for record in records):
        raise ValueError('evaluation firewall: training transitions only')
    positive = [record for record in records if record.get('kernel_completed') is True]
    if len(positive) < 2:
        raise ValueError('insufficient completed-proof training states')
    results = []
    for seed in seeds:
        file = root / f'jepa-{seed}.json'
        # Expected digests here come from trusted local artifacts, not an
        # independent authority. The loader still rejects malformed weights.
        checkpoint_sha = hashlib.sha256(file.read_bytes()).hexdigest()
        baseline = ProofJEPA.load(file, checkpoint_sha)
        baseline_statistics = embedding_statistics(baseline, positive)
        configure(seed)
        candidate = CovarianceDiagnostic(width=baseline.width)
        training = fit(candidate, records, 'jepa', seed=seed, epochs=epochs)
        result = {
            'seed': seed, 'epochs': epochs,
            'baseline_checkpoint_sha256': checkpoint_sha,
            'baseline': baseline_statistics,
            'boosted': embedding_statistics(candidate, positive),
            'training': training,
        }
        results.append(result)
        print(json.dumps({'seed': seed, 'baseline': result['baseline'],
                          'boosted': result['boosted']}), flush=True)
    report = {
        'format': 'pcs-proof-jepa-training-decorrelation-diagnostic-v1',
        'authority': 'NONE',
        'primary_experiment_changed': False,
        'heldout_or_validation_data_used': False,
        'checkpoint_written_or_promoted': False,
        'base_covariance_coefficient': BASE_COVARIANCE_COEFFICIENT,
        'extra_covariance_coefficient': EXTRA_COVARIANCE_COEFFICIENT,
        'boosted_covariance_coefficient': BASE_COVARIANCE_COEFFICIENT + EXTRA_COVARIANCE_COEFFICIENT,
        'training_archive_sha256': hashlib.sha256(training_path.read_bytes()).hexdigest(),
        'training_states': len(positive), 'results': results,
        'source_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ('decorrelation.py', 'experiment.py', 'model.py')},
        'limitations': [
            'Exploratory training-only diagnostic outside the primary seven-method benchmark.',
            'Training labels and baseline artifact provenance are trusted local inputs, not freshly kernel-replayed here.',
            'Covariance participation dimension is an empirical finite-sample statistic, not semantic quality or a proof of non-collapse.',
            'No validation or held-out performance is measured; no generalization improvement is established.',
        ],
    }
    # Exclusive creation also protects against a concurrent output writer.
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=[17, 31])
    parser.add_argument('--epochs', type=int, default=6)
    args = parser.parse_args()
    run(args.run_directory, args.output, seeds=tuple(args.seeds), epochs=args.epochs)


if __name__ == '__main__':
    main()
