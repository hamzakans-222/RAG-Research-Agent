"use strict";

function copyButton(text, label, className = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `copy-button ${className}`;
  button.textContent = label;
  button.setAttribute("aria-label", label);
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = "Copié ✓";
    } catch {
      button.textContent = "Copie indisponible";
    }
    setTimeout(() => { button.textContent = label; }, 2000);
  });
  return button;
}

// Build formatting with DOM nodes: document and model text never becomes HTML.
function appendInline(parent, text) {
  const pattern = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let offset = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(offset, match.index)));
    const node = document.createElement(match[2] ? "strong" : "code");
    node.textContent = match[2] || match[3];
    parent.append(node);
    offset = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(offset)));
}

function formatReply(article) {
  const content = article.querySelector(".message-content");
  if (!content || content.classList.contains("formatted")) return;
  const raw = content.textContent;
  content.replaceChildren();
  content.classList.add("formatted");
  const lines = raw.split("\n");
  let paragraph = [], list = null;
  const flush = () => {
    if (paragraph.length) {
      const p = document.createElement("p");
      appendInline(p, paragraph.join("\n"));
      content.append(p);
      paragraph = [];
    }
    list = null;
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fence = line.match(/^\s*```(.*)$/);
    if (fence) {
      flush();
      const codeLines = [];
      while (++i < lines.length && !/^\s*```\s*$/.test(lines[i])) codeLines.push(lines[i]);
      const block = document.createElement("div");
      block.className = "code-block";
      const header = document.createElement("div");
      header.className = "code-header";
      const language = document.createElement("span");
      language.textContent = fence[1].trim() || "code";
      const codeText = codeLines.join("\n");
      header.append(language, copyButton(codeText, "Copier le code"));
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codeText;
      pre.append(code);
      block.append(header, pre);
      content.append(block);
    } else if (/^#{1,6}\s/.test(line)) {
      flush();
      const heading = document.createElement("h3");
      appendInline(heading, line.replace(/^#{1,6}\s+/, ""));
      content.append(heading);
    } else if (/^\s*(?:[-*]|\d+[.)])\s+/.test(line)) {
      const tag = /^\s*\d/.test(line) ? "ol" : "ul";
      if (!list || list.tagName.toLowerCase() !== tag) {
        flush();
        list = document.createElement(tag);
        content.append(list);
      }
      const item = document.createElement("li");
      appendInline(item, line.replace(/^\s*(?:[-*]|\d+[.)])\s+/, ""));
      list.append(item);
    } else if (!line.trim()) {
      flush();
    } else {
      list = null;
      paragraph.push(line);
    }
  }
  flush();
  article.querySelector(".message-body").append(copyButton(raw, "Copier la réponse", "message-copy"));
}

document.querySelectorAll("#message-list .message-assistant").forEach(formatReply);

/* ══════════════════════════════════════════════════════════════
   Research assistant — Client-side interactions
   ══════════════════════════════════════════════════════════════ */

