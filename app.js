(() => {
  const state = {
    all: [],
    filtered: [],
    index: 0,
    query: "",
    revealed: false,
  };

  const $ = (id) => document.getElementById(id);
  const els = {
    counter: $("counter"),
    search: $("search"),
    qid: $("q-id"),
    qpage: $("q-page"),
    question: $("question"),
    answer: $("answer"),
    reveal: $("reveal"),
    prev: $("prev"),
    next: $("next"),
    list: $("list"),
    matchCount: $("match-count"),
  };

  function renderCard() {
    const card = state.filtered[state.index];
    if (!card) {
      els.qid.textContent = "Q—";
      els.qpage.textContent = "page —";
      els.question.textContent = "No matches.";
      els.answer.hidden = true;
      els.reveal.disabled = true;
      els.counter.textContent = `0 / 0`;
      return;
    }
    els.qid.textContent = `Q${card.id}`;
    els.qpage.textContent = `page ${card.page}`;
    els.question.textContent = card.question;
    els.answer.textContent = card.answer;
    els.answer.hidden = !state.revealed;
    els.reveal.disabled = false;
    els.reveal.textContent = state.revealed ? "Hide Answer" : "Show Answer";
    els.counter.textContent = `${state.index + 1} / ${state.filtered.length}`;
  }

  function toggleReveal() {
    state.revealed = !state.revealed;
    renderCard();
  }

  function move(delta) {
    if (!state.filtered.length) return;
    state.index = (state.index + delta + state.filtered.length) % state.filtered.length;
    state.revealed = false;
    renderCard();
    syncListSelection();
  }

  function syncListSelection() {
    const items = els.list.querySelectorAll("li");
    items.forEach((li) => li.classList.toggle(
      "active",
      Number(li.dataset.id) === (state.filtered[state.index]?.id ?? -1),
    ));
    const active = els.list.querySelector("li.active");
    if (active) active.scrollIntoView({ block: "nearest" });
  }

  els.reveal.addEventListener("click", toggleReveal);
  els.prev.addEventListener("click", () => move(-1));
  els.next.addEventListener("click", () => move(1));

  function renderList() {
    const html = state.filtered
      .map(
        (q) => `<li data-id="${q.id}"><span class="id">${q.id}.</span><span class="qtext"></span></li>`,
      )
      .join("");
    els.list.innerHTML = html;
    const items = els.list.querySelectorAll("li");
    items.forEach((li, i) => {
      li.querySelector(".qtext").textContent = state.filtered[i].question;
    });
    els.matchCount.textContent = `(${state.filtered.length})`;
    syncListSelection();
  }

  els.list.addEventListener("click", (ev) => {
    const li = ev.target.closest("li");
    if (!li) return;
    const id = Number(li.dataset.id);
    const idx = state.filtered.findIndex((q) => q.id === id);
    if (idx < 0) return;
    state.index = idx;
    state.revealed = false;
    renderCard();
    syncListSelection();
  });

  function applyFilter() {
    const q = state.query.trim().toLowerCase();
    if (!q) {
      state.filtered = state.all;
    } else {
      state.filtered = state.all.filter(
        (r) =>
          r.question.toLowerCase().includes(q) ||
          r.answer.toLowerCase().includes(q),
      );
    }
    state.index = 0;
    state.revealed = false;
    renderList();
    renderCard();
  }

  els.search.addEventListener("input", (ev) => {
    state.query = ev.target.value;
    applyFilter();
  });

  async function load() {
    const res = await fetch("questions.json");
    state.all = await res.json();
    state.filtered = state.all;
    renderList();
    renderCard();
  }

  load();
  window.__app = { state, renderCard, els }; // dev hook
})();
