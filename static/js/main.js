/**
 * PulseCare Hospital Management System - Core Client Interactions
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Sidebar Drawer Toggle
  const menuToggle = document.getElementById("mobileMenuToggle");
  const sidebar = document.getElementById("appSidebar");
  const sidebarOverlay = document.getElementById("sidebarOverlay");

  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      if (sidebarOverlay) sidebarOverlay.classList.toggle("active");
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", function () {
      sidebar.classList.remove("open");
      sidebarOverlay.classList.remove("active");
    });
  }

  // 2. Password Visibility Toggle
  const togglePassBtns = document.querySelectorAll(".toggle-password");
  togglePassBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetInput = document.querySelector(btn.getAttribute("data-target"));
      if (targetInput) {
        if (targetInput.type === "password") {
          targetInput.type = "text";
          btn.textContent = "Hide";
        } else {
          targetInput.type = "password";
          btn.textContent = "Show";
        }
      }
    });
  });

  // 3. Auto-dismiss alerts after 5 seconds
  const autoAlerts = document.querySelectorAll(".alert");
  autoAlerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.4s ease, transform 0.4s ease";
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-10px)";
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // 4. Accessible Modal Controller
  window.openModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add("show");
      document.body.style.overflow = "hidden";
    }
  };

  window.closeModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("show");
      document.body.style.overflow = "";
    }
  };

  // Close modals on Escape key or backdrop click
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.show").forEach(m => {
        m.classList.remove("show");
      });
      document.body.style.overflow = "";
    }
  });

  document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
    backdrop.addEventListener("click", function (e) {
      if (e.target === backdrop) {
        backdrop.classList.remove("show");
        document.body.style.overflow = "";
      }
    });
  });

  // 5. Prevent double form submissions on primary forms
  const forms = document.querySelectorAll("form:not(.no-disable)");
  forms.forEach(function (form) {
    form.addEventListener("submit", function () {
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn && !submitBtn.disabled) {
        setTimeout(function () {
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span style="display:inline-block;animation:spin 1s linear infinite;">&#8635;</span> Processing...';
        }, 10);
      }
    });
  });
});
