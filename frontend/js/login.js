async function login() {
    const emailValue = document.getElementById('username').value; // Using the existing input box
    const pass = document.getElementById('password').value;
    const msg = document.getElementById('msg');

    if (!emailValue || !pass) {
        msg.textContent = "Please fill in both fields!";
        msg.className = "msg error-msg";
        return;
    }

    try {
        const response = await fetch('http://127.0.0.1:5000/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailValue, password: pass }) // Send as email
        });

        const data = await response.json();

        if (response.ok) {
            msg.textContent = "Login successful! 🚀";
            msg.className = "msg success-msg";
            
            // Save the exact variables from your backend
            localStorage.setItem('userId', data.user.id);
            localStorage.setItem('userFullName', data.user.full_name); 
            
            setTimeout(() => { window.location.href = "index.html"; }, 1000);
        } else {
            msg.textContent = data.error || "Wrong credentials, try again.";
            msg.className = "msg error-msg";
        }
    } catch (err) {
        msg.textContent = "Server error. Is Flask running?";
        msg.className = "msg error-msg";
    }
}