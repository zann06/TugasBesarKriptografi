const tabs = [...document.querySelectorAll('[role="tab"]')];

function selectTab(selectedTab) {
  for (const tab of tabs) {
    const active = tab === selectedTab;
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
    document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
  }
}

for (const [index, tab] of tabs.entries()) {
  tab.addEventListener('click', () => selectTab(tab));
  tab.addEventListener('keydown', (event) => {
    let next;
    switch (event.key) {
      case 'ArrowLeft':
        next = tabs[(index - 1 + tabs.length) % tabs.length];
        break;
      case 'ArrowRight':
        next = tabs[(index + 1) % tabs.length];
        break;
      case 'Home':
        next = tabs[0];
        break;
      case 'End':
        next = tabs.at(-1);
        break;
      default:
        return;
    }
    event.preventDefault();
    selectTab(next);
    next.focus();
  });
}

for (const picker of document.querySelectorAll('.file-picker')) {
  const input = picker.querySelector('input');
  const control = picker.querySelector('.file-control');
  const fileName = picker.querySelector('.file-name');
  const error = picker.querySelector('.file-error');
  const prompt = fileName.textContent;
  let dragDepth = 0;

  const validate = (files) => {
    if (files.length !== 1) return 'Pilih satu gambar PNG atau BMP.';
    if (!/\.(png|bmp)$/i.test(files[0].name)) return 'Format gambar harus PNG atau BMP.';
    return '';
  };

  const updateName = () => {
    const file = input.files[0];
    fileName.textContent = file?.name ?? prompt;
    fileName.title = file?.name ?? '';
    fileName.toggleAttribute('data-selected', Boolean(file));
  };

  updateName();
  input.addEventListener('change', () => {
    const message = input.files.length ? validate(input.files) : '';
    if (message) input.value = '';
    error.textContent = message;
    updateName();
  });

  control.addEventListener('dragenter', (event) => {
    if (!event.dataTransfer.types.includes('Files')) return;
    event.preventDefault();
    dragDepth += 1;
    control.setAttribute('data-dragging', '');
  });

  control.addEventListener('dragover', (event) => {
    if (!event.dataTransfer.types.includes('Files')) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  });

  control.addEventListener('dragleave', () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) control.removeAttribute('data-dragging');
  });

  control.addEventListener('drop', (event) => {
    if (!event.dataTransfer.types.includes('Files')) return;
    event.preventDefault();
    dragDepth = 0;
    control.removeAttribute('data-dragging');

    const files = event.dataTransfer.files;
    const message = validate(files);
    if (message) {
      error.textContent = message;
      return;
    }

    input.files = files;
    error.textContent = '';
    updateName();
  });
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function setCiphertext(id, value, placeholder) {
  const output = document.getElementById(id);
  output.textContent = value ?? placeholder;
  output.toggleAttribute('data-empty', value == null);
}

let lastEncodeData = null;
let lastCoverFile = null;
let activeVariant = 'modified';
const variantButtons = [...document.querySelectorAll('.variant-btn')];

function setActiveVariant(name) {
  if (!lastEncodeData?.variants?.[name]) return;
  activeVariant = name;
  const variant = lastEncodeData.variants[name];
  const metrics = lastEncodeData.metrics;
  const imageUrl = 'data:image/png;base64,' + variant.stego_image_b64;

  for (const button of variantButtons) {
    button.setAttribute('aria-pressed', String(button.dataset.variant === name));
  }

  setCiphertext('cipher-hex', variant.ciphertext_hex, 'Menunggu proses enkripsi.');
  setText('cipher-algo', variant.label + ' · HEX');

  const preview = document.getElementById('stego-preview');
  const download = document.getElementById('download-stego');
  preview.src = imageUrl;
  download.href = imageUrl;
  download.setAttribute('download', 'stego_' + name + '.png');

  setText('m-psnr', variant.psnr);
  setText('m-mse', variant.mse);
  setText('m-time', variant.process_time_ms + ' ms');
  setText('m-dim', metrics.image_dim);
  setText('m-bits', metrics.bits_embedded + ' bit');
  setText('m-ratio', metrics.payload_ratio + '%');
}

