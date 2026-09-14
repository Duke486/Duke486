import importlib.util, pathlib, tempfile, unittest, json, urllib.error
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('profile_assets', pathlib.Path(__file__).parents[1]/'scripts/profile.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class SnapshotProtection(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.dest = self.root/'assets/anilist'
        self.dest.mkdir(parents=True)
        self.good = p.card(100,100,'Saved',p.text(10,40,'Saved'))
        (self.dest/'a.svg').write_text(self.good)

    def tearDown(self): self.temp.cleanup()

    def test_one_bad_card_preserves_entire_module(self):
        with self.assertRaises(ValueError):
            p.promote('anilist',{'a.svg':p.card(100,100,'New',p.text(10,40,'New')),
                                'b.svg':p.card(100,100,'API error: 401','')},root=self.root)
        self.assertEqual((self.dest/'a.svg').read_text(),self.good)
        self.assertFalse((self.dest/'b.svg').exists())

    def test_malformed_xml_does_not_overwrite_saved_card(self):
        with self.assertRaises(Exception):p.promote('anilist',{'a.svg':'<svg>'},root=self.root)
        self.assertEqual((self.dest/'a.svg').read_text(),self.good)

    def test_healthy_module_replaces_old_snapshot(self):
        new = p.card(100,100,'New',p.text(10,40,'New'))
        p.promote('anilist',{'a.svg':new,'data.json':'{"date":"2026-09-14"}'},root=self.root)
        self.assertEqual((self.dest/'a.svg').read_text(),new)

    def test_external_image_is_rejected(self):
        with self.assertRaises(ValueError):
            p.validate_svg(p.card(100,100,'A','<image href="https://example.com/img.png"/>'))

    def test_markup_in_title_is_escaped(self):
        label='A & B <script>alert(1)</script>'
        root=p.validate_svg(p.card(300,100,label,p.text(10,40,label)))
        self.assertEqual(root.find(p.NS+'title').text,label)
        self.assertFalse(list(root.iter(p.NS+'script')))

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):p.promote('anilist',{'../../bad.svg':self.good},root=self.root)

    def test_graphql_errors_in_http_200_never_publish(self):
        with patch.object(p,'json_request',return_value={'data':{'User':None},'errors':[{'message':'Not Found'}]}),patch.object(p,'promote') as publish:
            with self.assertRaises(p.SourceError):p.anilist()
            publish.assert_not_called()

    def test_private_recent_games_are_not_interpreted_as_empty(self):
        with patch.object(p,'json_request',side_effect=[{'response':{'players':[{'steamid':p.CONFIG['steam_id']}] }},{'response':{}}]):
            with self.assertRaises(p.SourceError):p.steam_official('FAKE_TEST_SECRET')

    def test_http_error_never_discloses_query_key(self):
        secret='FAKE_TEST_SECRET'
        error=urllib.error.HTTPError('https://example.com/?key='+secret,401,'unauthorized',{},None)
        with patch.object(p.urllib.request,'urlopen',side_effect=error):
            with self.assertRaises(p.SourceError) as caught:p.request('https://example.com/?key='+secret)
        self.assertEqual(str(caught.exception),'HTTP 401')
        self.assertNotIn(secret,str(caught.exception))

    def test_rate_limit_has_bounded_retry_and_preserves_card(self):
        error=urllib.error.HTTPError('https://example.com',429,'limited',{'Retry-After':'300'},None)
        with patch.object(p.urllib.request,'urlopen',side_effect=error) as urlopen,patch.object(p.time,'sleep') as sleep:
            with self.assertRaises(p.SourceError):p.request('https://example.com')
        self.assertEqual(urlopen.call_count,3)
        self.assertEqual(sleep.call_count,2)
        self.assertTrue(all(call.args[0] <= 15 for call in sleep.call_args_list))
        self.assertEqual((self.dest/'a.svg').read_text(),self.good)

    def test_timeout_is_bounded(self):
        with patch.object(p.urllib.request,'urlopen',side_effect=TimeoutError),patch.object(p.time,'sleep'):
            with self.assertRaises(p.SourceError):p.request('https://example.com')

    def test_readme_images_use_direct_raw_urls_and_content_keys(self):
        folder=self.root/'assets/design';folder.mkdir(parents=True)
        for theme in ('light','dark'):(folder/f'hero.{theme}.svg').write_text(self.good)
        with patch.object(p,'ASSETS',self.root/'assets'):
            first=p.image_md('design/hero','Title',960)
            (folder/'hero.light.svg').write_text(self.good+'\n')
            second=p.image_md('design/hero','Title',960)
        self.assertIn('https://raw.githubusercontent.com/Duke486/Duke486/main/assets/design/hero.light.svg?v=',first)
        self.assertNotEqual(first,second)


if __name__=='__main__':unittest.main()
