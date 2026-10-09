/* The browser presents the game. Python decides and stores every result. */
"use strict";

const $ = (selector) => document.querySelector(selector);
const moveButtons = [...document.querySelectorAll("[data-move]")];
const formatButtons = [...document.querySelectorAll("[data-format]")];
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let match = null;
let csrf = "";
let busy = true;
let selectedFormat = 3;
let lastHistory = null;

function rememberName(value) {
  try {
    localStorage.setItem("rps-player", value);
  } catch {
    /* Storage is optional. */
  }
}
try {
  $("#player-name").value = localStorage.getItem("rps-player") || "";
} catch {
  /* Private mode. */
}
$("#player-name").addEventListener("input", (event) => rememberName(event.target.value));

function notify(message = "") {
  $("#notice").textContent = message;
  $("#notice").hidden = !message;
}

function setBusy(value) {
  busy = value;
  moveButtons.forEach((button) => {
    button.disabled = value || !match || match.finished;
  });
  formatButtons.forEach((button) => {
    button.disabled = value;
  });
  $("#new-match").disabled = value || !csrf;
  $("#end-match").disabled = value || !match || match.finished;
  $(".arena").setAttribute("aria-busy", String(value));
}

async function api(path, payload) {
  let response;
  try {
    response = await fetch(path, {
      method: payload === undefined ? "GET" : "POST",
      headers: payload === undefined ? {} : {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf
      },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      signal: AbortSignal.timeout(12000),
    });
  } catch {
    throw new Error(
      "Couldn't reach the game. Check that the Python server is running, then refresh.");
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Unexpected server response. Please refresh and try again.");
  }
  if (!response.ok) {
    if (data.match) {
      match = data.match;
      renderMatch();
    }
    throw new Error(data.error || "Something went wrong. Please try again.");
  }
  if (data.warning) notify(data.warning);
  return data;
}

function hand(selector, move) {
  const icon = $(selector);
  icon.querySelector("use").setAttribute("href", `#hand-${move}`);
  icon.setAttribute("aria-label", move);
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function smallHand(move) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#hand-${move}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", move);
  svg.append(use);
  return svg;
}

function renderRounds() {
  $("#round-count").textContent = match.rounds.length;
  if (!match.rounds.length) {
    const empty = makeElement("div", "empty-rounds");
    const arrow = makeElement("span", "", "↗");
    arrow.setAttribute("aria-hidden", "true");
    empty.append(arrow, makeElement("p", "", "No rounds yet."), makeElement("span", "",
      "Pick a move to start playing."));
    $("#round-history").replaceChildren(empty);
    return;
  }
  const rows = [...match.rounds].reverse().slice(0, 5).map((round) => {
    const row = makeElement("div", "round-row");
    const picks = makeElement("div", "round-picks");
    picks.append(
      smallHand(round.player),
      makeElement("span", "", "vs"),
      smallHand(round.computer)
    );
    row.append(makeElement("span", "round-index", String(round.number).padStart(2, "0")), picks,
      makeElement("span", `round-outcome ${round.outcome}`, {
        win: "WIN",
        loss: "LOSS",
        draw: "DRAW"
      } [round.outcome]));
    return row;
  });
  $("#round-history").replaceChildren(...rows);
}

