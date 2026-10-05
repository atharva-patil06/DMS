// main.js - wires the page together: Sandbox/Solver mode and Campaign mode.
// All mathematics happens on the C++ server; this file only collects input,
// sends it, and displays what comes back.
(function () {
  'use strict';

  var api = HQ.api, ui = HQ.ui, $ = ui.$;
  var canvas = new HQ.Canvas($('canvas'));
  var state = {
    view: 'sandbox',
    method: 'pairs',
    analysis: null,          // last /api/analyze reply
    practice: false,
    matrixLabels: [],
    matrix: [],
    clickPairs: [],
    level: null,             // current campaign level details
    picks: {},               // category -> array of labels
    pickCategory: null,
    tool: 'draw',
    latticeVerdict: '',
    timer: null
  };

  // Examples go through exactly the same code path as typed input.
  var EXAMPLES = [
    { name: 'Divisors of 12 (divisibility)', elements: '1, 2, 3, 4, 6, 12', method: 'rule', rule: 'divisibility' },
    { name: 'Power set of {a,b,c}', elements: 'e, a, b, c, ab, ac, bc, abc', method: 'rule', rule: 'subset' },
    { name: 'N shape (not a lattice)', elements: 'a, b, c, d', method: 'pairs', relation: '(a,c), (b,c), (b,d)', reflexive: true },
    { name: 'Two maximal elements (not a lattice)', elements: 'x, y, z', method: 'pairs', relation: 'x<=y, x<=z', reflexive: true },
    { name: 'Not transitive', elements: '1, 2, 3', method: 'pairs', relation: '(1,1), (2,2), (3,3), (1,2), (2,3)' },
    { name: 'Symmetric pair (antisymmetry fails)', elements: '1, 2, 3', method: 'pairs', relation: '(1,2), (2,1), (2,3), (1,3)', reflexive: true },
    { name: 'Cycle 1 -> 2 -> 3 -> 1', elements: '1, 2, 3', method: 'pairs', relation: '1>2; 2>3; 3>1', reflexive: true },
    { name: 'Reflexive pairs missing', elements: '1, 2, 4', method: 'pairs', relation: '(1,2), (2,4), (1,4)' },
    { name: 'Equivalence: same parity', elements: '1, 2, 3, 4', method: 'pairs', relation: '(1,3), (3,1), (2,4), (4,2)', reflexive: true },
    { name: 'Chain under <=', elements: '7, 2, 9, 4', method: 'rule', rule: 'leq' },
    { name: 'Antichain (only (a,a))', elements: 'p, q, r', method: 'pairs', relation: '', reflexive: true },
    { name: 'Matrix input: divisors of 6', elements: '1, 2, 3, 6', method: 'matrix', matrix: '1111;0101;0011;0001' },
    { name: 'Single element', elements: 'x', method: 'pairs', relation: '(x,x)' },
    { name: 'Empty set', elements: '', method: 'pairs', relation: '' }
  ];

  // ======================= Sandbox: input =======================

  function setMethod(method) {
    state.method = method;
    document.querySelectorAll('.method').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-method') === method); });
    document.querySelectorAll('.method-panel').forEach(function (p) { p.classList.toggle('hidden', p.getAttribute('data-panel') !== method); });
    if (method === 'matrix') buildMatrixGrid(false);
    if (method === 'click') placeClickNodes();
  }

  function elementLabels() {
    return $('elementsInput').value.replace(/[{},;]/g, ' ').split(/\s+/).filter(function (s) { return s.length; });
  }

  // Editable 0/1 grid for the matrix input method.
  function buildMatrixGrid(fromText, text) {
    var labels = elementLabels();
    if (!fromText || labels.join() !== state.matrixLabels.join()) {
      state.matrix = labels.map(function () { return labels.map(function () { return 0; }); });
    }
    if (fromText && text) {
      text.split(';').forEach(function (row, i) {
        for (var j = 0; j < row.length && i < labels.length && j < labels.length; j++) state.matrix[i][j] = row[j] === '1' ? 1 : 0;
      });
    }
    state.matrixLabels = labels;
    drawMatrixGrid();
  }

  function drawMatrixGrid() {
    var labels = state.matrixLabels;
    if (!labels.length) { $('matrixGrid').innerHTML = '<p class="help">Enter the elements first.</p>'; return; }
    var html = '<table><tr><th></th>' + labels.map(function (l) { return '<th>' + ui.escapeHtml(l) + '</th>'; }).join('') + '</tr>';
    labels.forEach(function (row, i) {
      html += '<tr><th>' + ui.escapeHtml(row) + '</th>';
      labels.forEach(function (col, j) {
        var on = state.matrix[i][j] === 1;
        html += '<td><button data-i="' + i + '" data-j="' + j + '" class="' + (on ? 'on' : '') + '" title="(' +
                ui.escapeHtml(row) + ',' + ui.escapeHtml(col) + ')">' + (on ? 1 : 0) + '</button></td>';
      });
      html += '</tr>';
    });
    $('matrixGrid').innerHTML = html + '</table>';
  }

  function matrixText() {
    return state.matrix.map(function (row) { return row.join(''); }).join(';');
  }

  // Click-to-build: elements on a circle; clicks add directed pairs.
  function placeClickNodes() {
    var labels = elementLabels();
    state.clickPairs = state.clickPairs.filter(function (p) { return labels.indexOf(p[0]) >= 0 && labels.indexOf(p[1]) >= 0; });
    canvas.mode = 'draw';
    canvas.showCircle(labels, state.clickPairs);
    canvas.message = labels.length ? '' : 'Enter elements, then press "Place elements on canvas".';
    canvas.onEdgesChanged = function () {
      state.clickPairs = canvas.edges.map(function (e) { return [e.a, e.b]; });
      drawClickPairs();
    };
    $('canvasTitle').textContent = 'Click-to-build: relation R';
    drawClickPairs();
    canvas.render();
  }

  function drawClickPairs() {
    $('clickPairs').innerHTML = state.clickPairs.length ? state.clickPairs.map(function (p) {
      return '<span class="pair-chip">(' + ui.escapeHtml(p[0]) + ',' + ui.escapeHtml(p[1]) + ')</span>';
    }).join('') : '<span class="help">No pairs yet.</span>';
  }

  // The form fields every poset route needs.
  function posetFields() {
    var fields = { elements: $('elementsInput').value, auto_reflexive: $('autoReflexive').checked ? '1' : '0' };
    if (state.method === 'pairs') { fields.mode = 'pairs'; fields.relation = $('relationInput').value; }
    if (state.method === 'click') {
      fields.mode = 'pairs';
      fields.relation = state.clickPairs.map(function (p) { return p[0] + '>' + p[1]; }).join(';');
    }
    if (state.method === 'matrix') {
      if (state.matrixLabels.join() !== elementLabels().join()) buildMatrixGrid(false);
      fields.mode = 'matrix'; fields.matrix = matrixText();
    }
    if (state.method === 'rule') { fields.mode = 'rule'; fields.rule = $('ruleSelect').value; }
    return fields;
  }

  // ======================= Sandbox: analysis =======================

  function analyze() {
    stopPractice();
    api.analyze(posetFields()).then(function (reply) {
      if (!reply.ok) { ui.showError(reply); return; }
      ui.hideBanner();
      state.analysis = reply;
      showAnalysis(reply);
      if (reply.notes.length) ui.banner(reply.notes.join(' '), 'info');
    });
  }

  function showAnalysis(a) {
    canvas.mode = 'move';
    canvas.onNodeClick = sandboxNodeClick;
    canvas.onEdgesChanged = null;
    if (a.isPoset) {
      $('canvasTitle').textContent = 'Hasse diagram';
      canvas.showLayered(a.elements, a.levels, a.covers);
      colourSpecialElements(a);
      if (a.elements.length === 0) canvas.clear('The empty set: nothing to draw.');
    } else {
      $('canvasTitle').textContent = 'Not a poset: relation R as a directed graph';
      var pairs = [];
      a.matrix.forEach(function (row, i) { row.forEach(function (v, j) { if (v) pairs.push([a.elements[i], a.elements[j]]); }); });
      canvas.showCircle(a.elements, pairs);
      canvas.message = 'No Hasse diagram: ' + a.failedAxiom + ' fails';
      canvas.render();
    }
    ui.renderSummary(a);
    ui.renderSteps(a.steps, a.elements, ui.latticeTablesHtml(a));
    $('boundsResult').classList.add('hidden');
  }

  // minimal = green, maximal = red, least/greatest = gold ring.
  function colourSpecialElements(a) {
    canvas.nodeClasses = {};
    a.elements.forEach(function (l) {
      var c = [];
      if (a.minimal.indexOf(l) >= 0) c.push('minimal');
      if (a.maximal.indexOf(l) >= 0) c.push('maximal');
      if (l === a.least || l === a.greatest) c.push('extreme');
      canvas.nodeClasses[l] = c;
    });
    canvas.render();
  }

  function sandboxNodeClick(label) {
    if (!$('pickSubset').checked || !state.analysis) return;
    var chosen = $('subsetInput').value.split(/[\s,]+/).filter(function (s) { return s; });
    var at = chosen.indexOf(label);
    if (at >= 0) chosen.splice(at, 1); else chosen.push(label);
    $('subsetInput').value = chosen.join(', ');
    markSubset(chosen);
  }

  function markSubset(chosen) {
    if (!state.analysis || !state.analysis.isPoset) return;
    colourSpecialElements(state.analysis);
    chosen.forEach(function (l) {
      if (canvas.nodeClasses[l]) canvas.nodeClasses[l] = canvas.nodeClasses[l].concat(['subset']);
    });
    canvas.render();
  }

  function computeBounds() {
    var fields = posetFields();
    fields.subset = $('subsetInput').value;
    api.bounds(fields).then(function (reply) {
      if (!reply.ok) { ui.showError(reply); return; }
      ui.hideBanner();
      var box = $('boundsResult');
      box.classList.remove('hidden');
      box.innerHTML = '<div class="kv"><b>S</b>' + ui.escapeHtml(ui.list(reply.subset)) + '</div>' +
        '<div class="kv"><b>Upper bounds</b>' + ui.escapeHtml(ui.list(reply.upperBounds)) + '</div>' +
        '<div class="kv"><b>Lower bounds</b>' + ui.escapeHtml(ui.list(reply.lowerBounds)) + '</div>' +
        '<div class="kv"><b>lub</b>' + ui.escapeHtml(reply.lub === null ? 'does not exist' : reply.lub) + '</div>' +
        '<div class="kv"><b>glb</b>' + ui.escapeHtml(reply.glb === null ? 'does not exist' : reply.glb) + '</div>';
      ui.renderSteps(reply.steps, state.analysis ? state.analysis.elements : []);
      markSubset(reply.subset);
    });
  }

  // ---- practice: draw the diagram yourself, judged by /api/check-hasse ----

  function startPractice() {
    if (!state.analysis || !state.analysis.isPoset) {
      ui.banner('Analyze a partial order first, then press "Start practice".', 'info');
      return;
    }
    state.practice = true;
    canvas.mode = 'draw';
    canvas.showScattered(state.analysis.elements);
    $('canvasTitle').textContent = 'Practice: draw the Hasse diagram (click two elements to join them)';
    $('checkPracticeBtn').classList.remove('hidden');
    $('practiceBtn').textContent = 'Restart practice';
  }

  function stopPractice() {
    state.practice = false;
    $('checkPracticeBtn').classList.add('hidden');
    $('practiceBtn').textContent = 'Start practice';
  }

  function edgesForServer() {
    var oriented = canvas.orientedEdges();
    if (oriented.flat.length) {
      ui.banner('Edge ' + oriented.flat[0].join('-') + ' is horizontal. Drag the larger element higher so the direction is clear.', 'info');
    }
    return oriented.pairs.map(function (p) { return p[0] + '>' + p[1]; }).join(';');
  }

  function checkPractice() {
    var fields = posetFields();
    fields.edges = edgesForServer();
    api.checkHasse(fields).then(function (reply) {
      if (!reply.ok) { ui.showError(reply); return; }
      markEdgeFeedback(reply.feedback);
      ui.banner('Accuracy ' + reply.accuracy + '% (precision ' + reply.precision + '%, recall ' + reply.recall +
                '%). ' + (reply.passed ? 'Perfect diagram!' : 'See the feedback in Show Working.'), reply.passed ? 'success' : 'info');
      var html = '<details open><summary>Feedback on your diagram</summary><div class="steps">' +
        reply.feedback.map(function (f) {
          var cls = f.kind === 'correct' ? 'OK' : (f.kind === 'missing' ? 'INFO' : 'FAIL');
          return '<div class="step ' + cls + '"><div class="step-detail">' + ui.escapeHtml(f.message) + '</div></div>';
        }).join('') + '</div></details>';
      $('working').innerHTML = html;
    });
  }

  // Wrong edges dashed red, correct edges flash green.
  function markEdgeFeedback(feedback) {
    canvas.edgeClasses = {};
    feedback.forEach(function (f) {
      if (!f.from || !f.to) return;
      var key = HQ.Canvas.edgeKey(f.from, f.to);
      if (f.kind === 'correct') canvas.edgeClasses[key] = 'correct';
      else if (f.kind !== 'missing') canvas.edgeClasses[key] = 'wrong';
    });
    canvas.render();
  }

  // ---- quick fills that ask the server for element lists ----

  function fillFromGenerator(query) {
    api.generate(query).then(function (g) {
      if (!g.ok) { ui.showError(g); return; }
      $('elementsInput').value = g.elements;
      $('autoReflexive').checked = g.autoReflexive;
      if (g.mode === 'rule') { $('ruleSelect').value = g.rule; setMethod('rule'); }
      else { $('relationInput').value = g.relation.split(';').join('; '); setMethod('pairs'); }
      ui.banner('Loaded: ' + g.title + '. Press Analyze (or edit it first).', 'success');
      analyze();
    });
  }

  function loadExample(index) {
    var ex = EXAMPLES[index];
    if (!ex) return;
    $('elementsInput').value = ex.elements;
    $('autoReflexive').checked = !!ex.reflexive;
    if (ex.method === 'rule') $('ruleSelect').value = ex.rule;
    if (ex.method === 'pairs') $('relationInput').value = ex.relation;
    setMethod(ex.method);
    if (ex.method === 'matrix') buildMatrixGrid(true, ex.matrix);
    analyze();
  }

  // ======================= Campaign =======================

  var TYPE_NAMES = { build_hasse: 'Build the Hasse', spot_elements: 'Spot the Elements', bounds: 'Bounds Challenge',
                     fix_relation: 'Fix the Relation', lattice: 'Lattice or Not?', boss: 'Boss Level' };

  function refreshLevels() {
    return api.levels().then(function (reply) {
      if (!reply.ok) { ui.showError(reply); return; }
      $('campaignTotal').textContent = reply.totalScore;
      $('campaignMax').textContent = reply.maxScore;
      $('levelList').innerHTML = reply.levels.map(function (l) {
        var cls = 'level-item' + (l.unlocked ? '' : ' locked') + (l.completed ? ' done' : '');
        return '<li class="' + cls + '" data-id="' + l.id + '" data-unlocked="' + l.unlocked + '"><span class="level-num">' +
          (l.unlocked ? l.id : '&#128274;') + '</span><span class="level-name">' + ui.escapeHtml(l.title) + '<small>' +
          TYPE_NAMES[l.type] + ' &middot; ' + l.points + ' pts' + (l.bestScore ? ' &middot; best ' + l.bestScore : '') +
          '</small></span>' + ui.stars(l.stars) + '</li>';
      }).join('');
      api.score().then(function (s) { if (s.ok) ui.renderScorePanel(reply.levels, s.history, s.totalScore, s.maxScore); });
    });
  }

  function openLevel(id) {
    api.level(id).then(function (lv) {
      if (!lv.ok) { ui.showError(lv); return; }
      ui.hideBanner();
      state.level = lv;
      state.picks = {};
      state.pickCategory = null;
      state.latticeVerdict = '';
      $('levelListView').classList.add('hidden');
      $('levelView').classList.remove('hidden');
      $('levelType').textContent = TYPE_NAMES[lv.type];
      $('levelPoints').textContent = lv.points + ' pts';
      $('levelTitle').textContent = lv.id + '. ' + lv.title;
      $('levelDescription').textContent = lv.description;
      $('levelTip').textContent = lv.tip ? 'Tip: ' + lv.tip : '';
      $('levelTip').classList.toggle('hidden', !lv.tip);
      $('hintBtn').textContent = 'Hint (-' + lv.costPercent + '%)';
      ['hintBox', 'resultBox'].forEach(function (b) { $(b).classList.add('hidden'); });
      $('feedbackList').innerHTML = '';
      showRelation(lv);
      setUpTask(lv);
      startTimer(lv);
    });
  }

  function showRelation(lv) {
    var text;
    if (lv.type === 'fix_relation') text = 'R = {' + lv.pairs.map(function (p) { return '(' + p[0] + ',' + p[1] + ')'; }).join(', ') + '}';
    else text = 'A = {' + lv.elements.join(', ') + '}<br>Pairs a &lt; b: ' +
      (lv.pairs.length ? lv.pairs.map(function (p) { return p[0] + '&le;' + p[1]; }).join(', ') : 'none') +
      '<br><span class="help">(plus every (a,a))</span>';
    if (lv.type === 'boss') text = '<b>' + ui.escapeHtml(lv.posetTitle) + '</b><br>' + text;
    if (lv.type === 'bounds') text += '<br><b>S = {' + lv.subset.join(', ') + '}</b>';
    $('levelRelation').innerHTML = text;
  }

  // ---- per-type task set-up ----

  function setUpTask(lv) {
    canvas.onNodeClick = levelNodeClick;
    canvas.onEdgesChanged = null;
    $('toolButtons').innerHTML = '';
    $('summary').innerHTML = '';
    $('working').innerHTML = '<p class="muted">Feedback for each answer appears on the left. Use the Sandbox to see full working for any poset.</p>';
    var task = $('levelTask');
    task.innerHTML = '';
    if (lv.type === 'build_hasse' || lv.type === 'boss') {
      canvas.mode = 'draw';
      canvas.showScattered(lv.elements);
      $('canvasTitle').textContent = 'Drag smaller elements lower; click two elements to join them';
      task.innerHTML = '<p class="help">Click an edge to delete it. Edge direction is read from your picture: the lower end is the smaller element.</p>' +
        '<button class="small" id="clearEdgesBtn">Clear all edges</button>';
      $('clearEdgesBtn').onclick = function () { canvas.edges = []; canvas.edgeClasses = {}; canvas.render(); };
      if (lv.type === 'boss') setUpBossTools(task);
    } else if (lv.type === 'fix_relation') {
      setUpFixTask(lv, task);
    } else {
      canvas.mode = 'pick';
      canvas.showLayered(lv.elements, lv.levels, lv.covers);
      $('canvasTitle').textContent = 'Hasse diagram';
      if (lv.type === 'bounds') lv.subset.forEach(function (l) { canvas.nodeClasses[l] = ['subset']; });
      if (lv.type === 'spot_elements') setUpPicker(task, ['minimal', 'maximal', 'least', 'greatest']);
      if (lv.type === 'bounds') setUpPicker(task, ['upper', 'lower', 'lub', 'glb']);
      if (lv.type === 'lattice') setUpLatticeTask(task);
      canvas.render();
    }
  }

  var PICK_LABELS = { minimal: 'Minimal', maximal: 'Maximal', least: 'Least', greatest: 'Greatest', upper: 'Upper bounds',
                      lower: 'Lower bounds', lub: 'lub', glb: 'glb', pair: 'Failing pair' };
  var PICK_BADGES = { minimal: 'min', maximal: 'max', least: 'least', greatest: 'greatest', upper: 'UB', lower: 'LB',
                      lub: 'lub', glb: 'glb', pair: 'pair' };
  var SINGLE = { least: 1, greatest: 1, lub: 1, glb: 1 };

  // Buttons to choose what the next node click marks.
  function setUpPicker(container, categories) {
    var html = '<div class="task-group"><b>Mark:</b><div class="pick-buttons">';
    categories.forEach(function (c) { html += '<button class="small" data-pick="' + c + '">' + PICK_LABELS[c] + '</button>'; });
    html += '</div><p class="help">Choose a category, then click elements on the diagram. Leave least/greatest/lub/glb empty for "none".</p><div id="pickSummary"></div></div>';
    var div = document.createElement('div');
    div.innerHTML = html;
    container.appendChild(div);
    categories.forEach(function (c) { state.picks[c] = state.picks[c] || []; });
    div.querySelectorAll('[data-pick]').forEach(function (b) {
      b.onclick = function () { choosePick(b.getAttribute('data-pick')); };
    });
    choosePick(categories[0]);
  }

  function choosePick(category) {
    state.pickCategory = category;
    document.querySelectorAll('[data-pick]').forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-pick') === category); });
    if (state.level && state.level.type === 'boss') { canvas.mode = 'pick'; setBossTool('mark'); }
    drawPickSummary();
  }

  function levelNodeClick(label) {
    var c = state.pickCategory;
    if (!c) return;
    var list = state.picks[c];
    var at = list.indexOf(label);
    if (at >= 0) list.splice(at, 1);
    else if (SINGLE[c]) state.picks[c] = [label];
    else if (c === 'pair' && list.length >= 2) state.picks[c] = [list[1], label];
    else list.push(label);
    drawPickSummary();
  }

  function drawPickSummary() {
    canvas.badges = {};
    var html = '';
    for (var c in state.picks) {
      if (!state.picks.hasOwnProperty(c)) continue;
      state.picks[c].forEach(function (l) { (canvas.badges[l] = canvas.badges[l] || []).push(PICK_BADGES[c]); });
      html += '<div class="pick-summary"><b>' + PICK_LABELS[c] + '</b>' +
        ui.escapeHtml(state.picks[c].length ? state.picks[c].join(', ') : (SINGLE[c] ? 'none' : '{ }')) + '</div>';
    }
    if ($('pickSummary')) $('pickSummary').innerHTML = html;
    canvas.render();
  }

  function setUpLatticeTask(task) {
    task.innerHTML = '<div class="task-group"><b>Is this poset a lattice?</b><div class="pick-buttons">' +
      '<button class="small" data-verdict="yes">Yes, it is a lattice</button>' +
      '<button class="small" data-verdict="no">No, it is not</button></div>' +
      '<p class="help" id="pairHelp">If not, click the two elements of a pair that has no lub or no glb.</p><div id="pickSummary"></div></div>';
    state.picks = { pair: [] };
    state.pickCategory = 'pair';
    task.querySelectorAll('[data-verdict]').forEach(function (b) {
      b.onclick = function () {
        state.latticeVerdict = b.getAttribute('data-verdict');
        task.querySelectorAll('[data-verdict]').forEach(function (x) { x.classList.toggle('active', x === b); });
      };
    });
    drawPickSummary();
  }

  // Boss: switch between drawing edges and marking minimal/maximal.
  function setUpBossTools(task) {
    var div = document.createElement('div');
    div.innerHTML = '<div class="task-group"><b>Tool:</b><div class="pick-buttons">' +
      '<button class="small active" data-tool="draw">Draw edges</button>' +
      '<button class="small" data-pick="minimal">Mark minimal</button>' +
      '<button class="small" data-pick="maximal">Mark maximal</button></div>' +
      '<b>Lattice?</b><div class="pick-buttons"><button class="small" data-verdict="yes">Yes</button>' +
      '<button class="small" data-verdict="no">No</button></div><div id="pickSummary"></div></div>';
    task.appendChild(div);
    state.picks = { minimal: [], maximal: [] };
    state.pickCategory = null;
    div.querySelector('[data-tool]').onclick = function () { setBossTool('draw'); };
    div.querySelectorAll('[data-pick]').forEach(function (b) { b.onclick = function () { choosePick(b.getAttribute('data-pick')); }; });
    div.querySelectorAll('[data-verdict]').forEach(function (b) {
      b.onclick = function () {
        state.latticeVerdict = b.getAttribute('data-verdict');
        div.querySelectorAll('[data-verdict]').forEach(function (x) { x.classList.toggle('active', x === b); });
      };
    });
    drawPickSummary();
  }

  function setBossTool(tool) {
    var drawBtn = document.querySelector('[data-tool="draw"]');
    if (tool === 'draw') {
      canvas.mode = 'draw';
      state.pickCategory = null;
      document.querySelectorAll('[data-pick]').forEach(function (b) { b.classList.remove('active'); });
    }
    if (drawBtn) drawBtn.classList.toggle('active', tool === 'draw');
  }

  // Fix the Relation: a matrix where original pairs are locked and the
  // player toggles pairs to add; the canvas shows R as a directed graph.
  function setUpFixTask(lv, task) {
    var labels = lv.elements;
    state.fixMatrix = lv.matrix.map(function (row) { return row.slice(); });
    task.innerHTML = '<div class="task-group"><b>Add pairs</b> (dark = already in R, green = added by you):' +
      '<div id="fixGrid" class="matrix-grid"></div></div>';
    canvas.mode = 'move';
    $('canvasTitle').textContent = 'Your relation as a directed graph';
    canvas.showCircle(labels, []);
    drawFixGrid(lv);
  }

  function drawFixGrid(lv) {
    var labels = lv.elements, pairs = [];
    var html = '<table><tr><th></th>' + labels.map(function (l) { return '<th>' + ui.escapeHtml(l) + '</th>'; }).join('') + '</tr>';
    labels.forEach(function (row, i) {
      html += '<tr><th>' + ui.escapeHtml(row) + '</th>';
      labels.forEach(function (col, j) {
        var original = lv.matrix[i][j] === 1, on = state.fixMatrix[i][j] === 1;
        if (on) pairs.push([row, col]);
        var cls = original ? 'locked' : (on ? 'added' : '');
        html += '<td><button data-i="' + i + '" data-j="' + j + '" class="' + cls + '"' + (original ? ' disabled' : '') +
                ' title="(' + ui.escapeHtml(row) + ',' + ui.escapeHtml(col) + ')">' + (on ? 1 : 0) + '</button></td>';
      });
      html += '</tr>';
    });
    $('fixGrid').innerHTML = html + '</table>';
    $('fixGrid').querySelectorAll('button[data-i]').forEach(function (b) {
      b.onclick = function () {
        var i = +b.getAttribute('data-i'), j = +b.getAttribute('data-j');
        state.fixMatrix[i][j] = 1 - state.fixMatrix[i][j];
        drawFixGrid(lv);
      };
    });
    var saved = canvas.nodes.map(function (n) { return { x: n.x, y: n.y }; });
    canvas.setEdges(pairs, true);
    canvas.nodes.forEach(function (n, k) { if (saved[k]) { n.x = saved[k].x; n.y = saved[k].y; } });
    canvas.render();
  }

  // ---- answers ----

  function pickText(c) { return c + ':' + (state.picks[c] && state.picks[c].length ? state.picks[c].join(',') : 'none'); }

  function buildAnswer(lv) {
    if (lv.type === 'build_hasse') return edgesForServer();
    if (lv.type === 'spot_elements') return ['minimal', 'maximal', 'least', 'greatest'].map(pickText).join(';');
    if (lv.type === 'bounds') return ['upper', 'lower', 'lub', 'glb'].map(pickText).join(';');
    if (lv.type === 'fix_relation') {
      var pairs = [];
      state.fixMatrix.forEach(function (row, i) { row.forEach(function (v, j) { if (v) pairs.push(lv.elements[i] + '>' + lv.elements[j]); }); });
      return pairs.join(';');
    }
    if (lv.type === 'lattice') {
      if (!state.latticeVerdict) return null;
      return 'lattice:' + state.latticeVerdict + (state.latticeVerdict === 'no' ? ';pair:' + state.picks.pair.join(',') : '');
    }
    if (!state.latticeVerdict) return null;
    return 'edges:' + edgesForServer().split(';').join(',') + ';' + pickText('minimal') + ';' + pickText('maximal') +
           ';lattice:' + state.latticeVerdict;
  }

  function submitAnswer() {
    var lv = state.level;
    var answer = buildAnswer(lv);
    if (answer === null) { ui.banner('Choose "Yes" or "No" for the lattice question first.', 'info'); return; }
    api.checkLevel(lv.id, answer).then(function (r) {
      if (!r.ok) { ui.showError(r); return; }
      ui.hideBanner();
      ui.renderFeedback(r.feedback);
      if (lv.type === 'build_hasse' || lv.type === 'boss') markEdgeFeedback(r.feedback);
      showResult(r);
      refreshLevels();
    });
  }

  function showResult(r) {
    var box = $('resultBox');
    box.classList.remove('hidden');
    box.className = 'result-box ' + (r.passed ? 'pass' : 'partial');
    var html = r.passed ? '<div class="big-stars">' + ui.stars(r.stars) + '</div><b>Level complete!</b>'
                        : '<b>Not quite: ' + r.accuracy + '% correct.</b> Read the feedback and try again.';
    html += '<div class="kv"><b>Score</b>' + r.score + (r.timeBonus ? ' (includes time bonus ' + r.timeBonus + ')' : '') +
            ' &middot; best ' + r.bestScore + '</div><div class="kv"><b>Attempts</b>' + r.attempts + '</div>';
    if (r.newlyUnlocked.length) {
      html += '<p><b>Unlocked level ' + r.newlyUnlocked.join(', ') + '!</b></p><button class="primary" id="nextLevelBtn">Next level &rarr;</button>';
    }
    box.innerHTML = html;
    if (r.passed) stopTimer();
    if ($('nextLevelBtn')) $('nextLevelBtn').onclick = function () { openLevel(r.newlyUnlocked[0]); };
  }

  function askHint() {
    api.hint(state.level.id).then(function (h) {
      if (!h.ok) { ui.showError(h); return; }
      var box = $('hintBox');
      box.classList.remove('hidden');
      box.innerHTML = (h.number ? '<b>Hint ' + h.number + '</b> (-' + h.costPercent + '% of the points): ' : '') + ui.escapeHtml(h.text);
    });
  }

  // Boss timer: runs in the browser for display; the server measures the real time.
  function startTimer(lv) {
    stopTimer();
    $('bossTimer').classList.toggle('hidden', lv.type !== 'boss');
    if (lv.type !== 'boss') return;
    var left = lv.timeLimit;
    var tick = function () {
      $('timerText').textContent = Math.floor(left / 60) + ':' + ('0' + left % 60).slice(-2);
      $('timerFill').style.width = (100 * left / lv.timeLimit) + '%';
      $('bossTimer').classList.toggle('low', left <= 30);
      if (left <= 0) { stopTimer(); $('timerText').textContent = 'Time up: no bonus'; }
      left--;
    };
    tick();
    state.timer = setInterval(tick, 1000);
  }

  function stopTimer() {
    if (state.timer) clearInterval(state.timer);
    state.timer = null;
  }

  // ======================= views and wiring =======================

  function showView(view) {
    state.view = view;
    document.querySelectorAll('.tab').forEach(function (t) { t.classList.toggle('active', t.getAttribute('data-view') === view); });
    $('sandboxControls').classList.toggle('hidden', view !== 'sandbox');
    $('campaignControls').classList.toggle('hidden', view !== 'campaign');
    ui.hideBanner();
    stopTimer();
    if (view === 'campaign') {
      $('levelView').classList.add('hidden');
      $('levelListView').classList.remove('hidden');
      canvas.clear('Pick a level on the left.');
      $('summary').innerHTML = '';
      $('canvasTitle').textContent = 'Campaign';
      $('toolButtons').innerHTML = '';
      refreshLevels();
    } else {
      $('summary').innerHTML = '';
      if (state.analysis) showAnalysis(state.analysis);
      else canvas.clear('Enter a set and a relation, or load an example, then press Analyze.');
    }
  }

  function wire() {
    document.querySelectorAll('.tab').forEach(function (t) { t.onclick = function () { showView(t.getAttribute('data-view')); }; });
    document.querySelectorAll('.side-tab').forEach(function (t) {
      t.onclick = function () {
        var side = t.getAttribute('data-side');
        document.querySelectorAll('.side-tab').forEach(function (x) { x.classList.toggle('active', x === t); });
        document.querySelectorAll('.side-panel').forEach(function (p) { p.classList.toggle('hidden', p.getAttribute('data-sidepanel') !== side); });
        if (side === 'score') refreshLevels();
      };
    });
    document.querySelectorAll('.method').forEach(function (b) { b.onclick = function () { setMethod(b.getAttribute('data-method')); }; });
    var select = $('exampleSelect');
    EXAMPLES.forEach(function (ex, i) { var o = document.createElement('option'); o.value = i; o.textContent = ex.name; select.appendChild(o); });
    select.onchange = function () { if (select.value !== '') loadExample(+select.value); };
    $('analyzeBtn').onclick = analyze;
    $('relationInput').onkeydown = function (e) { if (e.key === 'Enter' && e.ctrlKey) analyze(); };
    $('elementsInput').onkeydown = function (e) { if (e.key === 'Enter') analyze(); };
    $('makeGridBtn').onclick = function () { buildMatrixGrid(false); };
    $('matrixGrid').onclick = function (e) {
      var b = e.target.closest('button[data-i]');
      if (!b) return;
      var i = +b.getAttribute('data-i'), j = +b.getAttribute('data-j');
      state.matrix[i][j] = 1 - state.matrix[i][j];
      drawMatrixGrid();
    };
    $('placeNodesBtn').onclick = placeClickNodes;
    $('clearClickBtn').onclick = function () { state.clickPairs = []; placeClickNodes(); };
    $('divisorsBtn').onclick = function () { fillFromGenerator({ type: 'divisors', n: $('divisorsN').value }); };
    $('powersetBtn').onclick = function () { fillFromGenerator({ type: 'powerset', letters: $('powersetLetters').value }); };
    $('randomBtn').onclick = function () { fillFromGenerator({ type: $('randomType').value, size: $('randomSize').value }); };
    $('boundsBtn').onclick = computeBounds;
    $('subsetInput').oninput = function () { markSubset($('subsetInput').value.split(/[\s,]+/).filter(function (s) { return s; })); };
    $('practiceBtn').onclick = startPractice;
    $('checkPracticeBtn').onclick = checkPractice;
    $('autoLayoutBtn').onclick = function () { canvas.autoLayout(); };

    $('levelList').onclick = function (e) {
      var item = e.target.closest('.level-item');
      if (!item) return;
      if (item.getAttribute('data-unlocked') !== 'true') { ui.banner('That level is locked. Complete the previous level first.', 'info'); return; }
      openLevel(+item.getAttribute('data-id'));
    };
    $('backToLevels').onclick = function () { showView('campaign'); };
    $('submitBtn').onclick = submitAnswer;
    $('hintBtn').onclick = askHint;
    $('resetBtn').onclick = function () { api.reset().then(refreshLevels); };
    $('unlockAllBtn').onclick = function () { api.unlockAll().then(refreshLevels); };
  }

  // Optional deep links for demos and screenshots: ?example=N or ?view=campaign&level=ID
  function applyUrlOptions() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('view') === 'campaign') {
      showView('campaign');
      if (params.get('unlock') === '1') api.unlockAll().then(refreshLevels);
      if (params.get('level')) setTimeout(function () { openLevel(+params.get('level')); }, 300);
      return;
    }
    if (params.get('example') !== null) {
      $('exampleSelect').value = params.get('example');
      loadExample(+params.get('example'));
      if (params.get('side')) document.querySelector('[data-side="' + params.get('side') + '"]').click();
      return;
    }
    showView('sandbox');
  }

  wire();
  applyUrlOptions();
  refreshLevels();
})();
