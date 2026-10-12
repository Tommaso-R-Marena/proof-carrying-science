"""Technical declarations cannot become legal or distribution authority."""
import importlib.util
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('inventory_release', Path(__file__).parents[1] / 'scripts/inventory_release_provenance.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

def test_inventory_hashes_sources_and_flags_mutable_actions(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    for key,value in [('user.name','Synthetic fixture'),('user.email','fixture@example.invalid')]:
        subprocess.run(['git','-C',str(tmp_path),'config',key,value],check=True)
    (tmp_path/'LICENSE').write_text('Synthetic test declaration; no legal clearance')
    (tmp_path/'pyproject.toml').write_text('[project]\nlicense="Apache-2.0"\n')
    workflow=tmp_path/'.github/workflows/audit.yml';workflow.parent.mkdir(parents=True)
    workflow.write_text('steps:\n - uses: actions/checkout@v4\n - uses: actions/setup-python@'+'a'*40+'\n')
    subprocess.run(['git','-C',str(tmp_path),'add','.'],check=True)
    subprocess.run(['git','-C',str(tmp_path),'commit','-qm','synthetic'],check=True)
    inventory=module.inventory(tmp_path)
    assert inventory['workflow_actions'][0]['immutable_commit_pin'] is False
    assert inventory['workflow_actions'][1]['immutable_commit_pin'] is True
    assert not inventory['legal_clearance'] and not inventory['automatic_distribution_authority']
    assert inventory['first_party_license_file_sha256']==module.digest(tmp_path/'LICENSE')
    assert inventory['dependency_manifests'][0]['sha256']==module.digest(tmp_path/'pyproject.toml')

def test_uncommitted_overlay_is_inventoried_without_inventing_commit_clearance(tmp_path):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    for key,value in [('user.name','Synthetic fixture'),('user.email','fixture@example.invalid')]:
        subprocess.run(['git','-C',str(tmp_path),'config',key,value],check=True)
    (tmp_path/'LICENSE').write_text('Fixture license')
    subprocess.run(['git','-C',str(tmp_path),'add','.'],check=True)
    subprocess.run(['git','-C',str(tmp_path),'commit','-qm','synthetic'],check=True)
    (tmp_path/'requirements-extra.txt').write_text('fixture-only==0\n')
    (tmp_path/'DATA_CARD.md').write_text('Uncommitted source provenance')
    inventory=module.inventory(tmp_path)
    assert inventory['nonignored_untracked_path_count']==2
    assert inventory['dirty_status']
    assert any(row['path']=='requirements-extra.txt' for row in inventory['dependency_manifests'])
    assert any(row['path']=='DATA_CARD.md' for row in inventory['rights_files'])
    assert not inventory['legal_clearance'] and not inventory['automatic_distribution_authority']
