// YouTube 相場予想集計 - フロントエンド制御スクリプト

let currentData = null;
let histogramChart = null;
let categoryChart = null;

const SAMPLE_POST_URL = 'https://www.youtube.com/post/UgkxjHhnb7b_31Ry7mGWXCmVnOL--bN4czrL';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('analyzeForm');
  const postUrlInput = document.getElementById('postUrl');
  const sampleBtn = document.getElementById('samplePresetBtn');
  const applyCorrectBtn = document.getElementById('applyCorrectPriceBtn');
  const correctPriceInput = document.getElementById('correctPriceInput');
  const copyScriptBtn = document.getElementById('copyScriptBtn');
  const sortSelect = document.getElementById('commentSortSelect');

  const exportGraphBtn = document.getElementById('exportTransparentGraphBtn');
  const exportQuizCardBtn = document.getElementById('exportQuizCardBtn');
  const exportCsvBtn = document.getElementById('exportCsvBtn');

  // サンプルボタン
  if (sampleBtn && postUrlInput) {
    sampleBtn.addEventListener('click', () => {
      postUrlInput.value = SAMPLE_POST_URL;
      if (form) form.dispatchEvent(new Event('submit'));
    });
  }

  // 集計フォーム送信
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const url = postUrlInput ? postUrlInput.value.trim() : '';
      if (!url) return;
      await analyzePost(url);
    });
  }

  // 正解金額適用ボタン
  if (applyCorrectBtn && correctPriceInput) {
    applyCorrectBtn.addEventListener('click', () => {
      const val = parseFloat(correctPriceInput.value);
      if (!isNaN(val) && val > 0 && currentData) {
        recomputeQuiz(val);
      }
    });
  }

  // 台本コピー
  if (copyScriptBtn) {
    copyScriptBtn.addEventListener('click', () => {
      const textarea = document.getElementById('scriptTextArea');
      if (textarea) {
        textarea.select();
        navigator.clipboard.writeText(textarea.value);
        const originalText = copyScriptBtn.innerHTML;
        copyScriptBtn.innerHTML = '<span>✅ コピー完了!</span>';
        setTimeout(() => { copyScriptBtn.innerHTML = originalText; }, 2000);
      }
    });
  }

  // ソート変更
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      if (currentData && currentData.stats && currentData.stats.comments) {
        renderCommentsTable(currentData.stats.comments, sortSelect.value);
      }
    });
  }

  // エクスポートボタン
  if (exportGraphBtn) {
    exportGraphBtn.addEventListener('click', () => exportTransparentGraph(exportGraphBtn));
  }
  if (exportQuizCardBtn) {
    exportQuizCardBtn.addEventListener('click', () => exportQuizCard(exportQuizCardBtn));
  }
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => exportCsv());
  }
});

// 分析リクエスト
async function analyzePost(url) {
  const loading = document.getElementById('loadingSection');
  const dashboard = document.getElementById('resultDashboard');
  const errorAlert = document.getElementById('errorAlert');
  const submitBtn = document.getElementById('submitBtn');
  const btnText = document.getElementById('btnText');
  const btnSpinner = document.getElementById('btnSpinner');

  if (loading) loading.classList.remove('hidden');
  if (dashboard) dashboard.classList.add('hidden');
  if (errorAlert) errorAlert.classList.add('hidden');
  if (submitBtn) submitBtn.disabled = true;
  if (btnText) btnText.classList.add('hidden');
  if (btnSpinner) btnSpinner.classList.remove('hidden');

  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, max_comments: 500 })
    });

    if (!resp.ok) {
      const errJson = await resp.json().catch(() => ({}));
      throw new Error(errJson.detail || HTTPエラー: );
    }

    const data = await resp.json();
    if (!data.success) {
      throw new Error(data.detail || '集計に失敗しました');
    }

    currentData = data;
    renderDashboard(data);
    if (dashboard) dashboard.classList.remove('hidden');

  } catch (err) {
    console.error('Analyze error:', err);
    if (errorAlert) {
      errorAlert.textContent = 'データ取得に失敗しました: ' + (err.message || 'URLをご確認ください。');
      errorAlert.classList.remove('hidden');
    }
  } finally {
    if (loading) loading.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = false;
    if (btnText) btnText.classList.remove('hidden');
    if (btnSpinner) btnSpinner.classList.add('hidden');
  }
}

