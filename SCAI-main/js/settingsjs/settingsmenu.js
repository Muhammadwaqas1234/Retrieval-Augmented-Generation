document.addEventListener('DOMContentLoaded', () => {
    const settingsLink = document.getElementById('settings-link');
    const settingsPopup = document.getElementById('settings-popup');
    const closeButton = document.getElementById('close-button');

    settingsLink.addEventListener('click', (event) => {
        event.preventDefault();
        settingsPopup.style.display = 'flex';
    });

    closeButton.addEventListener('click', () => {
        settingsPopup.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == settingsPopup) {
            settingsPopup.style.display = 'none';
        }
    });

    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.addEventListener('click', (event) => {
            event.preventDefault();
            document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.settings-section').forEach(section => section.classList.remove('active'));
            tab.classList.add('active');
            const sectionId = tab.id.replace('-tab', '-section');
            if (sectionId === 'contact-us-section') {
                loadContactUsPage();
            } else {
                document.getElementById(sectionId).classList.add('active');
            }
        });
    });

    document.getElementById('general-tab').click(); // Open the General tab by default

    function loadContactUsPage() {
        fetch('settingshtml/contact-us.html')
            .then(response => response.text())
            .then(html => {
                document.getElementById('help-section').innerHTML = html;
                const script = document.createElement('script');
                script.textContent = `
                    document.getElementById('contact-form').addEventListener('submit', function(event) {
                        event.preventDefault();
                        console.log('Form submitted');
                    });
                `;
                document.getElementById('help-section').appendChild(script);
            })
            .catch(error => console.error('Error loading Contact Us page:', error));
    }
});
document.addEventListener('DOMContentLoaded', () => {
    const languageDropdown = document.querySelector('.language-dropdown select');
    const voiceDropdown = document.querySelector('#speech-section select');

    languageDropdown.addEventListener('change', (event) => {
        const selectedLanguage = event.target.value;
        changeLanguage(selectedLanguage);
    });

    voiceDropdown.addEventListener('change', (event) => {
        const selectedVoice = event.target.value;
        changeVoice(selectedVoice);
    });

    const resources = {
        en: {
            translation: {
                "Language": "Language",
                "Speech": "Speech",
                // Add all your text translations here
            }
        },
        es: {
            translation: {
                "Language": "Idioma",
                "Speech": "Voz",
                // Add all your text translations here
            }
        }
    };

    i18next.init({
        lng: 'en',
        debug: true,
        resources
    }, function(err, t) {
        // Initialize the UI with the default language
        updateContent();
    });

    function changeLanguage(language) {
        i18next.changeLanguage(language, (err, t) => {
            if (err) return console.error('Error loading language', err);
            updateContent();
        });
    }

    function updateContent() {
        document.querySelector('.language-dropdown label').innerText = i18next.t('Language');
        document.querySelector('#speech-section h3').innerText = i18next.t('Speech');
        // Update other elements as needed
    }

    let synth = window.speechSynthesis;
    let selectedVoice;

    function changeVoice(voiceName) {
        selectedVoice = synth.getVoices().find(voice => voice.name === voiceName);
    }

    function speak(text) {
        if (synth.speaking) {
            console.error('speechSynthesis.speaking');
            return;
        }

        if (text !== '') {
            const utterThis = new SpeechSynthesisUtterance(text);
            utterThis.voice = selectedVoice;
            synth.speak(utterThis);
        }
    }

    // Populate voice options when voices are loaded
    synth.onvoiceschanged = () => {
        const voices = synth.getVoices();
        voiceDropdown.innerHTML = voices.map(voice => `<option>${voice.name}</option>`).join('');
        changeVoice(voices[0].name); // Set default voice
    };
});


