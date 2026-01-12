document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.sidebar-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            this.classList.toggle('active');
            const dropdown = this.nextElementSibling;
            if (dropdown && dropdown.classList.contains('dropdown')) {
                dropdown.classList.toggle('open');
            }
        });
    });

    const uploadInput = document.getElementById('upload-input');
    const docArea = document.getElementById('doc-area');
    const searchInput = document.getElementById('search-input');
    const sendButton = document.getElementById('send-button');
    const convertMenu = document.getElementById('convert-menu');
    const convertButton = document.getElementById('convert-button');
    const convertPdfButton = document.getElementById('convert-pdf-button');
    const convertWordButton = document.getElementById('convert-word-button');
    const extractTextButton = document.getElementById('extract-text-button');
    const editor = document.getElementById('editor');

    document.querySelector('.attach-icon').addEventListener('click', function() {
        uploadInput.click();
    });

    uploadInput.addEventListener('change', function() {
        const files = uploadInput.files;
        for (const file of files) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const newElement = document.createElement('div');
                newElement.classList.add('uploaded-element');
                newElement.innerHTML = `<button class="delete-btn">X</button>`;
                if (file.type.startsWith('image/')) {
                    newElement.innerHTML += `<img src="${e.target.result}" alt="${file.name}" class="uploaded-image">`;
                } else if (file.type === 'application/pdf') {
                    newElement.innerHTML += `<embed src="${e.target.result}" type="application/pdf" width="100%" height="500px">`;
                } else {
                    newElement.innerHTML += `<p>${file.name}</p>`;
                }
                docArea.appendChild(newElement);
                newElement.querySelector('.delete-btn').addEventListener('click', function() {
                    newElement.remove();
                });
            };
            reader.readAsDataURL(file);
        }
    });

    sendButton.addEventListener('click', sendMessage);
    searchInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    convertButton.addEventListener('click', function() {
        convertMenu.classList.toggle('show');
    });

    extractTextButton.addEventListener('click', function() {
        fetch('/extract_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ images: getImages() }),
        })
        .then(response => response.json())
        .then(data => {
            editor.value = data.extracted_text;
        });
    });

    convertPdfButton.addEventListener('click', function() {
        fetch('/convert_text_to_pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: editor.value }),
        })
        .then(response => response.blob())
        .then(blob => {
            displayConvertedFile(blob, 'document.pdf');
        });
    });

    convertWordButton.addEventListener('click', function() {
        fetch('/convert_text_to_word', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: editor.value }),
        })
        .then(response => response.blob())
        .then(blob => {
            displayConvertedFile(blob, 'document.docx');
        });
    });

    function sendMessage() {
        const userMessage = searchInput.value.trim();
        if (userMessage === '') return;

        const userMessageElement = document.createElement('div');
        userMessageElement.classList.add('message', 'user');
        userMessageElement.textContent = userMessage;
        docArea.prepend(userMessageElement);

        searchInput.value = '';

        setTimeout(() => {
            const serverMessageElement = document.createElement('div');
            serverMessageElement.classList.add('message', 'website');
            serverMessageElement.textContent = 'This is a simulated response.';
            docArea.prepend(serverMessageElement);
        }, 1000);
    }

    function getImages() {
        const images = [];
        docArea.querySelectorAll('.uploaded-image').forEach(img => {
            images.push(img.src);
        });
        return images;
    }

    function displayConvertedFile(blob, filename) {
        const newElement = document.createElement('div');
        newElement.classList.add('uploaded-element');
        const url = window.URL.createObjectURL(blob);
        if (filename.endsWith('.pdf')) {
            newElement.innerHTML = `<button class="delete-btn">X</button><embed src="${url}" type="application/pdf" width="100%" height="500px">`;
        } else if (filename.endsWith('.docx')) {
            newElement.innerHTML = `<button class="delete-btn">X</button><p>Word document created: <a href="${url}" download="${filename}">${filename}</a></p>`;
        }
        docArea.appendChild(newElement);
        newElement.querySelector('.delete-btn').addEventListener('click', function() {
            newElement.remove();
        });
    }
});
