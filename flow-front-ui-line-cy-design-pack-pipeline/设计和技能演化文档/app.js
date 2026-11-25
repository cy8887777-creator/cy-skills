const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const terms = {
  "Plan":"某次项目的执行计划与状态记录；不等于可复用的技能规则",
  "PRD":"产品需求文档；说明功能、业务规则、页面关系和主流程",
  "子代理":"主会话分派的独立 AI 工作会话，适合边界清楚的任务",
  "harness":"约束 AI 工作并验证其结果的任务书、工具、门禁与反馈机制",
  "gate":"门禁；进入下一步或交付前必须满足的条件",
  "mock":"开发和演示时使用的模拟数据，不等于真实后端服务",
  "token":"模型处理文本时的计量单位，也影响成本与上下文容量",
  "DPR":"设备像素比；源图物理像素与页面逻辑像素的比例",
  "DoD":"完成定义；交付一个任务时必须满足的可检查条件",
  "status_map":"同一页面的默认态、其他状态与触发条件的对应表",
  "Spec review":"对照需求与行为清单检查做得是否正确",
  "Standards review":"对照工程约定检查实现是否符合规范",
  "route-audit":"核对源码路由、冻结清单和运行时页面证据的脚本",
  "data-route":"页面根节点上的路由标记，供运行时审计验证",
  "intent":"交互意图标记，描述点击应触发的行为，不代替行为实现",
  "反例":"专门构造会让错误方案失败的输入或场景",
  "回归测试":"改动后重跑已有用例，确认旧行为没有再次出错",
  "技术栈":"工程使用的框架、语言、构建工具等技术组合",
  "Git":"记录文件版本与差异的工具，便于追溯修改",
  "工卡":"长期维护技能时使用的任务记录，与单次项目 PLAN 分开",
  "UDP":"全管线质检裁定协议；规定判断依据、独立复核、分歧升级和决策留痕",
  "证据索引":"按工程版本记录检查工具的结果，供终验核对最新有效证据",
  "决策账本":"记录业务推断、分歧、例外和用户推翻等有裁量的决定"
};
const stageTerms = {
  context:["DPR","gate"], problem:["Plan","PRD"], sample:["技术栈","Git"],
  sequence:["PRD","mock"], skill_choice:["Plan","harness"], contracts:["子代理","mock"],
  first:["gate","token"], ten:["子代理","DoD"], reviews:["反例","route-audit","data-route"],
  field:["Spec review","Standards review","intent"], delivery:["工卡","status_map"],
  document:["token","Git"], input_boundary:["Plan","技术栈"],
  second_run:["反例","gate"], workcards:["工卡","证据索引"],
  roles:["Spec review","Standards review"], arbitration:["UDP","决策账本"],
  adoption:["UDP","gate"]
};
let data = null;
let activePage = "skill";
let activeStage = "problem";
let query = "";
let start = 0;
let visible = 18;
let showTrace = false;
let searchResults = [];

