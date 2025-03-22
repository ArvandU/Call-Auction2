document.addEventListener('DOMContentLoaded', function(){
    const participantId = sessionStorage.getItem('participantInfo') ? JSON.parse(sessionStorage.getItem('participantInfo')).participantId : null;
    if (!participantId) {
        alert('خطا: اطلاعات شرکت‌کننده یافت نشد. لطفاً دوباره وارد شوید.');
        window.location.href = 'index.html';
        return;
    }

    fetch(`http://localhost:5000/final_tokens?participantId=${participantId}`)
    .then(response => response.json())
    .then(data => {
        if(data.error){
            alert(data.error);
        } else {
            document.getElementById('finalResults').innerHTML = `
                <p><strong>شناسه شرکت‌کننده:</strong> ${data.participantId}</p>
                <p><strong>مجموع توکن‌های کسب شده:</strong> ${data.total_tokens.toFixed(2)}</p>
            `;
        }
    })
    .catch(err => {
        console.error(err);
        alert('خطا در بارگذاری نتایج نهایی.');
    });
});
