"""Static profile assets. Standard-library-only; publish only validated modules."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, html, json, os, pathlib, re
import sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'profile.json').read_text(encoding='utf-8'))
ASSETS = ROOT / 'assets'
NS = '{http://www.w3.org/2000/svg}'


class SourceError(Exception):
    pass


def today():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')


def request(url, payload=None):
    """Bounded retry; errors never contain URLs (Steam keys are query parameters)."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                headers={'User-Agent': 'Duke486-profile/1.0 (https://github.com/Duke486/Duke486)',
                         'Content-Type': 'application/json'} if payload else
                        {'User-Agent': 'Duke486-profile/1.0 (https://github.com/Duke486/Duke486)'})
            with urllib.request.urlopen(req, timeout=25) as response:
                data = response.read(5_000_001)
                if len(data) > 5_000_000:
                    raise SourceError('Response exceeds size limit')
                return data, response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise SourceError(f'HTTP {error.code}') from None
            retry = error.headers.get('Retry-After', '3')
            time.sleep(min(15, int(retry) if retry.isdigit() else 3))
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise SourceError('Network unavailable or timed out') from None
            time.sleep(2 * (attempt + 1))
    raise SourceError('Request failed')


def json_request(url, payload=None):
    raw, _ = request(url, payload)
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise SourceError('Invalid JSON response') from None


def image_uri(url):
    if not url or not url.startswith('https://'):
        raise SourceError('Missing HTTPS image')
    cache = ROOT / '.cache' / 'images'
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    if path.exists():
        data = json.loads(path.read_text())
    else:
        raw, mime = request(url)
        if mime not in ('image/png', 'image/jpeg', 'image/webp', 'image/gif') or len(raw) < 100:
            raise SourceError('Invalid cover image')
        data = {'mime': mime, 'base64': base64.b64encode(raw).decode()}
        path.write_text(json.dumps(data))
    return f'data:{data["mime"]};base64,{data["base64"]}'


def esc(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, size=18, fill='ink', weight=400, theme='light', anchor='start'):
    color = '#' + CONFIG['themes'][theme].get(fill, fill)
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(value)}</text>'


def wrap(value, max_units, lines=2):
    """Conservative CJK-aware wrapping, truncating only display text."""
    result, current, count = [], '', 0
    for char in str(value):
        units = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        if count + units > max_units:
            result.append(current)
            current, count = '', 0
        current += char
        count += units
    if current:
        result.append(current)
    if len(result) > lines:
        result = result[:lines]
        result[-1] = result[-1][:-1] + '…'
    return result