// ダッシュボード全体のレンダリング
function renderDashboard(data) {
  const meta = data.metadata || {};
  const stats = data.stats || {};
  const summary = stats.summary || {};

  // 1. メタ情報
  try {
    const authorElem = document.getElementById('metaAuthor');
    const timeElem = document.getElementById('metaTime');
    const titleElem = document.getElementById('metaTitle');
    const totalElem = document.getElementById('metaTotalComments');
    const validElem = document.getElementById('metaValidAnswers');
    const outlierElem = document.getElementById('metaOutliers');
    const imgElem = document.getElementById('metaImage');

    if (authorElem) authorElem.textContent = meta.author || 'YouTube チャンネル';
    if (timeElem) timeElem.textContent = meta.published_time || '';
    if (titleElem) titleElem.textContent = meta.title || meta.post_text || '投稿';
    if (totalElem) totalElem.textContent = (summary.total_comments || 0).toLocaleString();
    if (validElem) validElem.textContent = (summary.valid_answers_count || 0).toLocaleString();
    if (outlierElem) outlierElem.textContent = (summary.outlier_count || 0).toLocaleString();

    if (imgElem) {
      if (meta.image_url) {
        imgElem.src = meta.image_url;
        imgElem.classList.remove('hidden');
      } else {
        imgElem.classList.add('hidden');
      }
    }
  } catch (e) {
    console.warn('Meta render error:', e);
  }

  // 2. KPI
  try {
    const kpiMean = document.getElementById('kpiMean');
    const kpiMedian = document.getElementById('kpiMedian');
    const kpiMode = document.getElementById('kpiMode');
    const kpiModeCount = document.getElementById('kpiModeCount');
    const kpiMin = document.getElementById('kpiMin');
    const kpiMax = document.getElementById('kpiMax');

    if (kpiMean) kpiMean.textContent = (summary.mean_price || 0).toLocaleString();
    if (kpiMedian) kpiMedian.textContent = (summary.median_price || 0).toLocaleString();
    if (kpiMode) kpiMode.textContent = (summary.mode_price || 0).toLocaleString();
    if (kpiModeCount) kpiModeCount.textContent = (summary.mode_count || 0).toLocaleString();
    if (kpiMin) kpiMin.textContent = (summary.min_price || 0).toLocaleString();
    if (kpiMax) kpiMax.textContent = (summary.max_price || 0).toLocaleString();
  } catch (e) {
    console.warn('KPI render error:', e);
  }

  // 3. グラフ
  try {
    renderCharts(stats.histogram || [], stats.category_distribution || []);
  } catch (e) {
    console.warn('Charts render error:', e);
  }

  // 4. コメント一覧
  try {
    const sortSelect = document.getElementById('commentSortSelect');
    renderCommentsTable(stats.comments || [], sortSelect ? sortSelect.value : 'likes');
  } catch (e) {
    console.warn('Comments table render error:', e);
  }

  // 5. 正解シミュレーター
  try {
    const priceInput = document.getElementById('correctPriceInput');
    if (stats.quiz_result) {
      if (priceInput) priceInput.value = stats.quiz_result.correct_price;
      renderQuizUI(stats.quiz_result);
    } else {
      const defaultPrice = summary.median_price || summary.mean_price || 0;
      if (priceInput) priceInput.value = defaultPrice || '';
      if (defaultPrice > 0) {
        recomputeQuiz(defaultPrice);
      }
    }
  } catch (e) {
    console.warn('Quiz simulator render error:', e);
  }
}

