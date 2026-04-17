// ── TRẠNG THÁI (STATE) ── by Chương ─────────────────────────
let activeMission = null;   // Đối tượng bài thi hiện đang thi
let timerInterval = null;   // Khoảng thời gian đếm ngược
let currentUsername = window.currentUsername || "";

// ── CÔNG CỤ (UTILS) ── by Chương ───────────────────────────
function escH(s) { const d=document.createElement('div');d.textContent=s||'';return d.innerHTML; }

function formatDuration(ms) {
  if (ms <= 0) return '00:00:00';
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  const pad = n => String(n).padStart(2,'0');
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function toast(msg, type='success') {
  const colors = {success:'bg-success',error:'bg-danger',info:'bg-primary',warning:'bg-warning text-dark'};
  const id='t'+Date.now();
  const el=document.createElement('div');
  el.id=id; el.className=`toast show align-items-center text-white ${colors[type]||'bg-primary'} border-0`;
  el.innerHTML=`<div class="d-flex"><div class="toast-body">${escH(msg)}</div>
    <button class="btn-close btn-close-white me-2 m-auto" onclick="document.getElementById('${id}').remove()"></button></div>`;
  let c=document.querySelector('.toast-container');
  if(!c){c=document.createElement('div');c.className='toast-container position-fixed top-0 end-0 p-3 mt-5';c.style.zIndex='9998';document.body.appendChild(c);}
  c.appendChild(el); setTimeout(()=>el.remove(),5000);
}

// ── TẢI BÀI THI (LOAD MISSIONS) ── by Chương ───────────────
function sectionHeader(label, color, count) {
  return `<div class="section-heading">
    <span class="dot" style="background:${color}"></span>
    ${label} <span style="color:var(--text-muted);font-weight:400;">(${count})</span>
  </div>`;
}

async function loadMyMissions() {
  const container = document.getElementById('missionsContainer');
  try {
    const res = await fetch('/user/api/my-missions');
    const missions = await res.json();
    if (!missions.length) {
      container.innerHTML = `<div class="empty-state">
        <i class="fa-solid fa-calendar-xmark"></i>
        <h3>Chưa có bài thi nào</h3>
        <p>Giáo viên chưa giao bài thi hoặc bài tập nào cho bạn.<br>Hãy quay lại sau nhé!</p>
      </div>`;
      return;
    }

    // Phân loại theo trạng thái
    const activeGroup    = missions.filter(m => getMissionStatus(m) === 'active');
    const upcomingGroup  = missions.filter(m => getMissionStatus(m) === 'upcoming');
    const submittedGroup = missions.filter(m => getMissionStatus(m) === 'submitted');
    const endedGroup     = missions.filter(m => getMissionStatus(m) === 'ended');
    const pastAll        = [...submittedGroup, ...endedGroup];

    let html = '';
    if (activeGroup.length) {
      html += sectionHeader('🟢 Đang diễn ra', 'var(--green)', activeGroup.length);
      html += activeGroup.map(m => renderMissionCard(m)).join('');
    }
    if (upcomingGroup.length) {
      html += sectionHeader('⏰ Sắp tới', 'var(--amber)', upcomingGroup.length);
      html += upcomingGroup.map(m => renderMissionCard(m)).join('');
    }
    if (pastAll.length) {
      html += sectionHeader('✅ Đã kết thúc / Đã nộp', 'var(--text-muted)', pastAll.length);
      html += pastAll.map(m => renderMissionCard(m)).join('');
    }

    container.innerHTML = html;
    // CHỈ kích hoạt chế độ thi (countdown + auto-submit) khi user CHỦ ĐỘNG mở trang
    // KHÔNG kích hoạt nếu đang chạy từ iframe ngầm (embed mode) để tránh auto-submit ẩn
    const isEmbedded = window.location.search.includes('embed=1');
    if (activeGroup.length && !isEmbedded) startExamMode(activeGroup[0]);
  } catch(e) {
    container.innerHTML = `<div class="empty-state">
      <i class="fa-solid fa-exclamation-circle"></i>
      <h3>Lỗi tải dữ liệu</h3>
      <p>Không thể kết nối máy chủ. Vui lòng tải lại trang.</p>
    </div>`;
  }
}


function getMissionStatus(m) {
  const now = Date.now();
  const start = new Date(m.start_time).getTime();
  const end = new Date(m.end_time).getTime();
  if (m.submitted) return 'submitted';
  if (now < start) return 'upcoming';
  if (now >= start && now <= end) return 'active';
  return 'ended';
}

function renderMissionCard(m) {
  const status = getMissionStatus(m);
  const start = new Date(m.start_time);
  const end = new Date(m.end_time);
  const fmt = d => d.toLocaleString('vi-VN',{dateStyle:'short',timeStyle:'short'});

  const statusConfig = {
    active:    { badge:'<span class="badge badge-active"><span style="width:6px;height:6px;border-radius:50%;background:var(--green);display:inline-block;animation:pulse-anim 2s infinite;"></span>Đang diễn ra</span>', iconBg:'var(--green-dim)', iconColor:'var(--green)', icon:'fa-play-circle' },
    upcoming:  { badge:'<span class="badge badge-upcoming"><i class="fa-solid fa-clock"></i>Sắp diễn ra</span>',  iconBg:'var(--amber-dim)', iconColor:'var(--amber)', icon:'fa-clock' },
    ended:     { badge:'<span class="badge badge-ended"><i class="fa-solid fa-flag-checkered"></i>Đã kết thúc</span>', iconBg:'rgba(255,255,255,0.04)', iconColor:'var(--text-muted)', icon:'fa-flag-checkered' },
    submitted: { badge:'<span class="badge badge-submitted"><i class="fa-solid fa-check"></i>Đã nộp bài</span>', iconBg:'rgba(6,182,212,0.12)', iconColor:'var(--cyan)', icon:'fa-check-circle' }
  };
  const cfg = statusConfig[status];

  // Khối đếm ngược (chỉ hiển thị cho bài sắp tới/đang diễn ra)
  let countdownBlock = '';
  if (status === 'active') {
    const msLeft = end.getTime() - Date.now();
    countdownBlock = `<div class="time-blocks" id="countdown_${m.id}">
      <div class="time-block"><div class="time-val" id="cdH_${m.id}">00</div><div class="time-label">Giờ</div></div>
      <div class="time-sep">:</div>
      <div class="time-block"><div class="time-val" id="cdM_${m.id}">00</div><div class="time-label">Phút</div></div>
      <div class="time-sep">:</div>
      <div class="time-block"><div class="time-val" id="cdS_${m.id}">00</div><div class="time-label">Giây</div></div>
    </div>`;
  } else if (status === 'upcoming') {
    countdownBlock = `<p style="font-size:0.85rem;color:var(--text-secondary);margin:0.75rem 0;">
      <i class="fa-solid fa-calendar-check" style="color:var(--amber)"></i>
      Bắt đầu lúc: <strong style="color:var(--text-primary)">${fmt(start)}</strong>
      &nbsp;→&nbsp; Kết thúc: <strong style="color:var(--text-primary)">${fmt(end)}</strong>
      &nbsp;•&nbsp; Thời lượng: <strong style="color:var(--accent)">${m.duration_minutes} phút</strong>
    </p>`;
  }

  // Nút hành động
  let actionBtn = '';
  if (status === 'active' && !m.submitted) {
    actionBtn = `
      <button onclick="startMission(${m.id})" class="btn btn-primary">
        <i class="fa-solid fa-code"></i> Vào làm bài
      </button>
      <button class="btn btn-green" onclick="promptSubmit(${m.id}, '${escH(m.name)}')">
        <i class="fa-solid fa-paper-plane"></i> Nộp bài
      </button>`;
  } else if (status === 'upcoming') {
    actionBtn = `<button class="btn btn-ghost" disabled>
      <i class="fa-solid fa-lock"></i> Chưa đến giờ thi
    </button>`;
  } else if (status === 'ended' && !m.submitted) {
    actionBtn = `<button class="btn btn-ghost" disabled>
      <i class="fa-solid fa-ban"></i> Đã hết hạn
    </button>`;
  }

  // Mô tả (chuyển đổi markdown sang HTML)
  const descHTML = m.description ? (typeof marked !== 'undefined' ? marked.parse(m.description) : escH(m.description)) : '<p style="color:var(--text-muted);font-style:italic;">Không có mô tả</p>';

  // Phần kết quả
  let resultSection = '';
  if (m.submission) {
    const score = m.submission.score;
    const scoreClass = score !== null ? (score >= 8 ? 'score-high' : score >= 5 ? 'score-mid' : 'score-low') : '';
    const criteriaHTML = (m.submission.ai_criteria || []).map(c =>
      `<div class="criterion-row">
        <span class="c-name">${escH(c.name)}</span>
        <div class="c-bar"><div class="c-fill" style="width:${c.score*10}%"></div></div>
        <span class="c-score">${c.score}/10</span>
      </div>`
    ).join('');
    resultSection = `
      <div style="border-top:1px solid var(--border);padding-top:1.5rem;margin-top:1.5rem;">
        <h4 style="font-size:0.8rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:var(--text-muted);margin-bottom:1rem;">
          <i class="fa-solid fa-chart-bar"></i> Kết quả
        </h4>
        <div class="result-card">
          ${score !== null ? `
            <div class="score-display">
              <span class="score-val ${scoreClass}">${score.toFixed(1)}</span>
              <span class="score-max">/ 10</span>
            </div>
            ${criteriaHTML ? `<div class="criteria-list">${criteriaHTML}</div>` : ''}
            ${m.submission.ai_feedback ? `<div class="feedback-text">${escH(m.submission.ai_feedback)}</div>` : ''}
          ` : `
            <p style="text-align:center;color:var(--text-muted);padding:1rem 0;font-size:0.875rem;">
              <i class="fa-solid fa-hourglass-half"></i> Giáo viên đang chấm điểm...
            </p>
          `}
        </div>
      </div>`;
  }

  return `
  <div class="mission-card ${status === 'active' && !m.submitted ? 'active-exam' : ''}" id="mcard_${m.id}">
    <div class="mission-card-header">
      <div class="mission-icon" style="background:${cfg.iconBg};color:${cfg.iconColor};">
        <i class="fa-solid ${cfg.icon}"></i>
      </div>
      <div class="mission-title-block">
        <div class="mission-title">${escH(m.name)}</div>
        <div class="mission-subtitle">
          ${cfg.badge}
          <span><i class="fa-solid fa-stopwatch"></i>${m.duration_minutes} phút</span>
          <span><i class="fa-solid fa-calendar"></i>${fmt(start)} → ${fmt(end)}</span>
        </div>
      </div>
    </div>
    <div class="mission-card-body">
      ${countdownBlock}
      <div class="desc-content">${descHTML}</div>
      ${resultSection}
      ${actionBtn ? `<div class="action-area">${actionBtn}</div>` : ''}
    </div>
  </div>`;
}

// ── CHẾ ĐỘ THI (EXAM MODE) ── by Chương ────────────────────
function startExamMode(mission) {
  activeMission = mission;
  const banner = document.getElementById('examBanner');
  banner.classList.remove('hidden');
  document.getElementById('pageWrap').classList.add('has-banner');
  document.getElementById('bannerMissionName').textContent = mission.name;

  // Bắt đầu bộ đếm
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => tickTimer(mission), 1000);
  tickTimer(mission);
}

