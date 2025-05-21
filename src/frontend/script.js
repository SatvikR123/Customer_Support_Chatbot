// DOM Elements
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const chatContainer = document.getElementById("chat-container");
const chatWidgetButton = document.getElementById("chat-widget-button");
const minimizeButton = document.getElementById("minimize-button");
const closeButton = document.getElementById("close-button");

// Chat state
let isChatOpen = false;
let hasShownWelcomeMessage = false;

// WebSocket Connection
let socket;
let isConnected = false;

// Toggle chat widget
function toggleChatWidget() {
  if (isChatOpen) {
    chatContainer.classList.remove("active");
    setTimeout(() => {
      chatWidgetButton.style.display = "flex";
    }, 300);
  } else {
    chatWidgetButton.style.display = "none";
    chatContainer.classList.add("active");
    chatInput.focus();

    // Show welcome message if it's the first time opening
    if (!hasShownWelcomeMessage) {
      addWelcomeMessage();
      hasShownWelcomeMessage = true;
    }
  }

  isChatOpen = !isChatOpen;
}

// Add welcome message
function addWelcomeMessage() {
  const welcomeMessage = document.createElement("div");
  welcomeMessage.classList.add("message", "welcome-message");
  welcomeMessage.innerHTML = `
    <strong>Welcome to boAt Customer Support!</strong><br>
    How can I help you today? You can ask about:
    <ul style="text-align: left; margin-top: 8px; padding-left: 20px;">
      <li>Return policies</li>
      <li>Service center locations</li>
      <li>Product information</li>
    </ul>
  `;

  chatMessages.appendChild(welcomeMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Connect to WebSocket
function connectWebSocket() {
  // Get the current hostname and protocol
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  const port = "8000"; // Make sure this matches your FastAPI server port

  // Generate a random conversation ID
  const conversationId = Math.random().toString(36).substring(2, 15);

  const socketUrl = `${protocol}//${host}:${port}/ws/chat/${conversationId}`;

  console.log(`Connecting to WebSocket at ${socketUrl}`);

  socket = new WebSocket(socketUrl);

  // Connection opened
  socket.addEventListener("open", function (event) {
    isConnected = true;
    console.log("Connected to WebSocket server");
  });

  // Listen for messages
  socket.addEventListener("message", function (event) {
    console.log("Raw message from server:", event.data);

    try {
      const response = JSON.parse(event.data);
      console.log("Parsed message from server:", response);

      // Only remove typing indicators right before adding the bot message
      console.log("Removing typing indicators before adding bot response");
      removeAllTypingIndicators();

      // Add bot message - use the message property from the response object
      if (response.message) {
        addBotMessage(response.message);
      } else {
        console.error("Received response without message property:", response);
        addBotMessage(
          "Sorry, I received an invalid response. Please try again."
        );
      }
    } catch (error) {
      console.error("Error parsing message:", error, event.data);
      // If parsing fails but we have data, try to display it directly
      removeAllTypingIndicators();
      if (event.data) {
        addBotMessage(`${event.data}`);
      } else {
        addBotMessage("Sorry, I encountered an error processing your request.");
      }
    }
  });

  // Connection closed
  socket.addEventListener("close", function (event) {
    isConnected = false;
    console.log("Disconnected from WebSocket server");

    // Try to reconnect after 5 seconds
    setTimeout(connectWebSocket, 5000);
  });

  // Connection error
  socket.addEventListener("error", function (event) {
    console.error("WebSocket error:", event);
    isConnected = false;
  });
}

// Remove all typing indicators
function removeAllTypingIndicators() {
  const indicators = document.querySelectorAll(".typing-indicator");
  indicators.forEach((indicator) => {
    indicator.remove();
  });
}

// Initialize connection
connectWebSocket();

// Event Listeners
chatWidgetButton.addEventListener("click", toggleChatWidget);
minimizeButton.addEventListener("click", toggleChatWidget);
closeButton.addEventListener("click", toggleChatWidget);
sendButton.addEventListener("click", sendMessage);

// Send message when Enter key is pressed
chatInput.addEventListener("keypress", function (event) {
  if (event.key === "Enter") {
    sendMessage();
  }
});

// Format and display a user message
function addUserMessage(message) {
  // First remove any existing typing indicators
  removeAllTypingIndicators();

  const messageElement = document.createElement("div");
  messageElement.classList.add("message", "user-message");
  messageElement.textContent = message;

  const timeElement = document.createElement("div");
  timeElement.classList.add("message-time");
  timeElement.textContent = getCurrentTime();

  messageElement.appendChild(timeElement);
  chatMessages.appendChild(messageElement);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Format and display a bot message
function addBotMessage(message) {
  const messageElement = document.createElement("div");
  messageElement.classList.add("message", "bot-message");
  messageElement.textContent = message;

  const timeElement = document.createElement("div");
  timeElement.classList.add("message-time");
  timeElement.textContent = getCurrentTime();

  messageElement.appendChild(timeElement);
  chatMessages.appendChild(messageElement);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // If chat is not open, show notification on the button
  if (!isChatOpen) {
    notifyNewMessage();
  }
}

// Show notification on chat button
function notifyNewMessage() {
  chatWidgetButton.classList.add("notification");
  setTimeout(() => {
    chatWidgetButton.classList.remove("notification");
  }, 3000);
}

// Show typing indicator
function showTypingIndicator() {
  // First remove any existing typing indicators
  removeAllTypingIndicators();
  console.log("Showing typing indicator");

  // Create the indicator
  const indicatorElement = document.createElement("div");
  indicatorElement.classList.add("typing-indicator");
  indicatorElement.setAttribute("id", "current-typing-indicator");

  // Add the dots
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    indicatorElement.appendChild(dot);
  }

  // Find all messages to position the indicator after the last one
  const allMessages = document.querySelectorAll(".message");
  console.log("Found total messages:", allMessages.length);

  if (allMessages.length > 0) {
    // Get the most recent message (whether user or bot)
    const lastMessage = allMessages[allMessages.length - 1];
    console.log(
      "Inserting after last message type:",
      lastMessage.classList.contains("user-message") ? "user" : "bot"
    );

    // Insert the typing indicator after the last message
    lastMessage.insertAdjacentElement("afterend", indicatorElement);
  } else {
    // If no messages yet, just append to the chat container
    console.log("No messages found, appending to chat container");
    chatMessages.appendChild(indicatorElement);
  }

  // Force browser to acknowledge the indicator
  indicatorElement.style.display = "flex";
  indicatorElement.offsetHeight; // Force reflow

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Log for debugging
  console.log(
    "Typing indicator inserted:",
    document.getElementById("current-typing-indicator") !== null
  );
}

// Get current time in HH:MM format
function getCurrentTime() {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, "0");
  const minutes = now.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
}

// Send message to server
function sendMessage() {
  const message = chatInput.value.trim();

  if (message && isConnected) {
    // Add user message to chat
    addUserMessage(message);

    // Clear input
    chatInput.value = "";

    // Show typing indicator - add a small delay to ensure DOM has updated
    setTimeout(() => {
      showTypingIndicator();
    }, 100);

    // Prepare JSON message for the server
    const messageData = {
      message: message,
    };

    // Send to server as JSON string
    socket.send(JSON.stringify(messageData));

    // Make sure chat is open when sending a message
    if (!isChatOpen) {
      toggleChatWidget();
    }
  } else if (!isConnected) {
    console.error("Cannot send message: WebSocket not connected");
    addBotMessage(
      "Sorry, I'm having trouble connecting to the server. Please try again in a moment."
    );
  }
}

// Handle disconnection when the page is closed
window.addEventListener("beforeunload", function () {
  if (socket && isConnected) {
    socket.close();
  }
});

// Add notification style
const style = document.createElement("style");
style.textContent = `
  @keyframes notification {
    0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
    70% { box-shadow: 0 0 0 15px rgba(255, 0, 0, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
  }
  
  .chat-widget-button.notification {
    animation: notification 1s ease-in-out infinite;
  }
`;
document.head.appendChild(style);
