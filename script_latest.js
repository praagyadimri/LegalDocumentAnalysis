const signupPage = document.getElementById("signupPage");
const signinPage = document.getElementById("signinPage");
const dashboardPage = document.getElementById("dashboardPage");
const signupForm = document.getElementById("signupForm");
const signinForm = document.getElementById("signinForm");
const showSignin = document.getElementById("showSignin");
const showSignup = document.getElementById("showSignup");
const signupMessage = document.getElementById("signupMessage");
const signinMessage = document.getElementById("signinMessage");

const askBtn = document.getElementById("askBtn");
const questionInput = document.getElementById("questionInput");
const chatBox = document.getElementById("chatBox");
const loadingMessage = document.getElementById("loadingMessage");
const documentInput = document.getElementById("documentInput");
const chooseDocumentBtn = document.getElementById("chooseDocumentBtn");
const documentName = document.getElementById("documentName");
const historyList = document.getElementById("historyList");
const newChatBtn = document.getElementById("newChatBtn");
const chatTitle = document.getElementById("chatTitle");

let currentUserEmail = "";
let currentConversationId = null;
let conversations = [];

showSignin.addEventListener("click", function (event) {
    event.preventDefault();
    signupPage.style.display = "none";
    signinPage.style.display = "block";
});

showSignup.addEventListener("click", function (event) {
    event.preventDefault();
    signinPage.style.display = "none";
    signupPage.style.display = "block";
});

signupForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const name = document.getElementById("signupName").value.trim();
    const email = document.getElementById("signupEmail").value.trim().toLowerCase();
    const password = document.getElementById("signupPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {
        signupMessage.textContent = "Passwords do not match.";
        return;
    }

    localStorage.setItem("userName", name);
    localStorage.setItem("userEmail", email);
    localStorage.setItem("userPassword", password);

    signupMessage.textContent = "Account created successfully.";
    setTimeout(function () {
        signupPage.style.display = "none";
        signinPage.style.display = "block";
        signupForm.reset();
        signupMessage.textContent = "";
    }, 700);
});

signinForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const email = document.getElementById("signinEmail").value.trim().toLowerCase();
    const password = document.getElementById("signinPassword").value;
    const savedEmail = localStorage.getItem("userEmail");
    const savedPassword = localStorage.getItem("userPassword");
    const savedName = localStorage.getItem("userName");

    if (email === savedEmail && password === savedPassword) {
        currentUserEmail = email;
        signupPage.style.display = "none";
        signinPage.style.display = "none";
        dashboardPage.style.display = "block";
        document.getElementById("welcomeUser").textContent = "Welcome, " + (savedName || "User");
        signinMessage.textContent = "";
        loadConversations();
        startNewConversation();
    } else {
        signinMessage.textContent = "Invalid email or password.";
    }
});

document.getElementById("logoutBtn").addEventListener("click", function () {
    dashboardPage.style.display = "none";
    signinPage.style.display = "block";
    signinForm.reset();
    signinMessage.textContent = "";
    currentUserEmail = "";
    currentConversationId = null;
    conversations = [];
});

newChatBtn.addEventListener("click", startNewConversation);
askBtn.addEventListener("click", askQuestion);

questionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        askQuestion();
    }
});

chooseDocumentBtn.addEventListener("click", function () {
    documentInput.click();
});

documentInput.addEventListener("change", function () {
    const file = documentInput.files[0];
    if (!file) {
        documentName.textContent = "No document selected.";
        return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        alert("Please select a PDF file.");
        documentInput.value = "";
        documentName.textContent = "No document selected.";
        return;
    }
    documentName.textContent = file.name;
});

function storageKey() {
    return "legalChatHistory:" + currentUserEmail;
}

function loadConversations() {
    try {
        conversations = JSON.parse(localStorage.getItem(storageKey()) || "[]");
        if (!Array.isArray(conversations)) conversations = [];
    } catch (error) {
        conversations = [];
    }
    renderHistoryList();
}

function saveConversations() {
    localStorage.setItem(storageKey(), JSON.stringify(conversations));
    renderHistoryList();
}

function startNewConversation() {
    currentConversationId = "chat-" + Date.now() + "-" + Math.random().toString(16).slice(2, 8);
    const conversation = {
        id: currentConversationId,
        title: "New Conversation",
        updatedAt: new Date().toISOString(),
        messages: []
    };
    conversations.unshift(conversation);
    saveConversations();
    renderConversation(conversation);
    questionInput.value = "";
    documentInput.value = "";
    documentName.textContent = "No document selected.";
}

function getCurrentConversation() {
    return conversations.find(function (conversation) {
        return conversation.id === currentConversationId;
    });
}

