"""Real Git tests for protected squash integration; no verifier verdict is mocked."""
import importlib.util
import json
import os
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('reconciled',Path(__file__).with_name('check_reconciled_prs.py'))
checker=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(checker)


class LinearSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.git('init','-q')
        self.git('config','user.name','PCS fixture');self.git('config','user.email','fixture@example.invalid')
        self.write('controller.py','original controller\n');self.write('science.txt','exact source\n')
        self.base=self.commit('protected baseline')
        self.write('first.py','first original contribution\n');self.first=self.commit('first original head')
        self.git('checkout','-qb','other',self.base)
        self.write('second.py','second original contribution\n');self.second=self.commit('second original head')
        self.git('merge','--no-ff','-m','intake source history',self.first)
        self.intake=self.git('rev-parse','HEAD');self.git('tag','retained-intake',self.intake)
        self.git('checkout','-qb','linear-main',self.base)
        self.git('read-tree','--reset','-u',self.intake)
        self.write('controller.py','reviewed integration controller\n')
        self.squash=self.commit('protected squash integration')
        self.assertNotEqual(self.git('rev-parse',self.squash+'^'),self.intake)
        self.assertNotEqual(subprocess.run(['git','-C',str(self.root),'merge-base','--is-ancestor',self.first,'HEAD'],capture_output=True).returncode,0)

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.PIPE).decode().strip()

    def write(self,name,text):
        (self.root/name).write_text(text)

    def commit(self,message):
        self.git('add','.');self.git('commit','-qm',message);return self.git('rev-parse','HEAD')

    def check(self):
        return checker._retained_sources(self.root,self.base,self.intake,'retained-intake',
            [self.first,self.second],{'controller.py'})

    def test_real_squash_keeps_exact_science_and_retained_original_lineage(self):
        result=self.check()
        self.assertTrue(result['original_ancestry_preserved_at_intake'])
        self.assertEqual(result['selected_noncontrol_source_files_checked'],3)
        self.assertEqual(len(self.git('rev-list','--parents','-n','1','HEAD').split()),2)

    def test_substituted_scientific_source_is_rejected(self):
        self.write('first.py','substitution\n');self.commit('hostile substitution')
        with self.assertRaisesRegex(AssertionError,'non-control'):self.check()

    def test_added_source_is_rejected(self):
        self.write('unknown.py','unexpected source\n');self.commit('hostile added source')
        with self.assertRaisesRegex(AssertionError,'non-control'):self.check()

    def test_missing_source_is_rejected(self):
        (self.root/'second.py').unlink();self.commit('hostile removal')
        with self.assertRaisesRegex(AssertionError,'non-control'):self.check()

    def test_changed_mode_is_rejected(self):
        (self.root/'first.py').chmod(0o755);self.commit('hostile mode')
        with self.assertRaisesRegex(AssertionError,'non-control'):self.check()

    def test_retargeted_retention_tag_is_rejected(self):
        self.git('tag','-f','retained-intake',self.base)
        with self.assertRaisesRegex(AssertionError,'tag differs'):self.check()

    def test_missing_retention_tag_is_rejected(self):
        self.git('tag','-d','retained-intake')
        with self.assertRaises(subprocess.CalledProcessError):self.check()

    def test_unrelated_original_head_is_rejected(self):
        self.git('checkout','-qb','unreviewed',self.base);self.write('third.py','outside intake\n')
        unrelated=self.commit('unrelated');self.git('checkout','linear-main')
        with self.assertRaises(subprocess.CalledProcessError):
            checker._retained_sources(self.root,self.base,self.intake,'retained-intake',[unrelated],{'controller.py'})

    def test_dirty_controller_is_not_self_authorizing(self):
        self.write('controller.py','uncommitted replacement\n')
        with self.assertRaisesRegex(AssertionError,'Working source'):self.check()

    def test_untracked_source_is_rejected(self):
        self.write('hidden.py','untracked source\n')
        with self.assertRaisesRegex(AssertionError,'Working source'):self.check()

    def test_missing_controller_is_rejected(self):
        (self.root/'controller.py').unlink();self.commit('remove integration control')
        with self.assertRaisesRegex(AssertionError,'control required'):self.check()

    def test_new_history_must_descend_from_protected_baseline(self):
        self.git('checkout','--orphan','alien');self.git('rm','-rf','.')
        self.write('controller.py','alien\n');self.commit('unrelated root')
        with self.assertRaises(subprocess.CalledProcessError):self.check()


class CurrentRepositorySquash(unittest.TestCase):
    def test_entire_current_source_tree_passes_under_a_real_one_parent_squash(self):
        root=Path(__file__).resolve().parents[1]
        name='proof-carrying-science' if (root/'formal/PCS.lean').exists() else 'proof-carrying-science-site'
        registry=json.loads((root/'docs/reconciliation/OPEN_PRS.json').read_text())
        entry=next(e for e in registry['repositories'] if e['repository'].split('/')[-1]==name)
        baseline=entry['protected']['main'];intake,tag=checker.INTAKES[name]
        def original(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
        objects=Path(original('rev-parse','--git-path','objects'))
        if not objects.is_absolute():objects=(root/objects).resolve()
        tree=original('rev-parse','HEAD^{tree}');tag_object=original('rev-parse','refs/tags/'+tag)
        exclude=Path(original('rev-parse','--git-path','info/exclude'))
        if not exclude.is_absolute():exclude=root/exclude
        with tempfile.TemporaryDirectory(prefix='pcs-squash-source-') as folder:
            private=Path(folder)/'repo.git'
            subprocess.run(['git','init','--bare','-q',str(private)],check=True)
            (private/'objects/info/alternates').write_text(str(objects)+'\n')
            if exclude.is_file():(private/'info/exclude').write_bytes(exclude.read_bytes())
            env={**os.environ,'GIT_DIR':str(private),'GIT_WORK_TREE':str(root),'GIT_INDEX_FILE':str(private/'index'),
                 'GIT_AUTHOR_NAME':'PCS squash fixture','GIT_AUTHOR_EMAIL':'fixture@example.invalid',
                 'GIT_COMMITTER_NAME':'PCS squash fixture','GIT_COMMITTER_EMAIL':'fixture@example.invalid'}
            def isolated(*args):return subprocess.check_output(['git','-c','core.bare=false',*args],cwd=root,env=env,text=True).strip()
            squash=isolated('commit-tree',tree,'-p',baseline,'-m','Isolated linear integration fixture; no protected ref mutation')
            isolated('update-ref','HEAD',squash);isolated('update-ref','refs/tags/'+tag,tag_object);isolated('read-tree','HEAD')
            self.assertEqual(isolated('rev-parse','HEAD^{tree}'),tree)
            self.assertEqual(len(isolated('rev-list','--parents','-n','1','HEAD').split()),2)
            scope='--core' if name=='proof-carrying-science' else '--site'
            run=subprocess.run([sys.executable,str(root/'scripts/check_reconciled_prs.py'),scope,str(root)],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertTrue(json.loads(run.stdout)['passed'])
            if name=='proof-carrying-science':
                run=subprocess.run([sys.executable,'-m','research.integration_v2.reconcile','--require-committed'],cwd=root,env=env,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                self.assertEqual(json.loads(run.stdout)['prs_checked'],72)


if __name__=='__main__':unittest.main(verbosity=2)
