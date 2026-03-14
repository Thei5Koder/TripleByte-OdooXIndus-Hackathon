document.getElementById('operations-toggle').addEventListener('click', function() {
    const submenu = document.getElementById('operations-submenu');
    const arrow = this.querySelector('.arrow');
    submenu.classList.toggle('show');
    arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
});

// Fetch Real Ledger Data from Python Backend
async function loadMoveHistory() {
    try {
        const res = await fetch('http://127.0.0.1:5000/api/move-history');
        if (!res.ok) throw new Error("Backend connection failed");
        
        const historyData = await res.json();
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = ''; 

        const dash = '<span class="empty-dash">—</span>';

        historyData.forEach((record, index) => {
            let arrowHTML = '';
            let receiptRef = null;
            let deliveryRef = null;
            let transferRef = null;

            // 1. Identify Movement Type based on Location IDs
            if (record.from_location_id === null) {
                // Coming from outside (Vendor) = RECEIPT
                arrowHTML = '<span class="arrow-icon neon-green">⬇</span>';
                receiptRef = `WH/IN/${record.operation_id}`;
            } else if (record.to_location_id === null) {
                // Going to outside (Customer) = DELIVERY
                arrowHTML = '<span class="arrow-icon neon-red">⬆</span>';
                deliveryRef = `WH/OUT/${record.operation_id}`;
            } else {
                // Moving between internal warehouses = TRANSFER
                arrowHTML = '<span class="arrow-icon neon-orange">⇄</span>';
                transferRef = `WH/TR/${record.operation_id}`;
            }

            // 2. Format the Date (Cleans up MySQL timestamps)
            const rawDate = new Date(record.timestamp);
            const formattedDate = rawDate.toISOString().split('T')[0];

            // 3. Render the Row
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="color: #8b92a5;">${index + 1}</td>
                <td class="text-center">${arrowHTML}</td>
                <td style="font-family: monospace;">${receiptRef || dash}</td>
                <td style="font-family: monospace;">${deliveryRef || dash}</td>
                <td style="font-family: monospace;">${transferRef || dash}</td>
                <td style="font-weight: 600; color: #fff;">
                    ${record.product_name} 
                    <span style="color: #8b92a5; font-size: 0.85em; margin-left: 8px;">(Qty: ${record.quantity_moved})</span>
                </td>
                <td>${formattedDate}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error("Error loading history:", err);
        document.getElementById('historyTableBody').innerHTML = 
            `<tr><td colspan="7" class="text-center" style="color: #ff4757;">Failed to load live ledger data. Is your Flask server running?</td></tr>`;
    }
}

// Run the fetch function as soon as the page loads
window.onload = loadMoveHistory;