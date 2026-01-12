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

    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const docArea = document.getElementById('doc-area');

    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });

    uploadArea.addEventListener('dragover', function(event) {
        event.preventDefault();
        uploadArea.classList.add('dragging');
    });

    uploadArea.addEventListener('dragleave', function() {
        uploadArea.classList.remove('dragging');
    });

    uploadArea.addEventListener('drop', function(event) {
        event.preventDefault();
        uploadArea.classList.remove('dragging');
        const files = event.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        const files = fileInput.files;
        handleFiles(files);
    });

    function handleFiles(files) {
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
    }

    // Save functions
    window.saveAsPDF = function() {
        // Implement save as PDF logic
        alert('Save as PDF functionality coming soon!');
    };

    window.saveAsWord = function() {
        // Implement save as Word logic
        alert('Save as Word functionality coming soon!');
    };

    window.saveAsDoc = function() {
        // Implement save as Doc logic
        alert('Save as Doc functionality coming soon!');
    };
});
