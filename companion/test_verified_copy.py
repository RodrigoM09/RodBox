import hashlib,importlib.util,pathlib,tempfile,unittest
from unittest import mock
spec=importlib.util.spec_from_file_location('verified_copy',pathlib.Path(__file__).with_name('verified_copy.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CopyTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.t.name)
        self.src=self.root/'src';self.dst=self.root/'dst';self.src.mkdir();self.dst.mkdir()
        self.data=b'music'*300000;(self.src/'track').write_bytes(self.data)
        self.sha=hashlib.sha256(self.data).hexdigest()
    def tearDown(self):self.t.cleanup()
    def run_copy(self,**kw):return c.copy_verified(self.src,'track',self.dst,'album/track',self.sha,len(self.data),**kw)
    def assert_no_temp(self):self.assertEqual(list(self.dst.rglob('.rodbox-copy-*')),[])
    def test_copy_and_resume(self):
        self.run_copy();self.assertEqual((self.dst/'album/track').read_bytes(),self.data)
        self.assertEqual(self.run_copy()['status'],'already verified')
    def test_mismatching_existing_is_preserved(self):
        (self.dst/'album').mkdir();p=self.dst/'album/track';p.write_bytes(b'original')
        with self.assertRaises(FileExistsError):self.run_copy()
        self.assertEqual(p.read_bytes(),b'original');self.assert_no_temp()
    def test_explicit_replacement(self):
        (self.dst/'album').mkdir();p=self.dst/'album/track';p.write_bytes(b'original')
        self.run_copy(expected_old_sha256=hashlib.sha256(b'original').hexdigest());self.assertEqual(p.read_bytes(),self.data)
    def test_wrong_checksum_does_not_commit(self):
        self.sha='0'*64
        with self.assertRaises(ValueError):self.run_copy()
        self.assertFalse((self.dst/'album/track').exists());self.assert_no_temp()
    def test_cancel_preserves_existing(self):
        (self.dst/'album').mkdir();p=self.dst/'album/track';p.write_bytes(b'old')
        with self.assertRaises(InterruptedError):self.run_copy(expected_old_sha256=hashlib.sha256(b'old').hexdigest(),cancel=lambda:True)
        self.assertEqual(p.read_bytes(),b'old');self.assert_no_temp()
    def test_disconnect_before_commit(self):
        calls=[]
        def identity():
            calls.append(1)
            if len(calls)>1:raise OSError('device disconnected')
        with self.assertRaises(OSError):self.run_copy(identity=identity)
        self.assertFalse((self.dst/'album/track').exists());self.assert_no_temp()
    def test_source_change_before_commit(self):
        calls=[]
        def cancel():
            calls.append(1)
            if len(calls)==1:(self.src/'track').write_bytes(b'changed')
            return False
        with self.assertRaises(ValueError):self.run_copy(cancel=cancel)
        self.assertFalse((self.dst/'album/track').exists());self.assert_no_temp()
    def test_path_escape_and_symlink(self):
        with self.assertRaises(ValueError):c.contained(self.dst,'../elsewhere')
        with self.assertRaises(ValueError):c.contained(self.dst,'/absolute')
        (self.dst/'link').symlink_to(self.src,target_is_directory=True)
        with self.assertRaises(ValueError):c.contained(self.dst,'link/track')
    def test_failed_write_preserves_existing(self):
        (self.dst/'album').mkdir();p=self.dst/'album/track';p.write_bytes(b'old')
        with mock.patch.object(c.os,'fsync',side_effect=OSError('full disk')):
            with self.assertRaises(OSError):self.run_copy(expected_old_sha256=hashlib.sha256(b'old').hexdigest())
        self.assertEqual(p.read_bytes(),b'old');self.assert_no_temp()

if __name__=='__main__':unittest.main()
