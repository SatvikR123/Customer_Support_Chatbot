// DOM Elements
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");

// WebSocket Connection
let socket;
let isConnected = false;

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

      // Remove typing indicator if present
      const typingIndicator = document.querySelector(".typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }

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

// Initialize connection
connectWebSocket();

// Send message when button is clicked
sendButton.addEventListener("click", sendMessage);

// Send message when Enter key is pressed
chatInput.addEventListener("keypress", function (event) {
  if (event.key === "Enter") {
    sendMessage();
  }
});

// Format and display a user message
function addUserMessage(message) {
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
}

// Show typing indicator
function showTypingIndicator() {
  const indicatorElement = document.createElement("div");
  indicatorElement.classList.add("typing-indicator");

  // Add the dots
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    indicatorElement.appendChild(dot);
  }

  chatMessages.appendChild(indicatorElement);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
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

    // Show typing indicator
    showTypingIndicator();

    // Prepare JSON message for the server
    const messageData = {
      message: message,
    };

    // Send to server as JSON string
    socket.send(JSON.stringify(messageData));
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
