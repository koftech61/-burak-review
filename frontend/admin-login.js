const form = document.getElementById("loginForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const button = document.getElementById("loginButton");
const message = document.getElementById("message");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    message.textContent = "";
    button.disabled = true;
    button.textContent = "⏳ Giriş yapılıyor...";

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "same-origin",
            body: JSON.stringify({
                email,
                password
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.error || "Giriş başarısız."
            );
        }

        window.location.href = "/admin.html";

    } catch (error) {
        console.error("LOGIN ERROR:", error);

        message.textContent =
            error.message || "Giriş yapılamadı.";

        button.disabled = false;
        button.textContent = "🔓 Giriş Yap";
    }
});
