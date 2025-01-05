document.addEventListener("DOMContentLoaded", function () {
    const errorMessage = document.getElementById("error-message");
    if (errorMessage) {
        setTimeout(() => {
            errorMessage.style.display = "none";
        }, 3000); // Hide after 3 seconds
    }
});
