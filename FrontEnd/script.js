document.getElementById("loginForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const phone = document.getElementById("phone").value;
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  // Simulated login
  if (phone === "0712345678" && password === "1234") {
    document.getElementById("message").innerText = `Welcome ${role.toUpperCase()}!`;
    document.getElementById("message").style.color = "green";
  } else {
    document.getElementById("message").innerText = "Invalid login!";
    document.getElementById("message").style.color = "red";
  }
});
// End of file: FrontEnd/script.js
// --- a/file:///c%3A/Users/hamisi/farmconnect/
document.getElementById("loginForm").addEventListener("submit", function (e) {
  e.preventDefault();

  const phone = document.getElementById("phone").value;
  const password = document.getElementById("password").value;
  const role = document.getElementById("role").value;

  // Simulated login (replace this with real login logic later)
  if (phone && password) {
    // Store the role for later use
    localStorage.setItem("role", role);
    localStorage.setItem("username", "Jane"); // Simulate name from DB

    // Redirect based on role
    if (role === "vba") {
      window.location.href = "VBA.html";
    } else if (role === "admin") {
      window.location.href = "admin-dashboard.html";
    } else if (role === "agro") {
      window.location.href = "agrodealer.html";
    }
  } else {
    alert("Please enter phone and password");
  }
});
