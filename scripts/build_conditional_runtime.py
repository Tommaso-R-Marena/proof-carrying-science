#!/usr/bin/env python3
"""Fresh sequential compilation of the source-bound conditional proof library.

Separate source certificates can exceed small hosts' memory if Lake schedules
them concurrently. This tool preserves all source/proof obligations and compiles
all library modules through the ordinary Lean kernel in dependency order.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def ordered_modules() -> list[tuple[str, Path]]:
 formal = ROOT / 'formal'
 modules = {str(p.relative_to(formal))[:-5].replace('/', '.'):p
            for p in (formal / 'PCSConditionalRuntime').glob('*.lean')}
 modules['PCSConditionalRuntime'] = formal / 'PCSConditionalRuntime.lean'
 seen, active, result = set(), set(), []
 def visit(name):
  if name in active: raise ValueError('cyclic imported proof modules')
  if name in seen: return
  active.add(name)
  for dep in re.findall(r'^import (\S+)', modules[name].read_text(), re.M):
   if dep in modules: visit(dep)
  active.remove(name); seen.add(name); result.append((name, modules[name]))
 for name in sorted(modules): visit(name)
 return result


def build(output: Path, memory_mb: int = 7500, heavy_timeout: int = 1800) -> dict:
 if not 1024 <= memory_mb <= 32000: raise ValueError('memory cap must be in [1024,32000] MB')
 if not 900 <= heavy_timeout <= 3600: raise ValueError('heavy timeout must be in [900,3600] seconds')
 if output.exists(): raise ValueError('build evidence must be new')
 output.parent.mkdir(parents=True, exist_ok=True)
 rows = []
 report = {'format':'pcs-conditional-sequential-build-v1', 'pass':False, 'modules':rows}
 for name, source in ordered_modules():
  target = ROOT / 'formal/.lake/build/lib/lean' / (name.replace('.', '/') + '.olean')
  target.parent.mkdir(parents=True, exist_ok=True)
  digest = hashlib.sha256(source.read_bytes()).hexdigest()
  command = ['lake','env','lean','-j1','-M' + str(memory_mb),'-D','Elab.async=false',
             '-D','maxHeartbeats=0','-D','maxRecDepth=100000','-o',str(target),str(source)]
  start = time.monotonic()
  try:
   timeout = heavy_timeout if name.endswith(('Conditional', 'ConditionalLowered')) else 900
   proc = subprocess.run(command, cwd=ROOT/'formal', text=True, capture_output=True, timeout=timeout)
   record={'module':name,'source_sha256':digest,'command':command,'returncode':proc.returncode,
           'stdout':proc.stdout,'stderr':proc.stderr,'wall_seconds':round(time.monotonic()-start,6)}
  except subprocess.TimeoutExpired as exc:
   record={'module':name,'source_sha256':digest,'command':command,'returncode':124,
           'wall_seconds':round(time.monotonic()-start,6),'failure':'timeout'}
  rows.append(record)
  if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
   record['returncode']=1; record['failure']='source changed during compilation'
  output.write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({'module':name,'returncode':record['returncode'],'wall_seconds':record['wall_seconds']}),flush=True)
  if record['returncode']:
   raise RuntimeError('conditional library build failed: '+name+'\n'+record.get('stdout','')+record.get('stderr',''))
 report['pass']=True
 output.write_text(json.dumps(report,indent=2)+'\n')
 return report


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--memory-mb',type=int,default=7500)
 parser.add_argument('--heavy-timeout',type=int,default=1800)
 args=parser.parse_args(); build(args.output,args.memory_mb,args.heavy_timeout)

if __name__=='__main__':main()
