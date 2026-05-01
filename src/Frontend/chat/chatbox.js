/**
 * Chat UI: dropdown (Connect bank), send message, textarea behavior, panel resize.
 * Uses window.openPlaidLink from plaid/plaid.js.
 */
(function () {
  function initChatModeDropdown() {
    var trigger = document.getElementById("chat-extra-btn");
    var dropdown = document.getElementById("chat-mode-dropdown");
    if (!trigger || !dropdown) return;

    function closeDropdown() {
      dropdown.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", onDocumentClick);
    }

    function onDocumentClick(e) {
      if (!dropdown.contains(e.target) && !trigger.contains(e.target)) closeDropdown();
    }

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.toggle("is-open");
      trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (isOpen) {
        requestAnimationFrame(function () {
          document.addEventListener("click", onDocumentClick);
        });
      } else {
        document.removeEventListener("click", onDocumentClick);
      }
    });

    dropdown.querySelectorAll(".chat-mode-dropdown-item").forEach(function (item) {
      item.addEventListener("click", function (e) {
        e.stopPropagation();
        closeDropdown();
        if (item.getAttribute("data-action") === "connect-bank" && window.openPlaidLink) window.openPlaidLink();
      });
    });
  }

  var chatMessages = document.getElementById("chat-messages");
  var chatInput = document.getElementById("chat-input");
  var chatSend = document.getElementById("chat-send");


  function appendMessage(role, text) {
    var wrap = document.createElement("div");
    wrap.className = "chat-message " + (role === "user" ? "chat-message-user" : "chat-message-assistant");
    var bubble = document.createElement("div");
    bubble.className = "chat-message-bubble";
    var p = document.createElement("p");
    p.textContent = text;
    bubble.appendChild(p);
    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }


  function appendStreamingAssistant() {
    var wrap = document.createElement("div");
    wrap.className = "chat-message chat-message-assistant";
    var bubble = document.createElement("div");
    bubble.className = "chat-message-bubble";
    var p = document.createElement("p");
    p.textContent = "";
    bubble.appendChild(p);
    wrap.appendChild(bubble);
    chatMessages.appendChild(wrap);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return p;
  }

  function sendMessage() {
    var text = (chatInput.value || "").trim();
    if (!text) return;
    chatInput.value = "";
    appendMessage("user", text);
    var base = window.API_BASE || "http://127.0.0.1:8001";
    var outP = appendStreamingAssistant();

    (window.serverFetch || fetch)(base + "/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.json().then(function (data) {
            throw new Error(data.detail || data.message || "HTTP " + res.status);
          });
        }
        if (!res.body || !res.body.getReader) {
          throw new Error("Streaming not supported in this browser");
        }
        var reader = res.body.getReader();
        var dec = new TextDecoder();
        var buf = "";

        function pump() {
          return reader.read().then(function (chunk) {
            if (chunk.done) return;
            buf += dec.decode(chunk.value, { stream: true });
            var sep;
            while ((sep = buf.indexOf("\n\n")) !== -1) {
              var block = buf.slice(0, sep);
              buf = buf.slice(sep + 2);
              block.split("\n").forEach(function (line) {
                if (line.indexOf("data: ") !== 0) return;
                var raw = line.slice(6).trim();
                if (!raw || raw === "[DONE]") return;
                var ev;
                try {
                  ev = JSON.parse(raw);
                } catch (e) {
                  return;
                }
                if (ev.type === "delta" && ev.content) {
                  outP.textContent += ev.content;
                  chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                if (ev.type === "error") {
                  outP.textContent = "Sorry, something went wrong: " + (ev.message || "error");
                }
              });
            }
            return pump();
          });
        }
        return pump();
      })
      .catch(function (err) {
        outP.textContent = "Sorry, something went wrong: " + (err.message || String(err));
      });
  }

  if (chatSend) chatSend.addEventListener("click", sendMessage);
  if (chatInput) {
    chatInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    chatInput.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 140) + "px";
    });
  }


  function initChatResize() {
    var column = document.getElementById("chat-column");
    var handle = document.getElementById("chat-resize-handle");
    if (!column || !handle) return;
    var rail = column.closest(".shell-chat-rail");
    var minW = 260;
    var maxW = 720;
    var startX = 0;
    var startW = 0;

    function onMouseMove(e) {
      var dx = startX - e.clientX;
      var newW = Math.min(maxW, Math.max(minW, startW + dx));
      if (rail) {
        rail.style.width = newW + "px";
        rail.style.maxWidth = "none";
      } else {
        column.style.width = newW + "px";
      }
    }

    function onMouseUp() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
    handle.addEventListener("mousedown", function (e) {
      e.preventDefault();
      startX = e.clientX;
      startW = rail ? rail.offsetWidth : column.offsetWidth;
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });
  }

  initChatModeDropdown();
  initChatResize();
})();
