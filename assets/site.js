(() => {
  const leagues = window.SPORTS_ELO || {};
  const showTab = () => {
    const id = (location.hash || '#mlb').slice(1);
    const active = leagues[id] ? id : Object.keys(leagues)[0];
    document.querySelectorAll('[data-tab]').forEach(el => el.classList.toggle('active', el.dataset.tab === active));
    document.querySelectorAll('[data-panel]').forEach(el => el.classList.toggle('active', el.dataset.panel === active));
    renderChart(active);
  };
  const renderChart = key => {
    const data = leagues[key]?.ratings; if (!data?.history?.length || !window.Plotly) return;
    const picker = document.querySelector(`[data-picker="${key}"]`); const chart = document.querySelector(`[data-chart="${key}"]`);
    const byTeam = {}; data.history.forEach(row => (byTeam[row.team] ??= []).push(row));
    if (!picker.options.length) Object.entries(byTeam).sort((a,b) => b[1].at(-1).rating-a[1].at(-1).rating).forEach(([team, rows], i) => picker.add(new Option(rows.at(-1).name, team, false, i < 4)));
    const plot = () => { const selected = [...picker.selectedOptions].map(o=>o.value); Plotly.react(chart, selected.map(team => {const rows=byTeam[team];return {x:rows.map(r=>r.checkpoint),y:rows.map(r=>r.rating),name:rows.at(-1).name,type:'scatter',mode:'lines+markers',line:{width:2},marker:{size:4},hovertemplate:'%{fullData.name}<br>%{x}: %{y:.1f} Elo<extra></extra>'};}),{paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{color:'#dbe8f5'},margin:{l:48,r:12,t:10,b:48},xaxis:{gridcolor:'#263d59'},yaxis:{gridcolor:'#263d59',zeroline:false},legend:{orientation:'h',y:1.14}},{responsive:true,displaylogo:false});}; picker.onchange=plot; plot();
  };
  document.querySelectorAll('.table-search').forEach(input => input.addEventListener('input', () => document.querySelectorAll(`[data-table="${input.dataset.search}"] tbody tr`).forEach(row => row.hidden = !row.textContent.toLowerCase().includes(input.value.toLowerCase()))));
  document.querySelectorAll('th[data-sort]').forEach(header => header.addEventListener('click', () => { const table=header.closest('table'), col=[...header.parentNode.children].indexOf(header), numeric=header.dataset.sort!=='wins'; const rows=[...table.tBodies[0].rows]; rows.sort((a,b)=>{const av=a.cells[col].textContent.trim(),bv=b.cells[col].textContent.trim();return numeric ? parseFloat(bv)-parseFloat(av) : av.localeCompare(bv)}); rows.forEach(row=>table.tBodies[0].append(row)); }));
  window.addEventListener('hashchange', showTab); showTab();
})();
