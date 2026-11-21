(function () {
  'use strict';

  var API = '/api/v1';
  var $ = function (id) { return document.getElementById(id); };

  var el = {
    title: $('title'),
    query: $('query'),
    searchBtn: $('search-btn'),
    results: $('results'),
    count: $('result-count'),
    saveBtn: $('save-btn'),
    newBtn: $('new-btn'),
    list: $('project-list'),
    listNote: $('project-list-note'),
    status: $('status'),
    error: $('error'),
    preview: $('preview'),
    previewCaption: $('preview-caption'),
    selNote: $('selection-note'),
    titleError: $('title-error'),
    queryError: $('query-error')
  };

  var state = {
    id: null,
    version: null,
    selected: null,   // {path, line} or null
    dirty: false,
    saving: false,
    epoch: 0,         // bumped whenever the working exploration is replaced
    searchSeq: 0,
    previewSeq: 0,
    listSeq: 0,
    resultsQuery: '', // query that produced the rendered results
    errorKind: null
  };

  // ---------- helpers ----------

  function api(method, url, body) {
    var opts = { method: method, headers: { 'Accept': 'application/json' } };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (resp) {
      return resp.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        return { ok: resp.ok, status: resp.status, data: data };
      });
    });
  }

  function errMessage(r, fallback) {
    if (r && r.data && r.data.error && typeof r.data.error.message === 'string') {
      return r.data.error.message;
    }
    return fallback || ('Request failed (HTTP ' + (r ? r.status : '?') + ').');
  }

  var NETWORK_MSG = 'Could not reach the server. Check that it is still running.';

  function make(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function sameSel(a, b) {
    if (!a || !b) return a === b;
    return a.path === b.path && a.line === b.line;
  }

  // ---------- status / errors ----------

  function refreshStatus() {
    var text;
    if (state.saving) text = 'Saving…';
    else if (state.dirty) text = 'Unsaved changes';
    else if (state.id) text = 'Saved (version ' + state.version + ')';
    else text = 'New exploration';
    el.status.textContent = text;
  }

  function clearFieldErrors() {
    [el.titleError, el.queryError].forEach(function (p) {
      p.textContent = '';
      p.hidden = true;
    });
    el.title.removeAttribute('aria-invalid');
    el.query.removeAttribute('aria-invalid');
  }

  function clearError() {
    el.error.textContent = '';
    el.error.hidden = true;
    state.errorKind = null;
    clearFieldErrors();
  }

  function showError(message, kind) {
    el.error.textContent = message;
    el.error.hidden = false;
    state.errorKind = kind || 'general';
  }

  function showFieldErrors(fields) {
    var map = { title: [el.title, el.titleError], query: [el.query, el.queryError] };
    var shown = false;
    Object.keys(fields || {}).forEach(function (k) {
      if (map[k]) {
        map[k][1].textContent = String(fields[k]);
        map[k][1].hidden = false;
        map[k][0].setAttribute('aria-invalid', 'true');
        shown = true;
      }
    });
    return shown;
  }

  function markDirty() {
    state.dirty = true;
    refreshStatus();
  }

  function hideSelNote() {
    el.selNote.textContent = '';
    el.selNote.hidden = true;
  }

  // ---------- hash ----------

  function hashId() {
    var m = /^#project=([0-9a-fA-F]{32})$/.exec(window.location.hash);
    return m ? m[1].toLowerCase() : null;
  }

  function setHash(id) {
    var url = window.location.pathname + window.location.search + (id ? '#project=' + id : '');
    // replaceState does not fire hashchange, so no re-entrant load.
    window.history.replaceState(null, '', url);
  }

  // ---------- results ----------

  function appendHighlighted(parent, text, q) {
    if (!q) { parent.appendChild(document.createTextNode(text)); return; }
    var pos = 0;
    var idx = text.indexOf(q, pos);
    if (idx === -1) { parent.appendChild(document.createTextNode(text)); return; }
    while (idx !== -1) {
      if (idx > pos) parent.appendChild(document.createTextNode(text.slice(pos, idx)));
      parent.appendChild(make('mark', null, q));
      pos = idx + q.length;
      idx = text.indexOf(q, pos);
    }
    if (pos < text.length) parent.appendChild(document.createTextNode(text.slice(pos)));
  }

  function resultButtons() {
    return Array.prototype.slice.call(el.results.querySelectorAll('button.result-row'));
  }

  function markSelected() {
    resultButtons().forEach(function (b) {
      var on = !!state.selected &&
        b.dataset.path === state.selected.path &&
        Number(b.dataset.line) === state.selected.line;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (on) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
  }

  function renderResults(data, q) {
    el.results.textContent = '';
    state.resultsQuery = q;
    var results = (data && Array.isArray(data.results)) ? data.results : [];
    results.forEach(function (r) {
      var li = make('li');
      var btn = make('button', 'result-row');
      btn.type = 'button';
      btn.dataset.path = r.path;
      btn.dataset.line = String(r.line);
      var loc = make('span', 'loc');
      loc.appendChild(make('span', 'path', r.path));
      loc.appendChild(make('span', 'sep', ':'));
      loc.appendChild(make('span', 'line', String(r.line)));
      var ex = make('span', 'excerpt');
      appendHighlighted(ex, r.excerpt, q);
      btn.appendChild(loc);
      btn.appendChild(ex);
      btn.setAttribute('aria-pressed', 'false');
      btn.addEventListener('click', function () {
        selectResult(r.path, r.line);
      });
      li.appendChild(btn);
      el.results.appendChild(li);
    });
    var n = results.length;
    var msg;
    if (!q) {
      msg = 'Enter a query and press Search.';
    } else {
      msg = n + (n === 1 ? ' result' : ' results') + ' for “' + q + '”';
      if (data && data.truncated) {
        msg += ' (truncated: showing the first ' + n + '; refine your query to see more)';
      }
      msg += '.';
    }
    el.count.textContent = msg;
    markSelected();
    return results;
  }

  // Returns a promise resolving to {status:'ok'|'stale'|'error', results:[...]}
  function runSearch() {
    var q = el.query.value;
    var seq = ++state.searchSeq;
    if (q === '') {
      return Promise.resolve({ status: 'ok', results: renderResults(null, '') });
    }
    el.count.textContent = 'Searching…';
    return api('GET', API + '/fixtures/search?q=' + encodeURIComponent(q)).then(function (r) {
      if (seq !== state.searchSeq) return { status: 'stale', results: [] };
      if (!r.ok || !r.data) {
        el.results.textContent = '';
        el.count.textContent = 'Search failed.';
        showError(errMessage(r, 'Search failed.'), 'search');
        return { status: 'error', results: [] };
      }
      if (state.errorKind === 'search') clearError();
      return { status: 'ok', results: renderResults(r.data, q) };
    }, function () {
      if (seq !== state.searchSeq) return { status: 'stale', results: [] };
      el.results.textContent = '';
      el.count.textContent = 'Search failed.';
      showError(NETWORK_MSG, 'search');
      return { status: 'error', results: [] };
    });
  }

  // User-initiated search: a selection that the new results do not contain is dropped,
  // so Save never stores a selection the page is not showing.
  function userSearch() {
    var epoch = state.epoch;
    return runSearch().then(function (res) {
      if (epoch !== state.epoch || res.status !== 'ok') return;
      var sel = state.selected;
      if (!sel) return;
      var found = res.results.some(function (r) { return r.path === sel.path && r.line === sel.line; });
      if (!found) {
        state.selected = null;
        hideSelNote();
        clearPreview();
        markSelected();
        markDirty();
      }
    });
  }

  function selectResult(path, line) {
    var changed = !sameSel(state.selected, { path: path, line: line });
    state.selected = { path: path, line: line };
    hideSelNote();
    markSelected();
    if (changed) markDirty();
    showPreview(path, line);
  }

  // ---------- preview ----------

  function clearPreview(message) {
    state.previewSeq++;
    el.preview.textContent = '';
    el.preview.appendChild(make('p', 'empty', message || 'Select a result to preview its file.'));
    el.previewCaption.textContent = '';
  }

  function showPreview(path, line) {
    var seq = ++state.previewSeq;
    el.previewCaption.textContent = path + ':' + line;
    return api('GET', API + '/fixtures/file?path=' + encodeURIComponent(path)).then(function (r) {
      if (seq !== state.previewSeq) return;
      el.preview.textContent = '';
      if (!r.ok || !r.data || !Array.isArray(r.data.lines)) {
        el.preview.appendChild(make('p', 'empty', errMessage(r, 'Could not load file.')));
        return;
      }
      var target = null;
      r.data.lines.forEach(function (text, i) {
        var n = i + 1;
        var row = make('div', 'line-row');
        row.appendChild(make('span', 'gutter', String(n)));
        row.appendChild(make('span', 'code', text));
        if (n === line) {
          row.className += ' hl';
          row.setAttribute('aria-current', 'true');
          target = row;
        }
        el.preview.appendChild(row);
      });
      if (target) {
        // Scroll only the preview container, not the page.
        var top = target.offsetTop - (el.preview.clientHeight - target.offsetHeight) / 2;
        el.preview.scrollTop = Math.max(0, top);
      }
    }, function () {
      if (seq !== state.previewSeq) return;
      el.preview.textContent = '';
      el.preview.appendChild(make('p', 'empty', NETWORK_MSG));
    });
  }

  // ---------- project list ----------

  function fmtDate(iso) {
    return typeof iso === 'string' ? iso.replace('T', ' ').replace(/(\.\d+)?Z$/, 'Z') : '';
  }

  function renderProjects(projects) {
    el.list.textContent = '';
    el.listNote.textContent = projects.length ? '' : 'No saved explorations yet.';
    projects.forEach(function (p) {
      var li = make('li');
      var b = make('button');
      b.type = 'button';
      b.dataset.id = p.id;
      b.appendChild(make('span', 'project-title', p.title));
      b.appendChild(make('span', 'project-meta', fmtDate(p.updated_at)));
      if (p.id === state.id) b.setAttribute('aria-current', 'true');
      b.addEventListener('click', function () { openProject(p.id); });
      li.appendChild(b);
      el.list.appendChild(li);
    });
  }

  function markListCurrent() {
    Array.prototype.forEach.call(el.list.querySelectorAll('button'), function (b) {
      if (b.dataset.id === state.id) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
  }

  function loadProjects() {
    var seq = ++state.listSeq;
    return api('GET', API + '/projects').then(function (r) {
      if (seq !== state.listSeq) return;
      if (!r.ok || !r.data || !Array.isArray(r.data.projects)) {
        el.listNote.textContent = errMessage(r, 'Could not load saved explorations.');
        return;
      }
      renderProjects(r.data.projects);
    }, function () {
      if (seq !== state.listSeq) return;
      el.listNote.textContent = NETWORK_MSG;
    });
  }

  // ---------- open / new ----------

  // Adopt a project object as the working exploration, re-run its search and
  // re-select its saved line when it is still present in the results.
  function applyProject(p) {
    var epoch = ++state.epoch;
    state.id = p.id;
    state.version = p.version;
    state.dirty = false;
    state.selected = p.selected ? { path: p.selected.path, line: p.selected.line } : null;
    el.title.value = p.title;
    el.query.value = p.query;
    clearError();
    hideSelNote();
    setHash(p.id);
    refreshStatus();
    markListCurrent();
    if (state.selected) {
      showPreview(state.selected.path, state.selected.line);
    } else {
      clearPreview();
    }
    return runSearch().then(function (res) {
      if (epoch !== state.epoch || res.status !== 'ok') return;
      var sel = state.selected;
      if (!sel) return;
      var found = res.results.some(function (r) { return r.path === sel.path && r.line === sel.line; });
      if (!found) {
        el.selNote.textContent = 'The saved selection (' + sel.path + ':' + sel.line +
          ') no longer matches the current search results.';
        el.selNote.hidden = false;
      }
    });
  }

  function openProject(id) {
    return api('GET', API + '/projects/' + encodeURIComponent(id)).then(function (r) {
      if (!r.ok || !r.data) {
        showError(r.status === 404 ? 'That exploration was not found.' : errMessage(r), 'open');
        return;
      }
      return applyProject(r.data);
    }, function () {
      showError(NETWORK_MSG, 'open');
    });
  }

  function newExploration() {
    state.epoch++;
    state.searchSeq++;
    state.id = null;
    state.version = null;
    state.selected = null;
    state.dirty = false;
    el.title.value = '';
    el.query.value = '';
    clearError();
    hideSelNote();
    setHash(null);
    renderResults(null, '');
    clearPreview();
    markListCurrent();
    refreshStatus();
    el.title.focus();
  }

  // ---------- save ----------

  function showConflict(current) {
    el.error.textContent = '';
    el.error.appendChild(document.createTextNode(
      'This exploration was changed elsewhere (conflict). Your edits were not saved.'));
    var btn = make('button', 'btn', 'Load latest');
    btn.type = 'button';
    btn.addEventListener('click', function () {
      if (current && typeof current === 'object') {
        applyProject(current);
        loadProjects();
        el.title.focus();
      } else if (state.id) {
        openProject(state.id);
      }
    });
    el.error.appendChild(btn);
    el.error.hidden = false;
    state.errorKind = 'conflict';
  }

  function save() {
    if (state.saving) return;
    clearError();
    var snap = { title: el.title.value, query: el.query.value, selected: state.selected };
    var epoch = state.epoch;
    var body = { title: snap.title, query: snap.query, selected: snap.selected };
    var req;
    if (state.id) {
      body.version = state.version;
      req = api('PUT', API + '/projects/' + encodeURIComponent(state.id), body);
    } else {
      req = api('POST', API + '/projects', body);
    }
    state.saving = true;
    refreshStatus();
    req.then(function (r) {
      state.saving = false;
      if (epoch !== state.epoch) {
        // User moved to another exploration mid-save; just refresh the list.
        refreshStatus();
        loadProjects();
        return;
      }
      if (r.ok && r.data && r.data.id) {
        var p = r.data;
        state.id = p.id;
        state.version = p.version;
        setHash(p.id);
        var unchanged = el.title.value === snap.title &&
          el.query.value === snap.query &&
          sameSel(state.selected, snap.selected);
        state.dirty = !unchanged;
        if (unchanged) el.title.value = p.title;
        refreshStatus();
        loadProjects();
        return;
      }
      refreshStatus();
      if (r.status === 409) {
        el.status.textContent = 'Conflict: not saved';
        showConflict(r.data && r.data.current);
        return;
      }
      var fields = r.data && r.data.error && r.data.error.fields;
      if (r.status === 400 && fields && showFieldErrors(fields)) {
        showError(errMessage(r, 'Please fix the highlighted fields.'), 'validation');
        return;
      }
      showError(errMessage(r), 'save');
    }, function () {
      state.saving = false;
      refreshStatus();
      showError(NETWORK_MSG, 'save');
    });
  }

  // ---------- events ----------

  el.title.addEventListener('input', markDirty);
  el.query.addEventListener('input', markDirty);

  el.searchBtn.addEventListener('click', function () { userSearch(); });
  el.query.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.isComposing) {
      e.preventDefault();
      userSearch();
    } else if (e.key === 'ArrowDown' && !e.altKey) {
      var first = resultButtons()[0];
      if (first) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  el.saveBtn.addEventListener('click', save);
  el.newBtn.addEventListener('click', newExploration);

  el.results.addEventListener('keydown', function (e) {
    var keys = { ArrowDown: 1, ArrowUp: -1, Home: 0, End: 0 };
    if (!(e.key in keys) || e.altKey || e.ctrlKey || e.metaKey) return;
    var btns = resultButtons();
    if (!btns.length) return;
    var i = btns.indexOf(document.activeElement);
    var next;
    if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = btns.length - 1;
    else next = Math.min(btns.length - 1, Math.max(0, (i === -1 ? 0 : i + keys[e.key])));
    e.preventDefault();
    btns[next].focus();
  });

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      save();
      return;
    }
    if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
      var t = e.target;
      var tag = t && t.tagName;
      var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' ||
        (t && t.isContentEditable);
      if (!typing) {
        e.preventDefault();
        el.query.focus();
        el.query.select();
      }
    }
  });

  window.addEventListener('hashchange', function () {
    var id = hashId();
    if (id && id !== state.id) openProject(id);
  });

  // ---------- init ----------

  refreshStatus();
  renderResults(null, '');
  loadProjects();
  var initial = hashId();
  if (initial) openProject(initial);
})();
