// Get modal element
var modal = document.getElementById("terms-modal");

// Get open modal button
var termsLink = document.getElementById("terms-link");

// Get close button
var closeBtn = document.getElementById("close-modal");

// Get modal checkbox
var modalCheckbox = document.getElementById("modal-terms");

// Get registration form checkbox
var regCheckbox = document.getElementById("terms");

// Listen for open click
termsLink.addEventListener("click", function(event){
    event.preventDefault(); // Prevent default link behavior
    modal.style.display = "block";
});

// Listen for close click
closeBtn.addEventListener("click", function(){
    modal.style.display = "none";
});

// Listen for outside click (optional)
window.addEventListener("click", function(event){
    if (event.target == modal) {
        modal.style.display = "none";
    }
});

// Listen for modal checkbox change
modalCheckbox.addEventListener("change", function(){
    regCheckbox.checked = this.checked;
});


// Validate checkbox on form submission
document.querySelector('.register-form').addEventListener('submit', function(event) {
    var regCheckbox = document.getElementById("terms");
    if (!regCheckbox.checked) {
        event.preventDefault(); // Prevent form submission
        alert("Please agree to the Terms and Conditions by checking the box.");
    }
});
