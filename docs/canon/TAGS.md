# docs/canon/TAGS.md — the canon tag vocabulary

> **The recommended palette of tags for canon facts.** Tags let the writers' room narrow canon by
> topic (D2): the structured path (`store.canon_by_tags`) matches a fact's tags against a topic, and
> they complement semantic (meaning-based) recall. This file is the authoring **reference** —
> "what tags can I use?" — and the conventions that keep them working. See `README.md` §5 for where
> the tag bullet goes in a fact.

---

## 1. The rules (these are the only hard ones)

Tags are **free-form** — there is **no enforced allow-list in code**. The parser just splits your
comma list; matching is plain set-overlap. So you can invent a tag any time. Two conventions keep
them actually matchable:

1. **Lowercase, single words.** `loneliness`, `relay`, `festival`. **No spaces, no hyphens, no
   capitals.** The query side lowercases a topic and splits it on every non-alphanumeric character,
   so a topic "deep space" becomes `deep` + `space` and "Lumen-Festival" becomes `lumen` + `festival`.
   A tag must be one of *those* tokens to match — `lumen-festival` or `Deep Space` as a tag never will.
   Use two single-word tags instead (`lumen, festival`).
2. **Format:** an indented `- **Tags:**` child bullet **directly under** the numbered fact, with **no
   blank line** between the fact and the bullet (a blank line ends the fact and orphans the tags):

   ```markdown
   1. Travel between worlds takes weeks; radio is the thread that connects them.
      - **Tags:** travel, distance, radio, connection, isolation
   ```

That's it. Get the format wrong and `make seed-canon` **fails loud** (it won't silently corrupt
anything) — so you can't quietly break the system with a tag.

**Tips:** prefer 4–10 tags per fact; reuse existing tags from the palette below before coining a new
one (consistency is what makes a topic match across facts); tag for the *themes a DJ segment is about*
(emotions, places, ideas), not just the literal nouns in the sentence.

---

## 2. The palette (grouped by theme)

Pick from these first. A tag can belong to several themes (e.g. `ritual` is both daily-life and
faith) — that's fine. This list grows: add a new word here when you coin one, so the palette stays
the shared vocabulary.

**Place & distance** — `settlements`, `worlds`, `core`, `frontier`, `between`, `dark`, `void`,
`station`, `relay`, `ship`, `route`, `orbit`, `home`, `earth`, `place`, `distance`, `scale`,
`isolation`, `journey`, `neutrality`, `edge`, `zone`, `position`, `halo`, `geography`, `space`,
`environment`, `traffic`, `navigation`, `port`, `capital`, `night`, `darkness`, `ice`, `storm`,
`weather`, `thaw`, `empty`, `gardens`, `lighthouse`

**Named places** (one tag per named world/station — see `06-gazetteer.md`) — `concordance`,
`meridian`, `cold`, `harbor` (Cold Harbor splits into two tags), `forge`, `halcyon`, `ashfall`

**Time & history** — `time`, `clock`, `calendar`, `reckoning`, `founding`, `history`, `past`, `era`,
`age`, `memory`, `origins`, `diaspora`, `change`, `loss`, `anniversary`, `rhythm`, `synchrony`,
`simultaneity`, `scattered`, `continuity`, `expansion`, `reconnection`, `archaeology`, `archives`,
`preservation`, `remembrance`, `memorial`, `legend`, `myth`, `mythology`, `exodus`, `lesson`,
`record`, `week`, `future`, `permanence`, `impermanence`, `figures`, `anonymity`, `absence`,
`honour`

**People & society** — `humanity`, `peoples`, `identity`, `kinship`, `family`, `community`,
`belonging`, `generations`, `migration`, `adaptation`, `strangers`, `neighbours`, `djs`,
`children`, `elders`, `household`, `gender`, `body`, `gravity`, `heavy`, `prejudice`,
`difference`, `variety`, `subculture`, `culture`, `society`, `social`, `crew`, `captain`,
`learning`, `education`

**Feeling & theme** (the emotional palette) — `loneliness`, `solitude`, `longing`, `hope`, `wonder`,
`awe`, `grief`, `mourning`, `comfort`, `warmth`, `nostalgia`, `companionship`, `melancholy`, `joy`,
`courage`, `kindness`, `separation`, `waiting`, `silence`, `endurance`, `patience`, `trust`,
`humility`, `optimism`, `acceptance`, `uncertainty`, `curiosity`, `love`, `luck`, `humour`,
`safety`, `precious`, `hardship`

**Communication & the station** — `radio`, `broadcast`, `signal`, `message`, `messages`, `letters`,
`correspondence`, `news`, `connection`, `lag`, `delay`, `dedications`, `listeners`, `voice`,
`communication`, `network`, `infrastructure`, `queue`, `encryption`, `routing`, `recording`,
`library`, `programming`, `observatory`, `dome`, `telescope`, `beacon`, `reporting`, `currents`,
`field`, `chorus`, `listening`

**Governance & law** — `governance`, `polity`, `autonomy`, `council`, `compact`, `legitimacy`,
`law`, `justice`, `rights`, `freedom`, `custom`, `order`, `exile`, `authority`, `institution`,
`politics`, `nations`, `enforcement`, `treaty`, `constitution`, `federalism`, `delegate`, `state`,
`bureaucracy`, `corporation`, `cooperative`, `protectorate`, `freehold`, `consent`, `sanction`,
`dispute`, `voluntary`, `crime`, `harm`, `punishment`, `restoration`, `individual`, `contract`,
`code`, `market`

