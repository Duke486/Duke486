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

    def test_shorter_healthy_list_removes_only_generated_thumbnails(self):
        (self.dest/'character-9.light.svg').write_text(self.good)
        p.promote('anilist', {'character-0.light.svg':self.good, 'data.json':'{}'}, root=self.root)
        self.assertFalse((self.dest/'character-9.light.svg').exists())
        self.assertTrue((self.dest/'a.svg').exists())

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
        self.assertNotIn(' height=', first)

    def test_interest_assets_have_one_compact_footprint(self):
        paths = list((p.ASSETS/'anilist').glob('*.svg')) + list((p.ASSETS/'steam').glob('game-*.svg'))
        self.assertGreaterEqual(len(paths), 32)
        for path in paths:
            root = p.ET.parse(path).getroot()
            self.assertEqual((root.get('width'), root.get('height')), ('128', '148'), path.name)
            with patch.object(p, 'ASSETS', p.ASSETS):
                markup = p.image_md(str(path.relative_to(p.ASSETS)).rsplit('.', 2)[0], 'test', 128)
            self.assertIn('width="128" height="148"', markup)

    def test_public_steam_snapshot_can_show_four_games(self):
        xml = '<profile><steamID64>'+p.CONFIG['steam_id']+'</steamID64><privacyState>public</privacyState><mostPlayedGames>'
        for n in range(6):
            xml += f'<mostPlayedGame><gameName>Game {n}</gameName><gameLink>https://store.steampowered.com/app/{n}/</gameLink><hoursOnRecord>{n}</hoursOnRecord></mostPlayedGame>'
        xml += '</mostPlayedGames></profile>'
        with patch.object(p, 'request', return_value=(xml.encode(), 'text/xml')):
            result = p.steam_community()
        self.assertEqual([g['appid'] for g in result['games']], [0, 1, 2, 3])

    def test_steam_retains_verified_fourth_game_when_recent_list_shrinks(self):
        games = [{'appid':n,'name':f'Game {n}','hours':n,'image':'https://example.com/image.png'} for n in range(4)]
        fresh = {'games':games[:3], 'name':'Duke', 'source':'steam_community_xml'}
        old = {'date':'2026-09-14', 'games':games}
        with patch.dict(p.os.environ, {'STEAM_TOKEN':''}), patch.object(p,'steam_community',return_value=fresh), patch.object(p,'read_data',return_value=old), patch.object(p,'image_uri',return_value='data:image/png;base64,AA=='), patch.object(p,'promote') as publish:
            p.steam()
        result=json.loads(publish.call_args.args[1]['data.json'])
        self.assertEqual([g['appid'] for g in result['games']], [0,1,2,3])
        self.assertEqual(result['games'][3]['observed_at'], '2026-09-14')

    def test_requested_copy_is_removed_and_typewriter_is_animated(self):
        readme=(p.ROOT/'README.md').read_text(encoding='utf-8')
        for copy in ['项目导航 · 文字版','公开档案中的游戏','收藏与进度来自','最近成功更新：']:
            self.assertNotIn(copy, readme)
        svg=p.ET.parse(p.ASSETS/'design/typing.light.svg').getroot()
        self.assertEqual(len(svg.findall('.//'+p.NS+'g')), 2)
        self.assertTrue(any(a.get('attributeName')=='width' and a.get('calcMode')=='discrete' for a in svg.iter(p.NS+'animate')))
        self.assertIn('design/typing.light.svg', readme)


if __name__=='__main__':unittest.main()
