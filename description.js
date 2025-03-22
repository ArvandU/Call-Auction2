document.getElementById('descriptionForm').addEventListener('submit', function(e){
    e.preventDefault();
    const answer1 = document.getElementById('answer1').value;
    const answer2 = document.getElementById('answer2').value;
    const participantId = sessionStorage.getItem('participantInfo') ? JSON.parse(sessionStorage.getItem('participantInfo')).participantId : null;
    document.getElementById('participantId').value = participantId;
    
    if (!participantId) {
        alert('خطا: اطلاعات شرکت‌کننده یافت نشد. لطفاً دوباره وارد شوید.');
        window.location.href = 'index.html';
        return;
    }

    fetch('http://localhost:5000/submit_description', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ participantId, answer1, answer2 })
    })
    .then(response => response.json())
    .then(data => {
        if(data.error){
            alert(data.error);
        } else {
            window.location.href = 'info.html';
        }
    })
    .catch(err => {
        console.error(err);
        alert('خطا در ارسال پاسخ‌ها. لطفاً دوباره تلاش کنید.');
    });
});