// 正解シミュレーションの再計算
function recomputeQuiz(correctPrice) {
  if (!currentData || !currentData.stats) return;

  const comments = currentData.stats.comments || [];
  const validItems = comments.filter(c => c.has_price && !c.is_outlier);
  const meanVal = currentData.stats.summary.mean_price || 0;
  const exactMatches = [];
  const nearMatches = [];
  const nearMargin = Math.max(300, correctPrice * 0.10);

  validItems.forEach(item => {
    const p = item.price || 0;
    const diff = p - correctPrice;
    const absDiff = Math.abs(diff);
    if (absDiff === 0 || (item.is_range && item.range_low <= correctPrice && correctPrice <= item.range_high)) {
      exactMatches.push(item);
    } else if (absDiff <= nearMargin) {
      nearMatches.push({ ...item, diff, abs_diff: absDiff });
    }
  });

  nearMatches.sort((a, b) => a.abs_diff - b.abs_diff);
  const diffFromMean = correctPrice - meanVal;

  let talkGap = '';
  if (diffFromMean < -100) {
    talkGap = 視聴者の予想平均（円）より、実際は 円 安いという結果になりました！「コスパ最強」ですね！;
  } else if (diffFromMean > 100) {
    talkGap = 視聴者の予想平均（円）よりも、実際は 円 高い高級仕様でした！;
  } else {
    talkGap = 視聴者の予想平均（円）とほぼピタリ一致！視聴者の相場観が完璧でした！;
  }

  const scriptText = [
    【動画台本メモ・結果発表】,
    正解金額: 円,
    総予想回答数: 件,
    視聴者の予想平均: 円 (中央値: 円),
    最頻予想帯: 円前後 (名),
    ピタリ賞: 名,
    コメント: 
  ].join('\n');

  currentData.stats.quiz_result = {
    correct_price: correctPrice,
    exact_matches_count: exactMatches.length,
    exact_matches: exactMatches,
    near_matches_count: nearMatches.length,
    near_matches: nearMatches,
    diff_from_mean: diffFromMean,
    talk_gap: talkGap,
    script_text: scriptText
  };

  renderQuizUI(currentData.stats.quiz_result);
}

// 正解判定UI描画
function renderQuizUI(quiz) {
  if (!quiz) return;

  const exactCountElem = document.getElementById('exactCount');
  const nearCountElem = document.getElementById('nearCount');
  const diffElem = document.getElementById('gapSummary');
  const scriptArea = document.getElementById('scriptTextArea');
  const exactListElem = document.getElementById('exactList');

  if (exactCountElem) exactCountElem.textContent = quiz.exact_matches_count || 0;
  if (nearCountElem) nearCountElem.textContent = quiz.near_matches_count || 0;

  if (diffElem) {
    const diff = quiz.diff_from_mean || 0;
    if (diff > 0) {
      diffElem.textContent = + 円 (高め);
      diffElem.className = 'text-xl font-bold text-amber-600 mt-0.5';
    } else if (diff < 0) {
      diffElem.textContent = ${Math.round(diff).toLocaleString()} 円 (安め);
      diffElem.className = 'text-xl font-bold text-blue-600 mt-0.5';
    } else {
      diffElem.textContent = ±0 円 (ピタリ一致);
      diffElem.className = 'text-xl font-bold text-emerald-600 mt-0.5';
    }
  }

  if (scriptArea) {
    scriptArea.value = quiz.script_text || '';
  }

  if (exactListElem) {
    exactListElem.innerHTML = '';
    const matches = quiz.exact_matches || [];
    if (matches.length === 0) {
      exactListElem.innerHTML = '<div class="text-xs text-slate-400 py-2 col-span-2">完全一致のピタリ賞はいませんでした</div>';
    } else {
      matches.forEach(item => {
        const card = document.createElement('div');
        card.className = 'bg-white border border-slate-200 rounded-lg p-3 flex items-start space-x-3';
        const initial = (item.author || '匿').charAt(0);
        card.innerHTML = 
          <div class="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-600 text-xs flex-shrink-0">
            
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between text-xs">
              <span class="font-medium text-slate-800 truncate"></span>
              <span class="text-red-600 font-bold ml-2">円</span>
            </div>
            <p class="text-xs text-slate-600 mt-1 line-clamp-2"></p>
          </div>
        ;
        exactListElem.appendChild(card);
      });
    }
  }
}

