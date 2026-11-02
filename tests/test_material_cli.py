from argparse import Namespace
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

KIT=Path(__file__).resolve().parents[1]
loader=SourceFileLoader('kit_material_cli',str(KIT/'bin/kit'))
spec=importlib.util.spec_from_loader(loader.name,loader)
cli=importlib.util.module_from_spec(spec);loader.exec_module(cli)


class MaterialCLI(unittest.TestCase):
    def test_staging_and_selection_survive_course_working_directory_change(self):
        with tempfile.TemporaryDirectory() as td:
            args=Namespace(repo=td,thumbs=False,output_root='review artifacts',only='unit 1',limit=2,keep_tex=True)
            with patch.object(cli,'_echo',return_value=0) as call:
                self.assertEqual(cli.cmd_materials(args),0)
            command,cwd=call.call_args.args
            self.assertEqual(cwd,Path(td).resolve())
            self.assertEqual(command[command.index('--output-root')+1],str(Path('review artifacts').resolve()))
            self.assertEqual(command[command.index('--only')+1],'unit 1')
            self.assertEqual(command[command.index('--limit')+1],'2')
            self.assertIn('--keep-tex',command)

    def test_thumbnail_mode_never_silently_ignores_staging(self):
        args=Namespace(repo='.',thumbs=True,output_root='staging',only='',limit=0,keep_tex=False)
        with patch.object(cli,'_echo') as call:
            self.assertEqual(cli.cmd_materials(args),2)
        call.assert_not_called()
