let categoryChart = null;
let expiryChart = null;

async function loadStats() {
  const user = JSON.parse(localStorage.getItem('user'));
  const user_id = user ? user.id : '';
  const res = await fetch(`/api/stats?user_id=${user_id}`);
  const data = await res.json();
  document.getElementById('total-products').textContent = data.total_products;
  document.getElementById('expiring-soon').textContent = data.expiring_soon;
  document.getElementById('total-stock').textContent = data.total_stock;
}
async function loadProducts() {
  const user = JSON.parse(localStorage.getItem('user'));
  const user_id = user ? user.id : '';
  const res = await fetch(`/api/products?user_id=${user_id}`);
  const products = await res.json();
  const tbody = document.getElementById('products-table');
  if (products.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty">No products found</td></tr>';
    return;
  }
  tbody.innerHTML = '';
  products.forEach(p => {
    const today = new Date();
    const expiry = new Date(p.expiry_date);
    const daysLeft = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
    let status = '';
    if (daysLeft <= 0) {
      status = '<span class="tag warn">Expired</span>';
    } else if (daysLeft <= 7) {
      status = `<span class="tag warn">⚠️ ${daysLeft} days left</span>`;
    } else {
      status = '<span class="tag ok">✅ Good</span>';
    }
    tbody.innerHTML += `
      <tr>
        <td>${p.name}</td>
        <td>${p.category}</td>
        <td>${p.quantity}</td>
        <td>${p.expiry_date}</td>
        <td>${status}</td>
        <td>
          <button class="btn-add" style="padding:5px 14px;font-size:0.7rem;margin-right:6px;" onclick='editProduct(${JSON.stringify(p)})'>
            ✏️ Edit
          </button>
          <button class="btn-delete" onclick="deleteProduct(${p.id})">
            🗑️ Delete
          </button>
        </td>
      </tr>
    `;
  });
}async function loadAlerts() {
  const user = JSON.parse(localStorage.getItem('user'));
  const user_id = user ? user.id : '';
  const res = await fetch(`/api/alerts?user_id=${user_id}`);
  const alerts = await res.json();
  const alertsList = document.getElementById('alerts-list');
  const alertCount = document.getElementById('alert-count');
  alertCount.textContent = alerts.length;
  if (alerts.length === 0) {
    alertsList.innerHTML = '<p class="empty">No expiry alerts 🎉</p>';
    return;
  }
  alertsList.innerHTML = '';
  alerts.forEach(a => {
    alertsList.innerHTML += `
      <div class="alert-item">
        <div>
          <div class="alert-name">⚠️ ${a.name}</div>
          <div class="alert-date">Expiry: ${a.expiry_date} | Qty: ${a.quantity}</div>
        </div>
        <span class="tag warn">${a.category}</span>
      </div>
    `;
  });
}

let editingId = null;

function editProduct(product) {
  document.getElementById('name').value = product.name;
  document.getElementById('category').value = product.category;
  document.getElementById('quantity').value = product.quantity;
  document.getElementById('expiry_date').value = product.expiry_date;
  editingId = product.id;
  document.querySelector('.btn-add[onclick="addProduct()"]').textContent = '💾 Update Product';
  document.getElementById('products').scrollIntoView({ behavior: 'smooth' });
}

