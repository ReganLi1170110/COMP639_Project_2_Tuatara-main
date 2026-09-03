document.addEventListener('DOMContentLoaded', function () {
  const pendingBody = document.getElementById('pending-claims-body');
  const shippedBody = document.getElementById('shipped-claims-body');
  const alerts = document.getElementById('fulfillment-alerts');

  function showAlert(message, type = 'success') {
    const wrapper = document.createElement('div');
    wrapper.className = `alert alert-${type} alert-dismissible fade show`;
    wrapper.role = 'alert';
    wrapper.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alerts.innerHTML = '';
    alerts.appendChild(wrapper);
  }

  function createAddressNode(addressText) {
    const address = document.createElement('div');
    address.className = 'small text-muted';
    address.innerHTML = addressText ? addressText.replace(/\n/g, '<br>') : '<span class="text-muted">No address provided</span>';
    return address;
  }

  function createPendingRow(claim) {
    const tr = document.createElement('tr');
    tr.dataset.claimId = claim.id;

    tr.innerHTML = `
      <td>${claim.claimed_date || '-'}</td>
      <td>${claim.user_name || '-'}</td>
      <td>${claim.badge_name || '-'}</td>
      <td></td>
      <td><span class="badge bg-warning text-dark">${claim.status}</span></td>
      <td></td>
    `;

    tr.querySelector('td:nth-child(4)').appendChild(createAddressNode(claim.full_address));

    const actionCell = tr.querySelector('td:nth-child(6)');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm btn-primary';
    button.textContent = 'Mark Shipped';
    button.addEventListener('click', () => shipClaim(claim.id, tr, claim));
    actionCell.appendChild(button);

    return tr;
  }

  function createShippedRow(claim) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${claim.claimed_date || '-'}</td>
      <td>${claim.user_name || '-'}</td>
      <td>${claim.badge_name || '-'}</td>
      <td></td>
      <td><span class="badge bg-success">shipped</span></td>
    `;
    tr.querySelector('td:nth-child(4)').appendChild(createAddressNode(claim.full_address));
    return tr;
  }

  function clearTable(body, emptyMessage, cols) {
    body.innerHTML = `<tr><td colspan="${cols}" class="text-center text-muted">${emptyMessage}</td></tr>`;
  }

  function loadPendingClaims() {
    fetch('/api/admin/claims/pending', { credentials: 'same-origin' })
      .then(response => {
        if (!response.ok) throw new Error('Unable to load pending claims');
        return response.json();
      })
      .then(data => {
        pendingBody.innerHTML = '';
        if (!data.claims || data.claims.length === 0) {
          clearTable(pendingBody, 'No pending claims at this time.', 6);
          return;
        }
        data.claims.forEach(claim => {
          pendingBody.appendChild(createPendingRow(claim));
        });
      })
      .catch(() => {
        clearTable(pendingBody, 'Unable to load pending claims.', 6);
      });
  }

  function shipClaim(claimId, row, claim) {
    fetch(`/api/admin/claims/${claimId}/ship`, {
      method: 'POST',
      credentials: 'same-origin',
    })
      .then(response => {
        if (!response.ok) return response.json().then(body => Promise.reject(body.error || 'Failed to mark shipped'));
        return response.json();
      })
      .then(() => {
        row.remove();
        if (!pendingBody.querySelector('tr')) {
          clearTable(pendingBody, 'No pending claims at this time.', 6);
        }
        if (shippedBody.querySelector('td[colspan]')) {
          shippedBody.innerHTML = '';
        }
        shippedBody.appendChild(createShippedRow(claim));
        showAlert('Claim marked as shipped.', 'success');
      })
      .catch(error => {
        showAlert(error?.message || error || 'Unable to mark claim as shipped.', 'danger');
      });
  }

  loadPendingClaims();
});
