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
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="20" fill="url(#wash)" stroke="#{t['line']}"/>
{body}</svg>'''


def picture(uri, x, y, width, height, ident='cover', radius=12):
    return f'<defs><clipPath id="{ident}"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}"/></clipPath></defs><image href="{uri}" x="{x}" y="{y}" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{ident})"/>'


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
            body = picture(covers[media['id']], 18, 18, 99, 142)
            body += text(136, 39, 'READING  /  在读', 13, 'mint', 600, theme)
            for n, line in enumerate(wrap(media_title(media), 23, 2)):
                body += text(136, 71 + n*24, line, 18, 'ink', 600, theme)
            progress = f"已读 {entry['progress']} 话" + (f" / {media['chapters']}" if media.get('chapters') else '')
            body += text(136, 127, progress, 16, 'muted', theme=theme)
            body += text(136, 154, today(), 12, 'muted', theme=theme)
            files[f'reading-{index}.{theme}.svg'] = card(380, 178, media_title(media)+' · '+progress, body, theme)
        for index, char in enumerate(characters):
            name = char['name'].get('native') or char['name']['full']
            body = picture(portraits[char['id']], 10, 10, 132, 155, radius=13)
            for n, line in enumerate(wrap(name, 16, 2)):
                body += text(76, 188+n*21, line, 15, 'ink', 500, theme, 'middle')
            files[f'character-{index}.{theme}.svg'] = card(152, 220, name, body, theme)
        for index, media in enumerate(favorites):
            category = 'FAVORITE ANIME' if index == 0 and user['favourites']['anime']['nodes'] else 'FAVORITE MANGA'
            body = picture(favorite_images[media['id']], 18, 18, 99, 140)
            body += text(136, 42, category, 12, 'mint', 600, theme)
            for n, line in enumerate(wrap(media_title(media), 23, 3)):
                body += text(136, 76+n*24, line, 18, 'ink', 600, theme)
            files[f'favorite-{index}.{theme}.svg'] = card(380, 176, media_title(media), body, theme)
    files['data.json'] = json.dumps({'date': today(), 'id': user['id'], 'name': user['name'], 'reading': reading, 'characters': characters, 'favorites': favorites}, ensure_ascii=False, indent=2)
    promote('anilist', files)


def steam_official(key):
    base = 'https://api.steampowered.com/'
    query = urllib.parse.urlencode({'key': key, 'steamids': CONFIG['steam_id']})
    players = json_request(base+'ISteamUser/GetPlayerSummaries/v2/?'+query)['response']['players']
    if not players or players[0]['steamid'] != CONFIG['steam_id']:
        raise SourceError('Steam returned no matching player')
    query = urllib.parse.urlencode({'key': key, 'steamid': CONFIG['steam_id'], 'count': 2})
    result = json_request(base+'IPlayerService/GetRecentlyPlayedGames/v1/?'+query)['response']
    if not isinstance(result, dict) or 'total_count' not in result:
        raise SourceError('Recent games unavailable or private')
    games = [{'name': g['name'], 'appid': g['appid'], 'hours': round(g.get('playtime_forever', 0)/60,1),
              'image': f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{g['appid']}/capsule_184x69.jpg"} for g in result.get('games', [])[:2]]
    return {'name': players[0]['personaname'], 'avatar': players[0]['avatarfull'], 'games': games, 'source': 'steam_web_api', 'label': '最近游戏', 'note': None}


def steam_community():
    raw, _ = request(f'https://steamcommunity.com/profiles/{CONFIG["steam_id"]}/?xml=1')
    doc = ET.fromstring(raw)
    if doc.findtext('steamID64') != CONFIG['steam_id'] or doc.findtext('privacyState') != 'public':
        raise SourceError('Steam public profile unavailable')
    games = []
    for game in doc.findall('./mostPlayedGames/mostPlayedGame')[:2]:
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
    data['note'] = reason
    data['date'] = today()
    data['steam_id'] = CONFIG['steam_id']
    avatar = image_uri(data['avatar'])
    images = [image_uri(g['image']) for g in data['games']]
    files = {}
    for theme in CONFIG['themes']:
        body = picture(avatar, 22, 22, 54, 54, radius=27)
        body += text(92, 45, data['name'], 23, 'ink', 600, theme)
        body += text(92, 69, 'STEAM  /  '+data['label'], 13, 'muted', theme=theme)
        y = 102
        for index, game in enumerate(data['games']):
            body += picture(images[index], 22, y, 154, 60, 'game'+str(index), 9)
            for n, line in enumerate(wrap(game['name'], 23, 2)):
                body += text(192, y+20+n*21, line, 17, 'ink', 500, theme)
            body += text(192, y+62, str(game['hours'])+' h 总时长', 13, 'muted', theme=theme)
            y += 90
        if not data['games']:
            body += text(22, 133, '最近没有公开的游戏记录。', 17, 'muted', theme=theme)
            y = 166
        body += text(22, y+5, '档案快照 · '+today(), 12, 'muted', theme=theme)
        files[f'steam.{theme}.svg'] = card(420, y+28, 'Steam · '+data['name']+' · '+data['label'], body, theme)
    files['data.json'] = json.dumps(data, ensure_ascii=False, indent=2)
    promote('steam', files)


def design():
    art = 'data:image/png;base64,' + base64.b64encode((ASSETS/'art/miku-tamako.png').read_bytes()).decode()
    files = {}
    for theme, colors in CONFIG['themes'].items():
        body = '<defs><linearGradient id="title"><stop stop-color="#3BB4E6"/><stop offset="1" stop-color="#24B99F"/></linearGradient></defs>'
        body += f'<circle cx="830" cy="-15" r="235" fill="#{colors["blue"]}" opacity=".05"/><circle cx="45" cy="295" r="140" fill="#{colors["mint"]}" opacity=".06"/>'
        body += text(44, 61, 'WELCOME TO MY LITTLE CORNER', 17, 'mint', 600, theme)
        body += '<text x="40" y="162" font-size="90" font-weight="700" fill="url(#title)">Duke486</text>'
        body += text(46, 215, 'Nyaa(=・ω・=)~   Meow( · ω · )~', 25, 'ink', 500, theme)
        body += text(46, 266, 'CODE  /  ACGN  /  PT', 17, 'muted', 500, theme)
        body += f'<image href="{art}" x="594" y="5" width="346" height="300" preserveAspectRatio="xMidYMid meet"/>'
        files[f'hero.{theme}.svg'] = card(960, 320, 'Duke486 · Nyaa! Meow! · Code, ACGN and PT', body, theme)
    promote('design', files)


def read_data(module):
    path = ASSETS / module / 'data.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def image_md(path, alt, width, link=None):
    def raw_url(theme):
        file = ASSETS / f'{path}.{theme}.svg'
        version = hashlib.sha256(file.read_bytes()).hexdigest()[:12]
        return f'https://raw.githubusercontent.com/{CONFIG["github"]}/{CONFIG["github"]}/main/assets/{path}.{theme}.svg?v={version}'
    pic = f'<picture><source media="(prefers-color-scheme: dark)" srcset="{raw_url("dark")}"><img src="{raw_url("light")}" alt="{esc(alt)}" width="{width}" align="top"></picture>'
    return f'<a href="{esc(link)}">{pic}</a>' if link else pic


def readme():
    a = read_data('anilist'); s = read_data('steam'); g = read_data('github')
    lines = [image_md('design/hero', 'Duke486 的个人主页，Miku 与玉子的水蓝薄荷色插画', 960), '',
             '# Hi, I’m Duke486 👋', '', '> ~~24601♪~~ 雾', '',
             '**CS 毕业生，喜欢 ACGN 文化，PT 玩家。**', '',
             'Nyaa(=・ω・=)~ 这里是 Duke486！Meow( · ω · )~ here is Duke486!', '',
             '[✉ 欢迎来信](mailto:'+CONFIG['email']+') · [AniList](https://anilist.co/user/Duke486/) · [Steam](https://steamcommunity.com/profiles/'+CONFIG['steam_id']+'/)', '',
             '## 01 / Projects', '', '写一点代码，做一点喜欢的东西。', '', '<p>']
    for p in CONFIG['projects']:
        url = f'https://github.com/{CONFIG["github"]}/{p["name"]}'
        lines += [image_md('github/'+p['name'], p['name']+'：'+p['description'], 400, url)]
    lines += ['</p>', '', '<details>', '<summary>项目导航 · 文字版</summary>', '']
    for p in CONFIG['projects']:
        lines += [f'- [{p["name"]}](https://github.com/{CONFIG["github"]}/{p["name"]}) — {p["description"]}']
    lines += ['', '</details>', '', '### Community contribution', '',
              '[HDU 计算机科学讲义 · camera-2018/hdu-cs-wiki](https://github.com/camera-2018/hdu-cs-wiki)', '',
              image_md('github/hdu-cs-wiki', '社区贡献：camera-2018 / hdu-cs-wiki', 400, 'https://github.com/camera-2018/hdu-cs-wiki'), '',
              '## 02 / Off the keyboard', '', '游戏、漫画，还有喜欢的角色。', '', '### Steam', '',
              image_md('steam/steam', 'Steam 游戏档案 · Duke', 420, 'https://steamcommunity.com/profiles/'+CONFIG['steam_id']+'/'), '',
              '### A few favorites', '', '<p>']
    for index, media in enumerate(a.get('favorites', [])):
        lines += [image_md('anilist/favorite-'+str(index), media_title(media), 380, media['siteUrl'])]
    lines += ['</p>', '', '### Currently reading', '', '<p>']
    for index, entry in enumerate(a.get('reading', [])):
        media = entry['media']
        lines += [image_md('anilist/reading-'+str(index), media_title(media)+' · 已读 '+str(entry['progress'])+' 话', 380, media['siteUrl'])]
    lines += ['</p>', '']
    if not a.get('reading'):
        lines += ['暂时没有公开的在读记录。[前往 AniList](https://anilist.co/user/Duke486/)。', '']
    lines += ['### Favorite characters', '', '<p>']
    for index, char in enumerate(a.get('characters', [])):
        name = char['name'].get('native') or char['name']['full']
        lines += [image_md('anilist/character-'+str(index), name, 140, char['siteUrl'])]
    lines += ['</p>', '', '收藏与进度来自 [AniList](https://anilist.co/user/Duke486/)，保留原站排序。', '',
              '## 03 / GitHub', '', '<p>', image_md('github/stats', 'Duke486 的 GitHub 统计', 400, 'https://github.com/Duke486'),
              image_md('github/languages', '公开仓库语言分布，隐藏 Python', 400, 'https://github.com/Duke486?tab=repositories'), '</p>', '',
              '<sub>语言分布来自公开源码仓库，不代表熟练程度；延续原设置隐藏 Python。</sub>', '',
              '---', '', '<sub>最近成功更新：GitHub '+g.get('date','待更新')+' · AniList '+a.get('date','待更新')+' · Steam '+s.get('date','待更新')+'。每日生成，数据以来源为准。</sub>', '',
              '<sub>水蓝与薄荷之间，继续做喜欢的事。 · [素材来源与维护说明](./docs/MAINTENANCE.md)</sub>', '']
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
