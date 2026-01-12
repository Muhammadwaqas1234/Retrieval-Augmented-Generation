document.addEventListener('DOMContentLoaded', function() {
    const chatLinks = document.querySelectorAll('.chat-list li a');
    chatLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            window.location.href = this.getAttribute('href');
        });
    });
});
