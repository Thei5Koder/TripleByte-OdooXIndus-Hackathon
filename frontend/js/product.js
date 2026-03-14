 let allProductsData = [];
 document.getElementById('operations-toggle').addEventListener('click', function() {
            const submenu = document.getElementById('operations-submenu');
            const arrow = this.querySelector('.arrow');
            submenu.classList.toggle('show');
            arrow.style.transform = submenu.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
        });

        /* --- INVENTORY LOGIC SIMULATION --- 
           In your real app, this data will come from your SQL database.
           Formula: Available = (Initial Stock + Total Received) - Total Delivered 
        */
        
        const productsDB = [
            { 
                name: "Industrial Screws (Pack)", 
                category: "Hardware", 
                warehouse: "Main Warehouse",
                initialStock: 500,
                received: 100, // From Receipts page
                delivered: 150 // From Delivery page
            },
            { 
                name: "Safety Helmets", 
                category: "Safety Gear", 
                warehouse: "Main Warehouse",
                initialStock: 50,
                received: 0,
                delivered: 45
            },
            { 
                name: "Hydraulic Pump", 
                category: "Machinery", 
                warehouse: "Zone B Storage",
                initialStock: 12,
                received: 5,
                delivered: 2
            }
        ];



async function loadInventory() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/product-inventory');
        if (!response.ok) throw new Error("Backend unreachable");
        
        allProductsData = await response.json(); // Save to the global variable
        renderTable(); // Call renderTable without passing data directly
    } catch (err) {
        console.error("Failed to load inventory:", err);
        document.getElementById('productTableBody').innerHTML = 
            `<tr><td colspan="6" style="text-align:center; color:red;">Error loading data</td></tr>`;
    }
}

// 3. Make sure your renderTable logic is solid
function renderTable() {
    const selectedWarehouse = document.getElementById('warehouseFilter').value;
    const selectedCategory = document.getElementById('categoryFilter').value; // Grab the new filter
    
    const tbody = document.getElementById('productTableBody');
    tbody.innerHTML = ''; 

    allProductsData.forEach(product => {
        // 1. Check Warehouse Filter
        if (selectedWarehouse !== "All" && product.warehouse !== selectedWarehouse) {
            return; // Skip if it doesn't match
        }
        
        // 2. Check Category Filter
        if (selectedCategory !== "All" && product.category !== selectedCategory) {
            return; // Skip if it doesn't match
        }

        const currentQuantity = product.quantity;

        // Status logic
        let badgeClass = currentQuantity > 20 ? 'status-ready' : 
                         currentQuantity > 0 ? 'status-draft' : 'status-waiting';
        let statusText = currentQuantity > 20 ? 'In Stock' : 
                         currentQuantity > 0 ? 'Low Stock' : 'Out of Stock';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td style="font-weight: 600; color: #fff;">${product.name}</td>
            <td style="color: #8b92a5;">${product.sku || 'N/A'}</td>
            <td>${product.category}</td>
            <td>${product.warehouse}</td>
            <td style="font-size: 1.1rem; font-weight: bold;">${currentQuantity}</td>
            <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
        `;
        tbody.appendChild(row);
    });
}

// Trigger the initial load
loadInventory();