function renderHistoryList() {
    historyList.innerHTML = "";
    const savedConversations = conversations.slice().sort(function (a, b) {
        return new Date(b.updatedAt) - new Date(a.updatedAt);
    });

    if (savedConversations.length === 0) {
        historyList.innerHTML = '<p class="history-note">No conversations yet.</p>';
        return;
    }

    savedConversations.forEach(function (conversation) {
        const item = document.createElement("div");
        item.className = "history-item";

        const openButton = document.createElement("button");
        openButton.type = "button";
        openButton.className = "history-open-btn" +
            (conversation.id === currentConversationId ? " active" : "");
        openButton.textContent = conversation.title || "New Conversation";
        openButton.title = conversation.title || "New Conversation";
        openButton.addEventListener("click", function () {
            currentConversationId = conversation.id;
            renderConversation(conversation);
            renderHistoryList();
        });

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "history-delete-btn";
        deleteButton.textContent = "×";
        deleteButton.title = "Delete conversation";
        deleteButton.setAttribute("aria-label", "Delete conversation");
        deleteButton.addEventListener("click", function () {
            const confirmed = confirm("Delete this conversation from history?");
            if (!confirmed) return;
            conversations = conversations.filter(function (item) {
                return item.id !== conversation.id;
            });
            if (currentConversationId === conversation.id) {
                currentConversationId = null;
            }
            saveConversations();
            if (!currentConversationId) {
                if (conversations.length) {
                    currentConversationId = conversations[0].id;
                    renderConversation(conversations[0]);
                } else {
                    startNewConversation();
                }
            }
        });

        item.appendChild(openButton);
        item.appendChild(deleteButton);
        historyList.appendChild(item);
    });
}

function renderConversation(conversation) {
    chatBox.innerHTML = "";
    chatTitle.textContent = conversation.title || "New Conversation";

    (conversation.messages || []).forEach(function (message) {
        appendMessage(message.role, message.text, message.time, false);
    });
}

function appendMessage(role, text, time, shouldSave) {
    const wrapper = document.createElement("div");
    wrapper.className = role === "user" ? "user-message" : "ai-message";

    const label = document.createElement("strong");
    label.textContent = role === "user" ? "You:" : "AI:";
    wrapper.appendChild(label);

    const content = document.createElement("div");
    if (role === "assistant") {
        content.innerHTML = formatDocumentAnalysis(text);
    } else {
        content.textContent = text;
    }
    wrapper.appendChild(content);

    if (time) {
        const timeElement = document.createElement("div");
        timeElement.className = "message-time";
        timeElement.textContent = new Date(time).toLocaleString();
        wrapper.appendChild(timeElement);
    }

    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;

    if (shouldSave) {
        const conversation = getCurrentConversation();
        if (conversation) {
            conversation.messages.push({ role: role, text: text, time: time || new Date().toISOString() });
            conversation.updatedAt = new Date().toISOString();
            if (role === "user" && (!conversation.title || conversation.title === "New Conversation")) {
                conversation.title = text.length > 32 ? text.slice(0, 32) + "…" : text;
            }
            chatTitle.textContent = conversation.title;
            saveConversations();
        }
    }
}

async function askQuestion() {
    const question = questionInput.value.trim();
    const file = documentInput.files[0];

    if (question === "" && !file) {
        alert("Please enter a question or select a document.");
        return;
    }

    if (!currentConversationId) {
        startNewConversation();
    }

    const conversation = getCurrentConversation();
    if (!conversation) return;

    if (question) {
        appendMessage("user", question, new Date().toISOString(), true);
    }
    if (file) {
        appendMessage("user", "Uploaded document: " + file.name, new Date().toISOString(), true);
    }

    questionInput.value = "";
    loadingMessage.textContent = "AI is thinking...";
    loadingMessage.style.display = "block";
    askBtn.disabled = true;
    chooseDocumentBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append("question", question);
        formData.append("conversation_id", currentConversationId);

        formData.append(
            "conversation_history",
            JSON.stringify(conversation.messages)
        );

        if (file) {
            formData.append("file", file);
        }

        const response = await fetch("http://127.0.0.1:8000/ask", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Something went wrong.");
        }

        appendMessage("assistant", data.answer, new Date().toISOString(), true);
    } catch (error) {
        appendMessage("assistant", "Unable to get a response from the backend. " + error.message, new Date().toISOString(), true);
        console.error(error);
    } finally {
        loadingMessage.style.display = "none";
        askBtn.disabled = false;
        chooseDocumentBtn.disabled = false;
        documentInput.value = "";
        documentName.textContent = "No document selected.";
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatDocumentAnalysis(text) {
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    formatted = formatted.replace(/^- (.+)$/gm, "• $1");
    formatted = formatted.replace(/\n/g, "<br>");
    return formatted;
}
