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
`isolation`, `journey`, `neutrality`

**Time & history** — `time`, `clock`, `calendar`, `reckoning`, `founding`, `history`, `past`, `era`,
`age`, `memory`, `origins`, `diaspora`, `change`, `loss`, `anniversary`, `rhythm`, `synchrony`,
`simultaneity`, `scattered`

**People & society** — `humanity`, `peoples`, `identity`, `kinship`, `family`, `community`,
`belonging`, `generations`, `migration`, `adaptation`, `strangers`, `neighbours`, `djs`

**Feeling & theme** (the emotional palette) — `loneliness`, `solitude`, `longing`, `hope`, `wonder`,
`awe`, `grief`, `mourning`, `comfort`, `warmth`, `nostalgia`, `companionship`, `melancholy`, `joy`,
`courage`, `kindness`, `separation`, `waiting`, `silence`

**Communication & the station** — `radio`, `broadcast`, `signal`, `message`, `messages`, `letters`,
`correspondence`, `news`, `connection`, `lag`, `delay`, `dedications`, `listeners`, `voice`,
`communication`

**Governance & law** — `governance`, `polity`, `autonomy`, `council`, `compact`, `legitimacy`,
`law`, `justice`, `rights`, `freedom`, `custom`, `order`, `exile`

**Economy & material** — `trade`, `scarcity`, `abundance`, `currency`, `fortune`, `resources`,
`labour`, `work`, `inequality`, `local`, `cost`

**Conflict & peace** — `conflict`, `war`, `peace`, `mediation`, `blockade`, `piracy`, `danger`,
`scars`

**Daily life & ritual** — `daily`, `food`, `rest`, `sleep`, `morning`, `leisure`, `ritual`,
`hospitality`, `festival`, `celebration`, `tradition`, `lamps`, `lumen`, `lights`, `annual`,
`togetherness`, `unity`, `shared`, `midnight`, `newyear`

**Language, arts & music** — `language`, `dialect`, `drift`, `words`, `naming`, `fossil`, `habit`,
`story`, `art`, `performance`, `scene`, `music`, `song`, `poetry`, `instrument`, `genre`

**Faith & meaning** — `faith`, `belief`, `sacred`, `rite`, `religion`, `meaning`, `light`, `doubt`,
`pilgrimage`

**Technology & cosmos** — `technology`, `travel`, `limits`, `machines`, `automation`, `energy`,
`medicine`, `reliability`, `ethics`, `science`, `physics`, `fusion`, `cosmos`, `stars`, `sky`,
`mystery`, `sublime`, `discovery`, `rumour`

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
