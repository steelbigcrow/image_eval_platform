/**
 * 图片比对平台前端交互。
 *
 * 职责：
 *  - 上传区（点击选择 + 拖拽）与本地即时预览
 *  - 调用 /api/compare 提交比对请求
 *  - 渲染分数、结论、指标明细与图片对照
 * 无任何第三方依赖。
 */
(function () {
  'use strict';

  var RING_CIRCUMFERENCE = 2 * Math.PI * 52; // 与 CSS 中 r="52" 保持一致

  var els = {
    algorithm: document.getElementById('algorithm'),
    algoDesc: document.getElementById('algo-desc'),
    btnCompare: document.getElementById('btn-compare'),
    alert: document.getElementById('alert'),
    resultPanel: document.getElementById('result-panel'),
    ringValue: document.getElementById('ring-value'),
    scoreValue: document.getElementById('score-value'),
    levelTag: document.getElementById('level-tag'),
    algoUsed: document.getElementById('algo-used'),
    algoKey: document.getElementById('algo-key'),
    resultMessage: document.getElementById('result-message'),
    sourceSize: document.getElementById('source-size'),
    targetSize: document.getElementById('target-size'),
    createdAt: document.getElementById('created-at'),
    metricsBody: document.getElementById('metrics-body'),
    previewSource: document.getElementById('preview-source'),
    previewTarget: document.getElementById('preview-target'),
    captionSource: document.getElementById('caption-source'),
    captionTarget: document.getElementById('caption-target')
  };

  /** 每个上传区各自保存 File 与本地预览地址。 */
  var state = { source: { file: null, url: null }, target: { file: null, url: null } };

  /* ------------------------------------------------------------------ 工具 */

  function showAlert(message, isInfo) {
    els.alert.textContent = message;
    els.alert.classList.toggle('is-info', !!isInfo);
    els.alert.hidden = false;
  }

  function clearAlert() {
    els.alert.hidden = true;
    els.alert.textContent = '';
  }

  function formatBytes(bytes) {
    if (!bytes) return '0 B';
    var units = ['B', 'KB', 'MB', 'GB'];
    var i = Math.floor(Math.log(bytes) / Math.log(1024));
    i = Math.min(i, units.length - 1);
    return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 2) + ' ' + units[i];
  }

  function formatUtc(isoString) {
    if (!isoString) return '--';
    var date = new Date(isoString);
    return isNaN(date.getTime()) ? isoString : date.toLocaleString();
  }

  function levelClass(level) {
    if (level === '高度相似') return 'level-high';
    if (level === '较为相似') return 'level-mid';
    if (level === '差异明显') return 'level-low';
    return 'level-bad';
  }

  /* --------------------------------------------------------------- 上传区 */

  function setupDropzone(role) {
    var zone = document.getElementById('dropzone-' + role);
    var input = document.getElementById('file-' + role);
    var empty = zone.querySelector('.dz-empty');
    var preview = zone.querySelector('.dz-preview');
    var img = preview.querySelector('img');
    var nameEl = preview.querySelector('.dz-name');
    var sizeEl = preview.querySelector('.dz-size');
    var clearBtn = zone.querySelector('.btn-clear');

    function render(snapshot) {
      if (!snapshot.file) {
        empty.hidden = false;
        preview.hidden = true;
        img.removeAttribute('src');
        input.value = '';
        return;
      }
      empty.hidden = true;
      preview.hidden = false;
      img.src = snapshot.url;
      nameEl.textContent = snapshot.file.name;
      sizeEl.textContent = formatBytes(snapshot.file.size);
    }

    function accept(file) {
      if (!file) return;
      if (!/^image\//i.test(file.type) && !/\.(png|jpe?g|bmp|gif|webp|tiff?)$/i.test(file.name)) {
        showAlert('文件「' + file.name + '」不是受支持的图片格式');
        return;
      }
      clearAlert();
      if (state[role].url) URL.revokeObjectURL(state[role].url);
      state[role].file = file;
      state[role].url = URL.createObjectURL(file);
      render(state[role]);
    }

    input.addEventListener('change', function () {
      accept(input.files && input.files[0]);
    });

    zone.addEventListener('click', function (event) {
      if (event.target.closest('.btn-clear')) return;
      input.click();
    });

    zone.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        input.click();
      }
    });

    clearBtn.addEventListener('click', function (event) {
      event.stopPropagation();
      if (state[role].url) URL.revokeObjectURL(state[role].url);
      state[role] = { file: null, url: null };
      render(state[role]);
      clearAlert();
    });

    ['dragenter', 'dragover'].forEach(function (type) {
      zone.addEventListener(type, function (event) {
        event.preventDefault();
        zone.classList.add('is-dragover');
      });
    });

    ['dragleave', 'drop'].forEach(function (type) {
      zone.addEventListener(type, function (event) {
        event.preventDefault();
        if (type === 'dragleave' && zone.contains(event.relatedTarget)) return;
        zone.classList.remove('is-dragover');
      });
    });

    zone.addEventListener('drop', function (event) {
      var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      accept(file);
    });
  }

  /* ------------------------------------------------------------- 算法列表 */

  function updateAlgoDescription() {
    var option = els.algorithm.options[els.algorithm.selectedIndex];
    els.algoDesc.textContent = option ? option.textContent.trim() : '';
  }

  function loadAlgorithms() {
    return fetch('/api/algorithms')
      .then(function (res) { return res.json(); })
      .then(function (payload) {
        if (!payload.ok || !payload.data.algorithms.length) return;
        var current = els.algorithm.value;
        var descriptions = {};
        els.algorithm.innerHTML = '';
        payload.data.algorithms.forEach(function (item) {
          descriptions[item.key] = item.description;
          var option = document.createElement('option');
          option.value = item.key;
          option.textContent = item.label;
          els.algorithm.appendChild(option);
        });
        els.algorithm.value = current;
        els.algoDesc.textContent = descriptions[current] || '';
      })
      .catch(function () {
        /* 保留服务端渲染的下拉框，不打断使用 */
      });
  }

  /* --------------------------------------------------------------- 结果渲染 */

  function renderMetrics(metrics) {
    els.metricsBody.innerHTML = '';
    var entries = Object.keys(metrics || {}).map(function (k) { return [k, metrics[k]]; });
    if (!entries.length) {
      var emptyRow = document.createElement('tr');
      emptyRow.innerHTML = '<td colspan="2">该算法未提供明细指标</td>';
      els.metricsBody.appendChild(emptyRow);
      return;
    }
    entries.forEach(function (pair) {
      var row = document.createElement('tr');
      var name = document.createElement('td');
      var value = document.createElement('td');
      name.textContent = pair[0];
      value.textContent = pair[1];
      row.appendChild(name);
      row.appendChild(value);
      els.metricsBody.appendChild(row);
    });
  }

  function renderResult(data) {
    els.scoreValue.textContent = data.score.toFixed(2);
    els.ringValue.style.strokeDashoffset = String(RING_CIRCUMFERENCE * (1 - data.score / 100));

    els.levelTag.textContent = data.level;
    els.levelTag.className = 'level-tag ' + levelClass(data.level);

    els.algoUsed.textContent = data.algorithm.label;
    els.algoKey.textContent = data.algorithm.key;
    els.resultMessage.textContent = data.message || '';

    els.sourceSize.textContent = data.source.width + ' × ' + data.source.height;
    els.targetSize.textContent = data.target.width + ' × ' + data.target.height;
    els.createdAt.textContent = formatUtc(data.created_at);

    renderMetrics(data.metrics);

    els.previewSource.src = data.source.preview;
    els.previewTarget.src = data.target.preview;
    els.captionSource.textContent = '原图片 · ' + data.source.filename;
    els.captionTarget.textContent = '目标图片 · ' + data.target.filename;

    els.resultPanel.hidden = false;
    els.resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /* ----------------------------------------------------------------- 比对 */

  function compare() {
    clearAlert();

    if (!state.source.file || !state.target.file) {
      showAlert('请先上传原图片和目标图片');
      return;
    }

    var formData = new FormData();
    formData.append('source', state.source.file);
    formData.append('target', state.target.file);
    formData.append('algorithm', els.algorithm.value);

    els.btnCompare.disabled = true;
    els.btnCompare.textContent = '比对中…';

    fetch('/api/compare', { method: 'POST', body: formData })
      .then(function (res) {
        return res.json().then(function (payload) {
          if (!res.ok || !payload.ok) throw new Error(payload.message || '比对失败');
          return payload.data;
        });
      })
      .then(renderResult)
      .catch(function (error) {
        showAlert(error.message || '请求失败，请确认服务是否正常运行');
      })
      .then(function () {
        els.btnCompare.disabled = false;
        els.btnCompare.textContent = '开始比对';
      });
  }

  /* ------------------------------------------------------------------ 初始化 */

  setupDropzone('source');
  setupDropzone('target');
  els.btnCompare.addEventListener('click', compare);
  els.algorithm.addEventListener('change', updateAlgoDescription);
  updateAlgoDescription();
  loadAlgorithms();
})();