function tickTimer(mission) {
  const endTime = new Date(mission.end_time).getTime();
  const now = Date.now();
  const remaining = endTime - now;

  if (remaining <= 0) {
    clearInterval(timerInterval);
    handleTimeOut(mission);
    return;
  }

  const display = formatDuration(remaining);
  const bannerCd = document.getElementById('bannerCountdown');
  bannerCd.textContent = display;

  // Cảnh báo màu sắc
  bannerCd.classList.remove('warning','danger');
  if (remaining < 5 * 60 * 1000) bannerCd.classList.add('danger');
  else if (remaining < 15 * 60 * 1000) bannerCd.classList.add('warning');

  // Cập nhật đếm ngược trên thẻ bài tập
  if (mission) {
    const h = Math.floor(remaining / 3600000);
    const m = Math.floor((remaining % 3600000) / 60000);
    const s = Math.floor((remaining % 60000) / 1000);
    const pad = n => String(n).padStart(2,'0');
    const hEl = document.getElementById(`cdH_${mission.id}`);
    const mEl = document.getElementById(`cdM_${mission.id}`);
    const sEl = document.getElementById(`cdS_${mission.id}`);
    if (hEl) hEl.textContent = pad(h);
    if (mEl) mEl.textContent = pad(m);
    if (sEl) sEl.textContent = pad(s);
  }

  // Cập nhật thời gian còn lại trên modal nộp bài
  const stl = document.getElementById('submitTimeLeft');
  if (stl) stl.textContent = display;
}

