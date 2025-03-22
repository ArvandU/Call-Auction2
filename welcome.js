document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const firstName = document.getElementById('firstName').value;
        const lastName = document.getElementById('lastName').value;
        
        try {
            const response = await fetch('http://localhost:5000/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    firstName: firstName,
                    lastName: lastName
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Store participant info in sessionStorage
                sessionStorage.setItem('participantInfo', JSON.stringify(data));
                // Redirect to description page
                window.location.href = 'description.html';
            } else {
                alert(data.error || 'خطا در ثبت نام');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('خطا در ارتباط با سرور');
        }
    });
});
