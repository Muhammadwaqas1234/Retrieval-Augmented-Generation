document.getElementById('send-button').addEventListener('click', function() {
    sendMessage();
});

document.getElementById('search-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

document.getElementById('search-input').addEventListener('input', function() {
    autoResizeTextarea(this);
});

function sendMessage() {
    const inputElement = document.getElementById('search-input');
    const message = inputElement.value.trim();
    if (message !== '') {
        addMessage(message, 'user');
        inputElement.value = '';
        inputElement.style.height = '20px'; // Reset height
        setTimeout(() => addMessage('This is a generic response.', 'bot'), 500);
    }
}

function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;

    const chatArea = document.getElementById('chat-area');
    chatArea.insertBefore(messageElement, chatArea.firstChild);
}

function autoResizeTextarea(textarea) {
    textarea.style.height = '20px'; // Reset to initial height
    textarea.style.height = textarea.scrollHeight + 'px';
    const chatArea = document.getElementById('chat-area');
    chatArea.style.paddingBottom = textarea.scrollHeight + 25 + 'px';
}
