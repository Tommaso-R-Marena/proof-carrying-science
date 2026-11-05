"""Bounded optional mmCIF/Gemmi structure inspection (non-executing)."""
from __future__ import annotations
from collections import defaultdict
import math


def inspect_mmcif(r):
    try:
        import gemmi
    except ImportError:
        r.add('MMCIF_PARSER', 'OPEN','mmCIF parser dependency unavailable',
              'Install gemmi (pip install gemmi) for bounded atomic-coordinate inspection')
        return
    if len(r.data) > 16*1024*1024:
        raise ValueError('mmCIF exceeds 16 MiB native parser input budget')
    doc=gemmi.cif.read_string(r.data.decode('utf8'))
    if len(doc)>1:raise ValueError('Multi-block mmCIF not supported in the narrow adapter')
    block=doc.sole_block()
    structure=gemmi.make_structure_from_block(block)
    atoms=[]; residues=set();chains=set();bad=0;seen=set();duplicate=0
    for m in structure:
        for c in m:
            for res in c:
                rid=(m.num,c.name,res.seqid.num,str(res.seqid.icode),res.name)
                residues.add(rid);chains.add((m.num,c.name))
                for a in res:
                    if len(atoms)>=100_000:raise ValueError('mmCIF exceeds 100000 atoms')
                    xyz=(float(a.pos.x),float(a.pos.y),float(a.pos.z))
                    occ=float(a.occ)
                    if not all(math.isfinite(v) for v in (*xyz,occ)) or not 0<=occ<=1:bad+=1
                    token=(rid,a.name,str(a.altloc))
                    if token in seen:duplicate+=1
                    seen.add(token)
                    atoms.append((*xyz,m.num,c.name,res.seqid.num,a.element.name.upper(),str(a.altloc),rid))
    if not atoms:raise ValueError('No atomic coordinates recovered from mmCIF')
    grid=defaultdict(list);clashes=0;examples=[]
    # Use the same deliberately narrow <1.7 Å heavy-atom close-contact heuristic as PDB.
    for i,(x,y,z,model,chain,resnum,elem,alt,rid) in enumerate(atoms):
        if elem in ('H','D'):continue
        key=(math.floor(x/1.7),math.floor(y/1.7),math.floor(z/1.7))
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for j in grid.get((key[0]+dx,key[1]+dy,key[2]+dz),()):
                        xx,yy,zz,mm,cc,rr,ee,aa,rid2=atoms[j]
                        if mm!=model or rid2==rid:continue
                        if cc==chain and isinstance(resnum,int) and isinstance(rr,int) and abs(resnum-rr)<=1:continue
                        if alt not in ('\0','.','?',' ') and aa not in ('\0','.','?',' ') and alt!=aa:continue
                        if (x-xx)**2+(y-yy)**2+(z-zz)**2<1.7**2:
                            clashes+=1
                            if len(examples)<8:examples.append([j,i])
        grid[key].append(i)
    r.metrics={'models':len(structure),'atoms':len(atoms),'residues':len(residues),'chains':len(chains),
               'severe_close_pairs_heuristic':clashes,'invalid_or_nonfinite_atom_records':bad,
               'duplicate_atom_ids':duplicate}
    r.details={'clash_pair_indices_sample':examples,'parser':'gemmi '+gemmi.__version__}
    r.add('MMCIF_PARSER','PASS' if not (bad or duplicate) else 'FAIL','mmCIF atomic-coordinate parsing',
          f'{len(atoms)} atoms in {len(structure)} model(s); {bad} invalid geometry/occupancy records; {duplicate} duplicate atom labels.')
    r.add('MMCIF_CLOSE_CONTACTS','FAIL' if clashes>r.policy['max_pdb_clashes'] else 'PASS',
          'mmCIF heavy-atom proximity heuristic',
          f'{clashes} pairs closer than 1.7 Å outside same/adjacent residues; threshold {r.policy["max_pdb_clashes"]}. This is not force-field or stereochemical validation.')
    r.add('MMCIF_SCIENTIFIC_VALIDITY','OPEN','Structure validity and function not established',
          'No ensemble confidence, experimental fit, physical stability, binding activity or clinical significance asserted')