/* ── Document Upload ───────────────────────────────────────── */
const uploadForm = document.getElementById("document-upload-form");
if (uploadForm) {
  const uploadInput = document.getElementById("document-file");
  const uploadButton = document.getElementById("upload-submit");
  const feedback = document.getElementById("upload-feedback");
  const uploadStatus = document.getElementById("import-status");
  let uploading = false;
  function showUploadStatus(message, error = false) {
    feedback.textContent = message;
    uploadStatus.textContent = message;
    feedback.classList.toggle("error", error);
    uploadStatus.classList.toggle("error", error);
  }
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (uploading || !uploadInput.files.length) return;
    const file = uploadInput.files[0];
    if (file.size > 10 * 1024 * 1024) {
      showUploadStatus("Le fichier dépasse la taille maximale de 10 Mo.", true);
      return;
    }
    if (!/\.(pdf|txt|md)$/i.test(file.name)) {
      showUploadStatus("Formats acceptés : PDF, TXT et Markdown (.md).", true);
      return;
    }
    const body = new FormData(uploadForm);
    uploading = true;
    uploadInput.disabled = true;
    uploadButton.disabled = true;
    uploadButton.textContent = "Indexation en cours…";
    uploadForm.setAttribute("aria-busy", "true");
    showUploadStatus("Lecture et indexation en cours… Cela peut prendre quelques minutes.");
    try {
      const response = await fetch(uploadForm.action, {
        method: "POST", body, headers: { "Accept": "application/json" },
        credentials: "same-origin", signal: AbortSignal.timeout(600000),
      });
      if (response.redirected || response.status === 403) {
        throw new Error("Votre session a expiré. Reconnectez-vous puis réessayez l'import.");
      }
      if (!(response.headers.get("content-type") || "").includes("application/json")) {
        throw new Error(response.status === 404
          ? "Cette conversation n'est plus disponible."
          : "L'import n'a pas pu être confirmé. Vous pouvez réessayer sans créer de doublon.");
      }
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Impossible d'importer le document.");
      const list = document.getElementById("document-list");
      if (!list.querySelector(`[data-document-id="${data.document.id}"]`)) {
        const card = document.createElement("article");
        card.className = "document-card";
        card.dataset.documentId = data.document.id;
        const icon = document.createElement("span");
        icon.className = "document-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "▤";
        const info = document.createElement("div");
        info.className = "document-info";
        const name = document.createElement("strong");
        name.textContent = data.document.filename;
        const details = document.createElement("span");
        details.textContent = `${data.document.chunk_count} passage${data.document.chunk_count > 1 ? "s" : ""} · ${data.document.date}`;
        info.append(name, details);
        const badge = document.createElement("span");
        badge.className = "document-badge";
        badge.textContent = "Indexé";
        card.append(icon, info, badge);
        list.prepend(card);
      }
      document.getElementById("document-count").textContent = data.document_count;
      document.getElementById("document-empty").hidden = true;
      document.getElementById("document-panel").open = true;
      document.getElementById("chat-area").scrollTop = 0;
      showUploadStatus(data.message);
      uploadInput.value = "";
      document.getElementById("import-dialog").close();
    } catch (error) {
      showUploadStatus(["TimeoutError", "AbortError", "TypeError"].includes(error.name)
        ? "Connexion interrompue. Réessayez l'import : un document déjà indexé ne sera pas dupliqué."
        : error.message, true);
    } finally {
      uploading = false;
      uploadInput.disabled = false;
      uploadButton.disabled = false;
      uploadButton.textContent = "Importer et indexer";
      uploadForm.removeAttribute("aria-busy");
    }
  });
}

/* ── Sidebar (mobile toggle) ───────────────────────────────── */
const sidebar = document.querySelector(".sidebar");
const menuButton = document.querySelector(".menu-button");
const overlay = document.querySelector(".sidebar-overlay");
function closeSidebar() {
  sidebar?.classList.remove("open");
  if (overlay) overlay.hidden = true;
  menuButton?.setAttribute("aria-expanded", "false");
}
menuButton?.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  overlay.hidden = !open;
  menuButton.setAttribute("aria-expanded", String(open));
});
overlay?.addEventListener("click", closeSidebar);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeSidebar();
});

/* ── Dialog openers / closers ──────────────────────────────── */
document.querySelectorAll("[data-dialog]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.dialog).showModal());
});
document.querySelectorAll("[data-close-dialog]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

/* ── Conversation search ───────────────────────────────────── */
const search = document.getElementById("conversation-search");
document.getElementById("search-shortcut")?.addEventListener("click", () => search?.focus());
document.addEventListener("keydown", (event) => {
  if (!search || !menuButton) return;
  if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey
      && !event.target.closest("input, textarea, [contenteditable], dialog")) {
    event.preventDefault();
    if (getComputedStyle(menuButton).display !== "none" && !sidebar.classList.contains("open")) menuButton.click();
    search?.focus();
  }
});
document.querySelectorAll("[data-documents]").forEach((button) => {
  button.addEventListener("click", () => {
    const panel = document.getElementById("document-panel");
    if (!panel) return;
    panel.open = true;
    closeSidebar();
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    panel.querySelector("summary").focus({ preventScroll: true });
  });
});
search?.addEventListener("input", () => {
  const query = search.value.trim().toLocaleLowerCase("fr");
  let count = 0;
  document.querySelectorAll(".conversation-link").forEach((link) => {
    link.hidden = !link.querySelector(".conversation-name").textContent.toLocaleLowerCase("fr").includes(query);
    if (!link.hidden) count++;
  });
  document.getElementById("search-empty").hidden = count > 0 || query.length === 0;
});

/* ── Chat & Composer ───────────────────────────────────────── */
const form = document.getElementById("message-form");
const chatArea = document.getElementById("chat-area");
if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;

/* Auto-grow textarea */
function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
}

