document.addEventListener('DOMContentLoaded', () => {
    initAIChatWidget();
});

function initAIChatWidget() {
    const triggerBtn = document.getElementById('aiChatTrigger');
    const drawer = document.getElementById('aiChatDrawer');
    const closeBtn = document.getElementById('aiChatClose');
    const sendBtn = document.getElementById('aiSendBtn');
    const inputField = document.getElementById('aiInput');
    const chatBody = document.getElementById('aiChatBody');

    if (!triggerBtn || !drawer) return;

    triggerBtn.addEventListener('click', () => {
        drawer.classList.toggle('open');
        if (drawer.classList.contains('open') && inputField) {
            inputField.focus();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            drawer.classList.remove('open');
        });
    }

    async function sendMessage() {
        const text = inputField.value.strip ? inputField.value.trim() : inputField.value;
        if (!text) return;

        // Render User Bubble
        appendBubble(text, 'user');
        inputField.value = '';

        // Show typing indicator
        const typingId = appendTypingIndicator();

        try {
            const res = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();
            removeTypingIndicator(typingId);

            if (data.response) {
                appendBubble(data.response, 'bot');
            } else {
                appendBubble("Sorry, I could not process your query at this time.", 'bot');
            }
        } catch (err) {
            removeTypingIndicator(typingId);
            appendBubble("Network error connecting to AI Assistant.", 'bot');
        }
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (inputField) {
        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    function appendBubble(message, sender) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${sender}`;

        // Simple format for bold and line breaks
        let formatted = message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');

        bubble.innerHTML = formatted;
        chatBody.appendChild(bubble);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function appendTypingIndicator() {
        const id = 'typing_' + Date.now();
        const bubble = document.createElement('div');
        bubble.id = id;
        bubble.className = 'chat-bubble bot';
        bubble.innerHTML = '<span style="font-style:italic; color:#94a3b8;">AI Assistant is thinking...</span>';
        chatBody.appendChild(bubble);
        chatBody.scrollTop = chatBody.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
}
