// ui.js - panels: error banner, Show Working steps, summary cards, score board.
// Pure display code: everything shown here was computed by the C++ server.
var HQ = window.HQ || {};

HQ.ui = (function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  function escapeHtml(text) {
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ---------- banner ----------

  var bannerTimer = null;
  function banner(message, kind) {
    var el = $('banner');
    el.className = 'banner ' + (kind || 'error');
    el.innerHTML = '<span>' + escapeHtml(message) + '</span><button class="close" aria-label="Close">&times;</button>';
    el.querySelector('.close').onclick = hideBanner;
    clearTimeout(bannerTimer);
    if (kind === 'success') bannerTimer = setTimeout(hideBanner, 4000);
  }
  function hideBanner() { $('banner').className = 'banner hidden'; }

  // Shows a failed reply ({ok:false,error,field}) and marks the input at fault.
  var fieldIds = { elements: 'elementsInput', relation: 'relationInput', subset: 'subsetInput' };
  function showError(reply) {
    banner(reply.error || 'Something went wrong.', 'error');
    var id = fieldIds[reply.field];
    if (id && $(id)) $(id).focus();
  }

  // ---------- matrices ----------

  function matrixTable(matrix, labels, cellText) {
    var html = '<table class="matrix"><tr><th></th>';
    labels.forEach(function (l) { html += '<th>' + escapeHtml(l) + '</th>'; });
    html += '</tr>';
    for (var i = 0; i < matrix.length; i++) {
      html += '<tr><th>' + escapeHtml(labels[i]) + '</th>';
      for (var j = 0; j < matrix[i].length; j++) {
        var v = matrix[i][j];
        var text = cellText ? cellText(v) : v;
        var cls = v === 1 ? 'one' : (v === null ? 'none' : '');
        html += '<td class="' + cls + '">' + escapeHtml(text) + '</td>';
      }
      html += '</tr>';
    }
    return html + '</table>';
  }

  // ---------- Show Working ----------

  // Steps arrive as a flat list; "HEAD" steps start a new collapsible section.
  function renderSteps(steps, labels, extraHtml) {
    var html = '', open = false, sectionIndex = 0;
    steps.forEach(function (s) {
      if (s.result === 'HEAD') {
        if (open) html += '</div></details>';
        html += '<details' + (sectionIndex < 2 ? ' open' : '') + '><summary>' + escapeHtml(s.title) +
                '</summary><div class="steps">';
        open = true; sectionIndex++;
        return;
      }
      html += '<div class="step ' + s.result + '"><div class="step-title">' + escapeHtml(s.title) +
              ' <span class="tag ' + s.result + '">' + s.result + '</span></div>';
      if (s.detail) html += '<div class="step-detail">' + escapeHtml(s.detail) + '</div>';
      if (s.matrix) html += matrixTable(s.matrix, labels);
      html += '</div>';
    });
    if (open) html += '</div></details>';
    $('working').innerHTML = (extraHtml || '') + (html || '<p class="muted">No steps.</p>');
  }

  // ---------- summary cards ----------

  function list(labels) { return labels && labels.length ? '{' + labels.join(', ') + '}' : '{ }'; }

  function propertyRow(name, prop) {
    return '<div class="prop"><span class="mark ' + (prop.holds ? 'yes">&#10003;' : 'no">&#10007;') + '</span><div><b>' +
           name + '</b>' + (prop.holds ? '' : '<br><small>' + escapeHtml(prop.counterexample) + '</small>') + '</div></div>';
  }

  function verdictCard(a) {
    var title = a.isPoset ? 'This is a POSET' : 'Not a partial order';
    var body = a.isPoset ? 'Reflexive, antisymmetric and transitive.' : escapeHtml(a.reason);
    if (a.isEquivalence) body += '<br>It is an <b>equivalence relation</b>; classes: ' +
      a.equivalenceClasses.map(list).map(escapeHtml).join(' ');
    return '<div class="card ' + (a.isPoset ? 'ok' : 'fail') + ' wide"><h4>Verdict</h4><div class="verdict">' +
           title + '</div><p>' + body + '</p></div>';
  }

  function posetCards(a) {
    var lat = a.lattice;
    var html = '<div class="card"><h4>Special elements</h4>' +
      '<div class="kv"><b>Minimal</b>' + escapeHtml(list(a.minimal)) + '</div>' +
      '<div class="kv"><b>Maximal</b>' + escapeHtml(list(a.maximal)) + '</div>' +
      '<div class="kv"><b>Least</b>' + escapeHtml(a.least === null ? 'none' : a.least) + '</div>' +
      '<div class="kv"><b>Greatest</b>' + escapeHtml(a.greatest === null ? 'none' : a.greatest) + '</div></div>';
    html += '<div class="card ' + (lat.isLattice ? 'ok' : 'fail') + '"><h4>Lattice?</h4><div class="verdict">' +
      (lat.isLattice ? 'Yes, a lattice' : 'Not a lattice') + '</div><p>' +
      escapeHtml(lat.isLattice ? 'Every pair has a lub and a glb.' : lat.reason) + '</p></div>';
    html += '<div class="card"><h4>Chains</h4>' +
      '<div class="kv"><b>Height</b>' + a.height + ' &nbsp;e.g. ' + escapeHtml(a.longestChain.join(' < ') || '-') + '</div>' +
      '<div class="kv"><b>Width</b>' + a.width + ' &nbsp;e.g. ' + escapeHtml(list(a.largestAntichain)) + '</div>' +
      '<div class="kv"><b>Total order</b>' + (a.isTotalOrder ? 'yes (a chain)' : 'no') + '</div></div>';
    return html;
  }

  function renderSummary(a) {
    var html = verdictCard(a);
    html += '<div class="card"><h4>Properties</h4>' + propertyRow('Reflexive', a.properties.reflexive) +
      propertyRow('Symmetric', a.properties.symmetric) + propertyRow('Antisymmetric', a.properties.antisymmetric) +
      propertyRow('Transitive', a.properties.transitive) + '</div>';
    if (a.isPoset) html += posetCards(a);
    if (a.notes.length) {
      html += '<div class="card wide"><h4>Notes</h4><ul class="note-list">' +
        a.notes.map(function (n) { return '<li>' + escapeHtml(n) + '</li>'; }).join('') + '</ul></div>';
    }
    $('summary').innerHTML = html;
  }

  // The join/meet tables shown at the top of Show Working for a poset.
  function latticeTablesHtml(a) {
    if (!a.isPoset || a.elements.length === 0) return '';
    var show = function (v) { return v === null ? '-' : v; };
    return '<details><summary>lub (join) and glb (meet) tables</summary><div class="steps">' +
      '<p><b>a &or; b</b> (lub)</p>' + matrixTable(a.lattice.join, a.elements, show) +
      '<p><b>a &and; b</b> (glb)</p>' + matrixTable(a.lattice.meet, a.elements, show) + '</div></details>';
  }

  // ---------- campaign helpers ----------

  function stars(count) {
    var html = '<span class="stars">';
    for (var i = 1; i <= 3; i++) html += i <= count ? '&#9733;' : '<span class="off">&#9733;</span>';
    return html + '</span>';
  }

  var badKinds = { wrong: 1, redundant: 1, unrelated: 1, downward: 1, loop: 1, extra: 1 };
  function renderFeedback(feedback) {
    $('feedbackList').innerHTML = feedback.map(function (f) {
      var cls = badKinds[f.kind] ? 'bad' : f.kind;
      return '<li class="' + cls + '">' + escapeHtml(f.message) + '</li>';
    }).join('');
  }

  function renderScorePanel(levels, history, total, max) {
    var html = '<div class="score-big">' + total + ' <small class="muted">/ ' + max + '</small></div>';
    html += '<table><tr><th>Level</th><th>Stars</th><th>Best</th></tr>';
    levels.forEach(function (l) {
      html += '<tr><td>' + l.id + '. ' + escapeHtml(l.title) + '</td><td>' + stars(l.stars) + '</td><td>' + l.bestScore + '</td></tr>';
    });
    html += '</table>';
    if (history.length) {
      html += '<h3 style="margin-top:1rem">History</h3><table><tr><th>Level</th><th>Accuracy</th><th>Score</th></tr>';
      history.slice().reverse().forEach(function (h) {
        html += '<tr><td>' + escapeHtml(h.title) + '</td><td>' + h.accuracy + '%</td><td>' + h.score + '</td></tr>';
      });
      html += '</table>';
    }
    $('scorePanel').innerHTML = html;
    $('scoreChip').textContent = total;
  }

  return {
    $: $, escapeHtml: escapeHtml, banner: banner, hideBanner: hideBanner, showError: showError,
    matrixTable: matrixTable, renderSteps: renderSteps, renderSummary: renderSummary,
    latticeTablesHtml: latticeTablesHtml, stars: stars, renderFeedback: renderFeedback,
    renderScorePanel: renderScorePanel, list: list
  };
})();
