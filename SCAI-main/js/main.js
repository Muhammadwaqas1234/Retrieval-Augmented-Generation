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
        setTimeout(() => {
            typeMessage('This is a generic response.', 'bot');
        }, 500);
    }
}

function addMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = text;

    const chatArea = document.getElementById('chat-area');
    chatArea.appendChild(messageElement);

    scrollToBottom();
}

function typeMessage(text, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    const chatArea = document.getElementById('chat-area');
    chatArea.appendChild(messageElement);

    let index = 0;
    function typeNextCharacter() {
        if (index < text.length) {
            messageElement.textContent += text.charAt(index);
            index++;
            setTimeout(typeNextCharacter, 50); // Adjust typing speed here
        } else {
            scrollToBottom();
        }
    }
    typeNextCharacter();
}

function scrollToBottom() {
    const chatArea = document.getElementById('chat-area');
    setTimeout(() => {
        chatArea.scrollTop = chatArea.scrollHeight;
    }, 100);  // Small delay to ensure DOM is updated
}

function autoResizeTextarea(textarea) {
    textarea.style.height = '20px'; // Reset to initial height
    textarea.style.height = textarea.scrollHeight + 'px';
}