**Economy & material** — `trade`, `scarcity`, `abundance`, `currency`, `fortune`, `resources`,
`labour`, `work`, `inequality`, `local`, `cost`, `economy`, `debt`, `credit`, `exchange`, `money`,
`value`, `mass`, `transport`, `shipping`, `convoy`, `cargo`, `fuel`, `cartel`, `syndicate`,
`salvage`, `investment`, `risk`, `luxury`, `essentials`, `hierarchy`, `dependence`, `funding`,
`gift`, `aid`, `mutual`, `industry`, `materials`, `knowledge`, `information`, `power`, `control`

**Conflict & peace** — `conflict`, `war`, `peace`, `mediation`, `blockade`, `embargo`, `piracy`,
`danger`, `scars`, `siege`, `strategy`, `vulnerability`, `management`, `wisdom`, `cause`,
`tragedy`, `warning`

**Daily life & ritual** — `daily`, `food`, `rest`, `sleep`, `morning`, `leisure`, `ritual`,
`hospitality`, `festival`, `celebration`, `tradition`, `lamps`, `lumen`, `lights`, `annual`,
`togetherness`, `unity`, `shared`, `midnight`, `newyear`, `survival`, `maintenance`, `repair`,
`shift`, `competence`, `constraint`, `sensory`, `reunion`, `renewal`, `monthly`, `manual`

**Games & play** — `sports`, `games`, `play`, `competition`, `drama`, `commentary`, `dance`,
`hollowball`, `racing`, `circuits`, `season`, `team`, `amateur`, `wager`, `host`

**Knowledge & learning** — `knowledge`, `school`, `education`, `curriculum`, `academy`,
`practical`, `teaching`, `scholars`, `circuit`, `apprenticeship`, `casebook`, `research`,
`verification`, `replication`, `twin`, `profession`, `refusal`

**Language, arts & music** — `language`, `dialect`, `drift`, `words`, `naming`, `fossil`, `habit`,
`story`, `stories`, `art`, `performance`, `scene`, `music`, `song`, `poetry`, `instrument`,
`genre`, `literature`, `novel`, `theatre`, `sculpture`, `visual`, `speculation`, `curation`,
`canon`, `review`, `authenticity`, `aesthetics`, `interpretation`, `vocabulary`, `loanword`,
`translation`, `grammar`, `speech`, `standard`, `movements`, `orchestra`, `minimalism`,
`improvisation`, `sound`, `signature`, `collaboration`, `legacy`, `revival`, `rediscovery`

**Faith & meaning** — `faith`, `belief`, `sacred`, `rite`, `religion`, `meaning`, `light`, `doubt`,
`pilgrimage`, `theology`, `philosophy`, `mysticism`, `secular`, `humanism`, `covenant`,
`orthodoxy`, `creed`, `wayfarers`, `duty`, `liminality`, `reverence`, `consciousness`, `death`,
`question`, `depth`

**Technology & cosmos** — `technology`, `travel`, `limits`, `machines`, `automation`, `energy`,
`medicine`, `reliability`, `ethics`, `science`, `physics`, `fusion`, `cosmos`, `stars`, `sky`,
`mystery`, `sublime`, `discovery`, `rumour`, `reactor`, `generator`, `backup`, `simplicity`,
`durability`, `complexity`, `engineering`, `skill`, `innovation`, `biology`, `biosphere`,
`native`, `nature`, `life`, `protection`, `aliens`, `eclipse`, `astronomy`, `observation`,
`unknown`, `imagination`, `expansion`, `exploration`

---

## 3. Coining a new tag

You don't need permission from the code — just:

1. Make it a **lowercase single word** (rule 1 above).
2. **Add it to the palette** in §2 under the closest theme, so the next fact reuses it instead of a
   near-synonym (consistency is the whole point of a controlled vocabulary).
3. Re-run `make seed-canon`; confirm a topic that should hit it does:
   `store.canon_by_tags(conn, ["yourtag"])` returns the fact.

Avoid near-duplicates (`ship` vs `ships`, `letter` vs `letters`) — pick one form and stick to it.
The palette above uses the plural where a fact naturally would (`letters`, `worlds`, `settlements`).

---

## 4. The census (keeping the palette honest)

The palette drifts: writers coin tags mid-fact and forget to add them here. Periodically run the
census below; any tag it reports that deserves reuse goes into a §2 group (and any near-duplicate
pair it exposes — `ship`/`ships` — gets collapsed to the palette form across the files).

```bash
.venv/bin/python - <<'PY'
import re
from pathlib import Path
sec = Path('docs/canon/TAGS.md').read_text().split('## 2.')[1].split('## 3.')[0]
pal = set(re.findall(r'`([a-z0-9]+)`', sec))
used = {}
for p in sorted(Path('docs/canon').glob('[0-9]*.md')):
    for ln in p.read_text().splitlines():
        if '**Tags:**' in ln:
            for t in re.findall(r'[a-z0-9]+', ln.split('**Tags:**')[1]):
                used[t] = used.get(t, 0) + 1
missing = sorted((t for t in used if t not in pal), key=lambda t: (-used[t], t))
print(f"palette={len(pal)} used={len(used)} not-in-palette={len(missing)}")
print(', '.join(f"{t}({used[t]})" for t in missing))
PY
```

A one-off tag on a single fact is fine left out of the palette — the census is for spotting tags
that recur (or should) without a shared spelling.
