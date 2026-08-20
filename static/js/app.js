/**
 * UniDownloader Frontend Application
 * Ultra-modern reactive client for downloading video, audio, playlists, subtitles with cookies support.
 */

class UniDownloaderApp {
  constructor() {
    this.currentMedia = null;
    this.cookieProfiles = [];
    this.supportedBrowsers = [];
    this.activeCookie = { type: 'none', value: null, name: 'Без куки' };
    this.proxy = localStorage.getItem('unidownloader_proxy') || '';
    this.tasks = new Map();
    this.ws = null;
    this.theme = localStorage.getItem('unidownloader_theme') || 'dark';

    this.init();
  }

  init() {
    this.applyTheme(this.theme);
    this.bindEvents();
    this.initWebSocket();
    this.loadCookies();
    this.loadHistory();
    this.loadSystemInfo();
    this.checkUrlParams();
  }

  checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const url = params.get('url');
    if (url) {
      const urlInput = document.getElementById('url-input');
      const clearBtn = document.getElementById('btn-clear-url');
      if (urlInput) {
        urlInput.value = decodeURIComponent(url);
        clearBtn?.classList.remove('hidden');
        setTimeout(() => this.extractInfo(), 400);
      }
    }
  }

  // ==================== THEME & UI ====================

  applyTheme(theme) {
    this.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('unidownloader_theme', theme);

    const sunIcon = document.getElementById('icon-sun');
    const moonIcon = document.getElementById('icon-moon');
    if (theme === 'light') {
      sunIcon?.classList.remove('hidden');
      moonIcon?.classList.add('hidden');
    } else {
      sunIcon?.classList.add('hidden');
      moonIcon?.classList.remove('hidden');
    }
  }

  toggleTheme() {
    this.applyTheme(this.theme === 'dark' ? 'light' : 'dark');
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';

    let icon = 'info';
    let colorClass = 'text-indigo-400';
    if (type === 'success') {
      icon = 'check-circle';
      colorClass = 'text-emerald-400';
    } else if (type === 'error') {
      icon = 'alert-circle';
      colorClass = 'text-red-400';
    } else if (type === 'warning') {
      icon = 'alert-triangle';
      colorClass = 'text-amber-400';
    }

    toast.innerHTML = `
      <i data-lucide="${icon}" class="w-5 h-5 ${colorClass} shrink-0"></i>
      <span class="text-xs font-medium text-slate-200">${message}</span>
    `;

    container.appendChild(toast);
    lucide.createIcons({ root: toast });

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ==================== WEBSOCKET & TASKS ====================

  initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/tasks`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'initial_tasks') {
            data.tasks.forEach(t => this.updateTask(t));
          } else if (data.type === 'task_update') {
            this.updateTask(data.task);
          }
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };

      this.ws.onclose = () => {
        // Reconnect after 3 seconds
        setTimeout(() => this.initWebSocket(), 3000);
      };

      this.ws.onerror = () => {
        if (this.ws) this.ws.close();
      };
    } catch (e) {
      console.error('WS connection error:', e);
    }
  }

  updateTask(task) {
    this.tasks.set(task.id, task);
    this.renderTasks();

    if (task.status === 'completed') {
      this.showToast(`Скачано: ${task.title || task.filename}`, 'success');
      this.loadHistory();
    } else if (task.status === 'error') {
      this.showToast(`Ошибка загрузки: ${task.error_message || 'Сбой'}`, 'error');
    }
  }

  renderTasks() {
    const container = document.getElementById('tasks-container');
    const badge = document.getElementById('active-tasks-count');
    if (!container) return;

    const allTasks = Array.from(this.tasks.values());
    const activeTasks = allTasks.filter(t => ['queued', 'downloading', 'processing'].includes(t.status));

    if (badge) {
      badge.innerText = `${activeTasks.length} активных`;
      badge.style.display = activeTasks.length > 0 ? 'inline-block' : 'none';
    }

    if (activeTasks.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = activeTasks.map(t => {
      const pct = Math.min(Math.max(t.percent || 0, 0), 100);
      const isProcessing = t.status === 'processing' || pct >= 100;
      
      let statusText = 'В очереди...';
      let statusBadge = 'bg-slate-700 text-slate-300';
      if (t.status === 'downloading') {
        statusText = `${pct.toFixed(1)}% • ${t.speed_formatted || ''} • ост. ${t.eta_formatted || '--'}`;
        statusBadge = 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
      } else if (isProcessing) {
        statusText = 'Конвертация и объединение FFmpeg...';
        statusBadge = 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse';
      }

      return `
        <div class="glass-card p-4 space-y-3" id="task-card-${t.id}">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3 overflow-hidden">
              ${t.thumbnail ? `<img src="${t.thumbnail}" class="w-12 h-9 object-cover rounded bg-slate-800 shrink-0">` : `<div class="w-12 h-9 bg-slate-800 rounded flex items-center justify-center text-slate-500 shrink-0"><i data-lucide="download" class="w-4 h-4"></i></div>`}
              <div class="truncate">
                <h4 class="font-bold text-sm text-white truncate">${t.title || 'Скачивание медиа'}</h4>
                <span class="text-xs text-slate-400 font-mono">${t.output_format?.toUpperCase()} • ${t.quality}</span>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 rounded-full ${statusBadge} shrink-0">
              ${isProcessing ? 'Обработка' : `${pct.toFixed(1)}%`}
            </span>
          </div>

          <!-- Progress Bar -->
          <div class="space-y-1.5">
            <div class="progress-track">
              <div class="progress-fill ${isProcessing ? 'animated' : ''}" style="width: ${pct}%"></div>
            </div>
            <div class="flex justify-between text-[11px] text-slate-400">
              <span>${statusText}</span>
              <span>${t.total_bytes_formatted ? t.total_bytes_formatted : ''}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons({ root: container });
  }

  // ==================== METADATA EXTRACTION ====================

  async extractInfo() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput?.value.trim();
    if (!url) {
      this.showToast('Пожалуйста, вставьте ссылку на видео или плейлист', 'warning');
      return;
    }

    const isPlaylist = document.getElementById('chk-is-playlist')?.checked || false;
    const useCookies = document.getElementById('chk-use-cookies')?.checked || false;

    this.showLoading(true, 'Анализируем видео и доступные форматы...');
    this.hideError();
    this.hideResults();

    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          cookie_type: useCookies ? this.activeCookie.type : 'none',
          cookie_value: useCookies ? this.activeCookie.value : null,
          proxy: this.proxy || null,
          is_playlist: isPlaylist
        })
      });

      const data = await res.json();
      this.showLoading(false);

      if (!res.ok) {
        throw new Error(data.detail || 'Не удалось обработать ссылку');
      }

      this.currentMedia = data;

      if (data.is_playlist) {
        this.renderPlaylist(data);
      } else {
        this.renderMedia(data);
      }

    } catch (e) {
      this.showLoading(false);
      this.showError(e.message);
    }
  }

  renderMedia(info) {
    const section = document.getElementById('media-result-section');
    if (!section) return;

    // Overview
    document.getElementById('media-thumb').src = info.thumbnail || '';
    document.getElementById('media-title').innerText = info.title || 'Без названия';
    document.getElementById('media-author').innerText = info.uploader || 'Неизвестный автор';
    document.getElementById('media-duration').innerText = info.duration_formatted || '--:--';
    document.getElementById('media-description').innerText = info.description || '';
    document.getElementById('media-extractor-badge').innerText = info.extractor || 'Web';
    document.getElementById('media-source-link').href = info.webpage_url || '#';

    if (info.view_count) {
      document.getElementById('media-views').innerHTML = `<i data-lucide="eye" class="w-3.5 h-3.5"></i> <span>${info.view_count.toLocaleString()} просм.</span>`;
    }

    // Populate Video Formats
    const videoList = document.getElementById('video-formats-list');
    if (videoList) {
      if (!info.video_formats || info.video_formats.length === 0) {
        videoList.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">Доступен базовый MP4 видеопоток</div>`;
      } else {
        videoList.innerHTML = info.video_formats.map(f => {
          let codecBadgeClass = 'bg-slate-800 text-slate-300 border-white/10';
          if (f.codec.includes('H.264')) codecBadgeClass = 'bg-blue-500/20 text-blue-300 border-blue-500/30';
          else if (f.codec.includes('AV1')) codecBadgeClass = 'bg-purple-500/20 text-purple-300 border-purple-500/30';
          else if (f.codec.includes('VP9')) codecBadgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
          else if (f.codec.includes('HEVC') || f.codec.includes('H.265')) codecBadgeClass = 'bg-amber-500/20 text-amber-300 border-amber-500/30';

          return `
            <div class="quality-card">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center font-bold text-xs text-indigo-400 shrink-0">
                  ${f.height}p
                </div>
                <div>
                  <div class="font-bold text-white text-sm flex items-center gap-2 flex-wrap">
                    <span>${f.label}</span>
                    <span class="px-2 py-0.5 rounded text-[11px] font-semibold border ${codecBadgeClass}">${f.codec}</span>
                    ${f.fps > 30 ? `<span class="px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-bold">${f.fps} FPS</span>` : ''}
                  </div>
                  <div class="text-xs text-slate-400 mt-0.5">
                    ${f.filesize_formatted !== 'Неизвестно' ? `Размер: <span class="text-slate-200 font-semibold">${f.filesize_formatted}</span>` : 'Размер рассчитывается'} • Контейнер: ${f.ext.toUpperCase()}
                  </div>
                </div>
              </div>
              <button class="btn-secondary text-xs py-2 px-3.5 hover:border-indigo-500 hover:text-white" onclick="app.downloadVideoFormat('${f.format_id}', '${f.ext}', event)">
                <i data-lucide="download" class="w-3.5 h-3.5"></i>
                <span>Скачать</span>
              </button>
            </div>
          `;
        }).join('');
      }
    }

    // Populate Subtitles
    const subsList = document.getElementById('subtitles-list');
    const subsBadge = document.getElementById('subtitles-count-badge');
    const selectEmbedSubs = document.getElementById('select-embed-sub-lang');

    if (subsBadge) subsBadge.innerText = (info.subtitles || []).length;

    if (subsList) {
      if (!info.subtitles || info.subtitles.length === 0) {
        subsList.innerHTML = `<div class="col-span-full py-8 text-center text-slate-500 text-xs">Субтитры для этого видео не найдены</div>`;
      } else {
        subsList.innerHTML = info.subtitles.map(s => `
          <div class="quality-card">
            <div class="truncate mr-2">
              <div class="font-bold text-white text-xs truncate">${s.name}</div>
              <div class="text-[10px] text-slate-400 font-mono">${s.code.toUpperCase()} • ${s.is_auto ? 'Автоперевод' : 'Ручные'}</div>
            </div>
            <button class="btn-secondary text-xs py-1.5 px-2.5 shrink-0" onclick="app.downloadSubtitle('${s.code}', event)">
              <i data-lucide="download" class="w-3 h-3"></i>
              <span>Скачать</span>
            </button>
          </div>
        `).join('');
      }
    }

    // Populate embed subtitle options
    if (selectEmbedSubs) {
      if (info.subtitles && info.subtitles.length > 0) {
        selectEmbedSubs.innerHTML = info.subtitles.map(s => `
          <option value="${s.code}">${s.name}</option>
        `).join('');
      }
    }

    section.classList.remove('hidden');
    lucide.createIcons({ root: section });
  }

  renderPlaylist(playlist) {
    const section = document.getElementById('playlist-result-section');
    if (!section) return;

    document.getElementById('playlist-title').innerText = playlist.title || 'Плейлист';
    document.getElementById('playlist-total-count').innerText = playlist.entry_count || (playlist.entries || []).length;
    document.getElementById('playlist-uploader').innerText = playlist.uploader || 'Неизвестно';

    const container = document.getElementById('playlist-items-container');
    if (container && playlist.entries) {
      container.innerHTML = playlist.entries.map((item, idx) => `
        <div class="quality-card playlist-item-row" data-title="${item.title.toLowerCase()}">
          <div class="flex items-center gap-3 overflow-hidden">
            <input type="checkbox" class="playlist-item-checkbox rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-500 w-4 h-4" data-index="${idx}" checked>
            <span class="text-xs font-mono text-slate-500 w-5 text-center">${item.index || idx+1}</span>
            ${item.thumbnail ? `<img src="${item.thumbnail}" class="w-12 h-8 object-cover rounded bg-slate-800 shrink-0">` : ''}
            <div class="truncate">
              <div class="font-bold text-white text-xs truncate">${item.title}</div>
              <div class="text-[10px] text-slate-400">${item.duration_formatted}</div>
            </div>
          </div>
          <button class="btn-secondary text-[11px] py-1 px-2.5 shrink-0" onclick="app.downloadSingleFromPlaylist(${idx}, event)">
            <i data-lucide="download" class="w-3 h-3"></i>
          </button>
        </div>
      `).join('');
    }

    this.updatePlaylistSelectedCount();
    section.classList.remove('hidden');
    lucide.createIcons({ root: section });
  }

  updatePlaylistSelectedCount() {
    const checkboxes = document.querySelectorAll('.playlist-item-checkbox:checked');
    const badge = document.getElementById('playlist-selected-count');
    const zipBadge = document.getElementById('playlist-zip-count');
    if (badge) badge.innerText = checkboxes.length;
    if (zipBadge) zipBadge.innerText = checkboxes.length;
  }

  // ==================== DOWNLOAD DISPATCHERS ====================

  async triggerDownload({ url, title, thumbnail, download_type, quality, output_format, video_codec = 'copy', sub_lang = null, embed_subs = false, btn = null }) {
    const useCookies = document.getElementById('chk-use-cookies')?.checked || false;

    if (btn) {
      btn.disabled = true;
      const origHtml = btn.innerHTML;
      btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> <span>Добавлено...</span>`;
      lucide.createIcons({ root: btn });
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
        lucide.createIcons({ root: btn });
      }, 1500);
    }

    try {
      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url,
          title: title,
          thumbnail: thumbnail,
          download_type: download_type,
          quality: quality,
          output_format: output_format,
          video_codec: video_codec,
          sub_lang: sub_lang,
          embed_subs: embed_subs,
          cookie_type: useCookies ? this.activeCookie.type : 'none',
          cookie_value: useCookies ? this.activeCookie.value : null,
          proxy: this.proxy || null
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка запуска загрузки');

      this.showToast('Загрузка добавлена в очередь!', 'success');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  quickDownloadVideo(quality, format = 'mp4', event = null) {
    if (!this.currentMedia) return;
    const container = document.getElementById('select-video-container')?.value || format;
    const videoCodec = document.getElementById('select-video-codec')?.value || 'copy';
    const embedSubs = document.getElementById('chk-embed-subtitles')?.checked || false;
    const subLang = document.getElementById('select-embed-sub-lang')?.value || null;
    const btn = event ? event.currentTarget : null;

    this.triggerDownload({
      url: this.currentMedia.webpage_url,
      title: this.currentMedia.title,
      thumbnail: this.currentMedia.thumbnail,
      download_type: 'video',
      quality: quality,
      output_format: container,
      video_codec: videoCodec,
      sub_lang: embedSubs ? subLang : null,
      embed_subs: embedSubs,
      btn: btn
    });
  }

  downloadVideoFormat(formatId, ext, event = null) {
    if (!this.currentMedia) return;
    const container = document.getElementById('select-video-container')?.value || ext;
    const videoCodec = document.getElementById('select-video-codec')?.value || 'copy';
    const btn = event ? event.currentTarget : null;

    this.triggerDownload({
      url: this.currentMedia.webpage_url,
      title: this.currentMedia.title,
      thumbnail: this.currentMedia.thumbnail,
      download_type: 'video',
      quality: `custom_${formatId}`,
      output_format: container,
      video_codec: videoCodec,
      btn: btn
    });
  }

  quickDownloadAudio(quality = 'mp3_320', format = 'mp3', event = null) {
    if (!this.currentMedia) return;
    const btn = event ? event.currentTarget : null;
    this.triggerDownload({
      url: this.currentMedia.webpage_url,
      title: this.currentMedia.title,
      thumbnail: this.currentMedia.thumbnail,
      download_type: 'audio',
      quality: quality,
      output_format: format,
      btn: btn
    });
  }

  downloadAudio(quality, format, event = null) {
    if (!this.currentMedia) return;
    const btn = event ? event.currentTarget : null;
    this.triggerDownload({
      url: this.currentMedia.webpage_url,
      title: this.currentMedia.title,
      thumbnail: this.currentMedia.thumbnail,
      download_type: 'audio',
      quality: quality,
      output_format: format,
      btn: btn
    });
  }

  downloadSubtitle(langCode, event = null) {
    if (!this.currentMedia) return;
    const subFormat = document.getElementById('select-subtitle-format')?.value || 'srt';
    const btn = event ? event.currentTarget : null;
    this.triggerDownload({
      url: this.currentMedia.webpage_url,
      title: `${this.currentMedia.title} [${langCode.toUpperCase()}]`,
      thumbnail: this.currentMedia.thumbnail,
      download_type: 'subtitle',
      quality: 'best',
      output_format: subFormat,
      sub_lang: langCode,
      btn: btn
    });
  }

  downloadSingleFromPlaylist(index, event = null) {
    if (!this.currentMedia || !this.currentMedia.entries) return;
    const item = this.currentMedia.entries[index];
    if (!item) return;

    const downloadType = document.getElementById('select-playlist-type')?.value || 'video';
    const quality = document.getElementById('select-playlist-quality')?.value || 'best';
    const format = downloadType === 'audio' ? 'mp3' : 'mp4';
    const btn = event ? event.currentTarget : null;

    this.triggerDownload({
      url: item.url,
      title: item.title,
      thumbnail: item.thumbnail,
      download_type: downloadType,
      quality: quality,
      output_format: format,
      btn: btn
    });
  }

  async downloadSelectedPlaylist() {
    if (!this.currentMedia || !this.currentMedia.entries) return;

    const selectedCheckboxes = document.querySelectorAll('.playlist-item-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
      this.showToast('Выберите хотя бы одно видео из плейлиста', 'warning');
      return;
    }

    const downloadType = document.getElementById('select-playlist-type')?.value || 'video';
    const quality = document.getElementById('select-playlist-quality')?.value || 'best';
    const format = downloadType === 'audio' ? 'mp3' : 'mp4';
    const videoCodec = document.getElementById('select-video-codec')?.value || 'copy';
    const useCookies = document.getElementById('chk-use-cookies')?.checked || false;

    const itemsToDownload = [];
    selectedCheckboxes.forEach(cb => {
      const idx = parseInt(cb.getAttribute('data-index'));
      const item = this.currentMedia.entries[idx];
      if (item) {
        itemsToDownload.push({
          url: item.url,
          title: item.title,
          thumbnail: item.thumbnail
        });
      }
    });

    try {
      const res = await fetch('/api/batch-download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: itemsToDownload,
          download_type: downloadType,
          quality: quality,
          output_format: format,
          video_codec: videoCodec,
          cookie_type: useCookies ? this.activeCookie.type : 'none',
          cookie_value: useCookies ? this.activeCookie.value : null,
          proxy: this.proxy || null
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка пакета');

      this.showToast(`Запущена загрузка ${itemsToDownload.length} видео из плейлиста!`, 'success');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async downloadPlaylistZip(event = null) {
    if (!this.currentMedia || !this.currentMedia.entries) return;

    const selectedCheckboxes = document.querySelectorAll('.playlist-item-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
      this.showToast('Выберите хотя бы одно видео для архива', 'warning');
      return;
    }

    const btn = event ? event.currentTarget : document.getElementById('btn-download-playlist-zip');
    if (btn) {
      btn.disabled = true;
      const origHtml = btn.innerHTML;
      btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-white"></i> <span>Подготовка архива...</span>`;
      lucide.createIcons({ root: btn });
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = origHtml;
        lucide.createIcons({ root: btn });
      }, 2000);
    }

    const downloadType = document.getElementById('select-playlist-type')?.value || 'audio';
    const quality = document.getElementById('select-playlist-quality')?.value || (downloadType === 'audio' ? 'mp3_320' : 'best');
    const format = downloadType === 'audio' ? 'mp3' : 'mp4';
    const videoCodec = document.getElementById('select-video-codec')?.value || 'copy';
    const useCookies = document.getElementById('chk-use-cookies')?.checked || false;

    const itemsToDownload = [];
    selectedCheckboxes.forEach(cb => {
      const idx = parseInt(cb.getAttribute('data-index'));
      const item = this.currentMedia.entries[idx];
      if (item) {
        itemsToDownload.push({
          url: item.url,
          title: item.title,
          thumbnail: item.thumbnail
        });
      }
    });

    try {
      const res = await fetch('/api/playlist/download-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: this.currentMedia.title || 'playlist',
          items: itemsToDownload,
          download_type: downloadType,
          quality: quality,
          output_format: format,
          video_codec: videoCodec,
          cookie_type: useCookies ? this.activeCookie.type : 'none',
          cookie_value: useCookies ? this.activeCookie.value : null,
          proxy: this.proxy || null
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка запуска архивации');

      this.showToast(`Создание ZIP-архива из ${itemsToDownload.length} файлов запущено!`, 'success');
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  // ==================== HISTORY & PLAYER ====================

  async loadHistory() {
    try {
      const res = await fetch('/api/history');
      const history = await res.json();
      this.renderHistory(history);
    } catch (e) {
      console.error('History load error:', e);
    }
  }

  renderHistory(items) {
    const container = document.getElementById('history-container');
    const emptyMsg = document.getElementById('history-empty-message');
    const countBadge = document.getElementById('history-count-badge');
    if (!container) return;

    if (countBadge) {
      countBadge.innerText = items.length;
      countBadge.style.display = items.length > 0 ? 'inline-block' : 'none';
    }

    if (!items || items.length === 0) {
      container.innerHTML = '';
      if (emptyMsg) emptyMsg.classList.remove('hidden');
      return;
    }

    if (emptyMsg) emptyMsg.classList.add('hidden');

    container.innerHTML = items.map(item => {
      const isZip = item.download_type === 'zip' || (item.output_format && item.output_format.toLowerCase() === 'zip');
      return `
        <div class="quality-card ${isZip ? 'border-purple-500/30 bg-purple-950/10' : ''}" id="history-row-${item.id}">
          <div class="flex items-center gap-3 overflow-hidden">
            ${isZip ? `
              <div class="w-12 h-9 bg-purple-500/20 border border-purple-500/30 rounded flex items-center justify-center text-purple-400 shrink-0">
                <i data-lucide="archive" class="w-5 h-5"></i>
              </div>
            ` : (item.thumbnail ? `<img src="${item.thumbnail}" class="w-12 h-9 object-cover rounded bg-slate-800 shrink-0">` : `<div class="w-12 h-9 bg-slate-800 rounded flex items-center justify-center text-slate-500 shrink-0"><i data-lucide="file" class="w-4 h-4"></i></div>`)}
            <div class="truncate">
              <h4 class="font-bold text-xs text-white truncate">${item.title || item.filename}</h4>
              <div class="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                <span class="${isZip ? 'text-purple-400 font-bold px-1.5 py-0.2 bg-purple-500/20 rounded' : 'text-indigo-400 font-semibold'}">${item.output_format?.toUpperCase()}</span>
                <span>•</span>
                <span>${item.filesize_formatted}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            ${['video', 'audio'].includes(item.download_type) ? `
              <button class="btn-secondary text-xs py-1 px-2.5 text-purple-300 hover:text-white" title="Воспроизвести прямо на сайте" onclick="app.playMediaInModal('${item.id}', '${item.download_type}', '${encodeURIComponent(item.title)}')">
                <i data-lucide="play" class="w-3.5 h-3.5"></i>
                <span class="hidden sm:inline">Плеер</span>
              </button>
            ` : ''}
            <a href="/api/download-file/${item.id}" download class="${isZip ? 'btn-primary bg-gradient-to-r from-purple-600 to-pink-600 hover:brightness-110' : 'btn-primary'} text-xs py-1 px-2.5" title="Сохранить архив/файл на диск">
              <i data-lucide="${isZip ? 'archive' : 'download'}" class="w-3.5 h-3.5"></i>
              <span class="hidden sm:inline">${isZip ? 'Скачать ZIP' : 'Файл'}</span>
            </a>
            <button class="p-1.5 text-slate-500 hover:text-red-400 rounded transition-colors" title="Удалить файл" onclick="app.deleteHistoryItem('${item.id}')">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons({ root: container });
  }

  async deleteHistoryItem(id) {
    if (!confirm('Удалить этот файл с диска?')) return;
    try {
      const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        this.showToast('Файл удален', 'info');
        this.loadHistory();
      }
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  playMediaInModal(fileId, type, title) {
    const modal = document.getElementById('modal-player');
    const videoEl = document.getElementById('html5-video-player');
    const audioWrapper = document.getElementById('html5-audio-wrapper');
    const audioEl = document.getElementById('html5-audio-player');
    const titleEl = document.getElementById('player-title');

    titleEl.innerText = decodeURIComponent(title);

    const streamUrl = `/api/download-file/${fileId}?inline=true`;

    if (type === 'video') {
      audioWrapper.classList.add('hidden');
      audioEl.pause();

      videoEl.src = streamUrl;
      videoEl.classList.remove('hidden');
      videoEl.play().catch(() => {});
    } else {
      videoEl.classList.add('hidden');
      videoEl.pause();

      audioEl.src = streamUrl;
      audioWrapper.classList.remove('hidden');
      audioEl.play().catch(() => {});
    }

    modal.classList.add('active');
    lucide.createIcons({ root: modal });
  }

  closePlayerModal() {
    const modal = document.getElementById('modal-player');
    const videoEl = document.getElementById('html5-video-player');
    const audioEl = document.getElementById('html5-audio-player');

    videoEl.pause();
    videoEl.src = '';
    audioEl.pause();
    audioEl.src = '';

    modal.classList.remove('active');
  }

  // ==================== COOKIES MANAGEMENT ====================

  async loadCookies() {
    try {
      const res = await fetch('/api/cookies');
      const data = await res.json();
      this.cookieProfiles = data.profiles || [];
      this.supportedBrowsers = data.browsers || [];
      
      const isLocal = ['localhost', '127.0.0.1', '[::1]', ''].includes(window.location.hostname);
      const cachedCookie = localStorage.getItem('unidownloader_cached_cookie_text');
      const cachedName = localStorage.getItem('unidownloader_cached_cookie_name') || 'Авто-Куки';

      // 1. Для локального ПК: автоматический выбор установленного браузера
      if (isLocal && this.activeCookie.type === 'none') {
        const defaultBrowser = this.supportedBrowsers.find(b => b.id === 'chrome') || 
                               this.supportedBrowsers.find(b => b.id === 'edge') || 
                               this.supportedBrowsers[0];
        if (defaultBrowser) {
          this.activeCookie = { type: 'browser', value: defaultBrowser.id, name: defaultBrowser.name };
          this.updateActiveCookieUI();
        }
      }
      // 2. Для Railway / Cloud: авто-восстановление и синхронизация из LocalStorage браузера
      else if (!isLocal && this.cookieProfiles.length === 0 && cachedCookie) {
        try {
          const syncRes = await fetch('/api/cookies/save-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: cachedName, content: cachedCookie })
          });
          const syncData = await syncRes.json();
          if (syncData.success && syncData.profile) {
            this.cookieProfiles = [syncData.profile];
            this.activeCookie = { type: 'file', value: syncData.profile.id, name: syncData.profile.name };
            this.updateActiveCookieUI();
            this.showToast('Куки автоматически синхронизированы с сервером!', 'success');
          }
        } catch (e) {
          console.log('Cookie auto-sync skipped:', e);
        }
      }

      this.renderCookieOptions();
      this.renderCookieProfiles();
      this.updateBatchCookieDropdown();
    } catch (e) {
      console.error('Cookies load error:', e);
    }
  }

  renderCookieOptions() {
    const container = document.getElementById('browser-cookies-buttons');
    if (!container) return;

    container.innerHTML = this.supportedBrowsers.map(b => {
      const isActive = this.activeCookie.type === 'browser' && this.activeCookie.value === b.id;
      return `
        <button 
          class="btn-secondary text-xs py-2 px-3 flex items-center justify-between ${isActive ? 'border-amber-500 bg-amber-500/10 text-amber-300' : ''}" 
          onclick="app.selectBrowserCookie('${b.id}', '${b.name}')"
        >
          <div class="flex items-center gap-2 truncate">
            <i data-lucide="${b.icon || 'globe'}" class="w-3.5 h-3.5"></i>
            <span class="truncate">${b.name}</span>
          </div>
          ${isActive ? '<i data-lucide="check" class="w-3 h-3 text-amber-400 shrink-0"></i>' : ''}
        </button>
      `;
    }).join('');

    lucide.createIcons({ root: container });
  }

  renderCookieProfiles() {
    const container = document.getElementById('cookie-profiles-list');
    if (!container) return;

    if (this.cookieProfiles.length === 0) {
      container.innerHTML = `<div class="text-xs text-slate-500 p-2">Нет сохраненных профилей</div>`;
      return;
    }

    container.innerHTML = this.cookieProfiles.map(p => {
      const isActive = this.activeCookie.type === 'file' && this.activeCookie.value === p.id;
      return `
        <div class="quality-card p-2.5">
          <div class="flex items-center gap-2 truncate">
            <i data-lucide="file-check" class="w-4 h-4 text-emerald-400 shrink-0"></i>
            <span class="text-xs text-white font-medium truncate">${p.name}</span>
            <span class="text-[10px] text-slate-500">${(p.size / 1024).toFixed(1)} КБ</span>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="btn-secondary text-[11px] py-1 px-2 ${isActive ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : ''}" onclick="app.selectFileCookie('${p.id}', '${p.name}')">
              ${isActive ? '✓ Активен' : 'Использовать'}
            </button>
            <button class="p-1 text-slate-500 hover:text-red-400" onclick="app.deleteCookieProfile('${p.id}')">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons({ root: container });
  }

  updateBatchCookieDropdown() {
    const select = document.getElementById('batch-cookie-select');
    if (!select) return;

    let html = `<option value="none">Без куки</option>`;
    this.supportedBrowsers.forEach(b => {
      html += `<option value="browser:${b.id}">Браузер: ${b.name}</option>`;
    });
    this.cookieProfiles.forEach(p => {
      html += `<option value="file:${p.id}">Файл: ${p.name}</option>`;
    });

    select.innerHTML = html;
  }

  selectBrowserCookie(browserId, browserName) {
    if (this.activeCookie.type === 'browser' && this.activeCookie.value === browserId) {
      // Toggle off
      this.activeCookie = { type: 'none', value: null, name: 'Без куки' };
    } else {
      this.activeCookie = { type: 'browser', value: browserId, name: `Браузер: ${browserName}` };
      this.showToast(`Активированы куки из ${browserName}`, 'success');
    }
    this.updateActiveCookieUI();
    this.renderCookieOptions();
    this.renderCookieProfiles();
  }

  selectFileCookie(profileId, profileName) {
    if (this.activeCookie.type === 'file' && this.activeCookie.value === profileId) {
      this.activeCookie = { type: 'none', value: null, name: 'Без куки' };
    } else {
      this.activeCookie = { type: 'file', value: profileId, name: `Файл: ${profileName}` };
      this.showToast(`Активирован профиль cookies: ${profileName}`, 'success');
    }
    this.updateActiveCookieUI();
    this.renderCookieOptions();
    this.renderCookieProfiles();
  }

  updateActiveCookieUI() {
    const badge = document.getElementById('active-cookie-badge');
    const chk = document.getElementById('chk-use-cookies');
    if (this.activeCookie.type !== 'none') {
      badge.classList.remove('hidden');
      badge.classList.add('flex');
      if (chk) chk.checked = true;
    } else {
      badge.classList.add('hidden');
      badge.classList.remove('flex');
    }
  }

  async uploadCookieFile(file) {
    if (!file) return;
    const fileReader = new FileReader();
    fileReader.onload = async (e) => {
      const textContent = e.target.result;
      if (textContent) {
        localStorage.setItem('unidownloader_cached_cookie_text', textContent);
        localStorage.setItem('unidownloader_cached_cookie_name', file.name || 'cookies.txt');
      }
    };
    fileReader.readAsText(file);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name);

    try {
      const res = await fetch('/api/cookies/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка загрузки куки');

      this.showToast('Файл cookies сохранен и запомнен в браузере!', 'success');
      this.selectFileCookie(data.profile.id, data.profile.name);
      this.loadCookies();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async saveCookieText() {
    const textarea = document.getElementById('textarea-cookie-content');
    const content = textarea?.value.trim();
    if (!content) {
      this.showToast('Вставьте текст cookies в поле', 'warning');
      return;
    }

    localStorage.setItem('unidownloader_cached_cookie_text', content);
    localStorage.setItem('unidownloader_cached_cookie_name', 'Вставленные куки');

    try {
      const res = await fetch('/api/cookies/save-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'cookies_text', content: content })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка сохранения');

      this.showToast('Куки сохранены и запомнены в браузере!', 'success');
      if (textarea) textarea.value = '';
      this.selectFileCookie(data.profile.id, data.profile.name);
      this.loadCookies();
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  async deleteCookieProfile(id) {
    try {
      const res = await fetch(`/api/cookies/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (this.activeCookie.type === 'file' && this.activeCookie.value === id) {
          this.activeCookie = { type: 'none', value: null, name: 'Без куки' };
          this.updateActiveCookieUI();
        }
        this.showToast('Профиль куки удален', 'info');
        this.loadCookies();
      }
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  // ==================== BATCH DOWNLOAD ====================

  async startBatchDownload() {
    const textarea = document.getElementById('batch-urls-input');
    const rawText = textarea?.value.trim();
    if (!rawText) {
      this.showToast('Вставьте ссылки для скачивания', 'warning');
      return;
    }

    const urls = rawText.split('\n').map(u => u.trim()).filter(u => u.length > 5 && u.startsWith('http'));
    if (urls.length === 0) {
      this.showToast('Не найдено корректных URL адресов', 'error');
      return;
    }

    const typeSelection = document.getElementById('batch-type-select')?.value || 'video_1080p';
    const cookieSelection = document.getElementById('batch-cookie-select')?.value || 'none';

    let downloadType = 'video';
    let quality = '1080p';
    let outputFormat = 'mp4';

    if (typeSelection === 'video_best') {
      quality = 'best';
    } else if (typeSelection === 'audio_mp3') {
      downloadType = 'audio';
      quality = 'mp3_320';
      outputFormat = 'mp3';
    } else if (typeSelection === 'audio_m4a') {
      downloadType = 'audio';
      quality = 'm4a';
      outputFormat = 'm4a';
    }

    let cookieType = 'none';
    let cookieValue = null;
    if (cookieSelection.startsWith('browser:')) {
      cookieType = 'browser';
      cookieValue = cookieSelection.replace('browser:', '');
    } else if (cookieSelection.startsWith('file:')) {
      cookieType = 'file';
      cookieValue = cookieSelection.replace('file:', '');
    }

    const items = urls.map(u => ({ url: u, title: 'Пакетная загрузка' }));

    try {
      const res = await fetch('/api/batch-download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: items,
          download_type: downloadType,
          quality: quality,
          output_format: outputFormat,
          cookie_type: cookieType,
          cookie_value: cookieValue,
          proxy: this.proxy || null
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка запуска пакета');

      this.showToast(`Успешно запущено ${items.length} задач!`, 'success');
      this.closeModals();
      if (textarea) textarea.value = '';
    } catch (e) {
      this.showToast(e.message, 'error');
    }
  }

  // ==================== SYSTEM INFO & SETTINGS ====================

  async loadSystemInfo() {
    try {
      const res = await fetch('/api/system-info');
      const data = await res.json();

      document.getElementById('sys-ytdlp-ver').innerText = `yt-dlp v${data.ytdlp_version}`;
      document.getElementById('sys-ffmpeg-ver').innerText = data.ffmpeg_version;
      document.getElementById('sys-disk-free').innerText = `${data.disk_free} свободно (из ${data.disk_total})`;
      document.getElementById('sys-download-path').innerText = data.downloads_dir;

      const proxyInput = document.getElementById('input-proxy-url');
      if (proxyInput) proxyInput.value = this.proxy;
    } catch (e) {
      console.error('System info load error:', e);
    }
  }

  saveSettings() {
    const proxyInput = document.getElementById('input-proxy-url');
    this.proxy = proxyInput?.value.trim() || '';
    localStorage.setItem('unidownloader_proxy', this.proxy);
    this.showToast('Настройки сохранены', 'success');
    this.closeModals();
  }

  async updateYtDlp() {
    const btn = document.getElementById('btn-update-ytdlp');
    if (btn) btn.disabled = true;
    this.showToast('Обновление yt-dlp, подождите...', 'info');

    try {
      const res = await fetch('/api/update-ytdlp', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        this.showToast('yt-dlp успешно обновлен!', 'success');
        this.loadSystemInfo();
      } else {
        throw new Error(data.error || 'Ошибка обновления');
      }
    } catch (e) {
      this.showToast(e.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // ==================== MODALS & HELPERS ====================

  openCookiesModal() {
    this.closeModals();
    document.getElementById('modal-cookies')?.classList.add('active');
  }

  openBatchModal() {
    this.closeModals();
    document.getElementById('modal-batch')?.classList.add('active');
  }

  openSettingsModal() {
    this.closeModals();
    this.loadSystemInfo();
    document.getElementById('modal-settings')?.classList.add('active');
  }

  closeModals() {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('active'));
  }

  showLoading(show, text = 'Загрузка...') {
    const section = document.getElementById('loading-section');
    const textEl = document.getElementById('loading-text');
    if (!section) return;

    if (show) {
      if (textEl) textEl.innerText = text;
      section.classList.remove('hidden');
    } else {
      section.classList.add('hidden');
    }
  }

  showError(message) {
    const section = document.getElementById('error-section');
    const textEl = document.getElementById('error-message');
    const cookieHint = document.getElementById('error-cookie-hint');
    if (!section) return;

    if (textEl) textEl.innerText = message;

    if (message.includes('18+') || message.includes('Cookies') || message.includes('Sign in')) {
      if (cookieHint) cookieHint.classList.remove('hidden');
    } else {
      if (cookieHint) cookieHint.classList.add('hidden');
    }

    section.classList.remove('hidden');
  }

  hideError() {
    document.getElementById('error-section')?.classList.add('hidden');
  }

  hideResults() {
    document.getElementById('media-result-section')?.classList.add('hidden');
    document.getElementById('playlist-result-section')?.classList.add('hidden');
  }

  // ==================== EVENT LISTENERS ====================

  bindEvents() {
    // Theme toggle
    document.getElementById('btn-theme-toggle')?.addEventListener('click', () => this.toggleTheme());

    // Search input enter & buttons
    const urlInput = document.getElementById('url-input');
    const clearBtn = document.getElementById('btn-clear-url');

    urlInput?.addEventListener('input', () => {
      if (urlInput.value.length > 0) {
        clearBtn?.classList.remove('hidden');
      } else {
        clearBtn?.classList.add('hidden');
      }
    });

    urlInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.extractInfo();
    });

    clearBtn?.addEventListener('click', () => {
      if (urlInput) urlInput.value = '';
      clearBtn.classList.add('hidden');
      this.hideResults();
      this.hideError();
    });

    document.getElementById('btn-paste-url')?.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        if (text && urlInput) {
          urlInput.value = text;
          clearBtn?.classList.remove('hidden');
          this.extractInfo();
        }
      } catch (e) {
        this.showToast('Разрешите доступ к буферу обмена или вставьте вручную (Ctrl+V)', 'warning');
      }
    });

    document.getElementById('btn-extract')?.addEventListener('click', () => this.extractInfo());

    // Navigation buttons
    document.getElementById('btn-open-cookies')?.addEventListener('click', () => this.openCookiesModal());
    document.getElementById('btn-open-batch')?.addEventListener('click', () => this.openBatchModal());
    document.getElementById('btn-open-settings')?.addEventListener('click', () => this.openSettingsModal());
    document.getElementById('btn-toggle-history')?.addEventListener('click', () => {
      const historySec = document.getElementById('history-section');
      historySec?.scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('btn-refresh-history')?.addEventListener('click', () => this.loadHistory());

    // Format tabs switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const targetTab = btn.getAttribute('data-tab');
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.add('hidden'));
        document.getElementById(targetTab)?.classList.remove('hidden');
      });
    });

    // Subtitles embed checkbox toggle
    document.getElementById('chk-embed-subtitles')?.addEventListener('change', (e) => {
      const select = document.getElementById('select-embed-sub-lang');
      if (select) {
        if (e.target.checked) select.classList.remove('hidden');
        else select.classList.add('hidden');
      }
    });

    // Playlist controls
    document.getElementById('btn-playlist-select-all')?.addEventListener('click', () => {
      document.querySelectorAll('.playlist-item-checkbox').forEach(cb => cb.checked = true);
      this.updatePlaylistSelectedCount();
    });

    document.getElementById('btn-playlist-deselect-all')?.addEventListener('click', () => {
      document.querySelectorAll('.playlist-item-checkbox').forEach(cb => cb.checked = false);
      this.updatePlaylistSelectedCount();
    });

    document.addEventListener('change', (e) => {
      if (e.target.classList.contains('playlist-item-checkbox')) {
        this.updatePlaylistSelectedCount();
      }
    });

    document.getElementById('playlist-filter-input')?.addEventListener('input', (e) => {
      const term = e.target.value.toLowerCase();
      document.querySelectorAll('.playlist-item-row').forEach(row => {
        const title = row.getAttribute('data-title') || '';
        if (title.includes(term)) {
          row.style.display = 'flex';
        } else {
          row.style.display = 'none';
        }
      });
    });

    document.getElementById('btn-download-selected-playlist')?.addEventListener('click', () => this.downloadSelectedPlaylist());
    document.getElementById('btn-download-playlist-zip')?.addEventListener('click', (e) => this.downloadPlaylistZip(e));

    // Cookies modal actions
    document.getElementById('btn-save-cookie-text')?.addEventListener('click', () => this.saveCookieText());

    const dropZone = document.getElementById('drop-zone-cookie');
    const fileInput = document.getElementById('input-cookie-file');

    dropZone?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        this.uploadCookieFile(e.target.files[0]);
      }
    });

    dropZone?.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('border-indigo-500');
    });
    dropZone?.addEventListener('dragleave', () => {
      dropZone.classList.remove('border-indigo-500');
    });
    dropZone?.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('border-indigo-500');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.uploadCookieFile(e.dataTransfer.files[0]);
      }
    });

    // Batch download start
    document.getElementById('btn-start-batch')?.addEventListener('click', () => this.startBatchDownload());

    // Settings update yt-dlp
    document.getElementById('btn-update-ytdlp')?.addEventListener('click', () => this.updateYtDlp());

    // Close modals on outside click
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.closeModals();
      });
    });
  }
}

// Global App Instance
const app = new UniDownloaderApp();
