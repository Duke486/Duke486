import fs from 'node:fs/promises';
import { api, pin, topLangs, logger, loadConfigFromEnv } from '@stats-organization/github-readme-stats-core';

// Same maintained renderers used by github-readme-stats-action, installed once per run.
const config = JSON.parse(await fs.readFile(new URL('../profile.json', import.meta.url), 'utf8'));
const token = process.env.GITHUB_TOKEN;
const bootstrap = process.env.BOOTSTRAP_PUBLIC === '1';
if (!token && !bootstrap) throw new Error('GITHUB_TOKEN is required; no public-host fallback in scheduled builds.');
logger.error = () => {}; // HTTP client errors can include authorization headers.
loadConfigFromEnv({ PAT_1: token || '', FETCH_MULTI_PAGE_STARS: 'true' });
const directory = new URL('../.staging/github/', import.meta.url);
await fs.mkdir(directory, {recursive:true});
const cards = [
  ['stats', api, {username: config.github, custom_title: 'GitHub stats', hide_rank:'true', show_icons:'true', line_height:'27', contribs_include_own_repos:'true'}, '/api'],
  ['languages', topLangs, {username: config.github, layout:'compact', langs_count:'6', hide:config.hidden_languages.join(','), custom_title:'Languages'}, '/api/top-langs/'],
  ...config.projects.map(p => [p.name, pin, {username:config.github, repo:p.name}, '/api/pin/']),
  ['hdu-cs-wiki', pin, {username:'camera-2018',repo:'hdu-cs-wiki',show_owner:'true'}, '/api/pin/']
];
for (const [name, renderer, options, route] of cards) {
  for (const [theme, t] of Object.entries(config.themes)) {
    const query = {...options, card_width:'400', title_color:t.blue, text_color:t.ink, icon_color:t.mint,
      bg_color:t.background, border_color:t.line, border_radius:'6', disable_animations:'true', description_lines_count:'3'};
    let result;
    if (bootstrap) {
      const response = await fetch('https://github-stats-extended.vercel.app'+route+'?'+new URLSearchParams(query), {signal:AbortSignal.timeout(45000)});
      if (!response.ok) throw new Error(`Bootstrap ${name}: HTTP ${response.status}`);
      result = {status:'success',content:await response.text()};
    } else {
      result = await renderer(query, token);
    }
    if (result.status !== 'success' || !result.content?.includes('<svg') || /Something went wrong|API error|Bad credentials/i.test(result.content)) {
      throw new Error(`${name}/${theme}: renderer did not produce a healthy card; old module retained.`);
    }
    await fs.writeFile(new URL(`${name}.${theme}.svg`, directory), result.content);
    console.log(`Generated ${name}/${theme}`);
  }
}
await fs.writeFile(new URL('data.json', directory), JSON.stringify({date:new Date().toISOString().slice(0,10), generator:'github-stats-extended',version:'2.2.0',source:bootstrap?'public-bootstrap':'github-actions',scope:'public repositories'},null,2));
