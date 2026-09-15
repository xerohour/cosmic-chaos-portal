"use strict";
/* ============================================================================
 * Cosmic Chaos Portal — client-side Archon engine.
 * A faithful port of the Python core in src/ccp/:
 *   Archon state machine + policy safety gates + router affinity + the six
 *   specialist agents (tarot, astrology, numerology, shamanic, gateway,
 *   integration). Everything is deterministic: the same intention always
 *   draws the same reading. No network calls, no dependencies.
 * ========================================================================== */

/* ---------------- deterministic randomness ---------------- */

function xfnv1a(str) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleInPlace(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function pickOne(arr, rng) {
  return arr[Math.floor(rng() * arr.length)];
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------- safety policy (port of policy.py) ---------------- */

const PATTERNS = {
  crisis: [
    /\bkill myself\b/i, /\bsuicid\w*\b/i, /\bend my life\b/i,
    /\bhurt myself\b/i, /\bself[- ]harm\b/i, /\bcutting myself\b/i,
    /\bwant to die\b/i, /\bno reason to live\b/i, /\bplan to (die|kill)\b/i,
  ],
  substance: [
    /\bdmt\b/i, /\bpsilocybin\b/i, /\bshrooms?\b/i, /\bacid\b/i, /\blsd\b/i,
    /\bayahuasca\b/i, /\bmdma\b/i, /\bmolly\b/i, /\bketamine\b/i,
    /\bcocaine\b/i, /\bheroin\b/i, /\bmeth\b/i,
    /where (can|do) i (buy|get|find).*\b(drug|weed|shroom)/i,
    /how (much|to) (take|dose|grow)/i,
  ],
  neural: [/\btdcs\b/i, /\bneurostimulat\w*\b/i, /\bbrain.?stimulat\w*\b/i],
};

function hits(patterns, text) {
  return patterns.some(p => p.test(text));
}

const UNCERTAINTY_FRAME =
  "Take this as a reflective mirror, not a prediction — symbols suggest, they never decide.";

const CRISIS_RESPONSE =
  "I'm really glad you told me. If you might act on these thoughts, please reach " +
  "out right now — call or text 988 (US Suicide and Crisis Lifeline), or contact " +
  "your local emergency number. You don't have to go through this alone, and a person " +
  "who can truly help is better than any ritual I could offer.";

const BLOCKED_SUBSTANCE_RESPONSE =
  "I can't help with acquiring, dosing, growing, or using controlled substances. " +
  "If you'd like, I can offer grounding exercises, reflection prompts, or resources " +
  "for professional support instead.";

const BLOCKED_NEURAL_RESPONSE =
  "I can't recommend brain-stimulation settings or interpret biometric data. " +
  "Please consult a qualified clinician.";

/* ---------------- routing (port of router.py) ---------------- */

const TAG_AFFINITY = {
  shadow_work: ["tarot", "shamanic", "integration", "gateway"],
  relationship: ["tarot", "shamanic", "integration"],
  career: ["tarot", "numerology", "integration"],
  decision: ["tarot", "numerology", "integration"],
  purpose: ["numerology", "shamanic", "integration"],
  timing: ["astrology", "tarot", "integration"],
  grief: ["integration", "shamanic"],
  creativity: ["tarot", "gateway", "integration"],
  reflection: ["integration"],
};

const PROMPT_VERSIONS = {
  tarot: "tarot-1.3",
  astrology: "astrology-1.0",
  numerology: "numerology-1.1",
  shamanic: "shamanic-1.2",
  gateway: "gateway-1.1",
  integration: "integration-1.4",
};

/* ---------------- specialist data ---------------- */

const MAJOR_ARCANA = [
  ["The Fool", "beginnings; leaping before looking", "ambiguous"],
  ["The Magician", "agency; tools at hand", "supportive"],
  ["The High Priestess", "intuition; what is withheld", "ambiguous"],
  ["The Empress", "nurture; creative abundance", "supportive"],
  ["The Emperor", "structure; control asserted", "ambiguous"],
  ["The Hierophant", "tradition; inherited rules", "ambiguous"],
  ["The Lovers", "choice; values in relationship", "ambiguous"],
  ["The Chariot", "willpower; direction through tension", "supportive"],
  ["Strength", "gentle endurance; taming impulse", "supportive"],
  ["The Hermit", "withdrawal; inner counsel", "ambiguous"],
  ["Wheel of Fortune", "cycles; what turns without you", "ambiguous"],
  ["Justice", "accountability; cause and effect", "ambiguous"],
  ["The Hanged Man", "suspension; a new angle", "ambiguous"],
  ["Death", "endings; what must be released", "challenging"],
  ["Temperance", "integration; measured blending", "supportive"],
  ["The Devil", "attachment; the shadow contract", "challenging"],
  ["The Tower", "disruption; structures that fall", "challenging"],
  ["The Star", "hope; quiet repair", "supportive"],
  ["The Moon", "illusion; the unconscious tide", "challenging"],
  ["The Sun", "clarity; vitality returned", "supportive"],
  ["Judgement", "reckoning; answering a call", "ambiguous"],
  ["The World", "completion; the pattern seen whole", "supportive"],
];

const SPREADS = {
  shadow_work_cross: ["Root pattern", "What it protects", "What it costs", "Integration key"],
  three_card: ["Past influence", "Present shape", "Possible direction"],
};

const LETTER_VALUES = Object.assign(
  {}, ...["AIJQY"].flatMap(c => c.split("").map(ch => ({ [ch]: 1 }))),
  ...["BKR"].flatMap(c => c.split("").map(ch => ({ [ch]: 2 }))),
  ...["CLSG"].flatMap(c => c.split("").map(ch => ({ [ch]: 3 }))),
  ...["DMT"].flatMap(c => c.split("").map(ch => ({ [ch]: 4 }))),
  ...["EHNX"].flatMap(c => c.split("").map(ch => ({ [ch]: 5 }))),
  ...["UVW"].flatMap(c => c.split("").map(ch => ({ [ch]: 6 }))),
  ...["OZ"].flatMap(c => c.split("").map(ch => ({ [ch]: 7 }))),
  ...["FP"].flatMap(c => c.split("").map(ch => ({ [ch]: 8 }))),
);
const VOWELS = new Set("AEIOUY".split(""));

const NUMBER_MEANINGS = {
  1: "initiative; standing apart to begin",
  2: "receptivity; partnership and patience",
  3: "expression; voice finding form",
  4: "foundation; steady building",
  5: "change; freedom through motion",
  6: "care; responsibility in relationship",
  7: "inquiry; the inward turn",
  8: "power; material mastery",
  9: "completion; release and compassion",
  11: "illumination; heightened sensitivity (master number)",
  22: "the builder; vision made durable (master number)",
};

function reduceNum(n) {
  while (n > 9 && n !== 11 && n !== 22) {
    n = String(n).split("").reduce((a, d) => a + Number(d), 0);
  }
  return n;
}

const SIGNS = [
  ["Capricorn", [12, 22], [1, 19], "earth"],
  ["Aquarius", [1, 20], [2, 18], "air"],
  ["Pisces", [2, 19], [3, 20], "water"],
  ["Aries", [3, 21], [4, 19], "fire"],
  ["Taurus", [4, 20], [5, 20], "earth"],
  ["Gemini", [5, 21], [6, 20], "air"],
  ["Cancer", [6, 21], [7, 22], "water"],
  ["Leo", [7, 23], [8, 22], "fire"],
  ["Virgo", [8, 23], [9, 22], "earth"],
  ["Libra", [9, 23], [10, 22], "air"],
  ["Scorpio", [10, 23], [11, 21], "water"],
  ["Sagittarius", [11, 22], [12, 21], "fire"],
];
const ELEMENT_THEMES = {
  fire: ["direct action; naming what you want out loud", "supportive"],
  earth: ["steady craft; what is built slowly holds", "supportive"],
  air: ["perspective; the story can be retold", "ambiguous"],
  water: ["emotional honesty; feeling before fixing", "challenging"],
};

function sunSign(month, day) {
  for (const [name, [m1, d1], [m2, d2], element] of SIGNS) {
    if ((month === m1 && day >= d1) || (month === m2 && day <= d2)) return [name, element];
  }
  return ["Capricorn", "earth"];
}

const JOURNEYS = [
  ["the river crossing",
    "You stand at a river you have crossed a hundred times without noticing. " +
    "On the far bank, a keeper holds a lantern — not to light your way, " +
    "but to show you that you already know the stepping stones."],
  ["walking with the shadow keeper",
    "A figure walks beside you at dusk, carrying a bundle of everything " +
    "you pretend not to want. It does not ask you to open the bundle — " +
    "only to stop running from the one who carries it."],
  ["the house with many rooms",
    "You enter a house where every locked door is a version of a story " +
    "you tell. One door stands ajar. You do not have to enter; noticing " +
    "the draft is enough for today."],
  ["the garden after rain",
    "After heavy rain, a garden shows what the soil was holding. Nothing " +
    "here needs pulling up — the task is to witness what surfaces and let " +
    "the sun do its slow work."],
];
const RITUALS = [
  "Light a candle and name, aloud, one pattern you are ready to witness " +
  "without fixing. Blow it out when the naming feels complete.",
  "Place two objects on a table: one for the pattern, one for the part of " +
  "you that watches it. Sit with both for five unhurried minutes.",
  "Write the pattern a letter as if it were a tired traveler. Thank it " +
  "for how it once protected you, then set the letter aside.",
];

/* ---------------- specialists (port of agents/) ---------------- */

function runTarot(seed, spreadName) {
  const rng = mulberry32(xfnv1a(seed + "|tarot|" + spreadName));
  const positions = SPREADS[spreadName] || SPREADS.three_card;
  const deck = shuffleInPlace(MAJOR_ARCANA.slice(), rng).slice(0, positions.length);
  const themes = [], symbols = [];
  deck.forEach(([card, keywords, valence], i) => {
    const reversed = rng() < 0.25;
    const pos = positions[i];
    symbols.push({
      title: `${card} (${reversed ? "reversed" : "upright"})`,
      text: `${pos}: ${keywords}.`,
    });
    themes.push({
      id: `tarot-${card.toLowerCase().replace(/\s+/g, "-")}`,
      label: `${pos}: ${card}`,
      valence: reversed && valence === "ambiguous" ? "challenging" : valence,
      confidence: Math.round((0.55 + rng() * 0.3) * 100) / 100,
    });
  });
  themes.push({
    id: "tarot-pattern",
    label: "A repeating pattern is asking to be witnessed, not judged",
    valence: "ambiguous", confidence: 0.6,
  });
  return {
    agent: "tarot", title: "Tarot", glyph: "✦",
    themes, symbols,
    actions: [
      "Journal prompt: which of these cards feels most uncomfortable, and what might that discomfort be protecting?",
      "Reflection: name one small behavior from the spread you could experiment with changing this week.",
    ],
    warnings: ["Symbolic reading only — not a prediction of events or a statement about any person."],
  };
}

function runAstrology(seed, birthdate) {
  if (!birthdate) {
    return {
      agent: "astrology", title: "Astrology", glyph: "☽",
      themes: [], symbols: [],
      actions: [],
      warnings: ["Birth data not available; chart highlights skipped."],
    };
  }
  const [y, m, d] = birthdate.split("-").map(Number);
  const [sign, element] = sunSign(m, d);
  const [themeText, valence] = ELEMENT_THEMES[element];
  return {
    agent: "astrology", title: "Astrology", glyph: "☽",
    themes: [{ id: `astro-${sign.toLowerCase()}`, label: `Sun in ${sign} (${element} element)`, valence, confidence: 0.6 }],
    symbols: [{ title: "Sun-sign lens", text: `${sign}: ${themeText}.` }],
    actions: [`Reflection: where in your current question could a ${element}-element approach (${themeText.split(";")[0]}) help?`],
    warnings: ["Sun-sign highlights are symbolic prompts, not astrological determinations or life predictions."],
  };
}

function runNumerology(seed, name, birthdate) {
  const themes = [], symbols = [], warnings = [];
  if (birthdate) {
    const lp = reduceNum(birthdate.replace(/\D/g, "").split("").reduce((a, c) => a + Number(c), 0));
    themes.push({ id: "num-life-path", label: `Life Path ${lp}`, valence: "ambiguous", confidence: 0.65 });
    symbols.push({ title: "Life Path", text: `${lp} (from ${birthdate}): ${NUMBER_MEANINGS[lp]}.` });
  } else {
    warnings.push("No birth date available; life path not computed.");
  }
  const clean = (name || "").toUpperCase();
  if (clean.trim()) {
    let expr = 0, urge = 0;
    for (const ch of clean) {
      if (!(ch in LETTER_VALUES)) continue;
      if (VOWELS.has(ch)) urge += LETTER_VALUES[ch]; else expr += LETTER_VALUES[ch];
    }
    if (expr) {
      const e = reduceNum(expr);
      themes.push({ id: "num-expression", label: `Expression ${e}`, valence: "supportive", confidence: 0.6 });
      symbols.push({ title: "Expression", text: `${e}: ${NUMBER_MEANINGS[e]}.` });
    }
    if (urge) {
      const u = reduceNum(urge);
      symbols.push({ title: "Soul Urge", text: `${u}: ${NUMBER_MEANINGS[u]}.` });
    }
  } else {
    warnings.push("No name provided; name numbers not computed.");
  }
  warnings.push("Numerological meanings are symbolic lenses, not measurements of ability or destiny.");
  return {
    agent: "numerology", title: "Numerology", glyph: "⑨",
    themes, symbols,
    actions: ["Reflection: which of these number themes resonates — and which feels like a story you tell about yourself rather than a fact?"],
    warnings,
  };
}

function runShamanic(seed, priorThemes) {
  const rng = mulberry32(xfnv1a(seed + "|shamanic|journey"));
  const [title, journey] = pickOne(JOURNEYS, rng);
  const ritual = pickOne(RITUALS, rng);
  const anchor = priorThemes[0] || "a pattern asking for attention";
  return {
    agent: "shamanic", title: "Shamanic Guide", glyph: "❖",
    themes: [{ id: "shamanic-witness", label: "Witnessing before changing", valence: "supportive", confidence: 0.6 }],
    symbols: [{ title: `Journey image — ${title}`, text: `${journey} (woven around: ${anchor}).` }],
    actions: [
      `Small ritual: ${ritual}`,
      "Close: feel your feet on the floor, name three things you can see, and return fully to the room.",
    ],
    warnings: ["Metaphor and ritual suggestion only — not therapy, not treatment, and not a substitute for professional support."],
  };
}

function runGateway(seed) {
  return {
    agent: "gateway", title: "Gateway", glyph: "◉",
    themes: [{ id: "gateway-settle", label: "The nervous system settles before insight lands", valence: "supportive", confidence: 0.6 }],
    symbols: [
      {
        title: "Session structure — 'Gentle Witnessing' (12 min)",
        text: "Minutes 0–3: slow diaphragmatic breathing (in 4, out 6). " +
              "Minutes 3–9: quiet observation of thoughts as passing weather. " +
              "Minutes 9–12: return, stretch, journal one line.",
      },
      {
        title: "Audio outline",
        text: "Low-volume ambient drone or nature soundscape; optional binaural " +
              "layer only if you already use and tolerate it — stop if uncomfortable.",
      },
    ],
    actions: [
      "Try now: three rounds of in-for-4, out-for-6 breathing before continuing.",
      "After the session, note one sentence about what felt different — not what it 'meant'.",
    ],
    warnings: ["Non-drug relaxation practice only. Stop if you feel uncomfortable, dizzy, or distressed; this is not treatment."],
  };
}

function runIntegration(seed, priorThemes) {
  const focus = priorThemes[0] || "what surfaced for you";
  return {
    agent: "integration", title: "Integration", glyph: "⬢",
    themes: [{ id: "integration-grounding", label: "Small steps integrate better than big insights", valence: "supportive", confidence: 0.7 }],
    symbols: [{
      title: "Integration lens",
      text: `Insights about ${focus} become real through one concrete, kind action — not through understanding alone.`,
    }],
    actions: [
      "Grounding (2 min): slow breath in for 4, out for 6. Notice five things you can see, four you can hear.",
      "Journal: what is one specific, doable step related to this question you could take in the next 48 hours?",
      "If this feels heavy or stuck, consider talking it through with a trusted person, counselor, or therapist. Seeking support is a strong move.",
    ],
    warnings: [],
  };
}

const RUNNERS = {
  tarot: runTarot, astrology: runAstrology, numerology: runNumerology,
  shamanic: runShamanic, gateway: runGateway, integration: runIntegration,
};

/* ---------------- synthesis (port of synthesizer.py) ---------------- */

function composeNarrative(results, style, intentionText) {
  const lines = [];
  if (style === "spiritual") {
    lines.push("The Archon convenes the circle. From your intention — “" + intentionText + "” — the specialists return these reflections.");
  } else {
    lines.push("Here's what the specialists surfaced for your question: “" + intentionText + "”");
  }
  const allThemes = [];
  const seen = new Set();
  for (const r of results) {
    for (const t of r.themes) {
      if (seen.has(t.id)) continue;
      seen.add(t.id);
      allThemes.push({ ...t, agent: r.title });
    }
  }
  allThemes.sort((a, b) => b.confidence - a.confidence);
  if (allThemes.length) {
    lines.push("\nKey themes, ranked by resonance:");
    for (const t of allThemes.slice(0, 8)) {
      lines.push(`• ${t.label} — via ${t.agent}`);
    }
  }
  const symbols = results.flatMap(r => r.symbols.map(s => `• [${r.title}] ${s.title}: ${s.text}`));
  if (symbols.length) lines.push("\nSymbolic detail:\n" + symbols.join("\n"));
  const actions = results.flatMap(r => r.actions);
  if (actions.length) lines.push("\nSuggested actions:\n" + actions.map(a => `• ${a}`).join("\n"));
  return { narrative: lines.join("\n"), themes: allThemes.slice(0, 8) };
}

/* ---------------- UI ---------------- */

const $ = id => document.getElementById(id);
const STAGE_KEYS = ["received", "validating", "planning", "running", "aggregating", "synthesizing", "safety", "done"];
const sleep = ms => new Promise(r => setTimeout(r, ms));

function setStage(key, state) {
  document.querySelectorAll("#stages li").forEach(li => {
    if (li.dataset.stage === key) {
      li.classList.remove("active", "done", "failed");
      if (state) li.classList.add(state);
    }
  });
}
function resetStages() {
  document.querySelectorAll("#stages li").forEach(li => li.classList.remove("active", "done", "failed"));
}
function markStagesUpTo(key) {
  for (const k of STAGE_KEYS) {
    if (k === key) break;
    setStage(k, "done");
  }
}

function cardHtml({ cls = "", headGlyph = "", headTitle = "", version = "", body = "" }) {
  return `<article class="card ${cls}">
    <div class="card-head">
      <span class="glyph" aria-hidden="true">${headGlyph}</span>
      <h3>${headTitle}</h3>
      ${version ? `<span class="version">${esc(version)}</span>` : ""}
    </div>
    <div>${body}</div>
  </article>`;
}

function agentCardHtml(r) {
  const themes = r.themes.length
    ? `<div class="themes">${r.themes.map(t => `<span class="theme ${esc(t.valence)}">${esc(t.label)}</span>`).join("")}</div>` : "";
  const symbols = r.symbols.length
    ? r.symbols.map(s => `<p class="symbol"><strong>${esc(s.title)}.</strong> ${esc(s.text)}</p>`).join("") : "";
  const actions = r.actions.length
    ? `<ul>${r.actions.map(a => `<li>${esc(a)}</li>`).join("")}</ul>` : "";
  const warnings = r.warnings.length
    ? r.warnings.map(w => `<p class="warn">${esc(w)}</p>`).join("") : "";
  return cardHtml({
    headGlyph: esc(r.glyph), headTitle: esc(r.title),
    version: PROMPT_VERSIONS[r.agent] || "",
    body: themes + symbols + actions + warnings,
  });
}

function synthesisCardHtml(narrative, themes, notices, seed, runId, style) {
  const themeChips = themes.length
    ? `<div class="themes">${themes.map(t => `<span class="theme ${esc(t.valence)}">${esc(t.label)}</span>`).join("")}</div>` : "";
  const noticeHtml = notices.length
    ? `<ul>${notices.map(n => `<li>${esc(n)}</li>`).join("")}</ul>` : "";
  return cardHtml({
    cls: "synthesis", headGlyph: "✧", headTitle: "The Archon speaks",
    body: `<p class="narrative">${esc(narrative)}</p>${themeChips}
      ${noticeHtml ? `<p><strong>Notices</strong></p>${noticeHtml}` : ""}
      <p class="seed">run <code>${esc(runId)}</code> · deterministic seed <code>${seed}</code> · ${esc(style)} voice · same intention always draws the same reading</p>`,
  });
}

function blockedCardHtml(title, text, cls = "blocked-card") {
  return cardHtml({
    cls, headGlyph: "⚠", headTitle: title,
    body: `<p>${esc(text)}</p><p class="warn">${esc(UNCERTAINTY_FRAME)}</p>`,
  });
}

function crisisCardHtml() {
  return cardHtml({
    cls: "crisis-card", headGlyph: "⚠", headTitle: "A human should hold this, not a ritual",
    body: `<p>${esc(CRISIS_RESPONSE)}</p>
      <ul class="resources">
        <li>Call or text <strong>988</strong> (US Suicide and Crisis Lifeline)</li>
        <li>Outside the US: <a href="https://findahelpline.org" target="_blank" rel="noopener">findahelpline.org</a></li>
      </ul>`,
  });
}

function selectedTags() {
  return [...document.querySelectorAll('#tag-chips button[aria-pressed="true"]')]
    .map(b => b.dataset.tag);
}

function gatherConsent() {
  return {
    spiritual: $("consent-spiritual").checked,
    birthData: $("consent-birth").checked,
    traumaAdjacent: $("consent-trauma").checked,
    alteredState: $("consent-altered").checked,
  };
}

/* ---------------- the Archon loop ---------------- */

async function invoke() {
  const btn = $("invoke");
  const out = $("portal-output");
  const intentionText = $("intention").value.trim();
  const name = $("display-name").value.trim();
  const birthdate = $("birthdate").value;
  const tags = selectedTags();
  const consent = gatherConsent();
  const style = consent.spiritual ? "spiritual" : "plain";

  out.innerHTML = "";
  resetStages();
  btn.disabled = true;

  try {
    const seed = xfnv1a(intentionText.toLowerCase());
    const runId = "run-" + seed.toString(16).padStart(8, "0");
    const append = html => { out.insertAdjacentHTML("beforeend", html); };

    // RECEIVED -> VALIDATING
    setStage("received", "active"); await sleep(260);
    setStage("received", "done"); setStage("validating", "active"); await sleep(260);
    if (!intentionText) {
      setStage("validating", "failed");
      append(blockedCardHtml("Nothing to divine", "Please write an intention first — the Archon needs a question to hold."));
      return;
    }
    setStage("validating", "done");

    // Pre-routing safety gate
    if (hits(PATTERNS.crisis, intentionText)) {
      markStagesUpTo("done"); setStage("done", "failed");
      append(crisisCardHtml());
      return;
    }
    if (hits(PATTERNS.substance, intentionText)) {
      markStagesUpTo("done"); setStage("done", "failed");
      append(blockedCardHtml("Out of scope", BLOCKED_SUBSTANCE_RESPONSE));
      return;
    }
    if (hits(PATTERNS.neural, intentionText)) {
      markStagesUpTo("done"); setStage("done", "failed");
      append(blockedCardHtml("Out of scope", BLOCKED_NEURAL_RESPONSE));
      return;
    }

    // PLANNING
    setStage("planning", "active"); await sleep(420);
    const allowed = new Set(["tarot", "integration", "numerology", "astrology"]);
    if (consent.traumaAdjacent) allowed.add("shamanic");
    if (consent.alteredState) allowed.add("gateway");
    const notices = [];
    if (consent.birthData) {
      // birth-data consent present; astrology may still skip for missing date
    } else {
      allowed.delete("astrology");
      notices.push("Astrology needs birth-date consent; it was skipped.");
    }
    const selected = [];
    for (const tag of tags) {
      for (const a of (TAG_AFFINITY[tag] || [])) {
        if (!selected.includes(a) && allowed.has(a)) selected.push(a);
      }
    }
    if (selected.length && !selected.includes("integration")) selected.push("integration");
    if (!birthdate && selected.includes("astrology") && selected.includes("numerology")) {
      // keep both; they degrade gracefully with warnings
    }
    setStage("planning", "done");

    if (!selected.length) {
      setStage("done", "failed");
      append(blockedCardHtml("No specialists available",
        "No specialists are available for this request under your current consent settings."));
      return;
    }

    // RUNNING: reveal agent cards one by one (client-side stand-in for bounded fan-out)
    setStage("running", "active"); await sleep(300);
    const spread = (tags.includes("shadow_work") || tags.includes("relationship"))
      ? "shadow_work_cross" : "three_card";
    const ctx = { seed, name, birthdate: consent.birthData ? birthdate : "" };
    const results = [];
    const priorThemes = [];
    for (const agent of selected) {
      let r;
      if (agent === "tarot") r = runTarot(seed, spread);
      else if (agent === "astrology") r = runAstrology(seed, ctx.birthdate);
      else if (agent === "numerology") r = runNumerology(seed, ctx.name, ctx.birthdate);
      else if (agent === "shamanic") r = runShamanic(seed, priorThemes);
      else if (agent === "gateway") r = runGateway(seed);
      else r = runIntegration(seed, priorThemes);
      results.push(r);
      priorThemes.push(...r.themes.slice(0, 2).map(t => t.label));
      append(agentCardHtml(r));
      await sleep(560);
    }
    setStage("running", "done");

    // AGGREGATING
    setStage("aggregating", "active"); await sleep(420);
    const valid = results.filter(r => r.themes.length || r.symbols.length);
    setStage("aggregating", "done");

    // SYNTHESIZING
    setStage("synthesizing", "active"); await sleep(520);
    const { narrative, themes } = composeNarrative(valid, style, intentionText);
    setStage("synthesizing", "done");

    // SAFETY_REVIEW
    setStage("safety", "active"); await sleep(380);
    const reviewNotices = [...notices];
    let finalNarrative = narrative;
    if (style === "spiritual" && !finalNarrative.includes("reflective mirror")) {
      reviewNotices.push(UNCERTAINTY_FRAME);
    }
    setStage("safety", "done");

    // COMPLETED
    append(synthesisCardHtml(finalNarrative, themes, reviewNotices, seed, runId, style));
    setStage("done", "done");
  } finally {
    btn.disabled = false;
  }
}

/* ---------------- wiring ---------------- */

document.addEventListener("DOMContentLoaded", () => {
  $("birthdate").max = new Date().toISOString().slice(0, 10);

  document.querySelectorAll("#tag-chips button").forEach(b => {
    b.addEventListener("click", () => {
      b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") === "true" ? "false" : "true");
    });
  });

  $("invoke").addEventListener("click", invoke);
  $("intention").addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") invoke();
  });
  $("reset").addEventListener("click", () => {
    $("portal-output").innerHTML =
      `<div class="idle-card"><p>The portal is quiet. Set an intention above and the Archon will convene its specialists.</p></div>`;
    resetStages();
  });
});