async function handleTimeOut(mission) {
  clearInterval(timerInterval);
  // Hiển thị giao diện khóa ngay lập tức
  document.getElementById('timeoutScreen').classList.add('show');
  document.getElementById('timeoutScreen').innerHTML = `
    <i class="fa-solid fa-robot timeout-icon text-info" style="color: #0ea5e9;"></i>
    <h2 style="color: #0ea5e9;">Hết Giờ! Hệ thống đang tự động nộp bài...</h2>
    <p>Vui lòng chờ AI hoàn tất việc đánh giá Code của bạn (khoảng 30 giây).</p>
    <div class="mt-3"><i class="fa-solid fa-circle-notch fa-spin fa-2x" style="color:#555"></i></div>
  `;
  
  // Tự động nộp bài (Auto submit)
  try {
    const res = await fetch(`/user/api/missions/${mission.id}/submit`, { method: 'POST' });
    const data = await res.json();
    
    if (data.success || data.error.includes("already submitted")) {
      // Bắt đầu chờ điểm của AI Grader
      let pollCount = 0;
      const pollInterval = setInterval(async () => {
        pollCount++;
        const missionsResult = await fetch('/user/api/my-missions').then(r=>r.json()).catch(()=>[]);
        const m = missionsResult.find(x => x.id === mission.id);
        
        if ((m && m.submission && m.submission.score !== null) || pollCount >= 10) {
          clearInterval(pollInterval);
          if (m && m.submission && m.submission.score !== null) {
            document.getElementById('timeoutScreen').innerHTML = `
                <i class="fa-solid fa-graduation-cap timeout-icon" style="color: #22c55e;"></i>
                <h2 style="color: #22c55e;">Hoàn Tất! Điểm: ${m.submission.score.toFixed(1)}/10</h2>
                <p>Nộp bài thành công. Chúc mừng bạn đã hoàn thành bài thi!</p>
                <div style="margin-top: 30px;">
                    <button class="btn btn-primary" style="padding: 10px 20px; font-weight: bold; font-size: 1rem;" onclick="window.location.reload()">Đóng và Xem chi tiết</button>
                </div>
            `;
          } else {
             document.getElementById('timeoutScreen').innerHTML = `
                <i class="fa-solid fa-triangle-exclamation timeout-icon" style="color: #f59e0b;"></i>
                <h2 style="color: #f59e0b;">Đã gửi File thành công</h2>
                <p>Hệ thống AI xử lý chậm. Vui lòng quay lại sau để xem điểm.</p>
                <div style="margin-top: 30px;">
                    <button class="btn btn-primary" onclick="window.location.reload()">Trở về màn hình chờ</button>
                </div>
            `;
          }
        }
      }, 5000);
    }
  } catch(e) {
      document.getElementById('timeoutScreen').innerHTML = `
        <i class="fa-solid fa-bug timeout-icon" style="color: #ef4444;"></i>
        <h2 style="color: #ef4444;">Lỗi kết nối khi Submit</h2>
        <div style="margin-top: 30px;">
            <button class="btn btn-primary" onclick="window.location.reload()">Tải lại trang</button>
        </div>
    `;
  }
}

