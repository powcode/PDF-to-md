document.addEventListener("DOMContentLoaded", () => {
  // Tabs Navigation
  const tabList = document.querySelector('[role="tablist"]');
  if (tabList) {
    const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
    const panels = Array.from(document.querySelectorAll('[role="tabpanel"]'));

    function activateTab(tab, focus = true) {
      tabs.forEach((t) => {
        t.setAttribute("aria-selected", "false");
        t.setAttribute("tabindex", "-1");
      });

      tab.setAttribute("aria-selected", "true");
      tab.removeAttribute("tabindex");

      const targetId = tab.getAttribute("aria-controls");
      panels.forEach((p) => {
        if (p.id === targetId) {
          p.removeAttribute("hidden");
        } else {
          p.setAttribute("hidden", "");
        }
      });

      if (focus) {
        tab.focus();
      }
    }

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => activateTab(tab, false));
      tab.addEventListener("keydown", (e) => {
        let targetIndex = null;
        if (e.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
        else if (e.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") targetIndex = 0;
        else if (e.key === "End") targetIndex = tabs.length - 1;

        if (targetIndex !== null) {
          e.preventDefault();
          activateTab(tabs[targetIndex], true);
        }
      });
    });
  }

  // Helper for Upload Zones
  function setupUploadZone(zoneId, inputId, cardId, nameId, removeId, onChange) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const card = document.getElementById(cardId);
    const nameEl = document.getElementById(nameId);
    const removeBtn = document.getElementById(removeId);

    if (!zone || !input) return;

    function setFile(file) {
      if (file) {
        nameEl.textContent = file.name;
        card.removeAttribute("hidden");
        zone.classList.add("has-file");
        zone.classList.remove("has-error");
      } else {
        input.value = "";
        nameEl.textContent = "";
        card.setAttribute("hidden", "");
        zone.classList.remove("has-file");
      }
      if (onChange) onChange(file);
    }

    input.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0] ? e.target.files[0] : null;
      setFile(file);
    });

    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setFile(null);
    });

    // Drag and Drop
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        zone.classList.remove("drag-over");
      });
    });

    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        input.files = e.dataTransfer.files;
        setFile(input.files[0]);
      }
    });
  }

  // Convert Tab State
  const btnConvert = document.getElementById("btn-convert");
  const convertFileInput = document.getElementById("convert-file-input");
  const convertProgressCard = document.getElementById("convert-progress-card");
  const convertProgressText = document.getElementById("convert-progress-text");
  const convertProgressBar = document.getElementById("convert-progressbar");
  const convertProgressFill = document.getElementById("convert-progress-fill");
  const convertResultPanel = document.getElementById("convert-result-panel");
  const convertResultPreview = document.getElementById("convert-result-preview");
  const btnDownloadMd = document.getElementById("btn-download-md");
  const convertError = document.getElementById("convert-error");
  const convertErrorText = document.getElementById("convert-error-text");

  let currentConvertFile = null;
  let pollInterval = null;
  let activeJobId = null;

  function showConvertError(msg) {
    convertErrorText.textContent = msg;
    convertError.removeAttribute("hidden");
    convertProgressCard.setAttribute("hidden", "");
    btnConvert.disabled = !currentConvertFile;
  }

  function hideConvertError() {
    convertError.setAttribute("hidden", "");
  }

  setupUploadZone(
    "convert-upload-zone",
    "convert-file-input",
    "convert-file-card",
    "convert-file-name",
    "convert-file-remove",
    (file) => {
      currentConvertFile = file;
      btnConvert.disabled = !file;
      hideConvertError();
      convertResultPanel.setAttribute("hidden", "");
      convertProgressCard.setAttribute("hidden", "");
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    }
  );

  btnConvert.addEventListener("click", async () => {
    if (!currentConvertFile) return;

    hideConvertError();
    convertResultPanel.setAttribute("hidden", "");
    convertProgressCard.removeAttribute("hidden");
    btnConvert.disabled = true;

    convertProgressText.textContent = "Mengunggah dan memeriksa file...";
    convertProgressBar.setAttribute("aria-valuenow", "5");
    convertProgressFill.style.width = "5%";

    const formData = new FormData();
    formData.append("file", currentConvertFile);

    try {
      const resp = await fetch("/api/convert", {
        method: "POST",
        body: formData
      });

      const data = await resp.json();
      if (!resp.ok) {
        showConvertError(data.error || "Gagal memulai proses konversi.");
        return;
      }

      activeJobId = data.job_id;
      startProgressPolling(activeJobId);
    } catch (err) {
      showConvertError("Terjadi kesalahan jaringan saat mengunggah file.");
    }
  });

  function startProgressPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
      try {
        const resp = await fetch(`/api/jobs/${jobId}`);
        if (!resp.ok) {
          clearInterval(pollInterval);
          pollInterval = null;
          showConvertError("Gagal mengambil status pekerjaan.");
          return;
        }

        const job = await resp.json();

        // Calculate progress percentage
        let pct = 10;
        if (job.progress && job.progress.total_slides > 0) {
          pct = Math.round((job.progress.slide / job.progress.total_slides) * 90) + 10;
        }
        if (job.status === "done") pct = 100;

        convertProgressBar.setAttribute("aria-valuenow", pct.toString());
        convertProgressFill.style.width = `${pct}%`;
        convertProgressText.textContent = job.message || "Sedang memproses...";

        if (job.status === "done") {
          clearInterval(pollInterval);
          pollInterval = null;
          handleConvertDone(jobId);
        } else if (job.status === "error") {
          clearInterval(pollInterval);
          pollInterval = null;
          showConvertError(job.error || job.message || "Terjadi kesalahan saat konversi.");
        }
      } catch (err) {
        // Network error during poll, continue polling
      }
    }, 1000);
  }

  async function handleConvertDone(jobId) {
    try {
      const res = await fetch(`/api/jobs/${jobId}/result`);
      if (!res.ok) {
        showConvertError("Gagal mengambil hasil konversi.");
        return;
      }
      const data = await res.json();
      convertResultPreview.textContent = data.markdown || "";
      convertResultPanel.removeAttribute("hidden");
      convertProgressCard.setAttribute("hidden", "");
      btnConvert.disabled = false;

      btnDownloadMd.onclick = () => {
        window.location.href = `/api/jobs/${jobId}/download`;
      };
    } catch (e) {
      showConvertError("Terjadi kesalahan saat memuat hasil konversi.");
    }
  }

  // Split Tab State & Intuitive Controls
  const btnSplit = document.getElementById("btn-split");
  const splitFileInput = document.getElementById("split-file-input");
  const splitFileCard = document.getElementById("split-file-card");
  const splitFileName = document.getElementById("split-file-name");
  const splitFileRemove = document.getElementById("split-file-remove");
  const splitPageBadge = document.getElementById("split-page-badge");
  const splitControlsSection = document.getElementById("split-controls-section");
  const btnModeRange = document.getElementById("btn-mode-range");
  const btnModeCustom = document.getElementById("btn-mode-custom");
  const splitModeRangeBox = document.getElementById("split-mode-range-box");
  const splitModeCustomBox = document.getElementById("split-mode-custom-box");
  const splitFromPage = document.getElementById("split-from-page");
  const splitToPage = document.getElementById("split-to-page");
  const splitRanges = document.getElementById("split-ranges");
  const quickPresetContainer = document.getElementById("quick-preset-container");
  const splitSelectionPreview = document.getElementById("split-selection-preview");
  const splitSelectionList = document.getElementById("split-selection-list");
  const splitRangeError = document.getElementById("split-range-error");
  const splitRangeErrorText = document.getElementById("split-range-error-text");
  const splitError = document.getElementById("split-error");
  const splitErrorText = document.getElementById("split-error-text");

  let splitFile = null;
  let totalDocPages = 0;
  let activeSplitMode = "range"; // "range" or "custom"

  function setSplitMode(mode) {
    activeSplitMode = mode;
    if (mode === "range") {
      btnModeRange.classList.add("active");
      btnModeCustom.classList.remove("active");
      splitModeRangeBox.removeAttribute("hidden");
      splitModeCustomBox.setAttribute("hidden", "");
    } else {
      btnModeCustom.classList.add("active");
      btnModeRange.classList.remove("active");
      splitModeCustomBox.removeAttribute("hidden");
      splitModeRangeBox.setAttribute("hidden", "");
    }
    syncAndValidateSelection();
  }

  btnModeRange.addEventListener("click", () => setSplitMode("range"));
  btnModeCustom.addEventListener("click", () => setSplitMode("custom"));

  function parseRangeString(str, total) {
    if (!str || !str.trim()) return { pages: [], error: "Rentang halaman tidak boleh kosong." };
    const parts = str.split(",").map(p => p.trim()).filter(Boolean);
    if (!parts.length) return { pages: [], error: "Rentang halaman tidak valid." };

    const chosen = new Set();
    for (const part of parts) {
      if (part.includes("-")) {
        const sub = part.split("-").map(s => s.trim());
        if (sub.length !== 2) return { pages: [], error: `Format rentang '${part}' tidak valid.` };
        const s = parseInt(sub[0], 10);
        const e = parseInt(sub[1], 10);
        if (isNaN(s) || isNaN(e)) return { pages: [], error: `Rentang '${part}' harus berupa angka numerik.` };
        if (s < 1) return { pages: [], error: `Halaman awal ${s} tidak boleh kurang dari 1.` };
        if (total > 0 && e > total) return { pages: [], error: `Halaman akhir ${e} melebihi jumlah halaman dokumen (${total}).` };
        if (s > e) return { pages: [], error: `Halaman awal ${s} lebih besar dari halaman akhir ${e} pada rentang '${part}'.` };
        for (let i = s; i <= e; i++) chosen.add(i);
      } else {
        const p = parseInt(part, 10);
        if (isNaN(p)) return { pages: [], error: `Halaman '${part}' harus berupa angka numerik.` };
        if (p < 1) return { pages: [], error: `Halaman ${p} tidak boleh kurang dari 1.` };
        if (total > 0 && p > total) return { pages: [], error: `Halaman ${p} melebihi jumlah halaman dokumen (${total}).` };
        chosen.add(p);
      }
    }
    const sorted = Array.from(chosen).sort((a, b) => a - b);
    if (!sorted.length) return { pages: [], error: "Tidak ada halaman yang dipilih." };
    return { pages: sorted, error: null };
  }

  function getEffectiveRangeString() {
    if (activeSplitMode === "range") {
      const fromVal = splitFromPage.value.trim();
      const toVal = splitToPage.value.trim();
      if (!fromVal || !toVal) return "";
      return `${fromVal}-${toVal}`;
    } else {
      return splitRanges.value.trim();
    }
  }

  function syncAndValidateSelection() {
    if (!splitFile) {
      btnSplit.disabled = true;
      splitSelectionPreview.setAttribute("hidden", "");
      return;
    }

    const rangeStr = getEffectiveRangeString();
    const result = parseRangeString(rangeStr, totalDocPages);

    if (result.error) {
      splitRangeErrorText.textContent = result.error;
      splitRangeError.removeAttribute("hidden");
      splitSelectionPreview.setAttribute("hidden", "");
      btnSplit.disabled = true;
    } else {
      splitRangeError.setAttribute("hidden", "");
      splitSelectionPreview.removeAttribute("hidden");
      btnSplit.disabled = false;

      // Render friendly preview summary
      const count = result.pages.length;
      let displayPages = "";
      if (count <= 15) {
        displayPages = result.pages.join(", ");
      } else {
        const head = result.pages.slice(0, 10).join(", ");
        const tail = result.pages.slice(-3).join(", ");
        displayPages = `${head}, ... [dan ${count - 13} halaman lainnya] ..., ${tail}`;
      }
      splitSelectionList.innerHTML = `<strong>Total: ${count} halaman</strong><br>Halaman: ${displayPages}`;
    }
  }

  [splitFromPage, splitToPage].forEach(input => {
    input.addEventListener("input", () => {
      syncAndValidateSelection();
      splitError.setAttribute("hidden", "");
    });
  });

  splitRanges.addEventListener("input", () => {
    syncAndValidateSelection();
    splitError.setAttribute("hidden", "");
  });

  setupUploadZone(
    "split-upload-zone",
    "split-file-input",
    "split-file-card",
    "split-file-name",
    "split-file-remove",
    async (file) => {
      splitFile = file;
      splitError.setAttribute("hidden", "");
      splitRangeError.setAttribute("hidden", "");

      if (!file) {
        splitControlsSection.setAttribute("hidden", "");
        btnSplit.disabled = true;
        totalDocPages = 0;
        return;
      }

      // Inspect file via backend
      splitPageBadge.textContent = "Memeriksa dokumen...";
      splitControlsSection.setAttribute("hidden", "");
      btnSplit.disabled = true;

      const fd = new FormData();
      fd.append("file", file);

      try {
        const resp = await fetch("/api/inspect", { method: "POST", body: fd });
        const data = await resp.json();

        if (resp.ok && data.pages) {
          totalDocPages = data.pages;
          splitPageBadge.textContent = `${totalDocPages} Halaman (${data.size_mb} MB)`;

          splitFromPage.max = totalDocPages;
          splitToPage.max = totalDocPages;
          splitFromPage.value = "1";
          splitToPage.value = totalDocPages.toString();

          // Build Quick Presets
          quickPresetContainer.innerHTML = "";
          const presets = [
            { label: `Semua (1 – ${totalDocPages})`, from: 1, to: totalDocPages },
          ];

          if (totalDocPages > 1) {
            const half = Math.floor(totalDocPages / 2);
            presets.push({ label: `Paruh Awal (1 – ${half})`, from: 1, to: half });
            presets.push({ label: `Paruh Akhir (${half + 1} – ${totalDocPages})`, from: half + 1, to: totalDocPages });
          }

          presets.forEach(p => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "quick-chip-btn";
            chip.textContent = p.label;
            chip.addEventListener("click", () => {
              setSplitMode("range");
              splitFromPage.value = p.from;
              splitToPage.value = p.to;
              syncAndValidateSelection();
            });
            quickPresetContainer.appendChild(chip);
          });

          splitControlsSection.removeAttribute("hidden");
          syncAndValidateSelection();
        } else {
          splitPageBadge.textContent = "Dokumen terbaca";
          splitControlsSection.removeAttribute("hidden");
          syncAndValidateSelection();
        }
      } catch (err) {
        splitPageBadge.textContent = "Gagal membaca info dokumen";
        splitControlsSection.removeAttribute("hidden");
        syncAndValidateSelection();
      }
    }
  );

  btnSplit.addEventListener("click", async () => {
    if (!splitFile) return;
    const rangeStr = getEffectiveRangeString();
    if (!rangeStr) return;

    btnSplit.disabled = true;
    splitError.setAttribute("hidden", "");
    splitRangeError.setAttribute("hidden", "");

    const formData = new FormData();
    formData.append("file", splitFile);
    formData.append("ranges", rangeStr);

    try {
      btnSplit.textContent = "Sedang memproses unduhan...";
      const resp = await fetch("/api/split", {
        method: "POST",
        body: formData
      });

      if (!resp.ok) {
        const errData = await resp.json();
        const msg = errData.error || "Gagal memisahkan file PDF.";
        splitErrorText.textContent = msg;
        splitError.removeAttribute("hidden");
        btnSplit.disabled = false;
        btnSplit.textContent = "Pisahkan PDF";
        return;
      }

      // Download PDF response
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const originalStem = splitFile.name.replace(/\.[^/.]+$/, "");
      a.download = `${originalStem}_split.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      btnSplit.disabled = false;
      btnSplit.textContent = "Pisahkan PDF";
    } catch (err) {
      splitErrorText.textContent = "Terjadi kesalahan saat memproses pemisahan PDF.";
      splitError.removeAttribute("hidden");
      btnSplit.disabled = false;
      btnSplit.textContent = "Pisahkan PDF";
    }
  });
});