async function loadData() {
  if (data) return data;
  const bytes = Uint8Array.from(atob(archiveGzip), (char) => char.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  data = JSON.parse(await new Response(stream).text());
  $("#snapshot").textContent = `会话至 ${data.stats.source_end}`;
  $("#footer-stats").textContent = `${data.stats.human} 轮用户发言 · 构建 ${data.stats.build} · Git ${data.stats.head}`;
  renderProduct();
  renderStages();
  renderQuestions();
  renderGlossary();
  return data;
}

function stageForLine(line) {
  return data.stages.find((stage) => line >= stage.from && line <= stage.to);
}

function renderProduct() {
  $("#decision-timeline").innerHTML = data.decisions.map((item) => `<article class="product-item planning"><div class="product-item-head"><time>${esc(item.date)}</time><h4>${esc(item.label)}</h4></div><p>${esc(item.copy)}</p></article>`).join("");
  $("#release-timeline").innerHTML = data.releases.map((item) => `<article class="product-item release-item"><div class="product-item-head"><time>${esc(item.date)}</time><h4>${esc(item.label)}</h4></div><ul class="release-changes">${item.changes.map((change) => `<li>${esc(change)}</li>`).join("")}</ul><p class="release-reason"><strong>针对的问题</strong>${esc(item.fix)}</p><small class="release-source">Git ${item.commits.map(esc).join(" · ")}</small></article>`).join("");
}

function renderStages() {
  let phase = "";
  $("#stage-nav").innerHTML = data.stages.map((stage) => {
    const heading = phase === stage.phase ? "" : `<div class="phase-label">${esc(stage.phase)}</div>`;
    phase = stage.phase;
    return heading + `<button class="stage-link ${stage.id === activeStage ? "active" : ""}" type="button" data-stage="${esc(stage.id)}"><strong>${esc(stage.title)}</strong><span>${esc(stage.time)} · ${stage.count} 轮</span></button>`;
  }).join("");
}

function renderQuestions() {
  let number = 0;
  $("#review-groups").innerHTML = data.qa_groups.map((group, index) => {
    const questions = data.questions.filter((item) => item.tag === group.tag);
    const warnings = group.warnings ? `<div class="qa-warnings"><strong>先记住三条边界</strong>${group.warnings.map((warning) => `<p>${esc(warning)}</p>`).join("")}</div>` : "";
    const items = questions.map((item) => {
      number += 1;
      const refs = item.refs?.length ? `<div class="qa-refs"><span>公开参照</span>${item.refs.map((key) => { const source = data.sources[key]; return `<a href="${esc(source.url)}" title="${esc(source.title)}" target="_blank" rel="noopener noreferrer">${esc(source.label)} ↗</a>`; }).join("")}</div>` : "";
      return `<article class="qa-item"><span class="qa-number">${String(number).padStart(2, "0")}</span><div><h3>${esc(item.q)}</h3><p class="qa-answer">${esc(item.answer)}</p>${refs}<p class="qa-case"><strong>本次例证</strong>${esc(item.case)} <a href="#journey/${esc(item.stage)}/${esc(item.turn)}" data-open-stage="${esc(item.stage)}" data-turn="${esc(item.turn)}">原话第 ${item.line} 行 ↗</a></p></div></article>`;
    }).join("");
    return `<section class="qa-group"><div class="qa-group-intro"><span>${String(index + 1).padStart(2, "0")} / ${esc(group.tag)}</span><h2>${esc(group.title)}</h2><p>${esc(group.intro)}</p></div><div class="qa-items">${warnings}${items}</div></section>`;
  }).join("");
}

function renderGlossary() {
  $("#glossary-terms").innerHTML = Object.entries(terms).map(([term, definition]) => `<div class="glossary-entry" data-term-entry="${esc(term.toLowerCase())}"><dt>${esc(term)}</dt><dd>${esc(definition)}</dd></div>`).join("");
}

function stageTurns() {
  if (query) return searchResults;
  const stage = data.stages.find((item) => item.id === activeStage);
  return data.turns.filter((turn) => turn.line >= stage.from && turn.line <= stage.to);
}

function noteMarkup(turn) {
  const notes = data.annotations.filter((note) => note.turn === turn.id);
  if (!notes.length) return "";
  return `<div class="note-stack">${notes.map((note) => `<aside class="editor-note"><span class="note-label">旁批</span><strong>${esc(note.title)}</strong><p>${esc(note.body)}</p></aside>`).join("")}</div>`;
}

function actionFor(text) {
  if (/不要动|别动|停止动作|别再写计划|不要落盘|纯讨论|先讨论|不让你改|不要改文件|不要编辑文件/.test(text)) return "暂停或限定执行";
  if (/重新评审|再审|审查|复审/.test(text)) return "要求复核";
  return "";
}

function traceMarkup(turn) {
  if (!turn.trace.length && !turn.images) return "";
  return `<details class="trace-group" data-trace="${esc(turn.id)}" ${showTrace ? "open" : ""}><summary>执行与思考 ${turn.trace.length} 条${turn.images ? ` · 附件 ${turn.images}` : ""}</summary><div class="trace-list"></div></details>`;
}

function fillTrace(details) {
  if (details.dataset.loaded) return;
  const turn = data.turns.find((item) => item.id === details.dataset.trace);
  if (!turn) return;
  const records = turn.trace.map((entry) => {
    const name = {thinking:"AI 思考记录",tool:"工具调用",result:"工具结果",queue:"队列事件",context:"编辑器事件"}[entry.role] || entry.role;
    const preview = entry.text.replace(/\s+/g, " ").slice(0, 65);
    return `<details class="trace-item"><summary>${esc(name)} · ${esc(preview)}<span>第 ${entry.line} 行</span></summary><pre>${esc(entry.text)}</pre></details>`;
  }).join("");
  const attachment = turn.images ? `<div class="trace-item"><div style="padding:8px 10px">图片附件 ${turn.images} 个 · 原始内容保存在同目录 JSONL 第 ${turn.line} 行</div></div>` : "";
  details.querySelector(".trace-list").innerHTML = attachment + records;
  details.dataset.loaded = "true";
}

function replyMarkup(turn) {
  if (!turn.reply_html) return "";
  const plain = turn.reply_html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const long = plain.length > 800;
  const body = long ? `<div class="reply-excerpt">${esc(plain.slice(0, 280))}…</div><details class="reply-fold"><summary>展开 AI 完整回复 · ${plain.length} 字</summary><div class="bubble-body">${turn.reply_html}</div></details>` : `<div class="bubble-body">${turn.reply_html}</div>`;
  return `<div class="bubble bubble-ai"><div class="bubble-head"><span class="role-mark">AI</span> AI 响应 <small>${turn.reply_count > 1 ? `${turn.reply_count} 段原始文字已聚合` : ""}</small></div>${body}</div>`;
}

function turnMarkup(turn) {
  const stage = stageForLine(turn.line);
  const action = actionFor(turn.user);
  return `<article class="turn" id="${esc(turn.id)}"><div class="turn-line">${esc(turn.time)} · 原文件第 ${turn.line} 行${query ? ` · ${esc(stage?.title || "")}` : ""}</div><div class="bubble bubble-user"><div class="bubble-head"><span class="role-mark">你</span> ${turn.quoted ? "转引的评审材料" : "你的发言"} ${action ? `<span class="action-label">${action}</span>` : ""}<time>${esc(turn.time)}</time></div><div class="bubble-body">${turn.user_html || (turn.images ? "[图片附件]" : "")}</div></div>${noteMarkup(turn)}${replyMarkup(turn)}${traceMarkup(turn)}</article>`;
}

function addTermHints(root) {
  const used = new Map();
  const names = Object.keys(terms).sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`(?<![A-Za-z])(?:${names.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})(?![A-Za-z])`, "gi");
  const definitions = new Map(Object.entries(terms).map(([name, definition]) => [name.toLowerCase(), definition]));
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement?.closest("code,pre,a,button,summary,.editor-note,.stage-terms")) continue;
    if (pattern.test(node.textContent)) nodes.push(node);
    pattern.lastIndex = 0;
  }
  for (const node of nodes) {
    const text = node.textContent;
    const scope = node.parentElement?.closest(".stage-block")?.id || "search";
    if (!used.has(scope)) used.set(scope, new Set());
    const seen = used.get(scope);
    const matches = [...text.matchAll(pattern)];
    if (!matches.some((match) => !seen.has(match[0].toLowerCase()))) continue;
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const match of matches) {
      const key = match[0].toLowerCase();
      if (seen.has(key)) continue;
      fragment.append(document.createTextNode(text.slice(cursor, match.index)));
      const hint = document.createElement("button");
      hint.className = "term";
      hint.type = "button";
      hint.textContent = match[0];
      hint.title = definitions.get(key);
      hint.setAttribute("aria-label", `${match[0]}：${hint.title}`);
      hint.addEventListener("click", () => setGlossary(true, key));
      fragment.append(hint);
      seen.add(key);
      cursor = match.index + match[0].length;
    }
    fragment.append(document.createTextNode(text.slice(cursor)));
    node.replaceWith(fragment);
  }
}

