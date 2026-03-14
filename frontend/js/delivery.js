// js/delivery.js

// 1. Sidebar & UI Logic
document.getElementById('operations-toggle').addEventListener('click', function() {
    const submenu = document.getElementById('operations-submenu');
    const arrow = this.querySelector('.arrow');
    submenu.classList.toggle('show');
    arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
});

const modal = document.getElementById('deliveryModal');

function openModal() {
    modal.classList.add('active');
    const randomId = Math.floor(Math.random() * 9000) + 1000;
    document.getElementById('refNumber').value = `WH/OUT/${randomId}`;
}

function closeModal() {
    modal.classList.remove('active');
}

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

// 2. CREATE: Save Delivery using secureFetch
async function saveDelivery(event) {
    event.preventDefault();
    const deliveryData = {
        customer: document.getElementById('customerName').value,
        date: document.getElementById('scheduleDate').value,
        status: document.getElementById('deliveryStage').value,
        products: []
    };

    document.querySelectorAll('#productList tr').forEach(row => {
        const inputs = row.querySelectorAll('input');
        if(inputs[0] && inputs[0].value) {
            deliveryData.products.push({ name: inputs[0].value, qty: inputs[1].value });
        }
    });

    try {
        const response = await secureFetch('http://127.0.0.1:5000/api/deliveries', {
            method: 'POST',
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

// 3. READ: Load Deliveries for the current user
async function loadDeliveries() {
    try {
        const res = await secureFetch('http://127.0.0.1:5000/api/deliveries');
        const data = await res.json();
        const tbody = document.querySelector('.data-table tbody');
        if(!tbody) return;
        tbody.innerHTML = ''; 

        data.forEach(op => {
            let actionBtn = op.status !== 'Done' ? 
                `<button class="btn btn-primary" style="padding: 5px 10px;" onclick="validateDelivery(${op.operation_id})">Validate</button>` : 
                `<span style="color: #45a29e; font-weight: bold;">✓ Shipped</span>`;

            tbody.innerHTML += `
                <tr>
                    <td>WH/OUT/${op.operation_id}</td>
                    <td>${op.partner_name}</td>
                    <td>Main Warehouse</td>
                    <td>${op.scheduled_date}</td>
                    <td><span class="status-badge status-${op.status.toLowerCase()}">${op.status}</span></td>
                    <td>${actionBtn}</td> 
                </tr>`;
        });
    } catch (err) {
        console.error("Error loading deliveries:", err);
    }
}

// 4. UPDATE: Validate Delivery (Subtract stock)
async function validateDelivery(id) {
    if(!confirm("Validate this delivery? This will deduct the items from your warehouse stock.")) return;

    try {
        const res = await secureFetch(`http://127.0.0.1:5000/api/operations/${id}/validate`, {
            method: 'PUT'
        });

        if (res.ok) {
            alert("Stock deducted successfully!");
            location.reload(); 
        } else {
            alert("Error validating delivery. Check inventory levels.");
        }
    } catch (err) {
        console.error("Validation failed:", err);
    }
}

// Initialization
window.onload = loadDeliveries;