let currentRound = 1;

// Function to poll for round results.
function pollRoundResult(roundNumber) {
    const participantId = sessionStorage.getItem('participantInfo') ? JSON.parse(sessionStorage.getItem('participantInfo')).participantId : null;
    if (!participantId) {
        alert('خطا: اطلاعات شرکت‌کننده یافت نشد. لطفاً دوباره وارد شوید.');
        window.location.href = 'index.html';
        return;
    }

    fetch(`http://localhost:5000/round_result?participantId=${participantId}&roundNumber=${roundNumber}`)
    .then(response => response.json())
    .then(data => {
         if (data.round_info) {
             const roundInfo = data.round_info;
             document.getElementById('lastRoundResults').innerHTML = `
                 <p><strong>نتایج دور ${roundInfo.round_number}:</strong></p>
                 <p>قیمت یکسان: ${roundInfo.uniform_price.toFixed(2)}</p>
                 <p>تعداد کل: ${roundInfo.total_quantity}</p>
                 <p>تعداد اجرا شده شما: ${roundInfo.executed_quantity}</p>
                 <p>سود شما: ${roundInfo.profit.toFixed(2)}</p>
             `;
             currentRound++;
             document.getElementById('currentRound').textContent = currentRound;
             document.getElementById('bidForm').reset();
             document.getElementById('bidEntries').innerHTML = `
                    <div class="bid-entry">
                        <label>قیمت: <input type="number" class="price" step="0.01" required></label>
                        <label>تعداد: <input type="number" class="quantity" required></label>
                    </div>
             `;
         } else {
             setTimeout(() => pollRoundResult(roundNumber), 3000);
         }
    })
    .catch(err => {
         console.error(err);
         setTimeout(() => pollRoundResult(roundNumber), 3000);
    });
}

document.addEventListener('DOMContentLoaded', function(){
    const participantId = sessionStorage.getItem('participantInfo') ? JSON.parse(sessionStorage.getItem('participantInfo')).participantId : null;
    if (!participantId) {
        alert('خطا: اطلاعات شرکت‌کننده یافت نشد. لطفاً دوباره وارد شوید.');
        window.location.href = 'index.html';
        return;
    }
    document.getElementById('participantId').value = participantId;
});

document.getElementById('addBid').addEventListener('click', function () {
    const newEntry = document.createElement('div');
    newEntry.className = 'bid-entry';
    newEntry.innerHTML = `
        <label>قیمت: <input type="number" class="price" step="0.01" required></label>
        <label>تعداد: <input type="number" class="quantity" required></label>
    `;
    document.getElementById('bidEntries').appendChild(newEntry);
});

document.getElementById('showInfo').addEventListener('click', function(){
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
              const infoDiv = document.getElementById('participantInfo');
              infoDiv.innerHTML = `
              <p><strong>پول اولیه:</strong> $${data.initial_money}</p>
              <p><strong>آب:</strong> ${data.water} واحد</p>
              <p><strong>ارزش‌های نهایی:</strong> برای ۱۰ واحد اول: ${data.marginal_value_first}، برای ۱۰ واحد بعدی: ${data.marginal_value_second}</p>
              <p><strong>تابع سود:</strong> سود شما برابر است با: (قیمت × تعداد) - (ارزش نهایی × تعداد)</p>
              <p><strong>قانون حراج:</strong> در این حراج، قیمت یکسان برای تمام معاملات تعیین می‌شود. این قیمت به گونه‌ای انتخاب می‌شود که مجموع تقاضا با مجموع عرضه برابر باشد.</p>
              `;
              infoDiv.style.display = (infoDiv.style.display === "none" || infoDiv.style.display === "") ? "block" : "none";
           }
       })
       .catch(err => {
          console.error(err);
          alert("خطا در بارگذاری اطلاعات شرکت‌کننده.");
       });
});

document.getElementById('bidForm').addEventListener('submit', function(e){
    e.preventDefault();
    const participantId = document.getElementById('participantId').value;
    const type = document.getElementById('type').value;
    const entries = document.querySelectorAll('.bid-entry');
    let bids = [];
    let isValid = true;
    entries.forEach(entry => {
        const price = entry.querySelector('.price').value;
        const quantity = entry.querySelector('.quantity').value;
        if (!price || !quantity || isNaN(price) || isNaN(quantity)){
            isValid = false;
        }
        bids.push({ price: parseFloat(price), quantity: parseInt(quantity), type: type });
    });
    if (!isValid){
        alert("لطفاً تمام فیلدها را به درستی پر کنید.");
        return;
    }
    
    fetch('http://localhost:5000/bid_submit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ participantId, bids })
    })
    .then(response => response.json())
    .then(data => {
        if(data.error){
            alert(data.error);
        } else {
            if(data.message.includes('Waiting')) {
                document.getElementById('lastRoundResults').innerHTML = `<p>در انتظار نتایج دور...</p>`;
                const roundNumber = data.round_number;
                pollRoundResult(roundNumber);
            } else {
                const roundInfo = data.round_info;
                document.getElementById('lastRoundResults').innerHTML = `
                    <p><strong>نتایج دور ${roundInfo.round_number}:</strong></p>
                    <p>قیمت یکسان: ${roundInfo.uniform_price.toFixed(2)}</p>
                    <p>تعداد کل: ${roundInfo.total_quantity}</p>
                    <p>تعداد اجرا شده شما: ${data.participant_result.executed_quantity}</p>
                    <p>سود شما: ${data.participant_result.profit.toFixed(2)}</p>
                `;
                if(data.message && data.message.includes('Auction completed')){
                    alert('حراج به پایان رسید!');
                    window.location.href = 'final.html';
                    return;
                }
                currentRound++;
                document.getElementById('currentRound').textContent = currentRound;
                document.getElementById('bidForm').reset();
                document.getElementById('bidEntries').innerHTML = `
                    <div class="bid-entry">
                        <label>قیمت: <input type="number" class="price" step="0.01" required></label>
                        <label>تعداد: <input type="number" class="quantity" required></label>
                    </div>
                `;
            }
        }
    })
    .catch(err => {
        console.error(err);
        alert('خطا در ثبت پیشنهاد! لطفاً دوباره تلاش کنید.');
    });
});