function renderBenchmark(data) {
  const benchmark = data.metrics.benchmark;
  const std = data.variants.standard;
  const mod = data.variants.modified;

  setText('b-std-len', std.ciphertext_len + ' byte');
  setText('b-mod-len', mod.ciphertext_len + ' byte');
  setText('b-std-pipeline', std.process_time_ms + ' ms');
  setText('b-mod-pipeline', mod.process_time_ms + ' ms');
  setText('b-std-mse', std.mse);
  setText('b-mod-mse', mod.mse);
  setText('b-std-psnr', std.psnr);
  setText('b-mod-psnr', mod.psnr);
  setText('b-std-bits', benchmark.std_diff_bits + ' / ' + benchmark.total_bits);
  setText('b-mod-bits', benchmark.mod_diff_bits + ' / ' + benchmark.total_bits);
  setText('b-std-ae', benchmark.std_avalanche + '%');
  setText('b-mod-ae', benchmark.mod_avalanche + '%');
  setText('b-std-time', benchmark.std_time_ms + ' ms');
  setText('b-mod-time', benchmark.mod_time_ms + ' ms');
}

function renderEncode(data) {
  lastEncodeData = data;
  lastCoverFile = data ? document.getElementById('cover-file').files[0] ?? null : null;

  document.getElementById('stego-empty').hidden = Boolean(data);
  document.getElementById('stego-result-area').hidden = !data;
  document.getElementById('encode-metrics').hidden = !data;
  document.getElementById('variant-switch').hidden = !data;

  if (!data) {
    setCiphertext('cipher-hex', null, 'Menunggu proses enkripsi.');
    setText('cipher-algo', 'HEX');
    document.getElementById('stego-preview').removeAttribute('src');
    document.getElementById('download-stego').removeAttribute('href');
    return;
  }

  renderBenchmark(data);
  setActiveVariant(data.algorithm);
}

for (const button of variantButtons) {
  button.addEventListener('click', () => setActiveVariant(button.dataset.variant));
}

function renderDecode(data) {
  setCiphertext('ext-hex', data?.extracted_hex, 'Menunggu proses ekstraksi.');
  document.getElementById('recovered-text').value = data?.plaintext ?? '';
  setText('dec-algorithm', data ? 'Algoritma terdeteksi · ' + data.algorithm_label : '');
  setText('dec-time', data ? 'Waktu ekstraksi dan dekripsi · ' + data.process_time_ms + ' ms' : '');
}

let compareObjectUrls = [];

function clearCompareImages() {
  for (const url of compareObjectUrls) URL.revokeObjectURL(url);
  compareObjectUrls = [];
  for (const id of ['compare-cover-img', 'compare-stego-img', 'compare-diff-img']) {
    document.getElementById(id).removeAttribute('src');
  }
}

function setCompareObjectUrl(id, file) {
  if (!file) return;
  const url = URL.createObjectURL(file);
  compareObjectUrls.push(url);
  document.getElementById(id).src = url;
}

function renderCompare(data) {
  const result = document.getElementById('compare-result');
  if (!data) {
    result.hidden = true;
    clearCompareImages();
    return;
  }

  const metrics = data.metrics;
  setCompareObjectUrl('compare-cover-img', document.getElementById('compare-cover').files[0]);
  setCompareObjectUrl('compare-stego-img', document.getElementById('compare-stego').files[0]);
  document.getElementById('compare-diff-img').src = 'data:image/png;base64,' + metrics.diff_image_b64;

  setText('c-psnr', metrics.psnr);
  setText('c-mse', metrics.mse);
  setText('c-dim', metrics.image_dim);
  setText('c-changed', metrics.changed_pixels.toLocaleString('id-ID') + ' px');
  setText('c-ratio', metrics.changed_pixel_ratio + '%');
  setText('c-maxdiff', metrics.max_diff);
  setText('c-mean', metrics.mean_abs_diff);
  setText('c-subpixels', metrics.changed_subpixels.toLocaleString('id-ID'));

  const verdict = document.getElementById('compare-verdict');
  verdict.removeAttribute('data-warn');
  if (metrics.identical) {
    verdict.textContent = 'Kedua citra identik — tidak ada piksel yang berubah.';
  } else if (metrics.psnr_db == null || metrics.psnr_db >= 40) {
    verdict.textContent = 'Perubahan sangat kecil dan tidak kasat mata. Citra stego masih terlihat identik dengan aslinya.';
  } else if (metrics.psnr_db >= 30) {
    verdict.textContent = 'Perubahan kecil; kualitas citra masih baik untuk sebagian besar penggunaan.';
  } else {
    verdict.textContent = 'Perubahan cukup terlihat. Periksa kembali kapasitas citra dan proses penyisipan.';
    verdict.setAttribute('data-warn', '');
  }

  result.hidden = false;
}

