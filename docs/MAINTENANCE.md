# Profile maintenance

水蓝 × Miku 绿，明暗双主题。简介文字与项目配置在 `profile.json` 和 `scripts/profile.py` 中；README 由脚本生成，修改正文时请同时修改模板。

2026-09-15：兴趣区改为 128 × 148 的无描边彩色收藏卡；恢复中英文交替打字机；Steam 固定四款已核实游戏。当前设计与验收规则见 [DESIGN.md](DESIGN.md)。

## Sources and credits

- GitHub cards: [GitHub Stats Extended](https://github.com/stats-organization/github-stats-extended), MIT. This repository installs `@stats-organization/github-readme-stats-core@2.2.0`, the maintained renderer used by its official Action. A single Node process generates every theme and card, avoiding fourteen repeated Action installations. The npm lockfile pins transitive dependencies.
- AniList: official GraphQL API, user ID **5123998**. Current reading and favorites follow the source account. Cover art and character portraits belong to their respective rights holders; their source URLs and item links are retained in `assets/anilist/data.json`. Images are embedded in the generated SVGs so profile visitors do not need to contact image hosts.
- Steam: official Web API when `STEAM_TOKEN` is valid. If unavailable, the generator reads the public Steam Community XML and records that source in the snapshot metadata. This fallback does not claim live status or a precise two-week ranking. It displays lifetime hours from the source. The source and fallback reason are recorded in `assets/steam/data.json`.
- Hero decoration: **AI-generated fan art**, using the built-in image generation tool; Hatsune Miku and Tamako Kitashirakawa are owned by their respective rights holders. It is decorative fan art, not an official illustration. Original generated PNG: `assets/art/miku-tamako.png`. The generation prompt is preserved in `docs/ART-PROMPT.md`.
- Layout, glue code and custom interest cards were created for this profile. No code was copied from the evaluated Steam-card or AniCards projects.

## Automated updates

The `Refresh profile cards` workflow runs at **09:23 Asia/Shanghai** daily and can be run manually from Actions. It uses Node 24, Python 3.13, a pinned npm core version and pinned third-party Action SHAs.

GitHub data uses the automatically issued `GITHUB_TOKEN`; the old `METRICS_TOKEN` is no longer used. The workflow retains the existing `production` environment to access its `STEAM_TOKEN`. No secrets are stored in the source or generated files. Public repository language statistics continue to exclude Python as in the original profile; language proportions are not a measure of proficiency. GitHub contribution totals follow what the public profile/API exposes, including any anonymized contributions made public by profile settings; no private repository credential is supplied to the generator.

To restore the official Steam route, replace `STEAM_TOKEN` under repository **Settings → Environments → production → Environment secrets**, then run the workflow. Do not paste it into README, workflow YAML, issues or logs. The existing public fallback keeps the profile usable while a key is unavailable.

Each module is fully generated and validated before replacing its last healthy snapshot. A 200 response containing a GraphQL error or error SVG is rejected. A failed module keeps its last healthy data and the final workflow reports the failure, while healthy modules may still publish. Steam's successful, explicitly labeled public fallback is a warning, not a broken module. Dates in each module data.json show the successful source snapshot. Each Steam game also records observed_at; older verified games fill missing recent slots, so four games remain visible without claiming all four are currently recent.

Generated SVGs contain embedded cover/portrait bytes. Generation needs network access; viewing does not depend on a public card-generation server. Existing cards remain visible if a source or scheduled workflow stops. GitHub can disable scheduled workflows after 60 days without repository activity; re-enable the workflow and run it manually when needed. This repo does not add fake activity to circumvent that rule.

README images use explicit `raw.githubusercontent.com` URLs to avoid GitHub's relative-path redirect route. A short SHA-256 query parameter changes only when the image bytes change, so updated cards get a fresh cache key. Both theme versions are checked against local files before publishing the README.

## Local commands

```sh
npm ci --ignore-scripts
python -m unittest discover -s tests -v
# Set GITHUB_TOKEN in the environment, then:
node scripts/github.mjs
python scripts/profile.py publish-github
python scripts/profile.py interests
python scripts/profile.py design
python scripts/profile.py validate
```

`STEAM_TOKEN` is optional for local generation. `.cache/`, `.staging/` and `node_modules/` are ignored. A public-service bootstrap exists only for initial local previews via `BOOTSTRAP_PUBLIC=1`; scheduled builds never silently switch GitHub cards to a public host.

Rollback: revert the migration commit to restore the old README/workflow and SVG files. Old assets remain in Git history; no history rewrite is required. To stop new updates temporarily, disable `Refresh profile cards` in Actions.

## Trakt

Profile: https://app.trakt.tv/profile/duke486?share=true . On 2026-09-15 the public page explicitly reports a private profile. [Trakt-Widgets-2](https://github.com/pizidavi/Trakt-Widgets-2) and [LittleFox Trakt Widgets](https://foxbinner.dev/showcase/trakt-widgets) were tested with this username; both returned an empty visual instead of watch history. The README therefore uses a local illustrated profile link, not a fake recent-watch feed. A public history widget can be added if the account is made public by its owner.
