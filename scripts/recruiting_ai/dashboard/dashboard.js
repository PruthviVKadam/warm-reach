const state = {
  query: "",
  status: "",
  statusOptions: [],
  requestId: 0,
  replyReviewOptions: [],
};

const elements = {
  askDialog: document.querySelector("#ask-dialog"),
  askForm: document.querySelector("#ask-form"),
  asksBody: document.querySelector("#applications-body"),
  cancelDialogButton: document.querySelector("#cancel-dialog-button"),
  closeDialogButton: document.querySelector("#close-dialog-button"),
  followupList: document.querySelector("#followup-list"),
  formStatus: document.querySelector("#form-status"),
  metricGrid: document.querySelector("#metric-grid"),
  newAskButton: document.querySelector("#new-ask-button"),
  replyList: document.querySelector("#reply-list"),
  refreshButton: document.querySelector("#refresh-button"),
  resultCount: document.querySelector("#result-count"),
  searchInput: document.querySelector("#search-input"),
  statusFilter: document.querySelector("#status-filter"),
  syncStatus: document.querySelector("#sync-status"),
  timelineList: document.querySelector("#timeline-list"),
};

let searchTimer;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function displayStatus(value) {
  return String(value || "planned").replaceAll("_", " ");
}

function compactContext(ask) {
  const pieces = [ask.company, ask.opportunity].filter(Boolean);
  return pieces.length ? pieces.join(" - ") : "General referral ask";
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function setSyncStatus(message, isError = false) {
  elements.syncStatus.textContent = message;
  elements.syncStatus.style.color = isError ? "#b42318" : "";
}

function setFormStatus(message, isError = true) {
  elements.formStatus.textContent = message;
  elements.formStatus.style.color = isError ? "#b42318" : "#056b6b";
}

function renderStatusOptions(options) {
  if (state.statusOptions.join("|") === options.join("|")) {
    return;
  }
  state.statusOptions = options;
  const current = state.status;
  elements.statusFilter.innerHTML = [
    '<option value="">All statuses</option>',
    ...options.map((status) => `<option value="${escapeHtml(status)}">${escapeHtml(displayStatus(status))}</option>`),
  ].join("");
  elements.statusFilter.value = current;
}

function renderReplyReviewOptions(options) {
  state.replyReviewOptions = options;
}

function renderMetrics(summary) {
  const metrics = [
    ["All asks", summary.ask_count, "teal"],
    ["Drafts ready", summary.draft_ready_count, "blue"],
    ["Awaiting reply", summary.awaiting_reply_count, "gold"],
    ["Referrals received", summary.referral_count, "red"],
    ["People", summary.contact_count, "teal"],
    ["Replies to review", summary.pending_reply_candidate_count, "blue"],
  ];
  elements.metricGrid.innerHTML = metrics
    .map(
      ([label, value, tone]) => `
        <article class="metric-card" data-tone="${tone}">
          <div>
            <p class="metric-label">${label}</p>
            <p class="metric-value">${Number(value || 0)}</p>
          </div>
          <span class="metric-accent" aria-hidden="true"></span>
        </article>`,
    )
    .join("");
}

function replyReviewSelect(candidate) {
  const options = state.replyReviewOptions
    .map((status) => {
      const selected = status === candidate.review_status ? " selected" : "";
      return `<option value="${escapeHtml(status)}"${selected}>${escapeHtml(displayStatus(status))}</option>`;
    })
    .join("");
  return `<select class="reply-review-select" data-reply-candidate-id="${escapeHtml(candidate.id)}" aria-label="Review status for possible reply from ${escapeHtml(candidate.from_email)}">${options}</select>`;
}

function renderReplyCandidates(candidates) {
  if (!candidates.length) {
    elements.replyList.innerHTML = '<li class="empty-state">No inbox messages match sent referral asks.</li>';
    return;
  }
  elements.replyList.innerHTML = candidates
    .map(
      (candidate) => `
        <li class="reply-item">
          <div class="reply-heading">
            <p class="reply-title">${escapeHtml(candidate.contact_name)}</p>
            <span class="confidence-badge" data-confidence="${escapeHtml(candidate.match_confidence)}">${escapeHtml(displayStatus(candidate.match_confidence))} ${Number(candidate.match_score)}</span>
          </div>
          <p class="reply-subject">${escapeHtml(candidate.subject || "No subject")}</p>
          <div class="reply-meta"><span>${escapeHtml(candidate.from_email)}</span><span>${escapeHtml(formatDate(candidate.received_at))}</span></div>
          <div class="reply-actions">${replyReviewSelect(candidate)}</div>
        </li>`,
    )
    .join("");
}

function statusSelect(ask) {
  const options = state.statusOptions
    .map((status) => {
      const selected = status === ask.status ? " selected" : "";
      return `<option value="${escapeHtml(status)}"${selected}>${escapeHtml(displayStatus(status))}</option>`;
    })
    .join("");
  return `<select class="status-select" data-referral-ask-id="${escapeHtml(ask.id)}" aria-label="Status for ${escapeHtml(ask.contact_name)}">${options}</select>`;
}

function renderAsks(asks) {
  elements.resultCount.textContent = `${asks.length} shown`;
  if (!asks.length) {
    elements.asksBody.innerHTML = '<tr><td class="empty-table-cell" colspan="5">No referral asks match these filters.</td></tr>';
    return;
  }
  elements.asksBody.innerHTML = asks
    .map(
      (ask) => `
        <tr>
          <td class="company-cell">${escapeHtml(ask.contact_name)}<br><span class="meta-cell">${escapeHtml(ask.contact_email)}</span></td>
          <td class="role-cell">${escapeHtml(compactContext(ask))}</td>
          <td class="role-cell">${escapeHtml(ask.relationship_context || "-")}</td>
          <td class="meta-cell">${escapeHtml(formatDate(ask.next_followup_at))}</td>
          <td>${statusSelect(ask)}</td>
        </tr>`,
    )
    .join("");
}

function renderFollowups(followups) {
  if (!followups.length) {
    elements.followupList.innerHTML = '<li class="empty-state">No gentle follow-ups are due.</li>';
    return;
  }
  elements.followupList.innerHTML = followups
    .map(
      (followup) => `
        <li class="followup-item">
          <p class="followup-title">${escapeHtml(followup.contact_name)} - ${escapeHtml(compactContext(followup))}</p>
          <div class="followup-meta"><span class="due-badge">Due ${escapeHtml(formatDate(followup.next_followup_at))}</span></div>
          ${followup.ask_context ? `<p class="followup-reason">${escapeHtml(followup.ask_context)}</p>` : ""}
        </li>`,
    )
    .join("");
}

function renderTimeline(events) {
  if (!events.length) {
    elements.timelineList.innerHTML = '<li class="empty-state">No referral activity recorded.</li>';
    return;
  }
  elements.timelineList.innerHTML = events
    .map(
      (event) => `
        <li class="timeline-item">
          <p class="timeline-title">${escapeHtml(event.title)}</p>
          <div class="timeline-meta">
            <span>${escapeHtml(event.contact_name)}</span>
            <span>${escapeHtml(formatDate(event.event_time))}</span>
          </div>
        </li>`,
    )
    .join("");
}

async function loadDashboard() {
  const requestId = ++state.requestId;
  const parameters = new URLSearchParams();
  if (state.query) {
    parameters.set("query", state.query);
  }
  if (state.status) {
    parameters.set("status", state.status);
  }
  setSyncStatus("Refreshing");
  elements.refreshButton.disabled = true;
  try {
    const response = await fetch(`/api/dashboard?${parameters.toString()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Warm Reach data could not be loaded.");
    }
    const dashboard = await response.json();
    if (requestId !== state.requestId) {
      return;
    }
    renderStatusOptions(dashboard.status_options || []);
    renderReplyReviewOptions(dashboard.reply_review_options || []);
    renderMetrics(dashboard.summary || {});
    renderAsks(dashboard.asks || []);
    renderReplyCandidates(dashboard.reply_candidates || []);
    renderFollowups(dashboard.followups || []);
    renderTimeline(dashboard.timeline || []);
    setSyncStatus("Up to date");
  } catch (error) {
    setSyncStatus(error.message || "Unable to load", true);
  } finally {
    if (requestId === state.requestId) {
      elements.refreshButton.disabled = false;
    }
  }
}

async function updateReplyReview(candidateId, reviewStatus) {
  setSyncStatus("Saving");
  try {
    const response = await fetch("/api/referral-replies/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: candidateId, review_status: reviewStatus }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || "Reply review could not be saved.");
    }
    await loadDashboard();
  } catch (error) {
    setSyncStatus(error.message || "Reply review could not be saved.", true);
    await loadDashboard();
  }
}

async function updateAskStatus(referralAskId, status) {
  setSyncStatus("Saving");
  try {
    const response = await fetch("/api/referral-asks/status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ referral_ask_id: referralAskId, status }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || "Status could not be saved.");
    }
    await loadDashboard();
  } catch (error) {
    setSyncStatus(error.message || "Status could not be saved.", true);
    await loadDashboard();
  }
}

async function createAsk(event) {
  event.preventDefault();
  const form = new FormData(elements.askForm);
  const payload = Object.fromEntries(form.entries());
  setFormStatus("Saving", false);
  const submitButton = elements.askForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/referral-asks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || "Referral ask could not be saved.");
    }
    elements.askForm.reset();
    elements.askDialog.close();
    setFormStatus("");
    await loadDashboard();
  } catch (error) {
    setFormStatus(error.message || "Referral ask could not be saved.");
  } finally {
    submitButton.disabled = false;
  }
}

function openAskDialog() {
  setFormStatus("");
  elements.askDialog.showModal();
  elements.askForm.elements.contact_name.focus();
}

function closeAskDialog() {
  elements.askDialog.close();
  setFormStatus("");
}

elements.refreshButton.addEventListener("click", () => loadDashboard());
elements.newAskButton.addEventListener("click", openAskDialog);
elements.closeDialogButton.addEventListener("click", closeAskDialog);
elements.cancelDialogButton.addEventListener("click", closeAskDialog);
elements.askForm.addEventListener("submit", createAsk);
elements.searchInput.addEventListener("input", (event) => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    state.query = event.target.value.trim();
    loadDashboard();
  }, 220);
});
elements.statusFilter.addEventListener("change", (event) => {
  state.status = event.target.value;
  loadDashboard();
});
elements.asksBody.addEventListener("change", (event) => {
  if (event.target instanceof HTMLSelectElement && event.target.dataset.referralAskId) {
    updateAskStatus(event.target.dataset.referralAskId, event.target.value);
  }
});
elements.replyList.addEventListener("change", (event) => {
  if (event.target instanceof HTMLSelectElement && event.target.dataset.replyCandidateId) {
    updateReplyReview(event.target.dataset.replyCandidateId, event.target.value);
  }
});

loadDashboard();
