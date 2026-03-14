 const receiptData = {
    vendor: document.getElementById('vendorName').value, // Python must look for 'vendor'
    date: document.getElementById('scheduleDate').value,   // Python must look for 'date'
    status: document.getElementById('receiptStage').value, // Python must look for 'status'
    products: []
};
 document.getElementById('operations-toggle').addEventListener('click', function() {
            const submenu = document.getElementById('operations-submenu');
            const arrow = this.querySelector('.arrow');
            submenu.classList.toggle('show');
            arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
        });

        // Modal Logic
        const modal = document.getElementById('receiptModal');

        function openModal() {
            modal.classList.add('active');
            // Auto-generate a dummy reference number when opening
            const randomId = Math.floor(Math.random() * 9000) + 1000;
            document.getElementById('refNumber').value = `WH/IN/${randomId}`;
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
                <td><button type="button" class="btn-icon" onclick="removeProductRow(this)">🗑️</button></td>
            `;
            tbody.appendChild(row);
        }

        function removeProductRow(btn) {
            const row = btn.closest('tr');
            row.remove();
        }
        // Function to handle saving the receipt and adding it to the table
       async function saveReceipt(event) {
    event.preventDefault();

    const receiptData = {
        vendor: document.getElementById('vendorName').value,
        contact: document.getElementById('vendorContact').value,
        date: document.getElementById('scheduleDate').value,
        status: document.getElementById('receiptStage').value,
        products: []
    };

    // Correctly target the rows to get Name, Qty, and Category
    const rows = document.querySelectorAll('#productList tr');
    rows.forEach(row => {
        const inputs = row.querySelectorAll('input');
        const select = row.querySelector('select'); // Get the Category dropdown
        
        if(inputs[0].value) {
            receiptData.products.push({
                name: inputs[0].value,
                qty: inputs[1].value,
                category: select.value // New Field! [cite: 47]
            });
        }
    });

    try {
        const response = await fetch('http://127.0.0.1:5000/api/receipts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(receiptData)
        });

        if (response.ok) {
            alert("Receipt and Products Synced!");
            location.reload(); 
        }
    } catch (err) {
        console.error("Sync Error:", err);
    }
}
            // Function to change the dropdown's background color dynamically
            function updateStageColor(selectElement) {
                // Remove all color classes first
                selectElement.classList.remove('bg-ready', 'bg-draft', 'bg-waiting');
                
                // Add the specific color class based on the selection
                if (selectElement.value === 'Ready') selectElement.classList.add('bg-ready');
                if (selectElement.value === 'Draft') selectElement.classList.add('bg-draft');
                if (selectElement.value === 'Waiting') selectElement.classList.add('bg-waiting');
            }

            // Updated Function to save the receipt with the stage
            function saveReceipt(event) {
                event.preventDefault();

                const ref = document.getElementById('refNumber').value;
                const vendor = document.getElementById('vendorName').value;
                const date = document.getElementById('scheduleDate').value;
                const stage = document.getElementById('receiptStage').value; // Get the stage
                
                const destination = "Main Warehouse"; 
                const contact = "Pending Contact";

                // Determine which CSS class to use for the table badge
                let badgeClass = '';
                if (stage === 'Ready') badgeClass = 'status-ready';
                if (stage === 'Draft') badgeClass = 'status-draft';
                if (stage === 'Waiting') badgeClass = 'status-waiting';

                const tbody = document.querySelector('.data-table tbody');
                const newRow = document.createElement('tr');
                
                newRow.innerHTML = `
                    <td>${ref}</td>
                    <td>${vendor}</td>
                    <td>${destination}</td>
                    <td>${contact}</td>
                    <td>${date}</td>
                    <td><span class="status-badge ${badgeClass}">${stage}</span></td>
                `;
                
                tbody.insertBefore(newRow, tbody.firstChild);
                
                document.getElementById('newReceiptForm').reset();
                
                // Reset dropdown color back to default (Ready)
                const stageDropdown = document.getElementById('receiptStage');
                updateStageColor(stageDropdown);
                
                document.getElementById('productList').innerHTML = `
                    <tr>
                        <td><input type="text" placeholder="Enter product" required></td>
                        <td><input type="number" min="1" placeholder="0" required></td>
                        <td class="no-print"><button type="button" class="btn-icon" disabled>🗑️</button></td>
                    </tr>
                `;
                closeModal();
            }     
            // Updated Function to save the receipt with the contact info
            function saveReceipt(event) {
                event.preventDefault();

                const ref = document.getElementById('refNumber').value;
                const vendor = document.getElementById('vendorName').value;
                const contact = document.getElementById('vendorContact').value; // Get the contact info
                const date = document.getElementById('scheduleDate').value;
                const stage = document.getElementById('receiptStage').value; 
                
                // Still defaulting destination as it's not in the modal yet
                const destination = "Main Warehouse"; 

                // Determine which CSS class to use for the table badge
                let badgeClass = '';
                if (stage === 'Ready') badgeClass = 'status-ready';
                if (stage === 'Draft') badgeClass = 'status-draft';
                if (stage === 'Waiting') badgeClass = 'status-waiting';

                const tbody = document.querySelector('.data-table tbody');
                const newRow = document.createElement('tr');
                
                // Inject the real contact variable into the table row
                newRow.innerHTML = `
                    <td>${ref}</td>
                    <td>${vendor}</td>
                    <td>${destination}</td>
                    <td>${contact}</td> 
                    <td>${date}</td>
                    <td><span class="status-badge ${badgeClass}">${stage}</span></td>
                `;
                
                tbody.insertBefore(newRow, tbody.firstChild);
                
                document.getElementById('newReceiptForm').reset();
                
                // Reset dropdown color back to default (Ready)
                const stageDropdown = document.getElementById('receiptStage');
                updateStageColor(stageDropdown);
                
                document.getElementById('productList').innerHTML = `
                    <tr>
                        <td><input type="text" placeholder="Enter product" required></td>
                        <td><input type="number" min="1" placeholder="0" required></td>
                        <td class="no-print"><button type="button" class="btn-icon" disabled>🗑️</button></td>
                    </tr>
                `;
                
                closeModal();
            }   
            // Replace all existing saveReceipt functions with this SINGLE version:
async function saveReceipt(event) {
    event.preventDefault();
    const receiptData = {
        vendor: document.getElementById('vendorName').value,
        date: document.getElementById('scheduleDate').value,
        status: document.getElementById('receiptStage').value,
        products: []
    };

    document.querySelectorAll('#productList tr').forEach(row => {
        const inputs = row.querySelectorAll('input');
        const select = row.querySelector('select');
        if(inputs[0].value) {
            receiptData.products.push({
                name: inputs[0].value,
                qty: inputs[1].value,
                category: select ? select.value : "General"
            });
        }
    });

    // 2. Use secureFetch for POST requests
    const res = await secureFetch('http://127.0.0.1:5000/api/receipts', {
        method: 'POST',
        body: JSON.stringify(receiptData)
    });

    if (res.ok) location.reload();
}
async function loadReceiptsTable() {
    // 1. Use secureFetch to send the User-ID
    const res = await secureFetch('http://127.0.0.1:5000/api/receipts');
    const data = await res.json();
    const tbody = document.querySelector('.data-table tbody');
    tbody.innerHTML = ''; 

    data.forEach(op => {
        let actionBtn = op.status !== 'Done' ? 
            `<button class="btn btn-primary btn-small" onclick="validateReceipt(${op.operation_id})">Validate</button>` : 
            `<span style="color: #45a29e; font-weight: bold;">✓ Received</span>`;

        tbody.innerHTML += `
            <tr>
                <td>WH/IN/${op.operation_id}</td>
                <td>${op.partner_name}</td>
                <td>Main Warehouse</td>
                <td>${op.scheduled_date}</td>
                <td><span class="status-badge status-${op.status.toLowerCase()}">${op.status}</span></td>
                <td>${actionBtn}</td> 
            </tr>`;
    });
}

// Function to trigger the actual stock increase in the database
async function validateReceipt(id) {
    if(!confirm("Validate stock increase?")) return;
    const res = await secureFetch(`http://127.0.0.1:5000/api/operations/${id}/validate`, { method: 'PUT' });
    if (res.ok) location.reload();
}
window.onload = loadReceiptsTable;
// Updated Add Product Row Logic
function addProductRow() {
    const tbody = document.getElementById('productList');
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><input type="text" placeholder="Enter product" required></td>
        <td><input type="number" min="1" placeholder="0" required></td>
        <td>
            <select required>
                <option value="" disabled selected>Select Category...</option>
                <option value="Tech & Electronics">Tech & Electronics</option>
                <option value="Raw Materials">Raw Materials</option>
                <option value="Office Supplies">Office Supplies</option>
            </select>
        </td>
        <td class="no-print"><button type="button" class="btn-icon" onclick="removeProductRow(this)">🗑️</button></td>
    `;
    tbody.appendChild(row);
}

// ... (Keep the rest of your saveReceipt logic at the top the same) ...

    // INSIDE your saveReceipt(event) function, update the reset block at the very end:
    document.getElementById('productList').innerHTML = `
        <tr>
            <td><input type="text" placeholder="Enter product" required></td>
            <td><input type="number" min="1" placeholder="0" required></td>
            <td>
                <select required>
                    <option value="" disabled selected>Select Category...</option>
                    <option value="Tech & Electronics">Tech & Electronics</option>
                    <option value="Raw Materials">Raw Materials</option>
                    <option value="Office Supplies">Office Supplies</option>
                </select>
            </td>
            <td class="no-print"><button type="button" class="btn-icon" disabled>🗑️</button></td>
        </tr>
    `;
    
    closeModal();
// } <-- End of saveReceipt function