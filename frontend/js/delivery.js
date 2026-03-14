// Dropdown toggle logic
document.getElementById('operations-toggle').addEventListener('click', function() {
            const submenu = document.getElementById('operations-submenu');
            const arrow = this.querySelector('.arrow');
            submenu.classList.toggle('show');
            arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
});

        // Modal Logic
const modal = document.getElementById('deliveryModal');

function openModal() {
            modal.classList.add('active');
            // Auto-generate a dummy reference number using WH/OUT/ prefix
            const randomId = Math.floor(Math.random() * 9000) + 1000;
            document.getElementById('refNumber').value = `WH/OUT/${randomId}`;
}

function closeModal() {
            modal.classList.remove('active');
}

        // Add Product Row Logic
function addProductRow() {
    const tbody = document.getElementById('productList');
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><input type="text" placeholder="Enter product" required></td>
        <td><input type="number" min="1" placeholder="0" required></td>
        <td class="no-print"><button type="button" class="btn-icon" onclick="removeProductRow(this)">🗑️</button></td>
        `;
    tbody.appendChild(row);
        }

        function removeProductRow(btn) {
            btn.closest('tr').remove();
        }

        // Stage Dropdown Color Logic
        function updateStageColor(selectElement) {
            selectElement.classList.remove('bg-ready', 'bg-draft', 'bg-waiting');
            if (selectElement.value === 'Ready') selectElement.classList.add('bg-ready');
            if (selectElement.value === 'Draft') selectElement.classList.add('bg-draft');
            if (selectElement.value === 'Waiting') selectElement.classList.add('bg-waiting');
        }

        // Save Delivery Logic
async function saveDelivery(event) {
    event.preventDefault();

    // 1. Gather Data
    const deliveryData = {
        customer: document.getElementById('customerName').value,
        date: document.getElementById('scheduleDate').value,
        status: document.getElementById('deliveryStage').value,
        products: []
    };

    // 2. Gather Products
    const rows = document.querySelectorAll('#productList tr');
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        if(inputs[0].value) {
            deliveryData.products.push({
                name: inputs[0].value,
                qty: inputs[1].value
            });
        }
    });

    // 3. Send to Backend
    try {
        const response = await fetch('http://127.0.0.1:5000/api/deliveries', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(deliveryData)
        });

        if (response.ok) {
            alert("Delivery Order Created!");
            location.reload(); 
        }
    } catch (err) {
        console.error("Failed to sync delivery:", err);
    }
}

// 4. Load real deliveries on page load
async function loadDeliveries() {
    const res = await fetch('http://127.0.0.1:5000/api/deliveries');
    const data = await res.json();
    const tbody = document.querySelector('.data-table tbody');
    tbody.innerHTML = ''; 

    data.forEach(op => {
        tbody.innerHTML += `
            <tr>
                <td>WH/OUT/${op.operation_id}</td>
                <td>${op.partner_name}</td>
                <td>Main Warehouse</td>
                <td>${op.status}</td>
                <td>${op.scheduled_date}</td>
                <td><span class="status-badge status-${op.status.toLowerCase()}">${op.status}</span></td>
            </tr>
        `;
    });
}
window.onload = loadDeliveries;