async function addProduct() {
  const name = document.getElementById('name').value;
  const category = document.getElementById('category').value;
  const quantity = document.getElementById('quantity').value;
  const expiry_date = document.getElementById('expiry_date').value;
  if (!name || !quantity || !expiry_date) {
    alert('⚠️  Fill all fields!');
    return; 
  }
  const user = JSON.parse(localStorage.getItem('user'));
  const user_id = user ? user.id : '';

  if (editingId) {
    const res = await fetch(`/api/products/${editingId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, category, quantity, expiry_date })
    });
    const data = await res.json();
    alert(data.message);
    editingId = null;
    document.querySelector('.btn-add[onclick="addProduct()"]').textContent = '➕ Add Product';
  } else {
    const res = await fetch('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, category, quantity, expiry_date, user_id })
    });
    const data = await res.json();
    alert(data.message);
  }

  document.getElementById('name').value = '';
  document.getElementById('quantity').value = '';
  document.getElementById('expiry_date').value = '';
  loadStats();
  loadProducts();
  loadAlerts();
  loadCharts();
}

async function deleteProduct(id) {
 if (!confirm('Are you sure you want to delete?')) return;
  const res = await fetch(`/api/products/${id}`, {
    method: 'DELETE'
  });
  const data = await res.json();
  alert(data.message);
  loadStats();
  loadProducts();
  loadAlerts();
  loadCharts();
}

// EmailJS Initialize
emailjs.init("bEYPLUQgJnXnK6GAe");

async function sendAlerts() {
  const user = JSON.parse(localStorage.getItem('user'));
  const emailInput = document.getElementById('alert-email').value;
  const email = emailInput || user.email;

  if (!email) {
    alert('⚠️ please enter email address!');
    return;
  }

  const res = await fetch('/api/alerts');
  const alerts = await res.json();

  if (alerts.length === 0) {
    alert('✅ No expiring products!');
    return;
  }

  for (const product of alerts) {
    await emailjs.send(
      "service_nsve4oo",
      "template_ajcyi4h",
      {
        to_email: email,
        product_name: product.name,
        quantity: product.quantity,
        expiry_date: product.expiry_date
      }
    );
  }
  alert(`✅ Alert sent for ${alerts.length} products!`);
}
async function sendWhatsappAlerts() {
  const phoneInput = document.getElementById('alert-phone').value;

  if (!phoneInput) {
    alert('⚠️ please enter WhatsApp number!');
    return;
  }

  const res = await fetch('/api/send-whatsapp-alert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: phoneInput })
  });

  const data = await res.json();
  alert(data.message);
}
async function loadCharts() {
  try {
    const res = await fetch('/api/products');
    const products = await res.json();

    const categories = {};
    products.forEach(p => {
      categories[p.category] = (categories[p.category] || 0) + 1;
    });

    let good = 0, warning = 0, expired = 0;
    products.forEach(p => {
      const today = new Date();
      const expiry = new Date(p.expiry_date);
      const daysLeft = Math.floor((expiry - today) / (1000 * 60 * 60 * 24));
      if (daysLeft <= 0) expired++;
      else if (daysLeft <= 7) warning++;
      else good++;
    });

    const chartDefaults = {
      color: '#00ffcc',
      borderColor: 'rgba(0,255,200,0.1)',
      gridColor: 'rgba(0,255,200,0.05)',
    };

    // Category Chart
    if (categoryChart) categoryChart.destroy();
    const ctx1 = document.getElementById('categoryChart');
    categoryChart = new Chart(ctx1, {
      type: 'doughnut',
      data: {
        labels: Object.keys(categories),
        datasets: [{
          data: Object.values(categories),
          backgroundColor: [
            'rgba(0,255,200,0.7)',
            'rgba(0,170,255,0.7)',
            'rgba(170,0,255,0.7)',
            'rgba(255,51,102,0.7)',
            'rgba(255,170,0,0.7)',
          ],
          borderColor: 'rgba(2,4,8,0.8)',
          borderWidth: 3,
          hoverOffset: 8,
        }]
      },
      options: {
        cutout: '65%',
        plugins: {
          legend: {
            labels: {
              color: '#00ffcc',
              font: { family: 'Orbitron', size: 10 },
              padding: 16,
              usePointStyle: true,
            }
          }
        },
        animation: {
          animateRotate: true,
          duration: 1500,
          easing: 'easeInOutQuart',
        }
      }
    });

    // Expiry Chart
    if (expiryChart) expiryChart.destroy();
    const ctx2 = document.getElementById('expiryChart');
    expiryChart = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: ['✅ Good', '⚠️ Expiring', '❌ Expired'],
        datasets: [{
          label: 'Products',
          data: [good, warning, expired],
          backgroundColor: [
            'rgba(0,255,200,0.2)',
            'rgba(255,170,0,0.2)',
            'rgba(255,51,102,0.2)',
          ],
          borderColor: [
            'rgba(0,255,200,0.8)',
            'rgba(255,170,0,0.8)',
            'rgba(255,51,102,0.8)',
          ],
          borderWidth: 1,
          borderRadius: 2,
          borderSkipped: false,
        }]
      },
      options: {
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            ticks: {
              color: '#00ffcc',
              font: { family: 'Orbitron', size: 9 }
            },
            grid: { color: 'rgba(0,255,200,0.05)' },
            border: { color: 'rgba(0,255,200,0.1)' }
          },
          y: {
            ticks: {
              color: '#4a6080',
              font: { family: 'Orbitron', size: 9 },
              stepSize: 1,
            },
            grid: { color: 'rgba(0,255,200,0.05)' },
            border: { color: 'rgba(0,255,200,0.1)' }
          }
        },
        animation: {
          duration: 1500,
          easing: 'easeInOutQuart',
        }
      }
    });
  } catch(err) {
    console.error("Chart error:", err);
  }
}


window.onload = function() {
  const user = JSON.parse(localStorage.getItem('user'));
  if (user && user.email) {
    document.getElementById('alert-email').value = user.email;
  }

  // Set expiry date input to today's date by default
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  document.getElementById('expiry_date').min = `${yyyy}-${mm}-${dd}`;
  document.getElementById('expiry_date').value = `${yyyy}-${mm}-${dd}`;

  loadStats();
  loadProducts();
  loadAlerts();
  loadCharts();
}

// ── SMS Alert Send ──
async function sendSMS() {
  try {
    const res = await fetch('/api/send-sms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    document.getElementById('sms-msg').innerHTML = 
      `<p style="color:#00d4aa;font-size:0.85rem;">${data.message}</p>`;
  } catch(err) {
    document.getElementById('sms-msg').innerHTML = 
      `<p style="color:#ff6b35;font-size:0.85rem;">❌ Error: ${err.message}</p>`;
  }
}