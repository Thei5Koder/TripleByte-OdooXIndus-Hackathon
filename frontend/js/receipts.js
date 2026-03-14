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
        function saveReceipt(event) {
            event.preventDefault(); // Prevents the page from reloading

            // 1. Get values from the form
            const ref = document.getElementById('refNumber').value;
            const vendor = document.getElementById('vendorName').value;
            const date = document.getElementById('scheduleDate').value;
            
            // Defaulting these since they aren't in the simplified modal form
            const destination = "Main Warehouse"; 
            const contact = "Pending Contact";

            // 2. Create a new table row
            const tbody = document.querySelector('.data-table tbody');
            const newRow = document.createElement('tr');
    
            newRow.innerHTML = `
                <td>${ref}</td>
                <td>${vendor}</td>
                <td>${destination}</td>
                <td>${contact}</td>
                <td>${date}</td>
                <td><span class="status-badge status-ready">Ready</span></td>
            `;
    
            // 3. Add the row to the top of the table
            tbody.insertBefore(newRow, tbody.firstChild);
    
            // 4. Reset the form and close modal
            document.getElementById('newReceiptForm').reset();
    
            // Reset product rows back to just one empty row
            document.getElementById('productList').innerHTML = `
                <tr>
                    <td><input type="text" placeholder="Enter product" required></td>
                    <td><input type="number" min="1" placeholder="0" required></td>
                    <td class="no-print"><button type="button" class="btn-icon" disabled>🗑️</button></td>
                </tr>
            `;
    
            closeModal();
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
            async function saveReceipt(event) {
            event.preventDefault();

            // 1. Gather the Header Data
            const receiptData = {
                vendor: document.getElementById('vendorName').value,
                date: document.getElementById('scheduleDate').value,
                status: document.getElementById('receiptStage').value,
                products: []
            };

            // 2. Gather the Product List from the table
            const rows = document.querySelectorAll('#productList tr');
            rows.forEach(row => {
                const inputs = row.querySelectorAll('input');
                if(inputs[0].value) {
                    receiptData.products.push({
                        name: inputs[0].value,
                        qty: inputs[1].value
                    });
                }
            });

            // 3. SEND TO PYTHON BACKEND
            try {
                const response = await fetch('http://127.0.0.1:5000/api/receipts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(receiptData)
                });

                if (response.ok) {
                    alert("Receipt saved to Database!");
                    location.reload(); // Refresh to show the new data in the table
                }
            } catch (err) {
                console.error("Failed to save to backend:", err);
            }
        }
async function loadReceiptsTable() {
    const res = await fetch('http://127.0.0.1:5000/api/receipts');
    const data = await res.json();
    const tbody = document.querySelector('.data-table tbody');
    tbody.innerHTML = ''; // Clear fake rows

    data.forEach(op => {
        tbody.innerHTML += `
            <tr>
                <td>WH/IN/${op.operation_id}</td>
                <td>${op.partner_name}</td>
                <td>Main Warehouse</td>
                <td>${op.status}</td>
                <td>${op.scheduled_date}</td>
                <td><span class="status-badge status-${op.status.toLowerCase()}">${op.status}</span></td>
            </tr>
        `;
    });
}
window.onload = loadReceiptsTable;