function bindForm(mode, render, pendingLabel, successMessage) {
  const form = document.getElementById(mode + '-form');
  const button = form.querySelector('button[type="submit"]');
  const label = button.querySelector('span');
  const defaultLabel = label.textContent;
  const status = document.getElementById(mode + '-alert');
  const keyInput = form.elements.namedItem('secret_key');

  if (keyInput) {
    keyInput.addEventListener('input', () => keyInput.setCustomValidity(''));
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (button.disabled) return;

    if (keyInput && new TextEncoder().encode(keyInput.value).length > 56) {
      keyInput.setCustomValidity('Panjang kunci rahasia maksimal 56 byte UTF-8.');
      keyInput.reportValidity();
      return;
    }

    const payload = new FormData(form);
    status.textContent = '';
    status.removeAttribute('data-error');
    render(null);
    button.disabled = true;
    label.textContent = pendingLabel;

    try {
      const response = await fetch('/api/' + mode, { method: 'POST', body: payload });
      const data = await response.json();
      if (!response.ok || !data.success) {
        status.setAttribute('data-error', '');
        status.textContent = data.error || 'Proses gagal. Coba lagi.';
        return;
      }
      render(data);
      status.textContent = successMessage;
    } catch {
      status.setAttribute('data-error', '');
      status.textContent = 'Gagal memproses permintaan. Coba lagi.';
    } finally {
      button.disabled = false;
      label.textContent = defaultLabel;
    }
  });
}

document.getElementById('compare-last').addEventListener('click', async () => {
  if (!lastEncodeData || !lastCoverFile) return;

  const variant = lastEncodeData.variants[activeVariant];
  if (!variant) return;

  try {
    const stegoBlob = await (await fetch('data:image/png;base64,' + variant.stego_image_b64)).blob();
    const stegoFile = new File([stegoBlob], 'stego_' + activeVariant + '.png', { type: 'image/png' });

    const coverTransfer = new DataTransfer();
    coverTransfer.items.add(lastCoverFile);
    const stegoTransfer = new DataTransfer();
    stegoTransfer.items.add(stegoFile);

    const coverInput = document.getElementById('compare-cover');
    const stegoInput = document.getElementById('compare-stego');
    coverInput.files = coverTransfer.files;
    stegoInput.files = stegoTransfer.files;
    coverInput.dispatchEvent(new Event('change'));
    stegoInput.dispatchEvent(new Event('change'));

    selectTab(document.getElementById('tab-compare'));
    document.getElementById('compare-form').requestSubmit();
  } catch {
    selectTab(document.getElementById('tab-compare'));
    const alert = document.getElementById('compare-alert');
    alert.setAttribute('data-error', '');
    alert.textContent = 'Gagal menyiapkan perbandingan otomatis. Silakan pilih citra secara manual.';
  }
});

bindForm('encode', renderEncode, 'Mengenkripsi dan menyisipkan…', 'Pesan berhasil dienkripsi dan disisipkan.');
bindForm('decode', renderDecode, 'Mengekstrak dan mendekripsi…', 'Pesan berhasil dipulihkan.');
bindForm('compare', renderCompare, 'Membandingkan citra…', 'Perbandingan citra selesai.');
