// Frontend/js/auth.js

const API_BASE = "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
    // Check if already logged in
    const token = localStorage.getItem("stockwatch_token");
    if (token) {
        window.location.href = "dashboard.html";
        return;
    }

    const loginBtn = document.getElementById("loginBtn");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const messageEl = document.getElementById("message");

    if (loginBtn) {
        loginBtn.addEventListener("click", handleLogin);
    }

    // Support Enter key press
    [emailInput, passwordInput].forEach(input => {
        if (input) {
            input.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    handleLogin();
                }
            });
        }
    });

    async function handleLogin() {
        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();

        if (!email || !password) {
            showError("Please enter both email and password");
            return;
        }

        // Show loading state
        loginBtn.disabled = true;
        loginBtn.innerText = "Logging in...";
        messageEl.style.color = "#666";
        messageEl.innerText = "Please wait...";

        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Login failed");
            }

            // Success: save auth data
            localStorage.setItem("stockwatch_token", data.token);
            localStorage.setItem("stockwatch_user", JSON.stringify(data.user));

            messageEl.style.color = "green";
            messageEl.innerText = "Login successful! Redirecting...";

            setTimeout(() => {
                window.location.href = "dashboard.html";
            }, 800);

        } catch (error) {
            showError(error.message);
        } finally {
            loginBtn.disabled = false;
            loginBtn.innerText = "Login";
        }
    }

    function showError(msg) {
        messageEl.style.color = "#dc2626";
        messageEl.innerText = msg;
    }
});
