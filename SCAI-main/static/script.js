// Connect to the WebSocket server
const socket = io();

// DOM elements
const chatBox = document.getElementById('chat-box');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

// Function to append messages to the chat box
function appendMessage(message, type = 'received') {
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    messageElement.classList.add(type);
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight; // Scroll to the latest message
}

// Event listener for sending messages
sendButton.addEventListener('click', () => {
    const message = messageInput.value.trim();
    if (message) {
        socket.emit('send_message', message); // Send message to server
        appendMessage(message, 'sent'); // Add the message locally
        messageInput.value = ''; // Clear the input field
    }
});

// Listen for messages from the server
socket.on('receive_message', (message) => {
    appendMessage(message, 'received');
});
