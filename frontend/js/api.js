const API_URL = "http://127.0.0.1:5000/api";

async function fetchDashboard() {
    try {
        const response = await fetch(`${API_URL}/dashboard`);
        const data = await response.json();
        const receiptsWidget = document.querySelector('.widget:nth-child(1)');
        receiptsWidget.querySelector('.neon-red').innerText = data.receipts.late;
        receiptsWidget.querySelector('.neon-blue').innerText = data.receipts.in_ops;
        const deliveryWidget = document.querySelector('.widget:nth-child(2)');
        deliveryWidget.querySelector('.neon-orange').innerText = data.deliveries.remaining;
        deliveryWidget.querySelector('.neon-blue').innerText = data.deliveries.in_ops;
        deliveryWidget.querySelector('.neon-red').innerText = data.deliveries.late;
        document.getElementById('receipts-late').innerText = data.receipts.late;
        document.getElementById('receipts-ops').innerText = data.receipts.in_ops;

        // Update Deliveries using direct IDs
        document.getElementById('deliveries-rem').innerText = data.deliveries.remaining;
        document.getElementById('deliveries-ops').innerText = data.deliveries.in_ops;
        document.getElementById('deliveries-late').innerText = data.deliveries.late;
        console.log("Dashboard synced with Backend!");
    } catch (err) {
        console.error("Connection to Flask failed. Is the server running?", err);
    }
}
fetchDashboard();
setInterval(fetchDashboard, 30000);