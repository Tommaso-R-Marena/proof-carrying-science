// JSON-only bridge for independent Python/Lean tests. No Node packages required.
import {puzzle, exportCase, LEVEL_COUNT} from './engine.mjs';
const values = [];
const seeds = process.argv.length > 2 ? process.argv.slice(2).map(Number) : [20261021];
for (const seed of seeds) for (let level = 0; level < LEVEL_COUNT; level++) {
  const p = puzzle(seed, level);
  for (let choice = 0; choice < 3; choice++) values.push({bundle: exportCase(p, choice), analysis: p.candidates[choice].analysis});
}
process.stdout.write(JSON.stringify(values) + '\n');
