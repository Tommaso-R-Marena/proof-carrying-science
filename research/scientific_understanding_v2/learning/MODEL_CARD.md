This component ranks scientific source text for a question. Scores describe
source relevance only. They do not establish semantic correctness, entailment,
numerical validity, or checker authority.

The hypothesis was that a small nonlinear encoder trained on authored scientific
query/source wording pairs could outperform strong lexical retrieval on new
wording families. The untouched authored test gives a negative result:

| Method | Top 1 | MRR |
| --- | ---: | ---: |
| BM25 (k1=1.5, b=0.75) | 1.0000 | 1.0000 |
| Sublinear TFIDF cosine | 1.0000 | 1.0000 |
| Learned encoder | 0.7083 | 0.7935 |
| Identical model, shuffled training labels | 0.4167 | 0.5544 |

The 24 test questions each rank the same 24 test sources. The shuffled control
retains character overlap and shared query/source text structure; its scores are
not an estimate of uniform random ranking. Per-query ranks, full train and
validation results, timing, and artifact hashes are in `artifacts/evaluation.json`.
The test is deliberately small and relatively easy for lexical retrieval.
No statistical significance or publication-source transfer claim follows.

All 144 pairs were authored in `synthetic_benchmark.py`. Twelve paired wording
families were assigned to train (0–7, 96 pairs), validation (8–9, 24 pairs), and
test (10–11, 24 pairs) before surface generation. Each family covers initial
conditions, rate laws, units, objective equations, numerical results, and
uncertainty/conditions for two invented systems. Each split uses its entire
source pool as candidates, in the same order for all methods; ties use input
order. Family IDs, candidate kinds, and candidate IDs are not encoder inputs.
Vocabulary fitting uses training text alone. Validation is reported without
model selection. Both checkpoints were completed before first test evaluation.

The model is a newly initialized scientific text dual encoder, with 12,720
parameters. A shared learned embedding table combines 223 training words, one
unknown word, and 256 SHA256-hashed character-trigram buckets, at width 24. Mean
pooling feeds a 24-by-24 dense layer, tanh, another 24-by-24 dense layer, and L2
normalization. Training uses full-pool contrastive cross entropy at temperature
0.09, Adam (learning rate 0.018, weight decay 0.0001), and 40 epochs. Seed 1729
is used for initialization, with seed 1730 for label shuffling. PyTorch uses one
CPU thread. Both models use the same initial weights and number of updates.
The learned checkpoint is 378,780 JSON bytes; weights are finite numeric arrays,
validated by explicit shapes and SHA256. Inference is pure Python. No pickle
serialization or deserialization is used.

This is supervised contrastive retrieval, not JEPA. Native-only P1/P2 scientific
incompatibility is handled by using a new scientific encoder trained from
scratch, not by transplanting foreign weights. No real scientific project,
uploaded proof, proof trace, fixture, heldout source, reference file, or final
evaluation record was read as data by this component. Scientific projects are
reserved for independent evaluation after component freeze. No external model,
API, pretrained embedding, or extra architecture search was used.

Reproduce from the repository root with an environment containing PyTorch 2.7:

```sh
python research/scientific_understanding_v2/learning/train_retrieval.py --output-dir /tmp/scientific-retrieval-reproduction
python -m unittest discover -s research/scientific_understanding_v2 -p test_retrieval.py -v
```

The shipped API is `rank(query, candidates, mode='bm25', checkpoint=None)` in
`retrieval.py`, where each candidate contains `id` and `text`; extra metadata is
ignored. Modes `bm25`, `tfidf`, and `neural` return aligned floating point scores
with larger values indicating more relevant text. An explicit checkpoint path
selects a different finite JSON artifact with its matching `.json.sha256` file.