// グラフ描画
function renderCharts(histogram, categories) {
  // 1. ヒストグラム
  const histCanvas = document.getElementById('histogramChart');
  if (histCanvas && typeof Chart !== 'undefined') {
    const histCtx = histCanvas.getContext('2d');
    if (histogramChart) histogramChart.destroy();

    const labels = (histogram || []).map(h => h.label);
    const dataCounts = (histogram || []).map(h => h.count);

    histogramChart = new Chart(histCtx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: '予想人数',
          data: dataCounts,
          backgroundColor: '#334155',
          borderRadius: 4,
          hoverBackgroundColor: '#0f172a'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ${ctx.raw} 人 (%)
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: { font: { size: 11 } }
          },
          x: {
            grid: { display: false },
            ticks: { font: { size: 10 }, maxRotation: 45 }
          }
        }
      }
    });
  }

  // 2. 円グラフ
  const catCanvas = document.getElementById('categoryChart');
  if (catCanvas && typeof Chart !== 'undefined') {
    const catCtx = catCanvas.getContext('2d');
    if (categoryChart) categoryChart.destroy();

    const catLabels = (categories || []).map(c => c.name);
    const catData = (categories || []).map(c => c.count);

    categoryChart = new Chart(catCtx, {
      type: 'doughnut',
      data: {
        labels: catLabels,
        datasets: [{
          data: catData,
          backgroundColor: ['#64748b', '#3b82f6', '#f59e0b', '#ef4444'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { font: { size: 10 }, boxWidth: 12 }
          }
        },
        cutout: '65%'
      }
    });
  }
}

// コメント一覧テーブル描画
function renderCommentsTable(comments, sortBy = 'likes') {
  const tbody = document.getElementById('commentTableBody');
  const countElem = document.getElementById('commentCount');
  if (!tbody) return;

  tbody.innerHTML = '';

  const validComments = (comments || []).filter(c => c.has_price);
  if (countElem) countElem.textContent = validComments.length;

  const sorted = [...validComments];
  if (sortBy === 'likes') {
    sorted.sort((a, b) => (b.like_count || 0) - (a.like_count || 0));
  } else if (sortBy === 'price_desc') {
    sorted.sort((a, b) => (b.price || 0) - (a.price || 0));
  } else if (sortBy === 'price_asc') {
    sorted.sort((a, b) => (a.price || 0) - (b.price || 0));
  }

  sorted.forEach(c => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-50 transition border-b border-slate-100';

    let badges = '';
    if (c.is_outlier) {
      badges += '<span class="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-[10px] ml-1">外れ値除外</span>';
    }
    if (c.is_range) {
      badges += '<span class="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px] ml-1">範囲</span>';
    }
    if (c.is_tax_excluded) {
      badges += '<span class="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded text-[10px] ml-1">税別</span>';
    }

    tr.innerHTML = 
      <td class="py-2.5 px-4 font-medium text-slate-800 whitespace-nowrap">
        
      </td>
      <td class="py-2.5 px-4 text-right font-bold text-slate-900 whitespace-nowrap">
        
        
      </td>
      <td class="py-2.5 px-4 text-slate-600 max-w-md break-words">
        
      </td>
      <td class="py-2.5 px-4 text-right text-slate-500 whitespace-nowrap">
        👍 
      </td>
    ;
    tbody.appendChild(tr);
  });
}

