/**
 * HSN Classifier — Frontend Application
 * Handles SSE streaming, pipeline visualization, and result rendering.
 */

// ─── State ──────────────────────────────────────────────────────────────────
let isClassifying = false;
let stepStartTimes = {};
let eventSource = null;

// ─── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  setupExamples();
  setupKeyboardShortcut();
});

/** Load index stats from server */
async function loadStats() {
  try {
    const resp = await fetch('/health');
    const data = await resp.json();
    if (data.stats) {
      document.getElementById('statChunks').textContent = 
        (data.stats.total_chunks || 0).toLocaleString();
      document.getElementById('statHeadings').textContent = 
        (data.stats.total_headings || 0).toLocaleString();
      document.getElementById('statChapters').textContent = 
        (data.stats.total_chapters || 0).toLocaleString();
    }
  } catch (e) {
    console.warn('Could not load stats:', e);
  }
}

/** Wire up example chips */
function setupExamples() {
  document.querySelectorAll('.example-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.getElementById('productInput').value = chip.dataset.example;
      document.getElementById('productInput').focus();
    });
  });
}

/** Ctrl+Enter to classify */
function setupKeyboardShortcut() {
  document.getElementById('productInput').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      startClassification();
    }
  });
}

// ─── Classification Flow ────────────────────────────────────────────────────

