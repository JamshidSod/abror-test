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

  async function load() {
    const res = await fetch("questions.json");
    state.all = await res.json();
    state.filtered = state.all;
    renderCard();
  }

  load();
  window.__app = { state, renderCard, els }; // dev hook
})();
