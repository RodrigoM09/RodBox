import importlib.util,json,pathlib,tempfile,unittest
spec=importlib.util.spec_from_file_location('health_report',pathlib.Path(__file__).with_name('health_report.py'))
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class HealthTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.t.name)
        self.row={'relative':'Album/song.flac','bytes':100,'sha256':'a'*64,'audio':True,'tags':{'artist':['Artist'],'album':['Album'],'title':['Song']}}
        self.good={'root':'/test','finished':True,'files':1,'total_files':1,'errors':[],'rows':[self.row]}
        self.a=self.p/'device.json';self.b=self.p/'archive.json';self.out=self.p/'report.json'
        self.a.write_text(json.dumps(self.good));self.b.write_text(json.dumps(self.good));self.out.write_text('prior verified report')
    def tearDown(self):self.t.cleanup()
    def test_incomplete_scan_preserves_report(self):
        d=dict(self.good,finished=False);self.a.write_text(json.dumps(d))
        with self.assertRaises(ValueError):h.write_report(self.a,self.b,self.out)
        self.assertEqual(self.out.read_text(),'prior verified report')
    def test_disconnect_error_preserves_report(self):
        d=dict(self.good,errors=[{'error':'device disconnected'}]);self.b.write_text(json.dumps(d))
        with self.assertRaises(ValueError):h.write_report(self.a,self.b,self.out)
        self.assertEqual(self.out.read_text(),'prior verified report')
    def test_missing_art_and_tags_are_reported(self):
        self.good['rows'][0]['tags']['title']=[]
        r=h.build_report(self.good,self.good)
        self.assertEqual(r['missing_album_covers'],['Album']);self.assertEqual(r['missing_artist_photos'],['Album'])
        self.assertEqual(r['missing_required_tags'][0]['fields'],['title'])
    def test_wrong_audio_bytes_require_exact_backup(self):
        different=json.loads(json.dumps(self.good));different['rows'][0]['sha256']='b'*64
        self.assertEqual(h.build_report(self.good,different)['files_without_exact_verified_backup'],['Album/song.flac'])
        self.assertEqual(h.build_report(self.good,different,self.good)['files_without_exact_verified_backup'],[])
    def test_success_atomically_replaces_report(self):
        r=h.write_report(self.a,self.b,self.out)
        self.assertEqual(json.loads(self.out.read_text())['audio_tracks'],1)
        self.assertEqual(r['files_without_exact_verified_backup'],[])
        self.assertEqual(list(self.p.glob('.health-*')),[])
    def test_count_mismatch_refuses_report(self):
        self.a.write_text(json.dumps(dict(self.good,total_files=2)))
        with self.assertRaises(ValueError):h.write_report(self.a,self.b,self.out)
        self.assertEqual(self.out.read_text(),'prior verified report')

if __name__=='__main__':unittest.main()