function renderMatch() {
  if (!match) return;
  $("#player-label").textContent = match.player === "Guest" ? "You" : match.player;
  $("#player-score").textContent = match.wins;
  $("#computer-score").textContent = match.losses;
  $("#draw-count").textContent = `${match.draws} ${match.draws === 1 ? "draw" : "draws"}`;
  $("#match-label").textContent = match.best_of ? `BEST OF ${match.best_of}` : "FREE PLAY";
  $("#target-label").textContent = match.target ? `First to ${match.target} wins` :
    "Play at your own pace";
  $("#round-number").textContent = match.finished ? "SESSION ENDED" :
    `ROUND ${String(match.rounds.length + 1).padStart(2, "0")}`;
  $("#match-note").textContent = match.best_of ? "Draws don't count toward the win." :
    "End the session whenever you're ready.";
  $("#end-match").textContent = match.best_of ? "End this match" : "Finish & save session";
  selectedFormat = match.best_of;
  formatButtons.forEach((button) => {
    const format = button.dataset.format === "free" ? null : Number(button.dataset.format);
    const selected = format === selectedFormat;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  const round = match.rounds.at(-1);
  const arena = $(".arena");
  arena.classList.remove("won", "lost", "drawn");
  moveButtons.forEach((button) => {
    button.classList.toggle("chosen", button.dataset.move === round?.player);
  });
  if (round) {
    hand("#player-hand", round.player);
    hand("#computer-hand", round.computer);
    $("#player-move-label").textContent = round.player.toUpperCase();
    $("#computer-move-label").textContent = round.computer.toUpperCase();
    $("#result-title").textContent = {
      win: "That one's yours.",
      loss: "The computer takes it.",
      draw: "A meeting of minds."
    } [round.outcome];
    $("#result-description").textContent = round.explanation;
    arena.classList.add({
      win: "won",
      loss: "lost",
      draw: "drawn"
    } [round.outcome]);
  } else {
    hand("#player-hand", "rock");
    hand("#computer-hand", "rock");
    $("#player-move-label").textContent = "YOUR PICK";
    $("#computer-move-label").textContent = "THEIR PICK";
    $("#result-title").textContent = "Make your move.";
    $("#result-description").textContent = "Rock, paper, or scissors. What's it going to be?";
  }
  if (match.finished) {
    $("#result-title").textContent = {
      win: "The match is yours.",
      loss: "A worthy opponent.",
      draw: "Evenly matched.",
      abandoned: "We'll call it here."
    } [match.outcome];
    $("#result-description").textContent = match.outcome === "abandoned" ?
      "Saved as unfinished. A fresh start is one click away." :
      `${match.wins}–${match.losses}. ${match.best_of ? "Up for a rematch?" : "A good place to stop. Until next time."}`;
    $("#new-match").firstChild.textContent = "Play again ";
    if (!match.rounds.length) {
      $("#result-title").textContent = "A clean slate.";
      $("#result-description").textContent =
        "No rounds played, nothing saved. Start a new match when you're ready.";
    }
  } else {
    $("#new-match").firstChild.textContent = "New match ";
  }
  for (const [selector, score] of [
    ["#player-pips", match.wins],
    ["#computer-pips", match.losses]
  ]) {
    $(selector).replaceChildren(...Array.from({
      length: match.target || 0
    }, (_, index) => makeElement("span", index < score ? "filled" : "")));
  }
  renderRounds();
}

function canReplace() {
  if (!match || match.finished || !match.rounds.length) return true;
  return window.confirm(match.best_of ? "Start fresh? This match will be saved as unfinished." :
    "Start fresh? Your current free-play session will be saved.");
}

async function startMatch(format = selectedFormat) {
  if (busy || !canReplace()) return;
  notify();
  setBusy(true);
  try {
    const data = await api("/api/matches", {
      player: $("#player-name").value.trim() || "Guest",
      best_of: format
    });
    match = data.match;
    renderMatch();
    lastHistory = null;
  } catch (error) {
    notify(error.message);
  } finally {
    setBusy(false);
  }
}

async function play(move) {
  if (busy || !match || match.finished) return;
  notify();
  setBusy(true);
  const field = $("#battlefield");
  field.classList.remove("reveal");
  field.classList.add("shaking");
  $("#result-title").textContent = "Rock. Paper. Scissors…";
  $("#result-description").textContent = "A moment of suspense.";
  hand("#player-hand", "rock");
  hand("#computer-hand", "rock");
  try {
    const [data] = await Promise.all([
      api("/api/play", {
        move,
        match_id: match.id,
        revision: match.revision
      }),
      new Promise((resolve) => setTimeout(resolve, reducedMotion.matches ? 0 : 650)),
    ]);
    match = data.match;
    lastHistory = null;
  } catch (error) {
    notify(error.message);
  } finally {
    field.classList.remove("shaking");
    field.classList.add("reveal");
    renderMatch();
    setBusy(false);
  }
}

async function endMatch() {
  if (busy || !match || match.finished) return;
  if (match.best_of && match.rounds.length && !window.confirm(
      "End this match? It will be recorded as unfinished.")) return;
  notify();
  setBusy(true);
  try {
    const data = await api("/api/finish", {
      match_id: match.id,
      revision: match.revision
    });
    match = data.match;
    renderMatch();
    lastHistory = null;
  } catch (error) {
    notify(error.message);
  } finally {
    setBusy(false);
  }
}

function showView(history) {
  if (history) {
    $("#history-view").showModal();
    loadHistory();
  } else {
    $("#history-view").close();
  }
}

function renderSavedHistory(data) {
  const stats = data.stats;
  $("#stat-matches").textContent = stats.matches;
  $("#stat-wins").textContent = stats.wins;
  $("#stat-rate").textContent = stats.win_rate === null ? "—" : `${stats.win_rate}%`;
  $("#stat-rounds").textContent = stats.rounds;
  if (!data.records.length) {
    const empty = makeElement("div", "history-empty");
    empty.append(makeElement("h3", "", "Every rivalry starts somewhere."), makeElement("p", "",
      "Finish your first match and it will appear here.\nYour history stays on this device."));
    $("#saved-history").replaceChildren(empty);
    return;
  }
  const scroll = makeElement("div", "table-scroll");
  const table = makeElement("table");
  const caption = makeElement("caption", "sr-only",
    "Finished and unfinished sessions, most recent first");
  const head = makeElement("thead"),
    heading = makeElement("tr");
  ["Player", "Format", "Score", "Result", "Played"].forEach((label) => {
    const th = makeElement("th", "", label);
    th.scope = "col";
    heading.append(th);
  });
  head.append(heading);
  const body = makeElement("tbody");
  data.records.forEach((record) => {
    const row = makeElement("tr");
    row.append(makeElement("td", "", record.player), makeElement("td", "", record.best_of ?
      `Best of ${record.best_of}` : "Free play"), makeElement("td", "",
      `${record.wins}–${record.losses} · ${record.draws} draws`));
    const result = makeElement("td");
    result.append(makeElement("span", `round-outcome ${record.outcome}`, {
      win: "WON",
      loss: "LOST",
      draw: "TIED",
      abandoned: "UNFINISHED"
    } [record.outcome] || "UNKNOWN"));
    const date = makeElement("td"),
      time = makeElement("time", "", new Date(record.finished_at).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }));
    time.dateTime = record.finished_at;
    date.append(time);
    row.append(result, date);
    body.append(row);
  });
  table.append(caption, head, body);
  scroll.append(table);
  $("#saved-history").replaceChildren(scroll);
}

