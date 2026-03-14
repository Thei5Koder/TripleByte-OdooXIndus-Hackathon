document.getElementById('operations-toggle').addEventListener('click', function() {
    const submenu = document.getElementById('operations-submenu');
    const arrow = this.querySelector('.arrow');
    submenu.classList.toggle('show');
    arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
});

// Fetch Real Ledger Data from Python Backend
async function loadMoveHistory() {
    try {
        const res = await secureFetch('http://127.0.0.1:5000/api/move-history');
        const historyData = await res.json();
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = ''; 

        historyData.forEach((record, index) => {
            let arrowHTML = record.from_location_id === null ? '<span class="neon-green">⬇</span>' : 
                            record.to_location_id === null ? '<span class="neon-red">⬆</span>' : '<span class="neon-orange">⇄</span>';
            
            const rawDate = new Date(record.timestamp);
            tbody.innerHTML += `
                <tr>
                    <td style="color: #8b92a5;">${index + 1}</td>
                    <td class="text-center">${arrowHTML}</td>
                    <td>${record.from_location_id === null ? `WH/IN/${record.operation_id}` : '—'}</td>
                    <td>${record.to_location_id === null ? `WH/OUT/${record.operation_id}` : '—'}</td>
                    <td>${(record.from_location_id && record.to_location_id) ? `WH/TR/${record.operation_id}` : '—'}</td>
                    <td style="color: #fff;">${record.product_name} <span style="color: #8b92a5;">(Qty: ${record.quantity_moved})</span></td>
                    <td>${rawDate.toISOString().split('T')[0]}</td>
                </tr>`;
        });
    } catch (err) { console.error(err); }
}
window.onload = loadMoveHistory;