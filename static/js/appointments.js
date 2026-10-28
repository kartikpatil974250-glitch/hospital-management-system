/**
 * PulseCare HMS - Interactive Multi-Step Appointment Booking Logic
 */

document.addEventListener("DOMContentLoaded", function () {
  const deptSelect = document.getElementById("deptSelect");
  const doctorSelect = document.getElementById("doctorSelect");
  const dateInput = document.getElementById("appointmentDate");
  const slotsContainer = document.getElementById("slotsContainer");
  const selectedTimeInput = document.getElementById("selectedStartTime");
  const bookingSummary = document.getElementById("bookingSummary");

  // Filter Doctors when Department changes
  if (deptSelect && doctorSelect) {
    deptSelect.addEventListener("change", function () {
      const selectedDeptId = this.value;
      const options = doctorSelect.querySelectorAll("option");

      let firstValid = null;
      options.forEach(opt => {
        if (!opt.value) return; // Skip placeholder
        const deptId = opt.getAttribute("data-dept-id");
        if (!selectedDeptId || deptId === selectedDeptId) {
          opt.style.display = "";
          if (!firstValid) firstValid = opt.value;
        } else {
          opt.style.display = "none";
        }
      });

      if (firstValid && (!doctorSelect.value || doctorSelect.selectedOptions[0].style.display === "none")) {
        doctorSelect.value = firstValid;
      }
      loadSlots();
    });
  }

  // Reload slots when Doctor or Date changes
  if (doctorSelect) doctorSelect.addEventListener("change", loadSlots);
  if (dateInput) dateInput.addEventListener("change", loadSlots);

  function loadSlots() {
    if (!slotsContainer || !doctorSelect || !dateInput) return;

    const doctorId = doctorSelect.value;
    const dateVal = dateInput.value;

    if (!doctorId || !dateVal) {
      slotsContainer.innerHTML = '<div class="form-text">Select doctor and date to view available time slots.</div>';
      return;
    }

    slotsContainer.innerHTML = '<div class="form-text" style="color:var(--primary-blue);">Checking real-time doctor availability...</div>';

    fetch(`/appointments/api/slots?doctor_id=${doctorId}&date=${dateVal}`)
      .then(response => response.json())
      .then(data => {
        if (!data.success || !data.slots || data.slots.length === 0) {
          slotsContainer.innerHTML = `
            <div class="alert alert-warning" style="margin-top:8px;">
              No consultations available for this doctor on selected date (Outside clinic hours or on leave).
            </div>`;
          if (selectedTimeInput) selectedTimeInput.value = "";
          return;
        }

        let html = '<div class="slots-grid">';
        data.slots.forEach(slot => {
          const isAvail = slot.is_available;
          const statusLabel = slot.status === "booked" ? "Booked" : (slot.status === "past" ? "Past" : (slot.status === "blocked" ? "Leave" : ""));
          const disabledAttr = isAvail ? "" : "disabled";
          const titleText = isAvail ? "Click to select" : (slot.reason || statusLabel);

          html += `
            <button type="button" 
                    class="slot-btn ${isAvail ? '' : 'disabled'}" 
                    data-time="${slot.start_time}" 
                    title="${titleText}"
                    ${disabledAttr}>
              ${slot.start_time}
              ${statusLabel ? `<span style="display:block;font-size:0.65rem;color:var(--text-muted);font-weight:normal;">${statusLabel}</span>` : ''}
            </button>
          `;
        });
        html += "</div>";
        slotsContainer.innerHTML = html;

        // Attach slot click events
        const buttons = slotsContainer.querySelectorAll(".slot-btn:not(:disabled)");
        buttons.forEach(btn => {
          btn.addEventListener("click", function () {
            buttons.forEach(b => b.classList.remove("selected"));
            this.classList.add("selected");
            if (selectedTimeInput) {
              selectedTimeInput.value = this.getAttribute("data-time");
            }
            updateSummary();
          });
        });
      })
      .catch(err => {
        slotsContainer.innerHTML = `<div class="alert alert-danger">Error retrieving schedule: ${err.message}</div>`;
      });
  }

  function updateSummary() {
    if (!bookingSummary || !doctorSelect || !dateInput) return;
    const docOption = doctorSelect.selectedOptions[0];
    const docFee = docOption ? docOption.getAttribute("data-fee") : "50.00";
    const feeElem = document.getElementById("summaryFee");
    const slotElem = document.getElementById("summarySlot");

    if (feeElem) feeElem.textContent = `$${parseFloat(docFee).toFixed(2)}`;
    if (slotElem && selectedTimeInput) slotElem.textContent = selectedTimeInput.value || "—";
  }

  // Trigger initial slot check if values present
  if (doctorSelect && doctorSelect.value && dateInput && dateInput.value) {
    loadSlots();
  }
});