function stageTermsMarkup(stage) {
  const names = stageTerms[stage.id] || [];
  if (!names.length) return "";
  return `<dl class="stage-terms">${names.map((name) => `<div><dt>${esc(name)}</dt><dd>${esc(terms[name])}</dd></div>`).join("")}</dl>`;
}

function renderConversation() {
  const turns = query ? searchResults : data.turns;
  if (query) {
    $("#stage-heading").innerHTML = `<span class="stage-kicker">全文搜索</span><h2>“${esc(query)}”的结果</h2><p>显示命中的真实对话轮次。点击左侧过程节点可清除搜索并回到线性记录。</p><div class="stage-range">${turns.length} 轮匹配</div>`;
    const slice = turns.slice(start, start + visible);
    $("#conversation-list").innerHTML = slice.length ? slice.map(turnMarkup).join("") : `<p class="minor">没有符合条件的发言。</p>`;
    $("#load-turns").hidden = start + visible >= turns.length;
  } else {
    $("#stage-heading").innerHTML = `<span class="stage-kicker">原始对话 · 按时间连续排列</span><h2>从问题提出，到技能修订</h2><p>阶段边界来自会话本身。单页技能前史与文档探索也保留在时间线中，阅读重点从多图技能立项开始。</p><div class="stage-range">${data.stats.human} 轮用户发言 · AI 同轮响应已聚合 · 工具与思考按需展开</div>`;
    $("#conversation-list").innerHTML = data.stages.map((stage) => {
      const within = data.turns.filter((turn) => turn.line >= stage.from && turn.line <= stage.to);
      return `<section class="stage-block" id="s-${esc(stage.id)}"><div class="stage-divider"><span>${esc(stage.phase)} / ${esc(stage.time)}</span><h2>${esc(stage.title)}</h2><p>${esc(stage.note)}</p><small>原文件第 ${stage.from}–${stage.to === 999999 ? data.stats.lines : stage.to} 行 · ${within.length} 轮</small></div>${stageTermsMarkup(stage)}${within.map(turnMarkup).join("")}</section>`;
    }).join("");
    $("#load-turns").hidden = true;
    syncStageOnScroll();
  }
  addTermHints($("#conversation-list"));
  $("#journey-count").textContent = query ? `${turns.length} 轮匹配` : `${turns.length} 轮可读会话`;
  const index = data.stages.findIndex((item) => item.id === activeStage);
  $("#prev-stage").disabled = index <= 0 || !!query;
  $("#next-stage").disabled = index >= data.stages.length - 1 || !!query;
  document.querySelectorAll(".stage-link").forEach((button) => button.classList.toggle("active", button.dataset.stage === activeStage && !query));
  if (showTrace) document.querySelectorAll(".trace-group[open]").forEach(fillTrace);
}

