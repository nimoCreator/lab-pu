const appendMessage = (message, sender) => {
    const conversationCon = document.getElementById('conversationCon');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'bot' ? 'botMessage' : 'userMessage');

        const pfpDiv = document.createElement('div');
        pfpDiv.classList.add('messagePfp');
            const pfpIcon = document.createElement('span');
            pfpIcon.classList.add('material-symbols-outlined');
            pfpIcon.textContent = sender === 'bot' ? 'smart_toy' : 'person';
            pfpDiv.appendChild(pfpIcon);
        messageDiv.appendChild(pfpDiv);
    
        const labelSpan = document.createElement('span');
        labelSpan.classList.add('messageLabel');
        labelSpan.textContent = sender === 'bot' ? 'Gemini' : 'Użytkownik';
        messageDiv.appendChild(labelSpan);

        const textSpan = document.createElement('span');
        textSpan.classList.add('messageText');
        textSpan.textContent = message;
        messageDiv.appendChild(textSpan);

        const timeSpan = document.createElement('span');
        timeSpan.classList.add('messageTime');
        const now = new Date();
        timeSpan.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        messageDiv.appendChild(timeSpan);
    
    conversationCon.appendChild(messageDiv); 

    conversationCon.scrollTop = conversationCon.scrollHeight;
}

document.addEventListener("DOMContentLoaded", () => {
    const geminiForm = document.getElementById("geminiForm");
    geminiForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const promptInput = document.getElementById("promptInput");
        const userMessage = promptInput.value.trim();
        if (userMessage === "") return;
        appendMessage(userMessage, 'user');
        promptInput.value = "";

        appendMessage("Piszę odpowiedź...", 'bot');
    });
});  