// ── BẮT ĐẦU BÀI THI (START MISSION) ── by Chương ───────────
async function startMission(missionId) {
  try {
    toast('🚀 Đang khởi tạo môi trường bài thi...', 'info');
    const res = await fetch(`/user/api/missions/${missionId}/start`, { method: 'POST' });
    const data = await res.json();
    
    if (data.success) {
      // Mở workspace trong tab mới
      window.open(`/user/${currentUsername}/workspace`, '_blank');
      toast('✅ Khởi tạo thành công! Chúc bạn làm bài tốt.', 'success');
    } else {
      toast(data.error || 'Lỗi khởi tạo bài thi', 'error');
    }
  } catch (e) {
    toast('Lỗi kết nối máy chủ khi bắt đầu bài thi.', 'error');
  }
}

// ── NỘP BÀI (SUBMIT) ── by Chương ──────────────────────────
let submitMissionId = null;
let submitMissionName = '';

async function promptSubmit(missionId, missionName) {
  submitMissionId = missionId || (activeMission ? activeMission.id : null);
  submitMissionName = missionName || (activeMission ? activeMission.name : '');
  document.getElementById('submitMissionName').textContent = submitMissionName;
  if (activeMission) {
    const rem = new Date(activeMission.end_time).getTime() - Date.now();
    document.getElementById('submitTimeLeft').textContent = formatDuration(rem);
  }
  // Tải xem trước danh sách file (File preview)
  const fileListEl = document.getElementById('submitFileList');
  fileListEl.innerHTML = '<p style="font-size:0.8rem;color:var(--text-muted);"><i class="fa-solid fa-circle-notch fa-spin"></i> Đang đọc danh sách file...</p>';
  document.getElementById('submitModal').classList.add('open');

  try {
    const res = await fetch('/user/api/preview-files');
    const data = await res.json();
    if (data.success && data.files.length > 0) {
      fileListEl.innerHTML = `
        <p style="font-size:0.78rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem;"><i class="fa-solid fa-file-code"></i> File sẽ được nộp (${data.files.length} file)</p>
        <div style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-sm);padding:.5rem;max-height:150px;overflow-y:auto;">
          ${data.files.map(f => `<div style="display:flex;justify-content:space-between;align-items:center;padding:.3rem .5rem;font-size:.82rem;font-family:var(--mono);"><span style="color:var(--cyan);">${escH(f.path)}</span><span style="color:var(--text-muted);font-size:.75rem;">${(f.size/1024).toFixed(1)}KB</span></div>`).join('')}
        </div>`;
    } else if (data.success) {
      fileListEl.innerHTML = '<p style="font-size:0.82rem;color:var(--amber);"><i class="fa-solid fa-triangle-exclamation"></i> Không tìm thấy file code nào (.ino/.cpp/.c/.h/.py). Hãy kiểm tra lại workspace!</p>';
    } else {
      fileListEl.innerHTML = '<p style="font-size:0.82rem;color:var(--text-muted);"><i class="fa-solid fa-plug-circle-exclamation"></i> Không thể đọc danh sách file (server chưa kết nối).</p>';
    }
  } catch(e) {
    fileListEl.innerHTML = '<p style="font-size:0.82rem;color:var(--text-muted);"><i class="fa-solid fa-plug-circle-exclamation"></i> Không thể đọc danh sách file.</p>';
  }
}

