// js/adjustment.js

// Sidebar toggle logic
document.getElementById('operations-toggle').addEventListener('click', function() {
    const submenu = document.getElementById('operations-submenu');
    const arrow = this.querySelector('.arrow');
    submenu.classList.toggle('show');
    arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
});

let allInventoryData = [];

// Map text names to MySQL IDs (Update these to match your database IDs)
const locationMap = {
    "Main Warehouse": 1,
    "Zone B Storage": 2,
    "Storefront Retail": 3 
};

// 1. Load data using secureFetch to send the user's ID badge
async function loadAdjustmentTable() {
    try {
        const res = await secureFetch('http://127.0.0.1:5000/api/product-inventory');
        if (!res.ok) throw new Error("Unauthorized or server error");
        
        allInventoryData = await res.json();
        renderAdjustmentTable();
    } catch (err) {
        console.error("Failed to load inventory:", err);
        const tbody = document.getElementById('adjustmentTableBody');
        if(tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#ff4757;">Failed to load your warehouse data.</td></tr>`;
    }
}

function renderAdjustmentTable() {
    const sourceWh = document.getElementById('sourceWarehouse').value;
    const tbody = document.getElementById('adjustmentTableBody');
    if (!tbody) return;
    tbody.innerHTML = ''; 

    allInventoryData.forEach(product => {
        // Only show products belonging to the selected warehouse with stock available
        if (product.warehouse !== sourceWh || product.quantity <= 0) return; 

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="row-checkbox" onchange="toggleQuantityInput(this, 'qty-${product.product_id}')" data-id="${product.product_id}">
            </td>
            <td style="font-weight: 600; color: #fff;">${product.name}</td>
            <td>${product.category}</td>
            <td>${product.quantity}</td>
            <td>
                <input type="number" id="qty-${product.product_id}" class="inline-input" min="1" max="${product.quantity}" placeholder="0" disabled>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function toggleQuantityInput(checkbox, inputId) {
    const qtyInput = document.getElementById(inputId);
    if (checkbox.checked) {
        qtyInput.disabled = false;
        qtyInput.required = true;
        qtyInput.focus();
    } else {
        qtyInput.disabled = true;
        qtyInput.required = false;
        qtyInput.value = ''; 
    }
}

// Modal Controls
const modal = document.getElementById('transferModal');

function openTransferModal() {
    const selectedCheckboxes = document.querySelectorAll('.row-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        alert("Please select at least one product to move.");
        return;
    }
    document.getElementById('selectedItemCount').innerText = selectedCheckboxes.length;
    modal.classList.add('active');
}

function closeModal() {
    modal.classList.remove('active');
    const form = document.getElementById('transferForm');
    if(form) form.reset();
}

// 2. Confirm transfer using secureFetch
async function confirmTransfer(event) {
    event.preventDefault();
    const sourceName = document.getElementById('sourceWarehouse').value;
    const destName = document.getElementById('destinationWarehouse').value;

    if (sourceName === destName) {
        alert("Source and Destination warehouses cannot be the same!");
        return;
    }

    const payload = {
        source_location: locationMap[sourceName],
        dest_location: locationMap[destName],
        products: []
    };

    document.querySelectorAll('.row-checkbox:checked').forEach(cb => {
        const prodId = cb.getAttribute('data-id');
        const qty = document.getElementById(`qty-${prodId}`).value;
        payload.products.push({ product_id: prodId, qty: qty });
    });

    try {
        const response = await secureFetch('http://127.0.0.1:5000/api/transfer', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert(`Success! Stock moved from ${sourceName} to ${destName}.`);
            location.reload(); 
        } else {
            alert("Transfer failed. Ensure your warehouses are correctly mapped.");
        }
    } catch (err) {
        console.error("Transfer Error:", err);
    }
}

window.onload = loadAdjustmentTable;