async function loadHistory() {
  notify();
  if (lastHistory) {
    renderSavedHistory(lastHistory);
    return;
  }
  $("#saved-history").replaceChildren(makeElement("p", "history-empty", "Looking back…"));
  try {
    lastHistory = await api("/api/history");
    renderSavedHistory(lastHistory);
  } catch (error) {
    $("#saved-history").replaceChildren(makeElement("p", "history-empty",
      "History couldn't load. Return to the game, or try this tab again."));
    notify(error.message);
  }
}

moveButtons.forEach((button) => button.addEventListener("click", () => play(button.dataset.move)));
formatButtons.forEach((button) => button.addEventListener("click", () => {
  startMatch(button.dataset.format === "free" ? null : Number(button.dataset.format));
}));
$("#new-match").addEventListener("click", () => startMatch());
$("#end-match").addEventListener("click", endMatch);

$("#history-tab").addEventListener("click", () => showView(true));
$("#back-to-play").addEventListener("click", () => showView(false));
$("#open-rules").addEventListener("click", () => $("#rules-dialog").showModal());
[$("#close-rules"), $("#got-it")].forEach((button) => {
  button.addEventListener("click", () => $("#rules-dialog").close());
});
document.addEventListener("keydown", (event) => {
  if (
    event.repeat || event.ctrlKey || event.altKey || event.metaKey ||
    document.querySelector("dialog[open]") ||
    ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)
  ) return;
  const move = {
    r: "rock",
    p: "paper",
    s: "scissors"
  } [event.key.toLowerCase()];
  if (move) {
    event.preventDefault();
    play(move);
  }
});

async function initialize() {
  try {
    const data = await api("/api/state");
    csrf = data.csrf;
    match = data.match;
    if (!match) {
      const created = await api("/api/matches", {
        player: $("#player-name").value.trim() || "Guest",
        best_of: 3
      });
      match = created.match;
    }
    renderMatch();
  } catch (error) {
    notify(error.message);
  } finally {
    setBusy(false);
  }
}
initialize();

$("#open-settings").addEventListener("click", () => $("#settings-dialog").showModal());
$("#apply-settings").addEventListener("click", async () => {
  await startMatch();
  $("#settings-dialog").close();
});
document.querySelectorAll("[data-close]").forEach(button => button.addEventListener("click", () =>
  document.getElementById(button.dataset.close).close()));