def card(width, height, title, body, theme='light'):
    t = CONFIG['themes'][theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title><defs><linearGradient id="wash" x2="1" y2="1"><stop stop-color="#{t['background']}"/><stop offset="1" stop-color="#{t['end']}"/></linearGradient></defs>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei','Noto Sans CJK JP',sans-serif}}</style>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="6" fill="#{t['background']}" stroke="#{t['line']}"/>
{body}</svg>'''


def picture(uri, x, y, width, height, ident='cover', radius=12):
    return f'<defs><clipPath id="{ident}"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}"/></clipPath></defs><image href="{uri}" x="{x}" y="{y}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{ident})"/>'


PALETTES = [
    ('DDF8F2','A5E7DE','087F8C'), ('FFF0D1','FFD27A','A95D13'),
    ('EAE5FF','CEBEFF','7152B5'), ('FFE4EB','FFB7CD','B74475'),
    ('DDF3FF','A5DDFF','217BA9'), ('E9F7D5','C2E69B','54812C')]


def small_card(uri, title, theme, detail='', portrait=False, index=0, kind='cover'):
    """Small collectible tiles, with artwork and captions held together by color."""
    pale, strong, accent = PALETTES[index % len(PALETTES)]
    surface = pale if theme == 'light' else ['203D40','443627','322F49','472D3C','233B4D','303F29'][index % 6]
    if portrait:
        body = f'<rect x="3" y="3" width="99" height="142" rx="12" fill="#{surface}"/>'
        body += f'<path d="M81 3h9q12 0 12 12v12Z" fill="#{strong}" opacity=".7"/>'
        body += picture(uri, 17.5, 8, 70, 106, radius=8).replace('xMidYMid slice', 'xMidYMid meet')
        for n, line in enumerate(wrap(title, 12, 2)):
            body += text(52.5, 127+n*13, line, 11, 'ink', 600, theme, 'middle')
        return bare_svg(105, 148, title, body, theme)
    body = f'<rect x="3" y="3" width="122" height="142" rx="16" fill="#{surface}"/>'
    body += f'<path d="M88 3h21q16 0 16 16v18Q107 22 88 3" fill="#{strong}" opacity=".7"/>'
    body += f'<circle cx="14" cy="132" r="2" fill="#{accent}" opacity=".5"/>'
    if kind == 'game':
        body += picture(uri, 9, 23, 110, 67, radius=9).replace('xMidYMid slice','xMidYMid meet')
        body += f'<path d="M19 12h12m-6-6v12" stroke="#{accent}" stroke-width="2" stroke-linecap="round" opacity=".65"/>'
    else:
        body += f'<rect x="31" y="12" width="66" height="94" rx="5" fill="#{strong}" opacity=".6" transform="rotate(5 64 59)"/>'
        body += picture(uri, 32, 8, 64, 96, radius=4).replace('xMidYMid slice','xMidYMid meet')
    for n, line in enumerate(wrap(title, 18, 1 if detail else 2)):
        body += text(64, 120+n*15, line, 12, 'ink', 600, theme, 'middle')
    if detail:
        body += text(64, 136, detail, 10, 'muted', 400, theme, 'middle')
    return bare_svg(128, 148, title+(' · '+detail if detail else ''), body, theme)


def bare_svg(width, height, title, body, theme='light'):
    svg = card(width, height, title, body, theme)
    return re.sub(r'<rect x="\.5"[^>]+/>', '', svg, count=1)


def validate_svg(content):
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    root = ET.fromstring(content)
    if root.tag != NS + 'svg' or not root.get('viewBox'):
        raise ValueError('Not a self-contained SVG')
    visible = ' '.join(''.join(el.itertext()) for el in root.iter() if el.tag in (NS+'text', NS+'title'))
    if not visible.strip() or re.search(r'API error|Something went wrong|Invalid token|Bad credentials|DEPLOYMENT_PAUSED', visible, re.I):
        raise ValueError('Empty or error card')
    for element in root.iter():
        if element.tag in (NS+'script', NS+'foreignObject'):
            raise ValueError('Active or nonportable SVG content')
        for key, value in element.attrib.items():
            if key.lower().startswith('on'):
                raise ValueError('Event handler in SVG')
            if key.endswith('href') and element.tag == NS+'image' and not value.startswith('data:image/'):
                raise ValueError('Image is not embedded')
    return root


def promote(module, files, root=ROOT):
    """Validate the entire module before touching its last healthy generation."""
    if module not in ('design', 'github', 'anilist', 'steam') or not files:
        raise ValueError('Invalid module')
    for name, content in files.items():
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+\.(svg|json)', name):
            raise ValueError('Unsafe output name')
        if name.endswith('.svg'):
            validate_svg(content)
        else:
            json.loads(content)
    staging = root / '.staging' / ('publish-' + module)
    staging.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (staging / name).write_text(content, encoding='utf-8')
    dest = root / 'assets' / module
    dest.mkdir(parents=True, exist_ok=True)
    for name in files:
        os.replace(staging / name, dest / name)
    # A source list can shrink. Remove only obsolete generated thumbnails after
    # the complete healthy replacement has been validated and written.
    if module in ('anilist', 'steam') and 'data.json' in files:
        for path in dest.glob('*.svg'):
            if re.fullmatch(r'(game|character|favorite|reading)-\d+\.(light|dark)\.svg', path.name) and path.name not in files:
                path.unlink()


QUERY = '''query($id: Int!) { User(id: $id) { id name siteUrl statistics { anime { count episodesWatched } manga { count chaptersRead } } favourites { anime(perPage: 4) { nodes { id title { native romaji english } coverImage { large } siteUrl } } manga(perPage: 4) { nodes { id title { native romaji english } coverImage { large } siteUrl } } characters(perPage: 10) { nodes { id name { full native } image { large } siteUrl } } } } MediaListCollection(userId: $id, type: MANGA, status: CURRENT, sort: UPDATED_TIME_DESC) { lists { entries { progress media { id title { native romaji english } coverImage { large } chapters siteUrl } } } } }'''


def media_title(media):
    return media['title'].get('native') or media['title'].get('romaji') or media['title'].get('english') or 'Untitled'


def anilist():
    response = json_request('https://graphql.anilist.co', {'query': QUERY, 'variables': {'id': CONFIG['anilist_id']}})
    if response.get('errors') or not response.get('data', {}).get('User'):
        raise SourceError('AniList returned errors or no user')
    data = response['data']; user = data['User']
    if user['id'] != CONFIG['anilist_id']:
        raise SourceError('Unexpected AniList user')
    entries = [entry for group in data['MediaListCollection']['lists'] for entry in group['entries']]
    seen = set(); reading = []
    for entry in entries:
        if entry['media']['id'] not in seen:
            seen.add(entry['media']['id']); reading.append(entry)
    reading = reading[:CONFIG['reading_limit']]
    characters = user['favourites']['characters']['nodes'][:CONFIG['character_limit']]
    # Fetch all image bytes before committing any card or metadata.
    covers = {entry['media']['id']: image_uri(entry['media']['coverImage']['large']) for entry in reading}
    portraits = {entry['id']: image_uri(entry['image']['large']) for entry in characters}
    favorites = (user['favourites']['anime']['nodes'][:1] + user['favourites']['manga']['nodes'][:1])
    favorite_images = {entry['id']: image_uri(entry['coverImage']['large']) for entry in favorites}
    files = {}
    for theme in CONFIG['themes']:
        for index, entry in enumerate(reading):
            media = entry['media']
            progress = f"已读 {entry['progress']} 话" + (f" / {media['chapters']}" if media.get('chapters') else '')
            files[f'reading-{index}.{theme}.svg'] = small_card(covers[media['id']], media_title(media), theme, progress, index=index+4)
        for index, char in enumerate(characters):
            name = char['name'].get('native') or char['name']['full']
            files[f'character-{index}.{theme}.svg'] = small_card(portraits[char['id']], name, theme, portrait=True, index=index)
        for index, media in enumerate(favorites):
            files[f'favorite-{index}.{theme}.svg'] = small_card(favorite_images[media['id']], media_title(media), theme, index=index+1)
    files['data.json'] = json.dumps({'date': today(), 'id': user['id'], 'name': user['name'], 'reading': reading, 'characters': characters, 'favorites': favorites}, ensure_ascii=False, indent=2)
    promote('anilist', files)


def steam_official(key):
    base = 'https://api.steampowered.com/'
    query = urllib.parse.urlencode({'key': key, 'steamids': CONFIG['steam_id']})
    players = json_request(base+'ISteamUser/GetPlayerSummaries/v2/?'+query)['response']['players']
    if not players or players[0]['steamid'] != CONFIG['steam_id']:
        raise SourceError('Steam returned no matching player')
    query = urllib.parse.urlencode({'key': key, 'steamid': CONFIG['steam_id'], 'count': CONFIG.get('steam_limit', 4)})
    result = json_request(base+'IPlayerService/GetRecentlyPlayedGames/v1/?'+query)['response']
    if not isinstance(result, dict) or 'total_count' not in result:
        raise SourceError('Recent games unavailable or private')
    games = [{'name': g['name'], 'appid': g['appid'], 'hours': round(g.get('playtime_forever', 0)/60,1),
              'image': f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{g['appid']}/capsule_184x69.jpg"} for g in result.get('games', [])[:CONFIG.get('steam_limit', 4)]]
    return {'name': players[0]['personaname'], 'avatar': players[0]['avatarfull'], 'games': games, 'source': 'steam_web_api', 'label': '最近游戏', 'note': None}


def steam_community():
    raw, _ = request(f'https://steamcommunity.com/profiles/{CONFIG["steam_id"]}/?xml=1')
    doc = ET.fromstring(raw)
    if doc.findtext('steamID64') != CONFIG['steam_id'] or doc.findtext('privacyState') != 'public':
        raise SourceError('Steam public profile unavailable')
    games = []
    for game in doc.findall('./mostPlayedGames/mostPlayedGame')[:CONFIG.get('steam_limit', 4)]:
        appid = int((game.findtext('gameLink') or '').rstrip('/').rsplit('/', 1)[1])
        games.append({'name': game.findtext('gameName'), 'appid': appid,
                      'hours': game.findtext('hoursOnRecord') or '—', 'image': game.findtext('gameLogo')})
    return {'name': doc.findtext('steamID'), 'avatar': doc.findtext('avatarFull'), 'games': games,
            'source': 'steam_community_xml', 'label': '公开档案中的游戏', 'note': None}


def steam():
    key = os.environ.get('STEAM_TOKEN', '').strip()
    reason = None
    if key:
        try:
            data = steam_official(key)
        except (SourceError, KeyError, ValueError) as error:
            reason = 'official_api_unavailable'
            print('::warning::Steam API unavailable; using public community snapshot. Check STEAM_TOKEN.')
            data = steam_community()
    else:
        reason = 'api_key_not_configured'
        data = steam_community()
        print('Steam: using public community snapshot (API key not configured).')
    previous = read_data('steam')
    for game in data['games']:
        game['observed_at'] = today()
    ids = {g['appid'] for g in data['games']}
    for old in previous.get('games', []):
        if len(data['games']) >= CONFIG.get('steam_limit', 4): break
        if old['appid'] not in ids:
            old = dict(old, observed_at=old.get('observed_at', previous.get('date')))
            data['games'].append(old); ids.add(old['appid'])
    if len(data['games']) != CONFIG.get('steam_limit', 4):
        raise SourceError('Four-game showcase unavailable; retain last complete showcase')
    data['note'] = reason
    data['date'] = today()
    data['steam_id'] = CONFIG['steam_id']
    images = [image_uri(g['image']) for g in data['games']]
    files = {}
    for theme in CONFIG['themes']:
        for index, game in enumerate(data['games']):
            files[f'game-{index}.{theme}.svg'] = small_card(images[index], game['name'], theme, str(game['hours'])+' h', index=index, kind='game')
    files['data.json'] = json.dumps(data, ensure_ascii=False, indent=2)
    promote('steam', files)


def design():
    art = 'data:image/png;base64,' + base64.b64encode((ASSETS/'art/miku-tamako.png').read_bytes()).decode()
    files = {}
    sections = [('projects','Projects',0),('community','Community',4),('steam','Play time',1),('favorites','Favorites',3),('reading','On my bookshelf',5),('characters','Favorite characters',2),('github','GitHub',0),('trakt','Movie nights',3)]
    for theme, colors in CONFIG['themes'].items():
        base = '#E6FAF5' if theme == 'light' else '#163D40'
        body = f'<rect x="3" y="3" width="794" height="204" rx="28" fill="{base}"/>'
        body += '<defs><linearGradient id="rainbow"><stop stop-color="#66CBEF"/><stop offset=".32" stop-color="#54D5B9"/><stop offset=".66" stop-color="#FFD474"/><stop offset="1" stop-color="#F5A6CA"/></linearGradient></defs>'
        body += '<defs><clipPath id="hero-edge"><rect x="3" y="3" width="794" height="204" rx="28"/></clipPath></defs><path d="M400 207C466 40 634 55 797 101V207Z" fill="url(#rainbow)" opacity=".48" clip-path="url(#hero-edge)"/>'
        body += text(32, 93, 'Duke486', 60, 'ink', 700, theme)
        body += text(35, 135, 'CS · ACGN · PT', 23, 'mint', 600, theme)
        body += '<path d="M38 164h32m10 0h32m10 0h32m10 0h32" stroke="url(#rainbow)" stroke-width="8" stroke-linecap="round"/>'
        body += '<path d="M414 37v18m-9-9h18M750 163v16m-8-8h16" stroke="#E9A549" stroke-width="3" stroke-linecap="round"/>'
        body += f'<image href="{art}" x="535" y="-2" width="260" height="208" preserveAspectRatio="xMidYMid meet"/>'
        files[f'hero.{theme}.svg'] = bare_svg(800, 210, 'Duke486 · Code, ACGN and PT', body, theme)
        for key, label, i in sections:
            pale, strong, accent = PALETTES[i]
            body = f'<rect x="0" y="5" width="30" height="30" rx="10" fill="#{strong}"/>'
            icons = {
                'projects':'M11 14l-5 6 5 6m8-12 5 6-5 6m-3-14-3 16',
                'community':'M8 20a5 5 0 0 1 5-5h4m-4 10h4a5 5 0 0 0 0-10m-6 5h8',
                'steam':'M8 15h14l3 12-7-4h-6l-7 4zM10 17v5m-2-3h5m7-1v1m2 1v1',
                'favorites':'M15 11l3 6 7 1-5 5 1 7-6-4-6 4 1-7-5-5 7-1z',
                'reading':'M15 15Q9 11 5 14v15q5-3 10 0 5-3 10 0V14q-5-3-10 1v14',
                'characters':'M15 28C-1 18 8 8 15 16c7-8 16 2 0 12z',
                'github':'M8 26v-12m0 1h12v10m-12-3h12',
                'trakt':'M6 13h18v16H6zM6 18h18m-12-5v5m6-5v5'}
            body += f'<path d="{icons[key]}" fill="none" stroke="#{accent}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
            body += text(40, 28, label, 20, 'ink', 700, theme)
            files[f'section-{key}.{theme}.svg'] = bare_svg(260, 40, label, body, theme)
        # Two alternating typewriter lines. Native SVG animation, no scripts or remote renderer.
        lines = ['Nyaa(=・ω・=)~ 这里是 Duke486！', 'Meow( · ω · )~ here is Duke486!']
        times, widths = [], []
        for offset in (0, .5):
            for n in range(33):
                times.append(offset+n*.22/32); widths.append(n*350/32)
            times.append(offset+.42); widths.append(350)
            for n in range(1, 17):
                times.append(offset+.42+n*.06/16); widths.append(350*(1-n/16))
        times.append(1); widths.append(0)
        key_times = ';'.join(f'{v:.6f}' for v in times)
        values = ';'.join(f'{v:.2f}' for v in widths)
        animation = f'values="{values}" keyTimes="{key_times}" calcMode="discrete" dur="10s" repeatCount="indefinite"'
        body = f'<defs><clipPath id="typing"><rect x="0" y="0" width="0" height="44"><animate attributeName="width" {animation}/></rect></clipPath></defs>'
        for i, line in enumerate(lines):
            opacity = '1;0;0' if i == 0 else '0;1;1'
            body += f'<g clip-path="url(#typing)" opacity="{1-i}"><animate attributeName="opacity" values="{opacity}" keyTimes="0;.5;1" calcMode="discrete" dur="10s" repeatCount="indefinite"/>'
            body += text(2, 29, line, 21, 'mint' if i == 0 else 'blue', 500, theme).replace('<text ', '<text textLength="348" lengthAdjust="spacingAndGlyphs" ')+'</g>'
        body += f'<rect y="9" width="2" height="24" fill="#45B9B0"><animate attributeName="x" {animation}/><animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>'
        files[f'typing.{theme}.svg'] = bare_svg(440,44,' / '.join(lines),body,theme)
        body = '<rect x="3" y="3" width="314" height="112" rx="20" fill="'+('#FFE8EF' if theme == 'light' else '#472D3C')+'"/>'
        body += '<path d="M22 36h48v45H22z" fill="#F47D9D"/><path d="M28 25l40-8 3 14-40 8z" fill="#FFBE74"/><path d="M43 47l15 11-15 11z" fill="white"/>'
        body += text(88,50,'Trakt',24,'ink',700,theme)+text(88,77,'duke486  ↗',16,'muted',500,theme)
        files[f'trakt.{theme}.svg'] = bare_svg(320,120,'Trakt · duke486',body,theme)
    promote('design', files)


def read_data(module):
    path = ASSETS / module / 'data.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def image_md(path, alt, width, link=None):
    def raw_url(theme):
        file = ASSETS / f'{path}.{theme}.svg'
        version = hashlib.sha256(file.read_bytes()).hexdigest()[:12]
        return f'https://raw.githubusercontent.com/{CONFIG["github"]}/{CONFIG["github"]}/main/assets/{path}.{theme}.svg?v={version}'
    # Wide images must retain automatic height when GitHub constrains their width.
    # Only the fixed-size thumbnails reserve an explicit height.
    size = ' height="148"' if width in (105, 128) else ''
    pic = f'<picture><source media="(prefers-color-scheme: dark)" srcset="{raw_url("dark")}"><img src="{raw_url("light")}" alt="{esc(alt)}" width="{width}"{size} align="top"></picture>'
    return f'<a href="{esc(link)}">{pic}</a>' if link else pic


def readme():
    a = read_data('anilist'); s = read_data('steam'); g = read_data('github')
    lines = [image_md('design/hero', 'Duke486 的个人主页，Miku 与玉子的水蓝薄荷色插画', 800), '',
             '> ~~24601♪~~ 雾', '',
             '**CS 毕业生，喜欢 ACGN 文化，PT 玩家。**', '',
             image_md('design/typing', 'Nyaa(=・ω・=)~ 这里是 Duke486！ / Meow( · ω · )~ here is Duke486!', 440), '',
             '[✉ 欢迎来信](mailto:'+CONFIG['email']+') · [AniList](https://anilist.co/user/Duke486/) · [Steam](https://steamcommunity.com/profiles/'+CONFIG['steam_id']+'/)', '',
             image_md('design/section-projects', 'Projects', 260), '', '<p>']
    for p in CONFIG['projects']:
        url = f'https://github.com/{CONFIG["github"]}/{p["name"]}'
        lines += [image_md('github/'+p['name'], p['name']+'：'+p['description'], 400, url)]
    lines += ['</p>', '', image_md('design/section-community', 'Community', 260), '',
              image_md('github/hdu-cs-wiki', '社区贡献：camera-2018 / hdu-cs-wiki', 400, 'https://github.com/camera-2018/hdu-cs-wiki'), '',
              image_md('design/section-steam', 'Play time', 260), '', '<p>']
    for index, game in enumerate(s.get('games', [])):
        lines += [image_md('steam/game-'+str(index), game['name'], 128, 'https://store.steampowered.com/app/'+str(game['appid'])+'/')]
    lines += ['</p>', '', image_md('design/section-favorites', 'Favorites', 260), '', '<p>']
    for index, media in enumerate(a.get('favorites', [])):
        lines += [image_md('anilist/favorite-'+str(index), media_title(media), 128, media['siteUrl'])]
    lines += ['</p>', '', image_md('design/section-reading', 'On my bookshelf', 260), '', '<p>']
    for index, entry in enumerate(a.get('reading', [])):
        media = entry['media']
        lines += [image_md('anilist/reading-'+str(index), media_title(media)+' · 已读 '+str(entry['progress'])+' 话', 128, media['siteUrl'])]
    lines += ['</p>', '']
    if not a.get('reading'):
        lines += ['暂时没有公开的在读记录。[前往 AniList](https://anilist.co/user/Duke486/)。', '']
    lines += [image_md('design/section-characters', 'Favorite characters', 260), '', '<p>']
    for index, char in enumerate(a.get('characters', [])):
        name = char['name'].get('native') or char['name']['full']
        lines += [image_md('anilist/character-'+str(index), name, 105, char['siteUrl'])]
    lines += ['</p>', '', image_md('design/section-trakt', 'Movie nights', 260), '', image_md('design/trakt', 'Trakt · duke486', 320, 'https://app.trakt.tv/profile/duke486?share=true'), '',
              image_md('design/section-github', 'GitHub', 260), '', '<p>', image_md('github/stats', 'Duke486 的 GitHub 统计', 400, 'https://github.com/Duke486'),
              image_md('github/languages', '公开仓库语言分布，隐藏 Python', 400, 'https://github.com/Duke486?tab=repositories'), '</p>', '',
              '']
    content = '\n'.join(lines)
    raw_prefix = f'https://raw.githubusercontent.com/{CONFIG["github"]}/{CONFIG["github"]}/main/'
    for url in re.findall(r'(?:src|srcset)="([^\"]+)"', content):
        if not url.startswith(raw_prefix):
            raise ValueError('README image is not hosted in this repository')
        rel = url[len(raw_prefix):].split('?', 1)[0]
        if not (ROOT / rel).is_file():
            raise ValueError('Missing README image: '+rel)
    (ROOT/'README.md').write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['design','interests','readme','publish-github','validate'])
    args = parser.parse_args()
    if args.command == 'design': design()
    elif args.command == 'readme': readme()
    elif args.command == 'publish-github':
        directory = ROOT / '.staging' / 'github'
        expected = {'stats','languages','hdu-cs-wiki'} | {p['name'] for p in CONFIG['projects']}
        names = {f'{name}.{theme}.svg' for name in expected for theme in CONFIG['themes']} | {'data.json'}
        promote('github', {name: (directory/name).read_text(encoding='utf-8') for name in names})
    elif args.command == 'validate':
        for path in ASSETS.glob('*/*.svg'): validate_svg(path.read_text(encoding='utf-8'))
        readme()
        print('All static SVGs and README references validated.')
    else:
        failures = []
        for name, func in [('anilist',anilist),('steam',steam)]:
            try:
                func(); print(name+': healthy snapshot saved')
            except Exception as error:
                # Do not echo response bodies or credentials.
                failures.append(name)
                print(f'::error::{name} update failed ({type(error).__name__}); previous snapshot retained.')
        if failures: sys.exit(1)


if __name__ == '__main__': main()