function closeSubmitModal() {
  document.getElementById('submitModal').classList.remove('open');
}

async function confirmSubmit() {
  if (!submitMissionId) return;
  const btn = document.getElementById('confirmSubmitBtn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Đang nộp...';
  try {
    const res = await fetch(`/user/api/missions/${submitMissionId}/submit`, { method: 'POST' });
    const data = await res.json();
    closeSubmitModal();
    if (data.success) {
      toast('✅ Nộp bài thành công! AI đang chấm điểm, kết quả sẽ hiện trong vài giây...', 'success');
      clearInterval(timerInterval);
      document.getElementById('examBanner').classList.add('hidden');
      document.getElementById('pageWrap').classList.remove('has-banner');
      activeMission = null;
      await loadMyMissions();
      // Kiểm tra điểm định kỳ mỗi 8 giây, tối đa 10 lần (Polling)
      let pollCount = 0;
      const mId = submitMissionId;
      submitMissionId = null;
      const pollInterval = setInterval(async () => {
        pollCount++;
        const missions = await fetch('/user/api/my-missions').then(r=>r.json()).catch(()=>[]);
        const m = missions.find(x => x.id === mId);
        if ((m && m.submission && m.submission.score !== null) || pollCount >= 10) {
          clearInterval(pollInterval);
          await loadMyMissions();
          if (m && m.submission && m.submission.score !== null) {
            toast(`🎓 AI đã chấm xong! Điểm của bạn: ${m.submission.score.toFixed(1)}/10`, 'info');
          }
        }
      }, 8000);
    } else {
      toast(data.error || 'Lỗi nộp bài', 'error');
    }
  } catch(e) {
    toast('Lỗi kết nối. Vui lòng thử lại.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> Nộp bài ngay';
  }
}

// Đóng modal khi click ra ngoài (Click outside)
document.getElementById('submitModal').addEventListener('click', function(e) {
  if (e.target === this) closeSubmitModal();
});

// ── KHỞI TẠO (INIT) ── by Chương ───────────────────────────
document.addEventListener('DOMContentLoaded', loadMyMissions);