document.addEventListener('DOMContentLoaded', () => {
    const settingsPopup = document.getElementById('settings-popup');
    const profileButton = document.getElementById('profile-button');
    const closeButton = document.getElementById('close-button');
    const tabs = document.querySelectorAll('.settings-tab');
    const sections = document.querySelectorAll('.settings-section');
    const contactUsLink = document.getElementById('contact-us-link');
    const contactUsForm = document.getElementById('contact-us-form');
    const helpContent = document.getElementById('help-content');
    const backToHelp = document.getElementById('back-to-help');
    const faqLink = document.getElementById('faq-link');
    const faqContent = document.getElementById('faq-content');
    const backToHelpFromFaq = document.getElementById('back-to-help-from-faq');
    const faqQuestions = document.querySelectorAll('.faq-question');

    profileButton.addEventListener('click', () => {
        settingsPopup.style.display = 'block';
    });

    closeButton.addEventListener('click', () => {
        settingsPopup.style.display = 'none';
    });

    tabs.forEach(tab => {
        tab.addEventListener('click', (event) => {
            event.preventDefault();
            const targetSection = document.getElementById(tab.getAttribute('data-section'));

            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(section => section.style.display = 'none');

            tab.classList.add('active');
            targetSection.style.display = 'block';
        });
    });

    contactUsLink.addEventListener('click', (event) => {
        event.preventDefault();
        helpContent.style.display = 'none';
        contactUsForm.style.display = 'block';
    });

    backToHelp.addEventListener('click', (event) => {
        event.preventDefault();
        contactUsForm.style.display = 'none';
        helpContent.style.display = 'block';
    });

    faqLink.addEventListener('click', (event) => {
        event.preventDefault();
        helpContent.style.display = 'none';
        faqContent.style.display = 'block';
    });

    backToHelpFromFaq.addEventListener('click', (event) => {
        event.preventDefault();
        faqContent.style.display = 'none';
        helpContent.style.display = 'block';
    });

    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const answer = question.nextElementSibling;
            if (answer.style.display === 'none') {
                answer.style.display = 'block';
            } else {
                answer.style.display = 'none';
            }
        });
    });

    // Optional: close the popup if user clicks outside of it
    window.addEventListener('click', (event) => {
        if (event.target === settingsPopup) {
            settingsPopup.style.display = 'none';
        }
    });
});
document.getElementById('contact-form').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    fetch('/send-email', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            alert('Email sent successfully!');
        } else {
            alert('Error sending email.');
        }
    }).catch(error => {
        alert('Error sending email.');
    });
});
const subscriptionTab = document.getElementById('subscription-tab');
const subscriptionSection = document.getElementById('subscription-section');
const subscribeButton = document.getElementById('subscribe-button');

subscriptionTab.addEventListener('click', (event) => {
    event.preventDefault();
    tabs.forEach(t => t.classList.remove('active'));
    sections.forEach(section => section.style.display = 'none');
    subscriptionTab.classList.add('active');
    subscriptionSection.style.display = 'block';
});

subscribeButton.addEventListener('click', () => {
    // Redirect to the next page after subscription
    window.location.href = 'nextpage.html'; // Replace with your actual URL
});
document.getElementById('change-email-button').addEventListener('click', function() {
    document.getElementById('profile-info').style.display = 'none';
    document.getElementById('change-password-form').style.display = 'none';
    document.getElementById('change-email-form').style.display = 'block';
});

document.getElementById('change-password-button').addEventListener('click', function() {
    document.getElementById('profile-info').style.display = 'none';
    document.getElementById('change-email-form').style.display = 'none';
    document.getElementById('change-password-form').style.display = 'block';
});

document.getElementById('close-button').addEventListener('click', function() {
    document.getElementById('settings-popup').style.display = 'none';
    document.getElementById('profile-info').style.display = 'block';
    document.getElementById('change-email-form').style.display = 'none';
    document.getElementById('change-password-form').style.display = 'none';
});

function logoutAllDevices() {
    // Implement the function to log out of all devices
}
document.getElementById('faq-link').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('faq-content').style.display = 'block';
    document.getElementById('help-content').style.display = 'none';
});

document.getElementById('back-to-help-from-faq').addEventListener('click', function(e) {
    e.preventDefault();
    document.getElementById('faq-content').style.display = 'none';
    document.getElementById('help-content').style.display = 'block';
});

// Toggle FAQ answers visibility
document.querySelectorAll('.faq-question').forEach(question => {
    question.addEventListener('click', function() {
        const answer = this.nextElementSibling;
        const sign = this.querySelector('.dropdown-sign');
        if (answer.style.display === 'none') {
            answer.style.display = 'block';
            sign.textContent = '▲';
        } else {
            answer.style.display = 'none';
            sign.textContent = '▼';
        }
    });
});
const selectedFiles = new Set();

document.getElementById('attachments').addEventListener('change', function() {
    const fileList = this.files;
    const output = document.getElementById('file-list');

    // Loop through the selected files and add them to the set
    for (let i = 0; i < fileList.length; i++) {
        selectedFiles.add(fileList[i].name);
    }

    // Clear the output container
    output.innerHTML = '';

    // Display all unique file names
    selectedFiles.forEach(fileName => {
        const listItem = document.createElement('div');
        listItem.textContent = fileName;
        output.appendChild(listItem);
    });
});
