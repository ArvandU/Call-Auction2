document.addEventListener('DOMContentLoaded', function(){
    const participantId = sessionStorage.getItem('participantInfo') ? JSON.parse(sessionStorage.getItem('participantInfo')).participantId : null;
    if (!participantId) {
        alert('خطا: اطلاعات شرکت‌کننده یافت نشد. لطفاً دوباره وارد شوید.');
        window.location.href = 'index.html';
        return;
    }

    fetch(`http://localhost:5000/participant_info?participantId=${participantId}`)
       .then(response => response.json())
       .then(data => {
           if(data.error){
              alert(data.error);
           } else {
              document.getElementById('infoBox').innerHTML = `
              <p><strong>پول اولیه:</strong> $${data.initial_money}</p>
              <p><strong>آب:</strong> ${data.water} واحد</p>
              <p><strong>ارزش‌های نهایی:</strong> برای ۱۰ واحد اول: ${data.marginal_value_first}، برای ۱۰ واحد بعدی: ${data.marginal_value_second}</p>
              <p><strong>تابع سود:</strong> سود شما برابر است با: (قیمت × تعداد) - (ارزش نهایی × تعداد)</p>
              <p><strong>قانون حراج:</strong> در این حراج، قیمت یکسان برای تمام معاملات تعیین می‌شود. این قیمت به گونه‌ای انتخاب می‌شود که مجموع تقاضا با مجموع عرضه برابر باشد.</p>
              `;
           }
       })
       .catch(err => {
          console.error(err);
          alert("خطا در بارگذاری اطلاعات شرکت‌کننده.");
       });
});

document.getElementById('proceedBtn').addEventListener('click', function(){
    window.location.href = 'bid.html';
});