function syncStageOnScroll() {
  if (query || activePage !== "journey") return;
  const probe = innerWidth <= 760 ? 265 : 150;
  const current = [...document.querySelectorAll(".stage-block")].find((element) => {
    const rect = element.getBoundingClientRect();
    return rect.top <= probe && rect.bottom > probe;
  });
  if (!current || activeStage === current.id.slice(2)) return;
  activeStage = current.id.slice(2);
  document.querySelectorAll(".stage-link").forEach((button) => button.classList.toggle("active", button.dataset.stage === activeStage));
  if (innerWidth <= 760) {
    const item = document.querySelector(`.stage-link[data-stage="${activeStage}"]`);
    const strip = $("#stage-nav");
    strip.scrollTo({left:item.offsetLeft - strip.offsetLeft - 12,behavior:"smooth"});
  }
}
let scrollQueued = false;
window.addEventListener("scroll", () => {
  if (scrollQueued) return;
  scrollQueued = true;
  requestAnimationFrame(() => { scrollQueued = false; syncStageOnScroll(); });
}, {passive:true});

function setStage(id, turnId = "") {
  if (!data.stages.some((item) => item.id === id)) return;
  activeStage = id;
  query = "";
  $("#journey-search").value = "";
  start = 0;
  visible = 18;
  if (!$(".stage-block")) renderConversation();
  document.querySelectorAll(".stage-link").forEach((button) => button.classList.toggle("active", button.dataset.stage === activeStage));
  history.replaceState(null, "", `#journey/${id}${turnId ? `/${turnId}` : ""}`);
  requestAnimationFrame(() => (turnId ? document.getElementById(turnId) : document.getElementById(`s-${id}`))?.scrollIntoView({block:"start",behavior:"smooth"}));
}