async function startClassification() {
  const input = document.getElementById('productInput');
  const product = input.value.trim();
  
  if (!product || product.length < 3) {
    input.focus();
    input.style.borderColor = 'var(--error)';
    setTimeout(() => input.style.borderColor = '', 1500);
    return;
  }
  
  if (isClassifying) return;
  isClassifying = true;
  
  // Update UI state
  const btn = document.getElementById('classifyBtn');
  btn.classList.add('loading');
  btn.disabled = true;
  
  // Reset pipeline
  resetPipeline();
  
  // Show pipeline, hide results
  document.getElementById('pipelineSection').classList.add('active');
  document.getElementById('resultsSection').classList.remove('active');
  
  stepStartTimes = {};
  
  try {
    // Use fetch with streaming for SSE
    const response = await fetch('/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_description: product })
    });
    
    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE messages
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (dataStr === '[DONE]') continue;
          
          try {
            const event = JSON.parse(dataStr);
            handleSSEEvent(event);
          } catch (e) {
            // Ignore parse errors on heartbeats etc.
          }
        }
      }
    }
    
  } catch (error) {
    console.error('Classification error:', error);
    showError(error.message);
  } finally {
    isClassifying = false;
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

/** Handle a single SSE event */
function handleSSEEvent(event) {
  // Heartbeat
  if (event.type === 'heartbeat') return;
  
  // Final result
  if (event.type === 'complete') {
    renderResult(event.result);
    return;
  }
  
  // Error
  if (event.type === 'error') {
    showError(event.error);
    return;
  }
  
  // Progress event
  if (event.step !== undefined) {
    updatePipelineStep(event);
  }
}

// ─── Pipeline Visualization ─────────────────────────────────────────────────

function resetPipeline() {
  for (let i = 1; i <= 7; i++) {
    const step = document.getElementById(`step-${i}`);
    step.className = 'pipeline-step';
    
    const indicator = step.querySelector('.step-indicator');
    indicator.textContent = i;
    
    const detail = step.querySelector('.step-detail');
    // Reset to default text
    const defaults = [
      'Matching product to candidate chapters via routing map',
      'Searching across all indexed HS headings',
      'Gemma 4 scoring candidate relevance',
      'Loading GIR + chapter notes + heading details',
      'Applying GRI 1–6 methodology via Gemma 4',
      'Validating and calibrating result confidence',
      'Formatting formal Classification Opinion'
    ];
    detail.textContent = defaults[i - 1];
    
    // Remove data displays
    const existing = step.querySelector('.step-data');
    if (existing) existing.remove();
    
    document.getElementById(`step-${i}-time`).textContent = '';
  }
  
  document.getElementById('progressFill').style.width = '0%';
  document.getElementById('progressPct').textContent = '0%';
  document.getElementById('progressStepLabel').textContent = 'Initializing...';
}

function updatePipelineStep(event) {
  const stepNum = event.step;
  if (stepNum < 1 || stepNum > 7) return;
  
  const stepEl = document.getElementById(`step-${stepNum}`);
  if (!stepEl) return;
  
  const indicator = stepEl.querySelector('.step-indicator');
  const detail = stepEl.querySelector('.step-detail');
  
  // Track timing
  if (event.status === 'running') {
    stepStartTimes[stepNum] = Date.now();
    stepEl.className = 'pipeline-step running';
    // Scroll into view
    stepEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } else if (event.status === 'done') {
    stepEl.className = 'pipeline-step done';
    indicator.textContent = '✓';
    
    // Show elapsed time
    if (stepStartTimes[stepNum]) {
      const elapsed = ((Date.now() - stepStartTimes[stepNum]) / 1000).toFixed(1);
      document.getElementById(`step-${stepNum}-time`).textContent = `${elapsed}s`;
    }
  } else if (event.status === 'error') {
    stepEl.className = 'pipeline-step error';
    indicator.textContent = '✗';
  }
  
  // Update detail text
  if (event.detail) {
    detail.textContent = event.detail;
  }
  
  // Show step data
  if (event.data && Object.keys(event.data).length > 0 && event.status === 'done') {
    let existing = stepEl.querySelector('.step-data');
    if (!existing) {
      existing = document.createElement('div');
      existing.className = 'step-data';
      stepEl.querySelector('.step-content').appendChild(existing);
    }
    existing.textContent = formatStepData(event.data, stepNum);
  }
  
  // Update overall progress
  const pct = Math.round(event.progress_pct || 0);
  document.getElementById('progressFill').style.width = `${pct}%`;
  document.getElementById('progressPct').textContent = `${pct}%`;
  document.getElementById('progressStepLabel').textContent = 
    `Step ${stepNum}: ${event.name || ''}`;
}

function formatStepData(data, stepNum) {
  switch (stepNum) {
    case 1:
      return `Chapters: ${(data.routed_chapters || []).join(', ')}`;
    case 2:
      return (data.top_candidates || [])
        .slice(0, 5)
        .map(c => `${c.heading} (${c.title}) — score: ${c.score}`)
        .join('\n');
    case 3:
      return (data.reranked || [])
        .slice(0, 5)
        .map(r => `${r.heading} — BM25: ${r.bm25} | LLM: ${r.llm_score} | Combined: ${r.combined}`)
        .join('\n');
    case 4:
      return `Context: ${(data.context_chars || 0).toLocaleString()} chars | ` +
        `Chapters: ${(data.chapters_loaded || []).join(', ')} | ` +
        `Headings: ${(data.headings_loaded || []).join(', ')}`;
    case 5:
      return `HSN: ${data.hsn_code || '—'} | Confidence: ${data.confidence || '—'} | ` +
        `GRI Steps: ${data.gri_steps_count || 0}`;
    case 6:
      return `Confidence: ${((data.confidence || 0) * 100).toFixed(0)}% (${data.confidence_label || '—'}) | ` +
        `Valid: ${data.hsn_valid ? '✓' : '✗'} | ` +
        `Notes: ${(data.validation_notes || []).join(', ') || 'None'}`;
    default:
      return JSON.stringify(data, null, 2);
  }
}

// ─── Result Rendering ───────────────────────────────────────────────────────

function renderResult(result) {
  const section = document.getElementById('resultsSection');
  section.classList.add('active');
  
  // Smooth scroll to results
  setTimeout(() => {
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 300);
  
  // Hero card
  const hero = document.getElementById('resultHero');
  const confLevel = (result.confidence_label || 'low').toLowerCase();
  hero.className = `result-hero confidence-${confLevel}`;
  
  document.getElementById('hsnCodeDisplay').textContent = result.hsn_code || '—';
  document.getElementById('hsnDescription').textContent = result.hsn_description || '—';
  
  // Confidence badge
  const badge = document.getElementById('confidenceBadge');
  badge.className = `confidence-badge ${confLevel}`;
  document.getElementById('confidenceText').textContent = 
    `${((result.confidence || 0) * 100).toFixed(0)}% Confidence — ${result.confidence_label || 'Unknown'}`;
  
  // Meta
  document.getElementById('metaChapter').textContent = result.chapter || '—';
  document.getElementById('metaSection').textContent = result.section || '—';
  document.getElementById('metaSubheadings').textContent = 
    (result.subheadings_considered || []).length;
  
  // GRI Decision Flow
  renderGRIFlow(result.gri_steps || []);
  
  // Quotes
  renderQuotes(result.verbatim_quotes || []);
  
  // Alternatives
  renderAlternatives(result.alternative_codes || []);
  
  // Opinion
  document.getElementById('opinionText').textContent = 
    result.classification_opinion || result.reasoning_summary || '—';
}

function renderGRIFlow(steps) {
  const container = document.getElementById('griFlow');
  container.innerHTML = '';
  
  if (steps.length === 0) {
    container.innerHTML = '<div class="gri-step skipped"><span class="gri-reasoning">No GRI steps documented</span></div>';
    return;
  }
  
  steps.forEach(step => {
    const cls = step.resolved ? 'resolved' : (step.applied ? 'applied' : 'skipped');
    const icon = step.resolved ? '✅' : (step.applied ? '▶' : '—');
    
    const el = document.createElement('div');
    el.className = `gri-step ${cls}`;
    el.innerHTML = `
      <span class="gri-rule">${icon} ${escapeHtml(step.rule)}</span>
      <span class="gri-reasoning">${escapeHtml(step.reasoning || '')}</span>
    `;
    container.appendChild(el);
  });
}

function renderQuotes(quotes) {
  const container = document.getElementById('quoteList');
  container.innerHTML = '';
  
  if (quotes.length === 0) {
    container.innerHTML = '<div class="quote-item">No verbatim quotes provided</div>';
    return;
  }
  
  quotes.forEach(q => {
    const el = document.createElement('div');
    el.className = 'quote-item';
    el.textContent = q;
    container.appendChild(el);
  });
}

function renderAlternatives(alts) {
  const container = document.getElementById('altList');
  container.innerHTML = '';
  
  if (alts.length === 0) {
    container.innerHTML = '<div class="alt-item"><span class="alt-reason">No alternatives considered</span></div>';
    return;
  }
  
  alts.forEach(alt => {
    const el = document.createElement('div');
    el.className = 'alt-item';
    el.innerHTML = `
      <span class="alt-code">${escapeHtml(alt.code || '—')}</span>
      <span class="alt-reason">${escapeHtml(alt.reason || '')}</span>
    `;
    container.appendChild(el);
  });
}

// ─── Error Handling ─────────────────────────────────────────────────────────

function showError(message) {
  const section = document.getElementById('resultsSection');
  section.classList.add('active');
  
  const hero = document.getElementById('resultHero');
  hero.className = 'result-hero confidence-low';
  
  document.getElementById('hsnCodeDisplay').textContent = 'ERROR';
  document.getElementById('hsnDescription').textContent = message;
  document.getElementById('confidenceBadge').className = 'confidence-badge low';
  document.getElementById('confidenceText').textContent = 'Classification Failed';
}

// ─── Utilities ──────────────────────────────────────────────────────────────

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