// 透過PNGグラフの動的生成エクスポート
async function exportTransparentGraph(btnElem) {
  if (!currentData || !currentData.stats) return;
  const summary = currentData.stats.summary || {};
  const histogram = currentData.stats.histogram || [];

  const originalText = btnElem.innerHTML;
  btnElem.innerHTML = '<span>⏳ 画像作成中...</span>';
  btnElem.disabled = true;

  // 動的コンテナ作成
  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.left = '0';
  container.style.top = '0';
  container.style.width = '1920px';
  container.style.height = '1080px';
  container.style.zIndex = '-9999';
  container.style.background = 'transparent';
  container.style.padding = '80px';
  container.style.display = 'flex';
  container.style.flexDirection = 'column';
  container.style.justifyContent = 'space-between';
  container.style.fontFamily = 'sans-serif';

  container.innerHTML = 
    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
      <div style="background: rgba(15, 23, 42, 0.90); border-radius: 16px; padding: 24px 36px; color: white; border: 1px solid rgba(255,255,255,0.15);">
        <div style="font-size: 24px; color: #94a3b8; font-weight: 500;">視聴者による相場予想分布</div>
        <div style="font-size: 40px; font-weight: 700; margin-top: 4px;">平均予想: <span style="color: #f59e0b;"></span> 円</div>
      </div>
      <div style="background: rgba(15, 23, 42, 0.90); border-radius: 16px; padding: 24px 36px; color: white; border: 1px solid rgba(255,255,255,0.15); text-align: right;">
        <div style="font-size: 20px; color: #94a3b8;">総回答数</div>
        <div style="font-size: 36px; font-weight: 700; margin-top: 4px;"> 件</div>
      </div>
    </div>
    <div style="background: rgba(15, 23, 42, 0.92); border-radius: 24px; padding: 40px; height: 600px; border: 1px solid rgba(255,255,255,0.15);">
      <canvas id="tempExportCanvas" width="1760" height="520"></canvas>
    </div>
  ;

  document.body.appendChild(container);

  try {
    const canvasElem = container.querySelector('#tempExportCanvas');
    const ctx = canvasElem.getContext('2d');

    const labels = histogram.map(h => h.label);
    const dataCounts = histogram.map(h => h.count);

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: dataCounts,
          backgroundColor: '#38bdf8',
          borderRadius: 8
        }]
      },
      options: {
        responsive: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255,255,255,0.1)' },
            ticks: { color: '#94a3b8', font: { size: 18, weight: 'bold' } }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#e2e8f0', font: { size: 18, weight: 'bold' } }
          }
        }
      }
    });

    await new Promise(r => setTimeout(r, 200));

    const renderedCanvas = await html2canvas(container, {
      backgroundColor: null,
      width: 1920,
      height: 1080,
      scale: 1,
      logging: false
    });

    const link = document.createElement('a');
    link.download = 'youtube_price_chart_1080p.png';
    link.href = renderedCanvas.toDataURL('image/png');
    link.click();

    btnElem.innerHTML = '<span>✅ 保存完了!</span>';
    setTimeout(() => {
      btnElem.innerHTML = originalText;
      btnElem.disabled = false;
    }, 2000);

  } catch (e) {
    console.error('Export graph error:', e);
    alert('画像の書き出しに失敗しました: ' + e.message);
    btnElem.innerHTML = originalText;
    btnElem.disabled = false;
  } finally {
    document.body.removeChild(container);
  }
}

