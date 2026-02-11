/**
 * Vinum Chatbot – Floating widget (button + chat window).
 * Expects window.vinumChatbotConfig: { apiUrl, apiKey, title, welcomeMessage, inputPlaceholder, conversationTtl, buttonColor, buttonImageUrl }
 */
(function () {
    'use strict';

    var config = typeof window.vinumChatbotConfig !== 'undefined' ? window.vinumChatbotConfig : {};
    var apiUrl = (config.apiUrl || '').replace(/\/$/, '');
    var apiKey = config.apiKey || '';
    var title = config.title || 'Chat';
    var welcomeMessage = config.welcomeMessage || '';
    var inputPlaceholder = config.inputPlaceholder || 'Escribe tu mensaje...';
    var conversationTtl = Math.max(0, parseInt(config.conversationTtl, 10) || 0);
    var buttonColor = config.buttonColor || '#6E56CF';
    var buttonImageUrl = config.buttonImageUrl || '';
    var loadingGifUrl = (config.loadingGifUrl || '').trim();

    var STORAGE_KEY = 'vinum_chat_history';

    if (!apiUrl) return;

    var styleEl = document.createElement('style');
    styleEl.textContent = '.vc-hide{visibility:hidden;opacity:0;pointer-events:none;transform:translateY(8px);}.vc-window{transition:opacity .25s ease,transform .25s ease,visibility .25s;}.vc-fab{transition:transform .15s ease,box-shadow .15s ease;}' +
        '.vc-messages::-webkit-scrollbar,.vc-textarea::-webkit-scrollbar{width:6px;height:6px;}.vc-messages::-webkit-scrollbar-track,.vc-textarea::-webkit-scrollbar-track{background:#1f2937;border-radius:3px;}.vc-messages::-webkit-scrollbar-thumb,.vc-textarea::-webkit-scrollbar-thumb{background:#4b5563;border-radius:3px;}.vc-messages::-webkit-scrollbar-thumb:hover,.vc-textarea::-webkit-scrollbar-thumb:hover{background:#6b7280;}' +
        '.vc-messages{scrollbar-width:thin;scrollbar-color:#4b5563 #1f2937;}.vc-textarea{scrollbar-width:thin;scrollbar-color:#4b5563 #1f2937;}' +
        '.vc-loading{display:flex;align-items:center;gap:8px;max-width:80%;margin:6px 0;padding:12px 14px;background:#1f2937;border-radius:12px;border-top-left-radius:4px;margin-right:auto;}' +
        '.vc-loading-gif{width:32px;height:32px;object-fit:contain;flex-shrink:0;}' +
        '.vc-loading-dots{display:flex;gap:4px;align-items:center;}' +
        '.vc-loading-dots span{width:6px;height:6px;border-radius:50%;background:#9ca3af;animation:vc-bounce 0.6s ease-in-out infinite alternate;}' +
        '.vc-loading-dots span:nth-child(2){animation-delay:0.2s;}.vc-loading-dots span:nth-child(3){animation-delay:0.4s;}' +
        '@keyframes vc-bounce{0%{transform:translateY(0);}100%{transform:translateY(-6px);}}';
    (document.head || document.documentElement).appendChild(styleEl);

    function shade(hex, amt) {
        var h = hex.replace('#', '');
        var i = parseInt(h.length === 3 ? h.split('').map(function (c) { return c + c; }).join('') : h, 16);
        var r = (i >> 16) & 255, g = (i >> 8) & 255, b = i & 255;
        var d = Math.round(255 * amt / 100);
        r = Math.max(0, Math.min(255, r + d));
        g = Math.max(0, Math.min(255, g + d));
        b = Math.max(0, Math.min(255, b + d));
        return '#' + [r, g, b].map(function (x) { return x.toString(16).padStart(2, '0'); }).join('');
    }

    var brandDark = shade(buttonColor, -10);

    var wrap = document.createElement('div');
    wrap.className = 'vc-wrap';
    wrap.style.cssText = 'position:fixed;right:20px;bottom:20px;width:56px;height:56px;z-index:2147483000;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;';

    var windowEl = document.createElement('div');
    windowEl.className = 'vc-window vc-hide';
    windowEl.setAttribute('aria-label', title);
    windowEl.style.cssText = 'position:absolute;right:0;bottom:68px;width:min(360px,calc(100vw - 40px));height:520px;border-radius:16px;overflow:hidden;background:#111827;color:#e5e7eb;box-shadow:0 24px 60px rgba(0,0,0,.35);display:flex;flex-direction:column;';

    var header = document.createElement('div');
    header.className = 'vc-header';
    header.style.cssText = 'background:linear-gradient(180deg,' + buttonColor + ',' + brandDark + ');color:#fff;padding:12px 14px;display:flex;align-items:center;justify-content:space-between;gap:8px;';

    var headerLeft = document.createElement('div');
    headerLeft.style.cssText = 'display:inline-flex;align-items:center;gap:10px;min-width:0;';
    var logoImg = document.createElement('img');
    logoImg.className = 'vc-logo';
    logoImg.alt = 'Logo';
    logoImg.style.cssText = 'width:20px;height:20px;object-fit:contain;';
    if (buttonImageUrl) {
        logoImg.src = buttonImageUrl;
    } else {
        logoImg.style.display = 'none';
    }
    var titleEl = document.createElement('div');
    titleEl.className = 'vc-title';
    titleEl.style.cssText = 'font-weight:600;font-size:14px;letter-spacing:.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    titleEl.textContent = title;
    headerLeft.appendChild(logoImg);
    headerLeft.appendChild(titleEl);

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'vc-close';
    closeBtn.setAttribute('aria-label', 'Cerrar');
    closeBtn.title = 'Cerrar';
    closeBtn.textContent = '\u2715';
    closeBtn.style.cssText = 'appearance:none;border:none;background:transparent;color:#fff;width:32px;height:32px;border-radius:8px;cursor:pointer;';
    closeBtn.addEventListener('mouseenter', function () { closeBtn.style.background = 'rgba(255,255,255,.15)'; });
    closeBtn.addEventListener('mouseleave', function () { closeBtn.style.background = 'transparent'; });

    header.appendChild(headerLeft);
    header.appendChild(closeBtn);

    var messages = document.createElement('div');
    messages.className = 'vc-messages';
    messages.style.cssText = 'flex:1;overflow:auto;padding:12px;scroll-behavior:smooth;';

    var inputRow = document.createElement('div');
    inputRow.className = 'vc-input';
    inputRow.style.cssText = 'border-top:1px solid #1f2937;padding:10px;display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end;background:#0b1220;';

    var textarea = document.createElement('textarea');
    textarea.className = 'vc-textarea';
    textarea.rows = 1;
    textarea.placeholder = inputPlaceholder;
    textarea.setAttribute('aria-label', 'Escribir mensaje');
    textarea.style.cssText = 'resize:none;min-height:40px;max-height:120px;width:90%;font-size:13px;line-height:1.35;color:#e5e7eb;background:#0f172a;border:1px solid #1f2937;border-radius:10px;padding:10px 12px;outline:none;box-sizing:border-box;overflow-y:auto;';

    var sendBtn = document.createElement('button');
    sendBtn.type = 'button';
    sendBtn.className = 'vc-send';
    sendBtn.setAttribute('aria-label', 'Enviar');
    sendBtn.style.cssText = 'appearance:none;border:none;cursor:pointer;background:' + buttonColor + ';color:#fff;border-radius:10px;padding:10px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;';
    sendBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';

    inputRow.appendChild(textarea);
    inputRow.appendChild(sendBtn);

    windowEl.appendChild(header);
    windowEl.appendChild(messages);
    windowEl.appendChild(inputRow);

    var fab = document.createElement('button');
    fab.type = 'button';
    fab.className = 'vc-fab';
    fab.setAttribute('aria-label', 'Abrir chat');
    fab.title = title;
    fab.style.cssText = 'position:absolute;right:0;bottom:0;width:56px;height:56px;border-radius:999px;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 20px rgba(0,0,0,.15),0 2px 6px rgba(0,0,0,.1);background:' + buttonColor + ';color:#fff;border:none;cursor:pointer;';
    if (buttonImageUrl) {
        var fabImg = document.createElement('img');
        fabImg.src = buttonImageUrl;
        fabImg.alt = '';
        fabImg.style.cssText = 'width:40;height:36px;object-fit:contain;';
        fab.appendChild(fabImg);
    } else {
        fab.textContent = '\uD83D\uDCAC';
    }

    fab.addEventListener('mouseenter', function () {
        fab.style.transform = 'translateY(-1px)';
        fab.style.boxShadow = '0 12px 22px rgba(0,0,0,.18), 0 3px 7px rgba(0,0,0,.12)';
    });
    fab.addEventListener('mouseleave', function () {
        fab.style.transform = '';
        fab.style.boxShadow = '0 10px 20px rgba(0,0,0,.15), 0 2px 6px rgba(0,0,0,.1)';
    });

    wrap.appendChild(windowEl);
    wrap.appendChild(fab);

    var open = false;
    var sending = false;

    function toggle(show) {
        open = typeof show === 'boolean' ? show : !open;
        if (open) {
            windowEl.classList.remove('vc-hide');
            fab.classList.remove('vc-hide');
            fab.setAttribute('aria-label', 'Cerrar chat');
            if (welcomeMessage && messages.children.length === 0) {
                appendMessage('assistant', welcomeMessage, true, false);
                saveConversation();
            }
            setTimeout(function () { textarea.focus(); }, 0);
        } else {
            windowEl.classList.add('vc-hide');
            fab.setAttribute('aria-label', 'Abrir chat');
        }
        try { localStorage.setItem('vinum_chat_open', open ? '1' : '0'); } catch (e) {}
    }

    fab.addEventListener('click', function () { toggle(); });
    closeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggle(false);
    });

    function markdownToHtml(text) {
        if (!text) return '';
        var linkStyle = 'color:#93c5fd;text-decoration:underline;';
        text = (text + '').replace(/<a\s+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi, '[$2]($1)');
        var div = document.createElement('div');
        div.textContent = text;
        var s = div.innerHTML;
        s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="' + linkStyle + '">$1</a>');
        s = s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
        return s;
    }

    var loadingEl = null;

    function isGifUrl(url) {
        return url && /\.gif(\?|$)/i.test(url);
    }

    function showLoading() {
        if (loadingEl) return;
        loadingEl = document.createElement('div');
        loadingEl.className = 'vc-loading';
        loadingEl.setAttribute('aria-live', 'polite');
        if (isGifUrl(loadingGifUrl)) {
            var img = document.createElement('img');
            img.src = loadingGifUrl;
            img.alt = '';
            img.className = 'vc-loading-gif';
            loadingEl.appendChild(img);
        }
        var dots = document.createElement('div');
        dots.className = 'vc-loading-dots';
        dots.innerHTML = '<span></span><span></span><span></span>';
        loadingEl.appendChild(dots);
        messages.appendChild(loadingEl);
        messages.scrollTop = messages.scrollHeight;
    }

    function hideLoading() {
        if (loadingEl && loadingEl.parentNode) {
            loadingEl.parentNode.removeChild(loadingEl);
        }
        loadingEl = null;
    }

    function appendMessage(role, text, useHtml, isBotMarkdown) {
        var el = document.createElement('div');
        el.className = 'vc-msg ' + (role === 'user' ? 'vc-user' : 'vc-bot');
        el.style.cssText = 'max-width:80%;padding:10px 12px;border-radius:12px;margin:6px 0;line-height:1.35;font-size:13px;white-space:pre-wrap;word-wrap:break-word;';
        if (role === 'user') {
            el.style.background = '#374151';
            el.style.marginLeft = 'auto';
            el.style.borderTopRightRadius = '4px';
        } else {
            el.style.background = '#1f2937';
            el.style.marginRight = 'auto';
            el.style.borderTopLeftRadius = '4px';
        }
        if (useHtml) {
            el.innerHTML = text;
        } else if (isBotMarkdown && role === 'assistant') {
            el.innerHTML = markdownToHtml(text);
        } else {
            el.textContent = text;
        }
        messages.appendChild(el);
        messages.scrollTop = messages.scrollHeight;
    }

    function saveConversation() {
        if (conversationTtl <= 0) return;
        try {
            var items = [];
            var nodes = messages.querySelectorAll('.vc-msg');
            for (var i = 0; i < nodes.length; i++) {
                var n = nodes[i];
                var role = n.classList.contains('vc-user') ? 'user' : 'assistant';
                if (role === 'assistant') {
                    items.push({ role: role, content: n.innerHTML });
                } else {
                    items.push({ role: role, content: n.textContent || n.innerText || '' });
                }
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                messages: items,
                savedAt: Date.now()
            }));
        } catch (e) {}
    }

    function loadConversation() {
        if (conversationTtl <= 0) return;
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            var data = JSON.parse(raw);
            var items = data.messages;
            var savedAt = data.savedAt || 0;
            if (!items || !items.length) return;
            var maxAge = conversationTtl * 60 * 1000;
            if (Date.now() - savedAt > maxAge) {
                localStorage.removeItem(STORAGE_KEY);
                return;
            }
            for (var i = 0; i < items.length; i++) {
                var item = items[i];
                var content = item.content !== undefined ? item.content : item.text;
                if (item.role === 'user') {
                    appendMessage('user', content || '');
                } else {
                    appendMessage('assistant', content || '', true, false);
                }
            }
        } catch (e) {}
    }

    function sendToApi(message) {
        var url = apiUrl + '/chat';
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', url, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            if (apiKey) {
                xhr.setRequestHeader('Authorization', 'Bearer ' + apiKey);
            }
            xhr.onload = function () {
                if (xhr.status === 401) {
                    reject({ status: 401 });
                    return;
                }
                if (xhr.status < 200 || xhr.status >= 300) {
                    reject(new Error(xhr.responseText || 'HTTP ' + xhr.status));
                    return;
                }
                try {
                    var data = JSON.parse(xhr.responseText || '{}');
                    resolve(data);
                } catch (e) {
                    resolve({});
                }
            };
            xhr.onerror = function () { reject(new Error('Network error')); };
            xhr.send(JSON.stringify({ q: message }));
        });
    }

    function onSend() {
        if (sending) return;
        var text = (textarea.value || '').trim();
        if (!text) return;

        appendMessage('user', text);
        textarea.value = '';
        textarea.style.height = '40px';
        sending = true;
        sendBtn.disabled = true;
        showLoading();

        sendToApi(text)
            .then(function (data) {
                var answer = data && data.answer;
                if (typeof answer === 'string' && answer) {
                    appendMessage('assistant', answer, false, true);
                }
                saveConversation();
            })
            .catch(function (err) {
                if (!(err && err.status === 401)) {
                    appendMessage('assistant', 'No se pudo enviar el mensaje. Inténtalo de nuevo.');
                }
                saveConversation();
            })
            .finally(function () {
                hideLoading();
                sending = false;
                sendBtn.disabled = false;
            });
    }

    function autoResizeTextarea() {
        textarea.style.height = 'auto';
        var h = textarea.scrollHeight;
        if (h > 120) h = 120;
        else if (h < 40) h = 40;
        textarea.style.height = h + 'px';
    }
    textarea.addEventListener('input', autoResizeTextarea);

    sendBtn.addEventListener('click', onSend);
    textarea.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    });

    document.body.appendChild(wrap);

    try {
        loadConversation();
        if (localStorage.getItem('vinum_chat_open') === '1') {
            toggle(true);
        }
    } catch (e) {}
})();