function openPage(page, stage = "", turnId = "") {
  if (!["skill", "journey", "review"].includes(page)) page = "skill";
  activePage = page;
  document.querySelectorAll(".page").forEach((element) => element.classList.toggle("active", element.id === page));
  document.querySelectorAll(".nav-item").forEach((element) => element.classList.toggle("active", element.dataset.page === page));
  $("#breadcrumb").textContent = {skill:"技能说明",journey:"共创实录",review:"方法复盘"}[page];
  $(".side").classList.remove("open");
  if (page === "journey" && stage) setStage(stage, turnId);
  else {
    history.replaceState(null, "", `#${page}`);
    if (page === "journey") {
      if (!$(".stage-block")) renderConversation();
      requestAnimationFrame(() => document.getElementById("s-problem")?.scrollIntoView({block:"start",behavior:"instant"}));
    } else window.scrollTo({top:0,behavior:"instant"});
  }
}

function setGlossary(open, term = "") {
  $("#glossary").hidden = !open;
  $("#glossary-toggle").setAttribute("aria-expanded", String(open));
  document.querySelectorAll(".glossary-entry").forEach((entry) => entry.classList.toggle("selected", entry.dataset.termEntry === term));
  if (term) {
    const entry = [...document.querySelectorAll(".glossary-entry")].find((item) => item.dataset.termEntry === term);
    if (entry) $("#glossary").scrollTop = entry.offsetTop - $("#glossary").offsetTop - 20;
  }
}

document.addEventListener("click", (event) => {
  const nav = event.target.closest("[data-page]");
  if (nav) { event.preventDefault(); openPage(nav.dataset.page); return; }
  const stage = event.target.closest("[data-stage]");
  if (stage) { setStage(stage.dataset.stage); return; }
  const jump = event.target.closest("[data-open-stage]");
  if (jump) { event.preventDefault(); openPage("journey", jump.dataset.openStage, jump.dataset.turn || ""); return; }
});
$("#menu-toggle").addEventListener("click", () => $(".side").classList.toggle("open"));
$("#glossary-toggle").addEventListener("click", () => setGlossary($("#glossary").hidden));
$("#glossary-close").addEventListener("click", () => setGlossary(false));
$("#trace-toggle").addEventListener("click", () => {
  showTrace = !showTrace;
  $("#trace-toggle").setAttribute("aria-pressed", String(showTrace));
  document.querySelectorAll(".trace-group").forEach((item) => { item.open = showTrace; if (showTrace) fillTrace(item); });
});
$("#conversation-list").addEventListener("toggle", (event) => {
  const group = event.target.closest?.(".trace-group");
  if (group?.open) fillTrace(group);
}, true);
$("#journey-search").addEventListener("input", (event) => {
  query = event.target.value.trim();
  searchResults = query ? data.turns.filter((turn) => `${turn.search} ${turn.line} ${turn.time}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())) : [];
  start = 0;
  visible = 18;
  renderConversation();
});
$("#load-turns").addEventListener("click", () => { visible += 18; renderConversation(); });
$("#conversation-list").addEventListener("click", (event) => {
  if (event.target.id === "load-earlier") { start = Math.max(0, start - 18); visible += 18; renderConversation(); }
});
$("#prev-stage").addEventListener("click", () => setStage(data.stages[data.stages.findIndex((item) => item.id === activeStage) - 1].id));
$("#next-stage").addEventListener("click", () => setStage(data.stages[data.stages.findIndex((item) => item.id === activeStage) + 1].id));

loadData().then(() => {
  const [, page, stage, turnId] = location.hash.match(/^#([^/]+)(?:\/([^/]+))?(?:\/([^/]+))?/) || [];
  openPage(page || "skill", stage || "", turnId || "");
}).catch((error) => {
  $("#snapshot").textContent = "会话数据读取失败";
  console.error(error);
});