// 正解発表カードの動的生成エクスポート
async function exportQuizCard(btnElem) {
  if (!currentData || !currentData.stats || !currentData.stats.quiz_result) {
    alert('先に正解金額を入力して「判定」を押してください。');
    return;
  }

  const quiz = currentData.stats.quiz_result;
  const summary = currentData.stats.summary || {};
  const diff = quiz.diff_from_mean || 0;
  const diffStr = diff >= 0 ? + 円 : ${Math.round(diff).toLocaleString()} 円;
  const diffColor = diff >= 0 ? '#38bdf8' : '#34d399';

  const originalText = btnElem.innerHTML;
  btnElem.innerHTML = '<span>⏳ 画像作成中...</span>';
  btnElem.disabled = true;

  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.left = '0';
  container.style.top = '0';
  container.style.width = '1920px';
  container.style.height = '1080px';
  container.style.zIndex = '-9999';
  container.style.background = 'transparent';
  container.style.display = 'flex';
  container.style.alignItems = 'center';
  container.style.justifyContent = 'center';
  container.style.fontFamily = 'sans-serif';

  container.innerHTML = 
    <div style="width: 1300px; background: rgba(15, 23, 42, 0.95); border-radius: 28px; padding: 60px 80px; color: white; border: 2px solid rgba(255,255,255,0.2); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8);">
      <div style="text-align: center; border-bottom: 2px solid rgba(255,255,255,0.1); padding-bottom: 30px;">
        <div style="font-size: 28px; color: #94a3b8; font-weight: 600; letter-spacing: 2px;">QUIZ RESULT</div>
        <div style="font-size: 56px; font-weight: 800; margin-top: 10px; color: #ffffff;">正解金額: <span style="color: #ef4444;"></span> 円</div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px; margin-top: 40px;">
        <div style="background: rgba(255,255,255,0.05); padding: 30px; border-radius: 16px; text-align: center;">
          <div style="font-size: 22px; color: #94a3b8;">視聴者 予想平均</div>
          <div style="font-size: 38px; font-weight: 700; margin-top: 10px; color: #fbbf24;"> 円</div>
        </div>
        <div style="background: rgba(255,255,255,0.05); padding: 30px; border-radius: 16px; text-align: center;">
          <div style="font-size: 22px; color: #94a3b8;">ピタリ賞</div>
          <div style="font-size: 38px; font-weight: 700; margin-top: 10px; color: #34d399;"> 名</div>
        </div>
        <div style="background: rgba(255,255,255,0.05); padding: 30px; border-radius: 16px; text-align: center;">
          <div style="font-size: 22px; color: #94a3b8;">差額</div>
          <div style="font-size: 38px; font-weight: 700; margin-top: 10px; color: ;"></div>
        </div>
      </div>
      <div style="margin-top: 40px; background: rgba(255,255,255,0.08); padding: 24px 32px; border-radius: 16px; font-size: 24px; color: #e2e8f0; line-height: 1.5; text-align: center; font-weight: 500;">
        
      </div>
    </div>
  ;

  document.body.appendChild(container);

  try {
    await new Promise(r => setTimeout(r, 100));

    const renderedCanvas = await html2canvas(container, {
      backgroundColor: null,
      width: 1920,
      height: 1080,
      scale: 1,
      logging: false
    });

    const link = document.createElement('a');
    link.download = 'youtube_quiz_result_card.png';
    link.href = renderedCanvas.toDataURL('image/png');
    link.click();

    btnElem.innerHTML = '<span>✅ 保存完了!</span>';
    setTimeout(() => {
      btnElem.innerHTML = originalText;
      btnElem.disabled = false;
    }, 2000);

  } catch (e) {
    console.error('Export card error:', e);
    alert('画像の書き出しに失敗しました: ' + e.message);
    btnElem.innerHTML = originalText;
    btnElem.disabled = false;
  } finally {
    document.body.removeChild(container);
  }
}

// CSVエクスポート
function exportCsv() {
  if (!currentData || !currentData.stats) return;
  const comments = currentData.stats.comments || [];

  const header = ['投稿者', '抽出予想金額', '範囲指定', '税別', '外れ値', 'いいね数', 'コメント本文'];
  const rows = comments.map(c => [
    "",
    c.price || '',
    c.is_range ? 'はい' : 'いいえ',
    c.is_tax_excluded ? 'はい' : 'いいえ',
    c.is_outlier ? 'はい' : 'いいえ',
    c.like_count || 0,
    ""
  ]);

  const csvContent = '\uFEFF' + [header.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = youtube_price_stats_.csv;
  link.click();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