if (form) {
  const textarea = document.getElementById("message-content");
  const sendButton = document.getElementById("send-button");
  const status = document.getElementById("send-status");

  /* Auto-grow on input */
  textarea.addEventListener("input", () => autoGrow(textarea));
  /* Initial auto-grow if there's a draft */
  if (textarea.value.trim()) autoGrow(textarea);
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      if (textarea.readOnly) return;
      textarea.value = button.dataset.prompt;
      autoGrow(textarea);
      textarea.focus();
    });
  });

  /* Thinking indicator */
  const thinking = document.createElement("div");
  thinking.className = "message message-assistant chat-thinking";
  thinking.hidden = true;
  thinking.setAttribute("role", "status");
  thinking.innerHTML = '<span class="avatar assistant-avatar" aria-hidden="true">✦</span>'
    + '<div class="message-body"><div class="message-meta"><strong>Research assistant</strong></div>'
    + '<div class="thinking-label"><span class="thinking-dots" aria-hidden="true">'
    + '<span></span><span></span><span></span></span>Réflexion en cours…</div></div>';
  chatArea.append(thinking);
  let sending = false;

  function appendMessage(message) {
    if (!message) return;
    const list = document.getElementById("message-list");
    if (list.querySelector(`[data-message-id="${message.id}"]`)) return;
    const assistant = message.role === "assistant";
    const article = document.createElement("article");
    article.className = `message message-${assistant ? "assistant" : "user"}`;
    article.dataset.messageId = message.id;
    const avatar = document.createElement("span");
    avatar.className = assistant ? "avatar assistant-avatar" : "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = assistant ? "✦" : form.dataset.username.slice(0, 1).toLocaleUpperCase("fr");
    const body = document.createElement("div");
    body.className = "message-body";
    const meta = document.createElement("div");
    meta.className = "message-meta";
    const author = document.createElement("strong");
    author.textContent = assistant ? "Research assistant" : "Vous";
    const time = document.createElement("time");
    time.textContent = message.time;
    meta.append(author, time);
    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = message.content;
    body.append(meta, content);
    article.append(avatar, body);
    list.append(article);
    if (assistant) formatReply(article);
    document.getElementById("conversation-empty").hidden = true;
  }

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!sending && textarea.value.trim()) form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending || !textarea.value.trim()) return;
    sending = true;
    sendButton.disabled = true;
    textarea.readOnly = true;
    status.classList.remove("error");
    form.setAttribute("aria-busy", "true");
    status.textContent = "L'assistant prépare sa réponse… Le premier chargement peut prendre quelques minutes.";
    appendMessage({ id: "pending", role: "user", content: textarea.value.trim(),
      time: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) });
    thinking.hidden = false;
    document.getElementById("conversation-empty").hidden = true;
    chatArea.scrollTop = chatArea.scrollHeight;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "Accept": "application/json" },
        credentials: "same-origin",
        signal: AbortSignal.timeout(360000),
      });
      if (response.redirected) {
        throw new Error("Votre session a expiré. Copiez votre message puis reconnectez-vous.");
      }
      if (response.status === 403) {
        throw new Error("La session doit être actualisée. Copiez votre message puis rechargez la page.");
      }
      if (!(response.headers.get("content-type") || "").includes("application/json")) {
        throw new Error("L'enregistrement a échoué. Votre texte est conservé, vous pouvez réessayer.");
      }
      const data = await response.json();
      document.querySelector('[data-message-id="pending"]')?.remove();
      appendMessage(data.message);
      appendMessage(data.reply);
      if (!data.message) throw new Error(data.error || "Impossible d'enregistrer le message.");
      document.getElementById("conversation-empty").hidden = true;
      document.getElementById("conversation-title").textContent = data.title;
      document.getElementById("rename-title").value = data.title;
      document.getElementById("delete-title").textContent = data.title;
      document.title = `${data.title} — Research assistant`;
      const link = document.querySelector(`[data-conversation="${form.dataset.conversation}"].conversation-link`);
      if (link) {
        link.querySelector(".conversation-name").textContent = data.title;
        link.querySelector(".conversation-date").textContent = `Aujourd'hui · ${data.message_count} message${data.message_count > 1 ? "s" : ""}`;
        link.parentElement.prepend(link);
      }
      document.getElementById("request-id").value = data.next_request_id;
      chatArea.scrollTop = chatArea.scrollHeight;
      if (!response.ok) throw new Error(data.error || "La réponse est indisponible. Réessayez.");
      textarea.value = "";
      textarea.style.height = "auto";
      status.textContent = "Réponse enregistrée dans cette conversation.";
      chatArea.scrollTop = chatArea.scrollHeight;
    } catch (error) {
      status.classList.add("error");
      status.textContent = ["TimeoutError", "AbortError", "TypeError"].includes(error.name)
        ? "Connexion interrompue. Votre texte est conservé ; réessayez pour vérifier son enregistrement."
        : error.message;
    } finally {
      document.querySelector('[data-message-id="pending"]')?.remove();
      thinking.hidden = true;
      document.getElementById("conversation-empty").hidden = Boolean(
        document.querySelector("#message-list [data-message-id]"),
      );
      sending = false;
      form.removeAttribute("aria-busy");
      sendButton.disabled = false;
      textarea.readOnly = false;
      textarea.focus({ preventScroll: true });
    }
  });
}
