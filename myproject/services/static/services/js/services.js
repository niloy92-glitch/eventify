document.addEventListener('DOMContentLoaded', function () {
  const iconMap = {
    catering: "🍽",
    photography: "📷",
    decoration: "🎀",
    music: "🎵",
    other: "★",
  };
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const modal = document.getElementById('service-detail-modal');
  const icon = document.getElementById('service-detail-icon');
  const titleEl = document.getElementById('service-detail-title');
  const companyEl = document.getElementById('service-detail-company');
  const typeEl = document.getElementById('service-detail-type');
  const descEl = document.getElementById('service-detail-desc');
  const calendarLabel = document.getElementById('service-calendar-label');
  const monthSelect = document.getElementById('service-calendar-month');
  const yearSelect = document.getElementById('service-calendar-year');
  const grid = document.getElementById('service-calendar-grid');

  const today = new Date();
  const calendarState = {
    year: today.getFullYear(),
    month: today.getMonth(),
  };

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function buildMonthOptions() {
    if (!monthSelect) return;
    monthSelect.innerHTML = monthNames.map(function (name, index) {
      return '<option value="' + index + '">' + name + '</option>';
    }).join('');
  }

  function buildYearOptions() {
    if (!yearSelect) return;
    const startYear = today.getFullYear() - 5;
    const endYear = today.getFullYear() + 8;
    let options = '';

    for (let year = startYear; year <= endYear; year += 1) {
      options += '<option value="' + year + '">' + year + '</option>';
    }

    yearSelect.innerHTML = options;
  }

  function renderCalendar() {
    if (!grid) return;

    const firstDay = new Date(calendarState.year, calendarState.month, 1).getDay();
    const daysInMonth = new Date(calendarState.year, calendarState.month + 1, 0).getDate();
    const previousMonthDays = new Date(calendarState.year, calendarState.month, 0).getDate();
    const currentMonthLabel = monthNames[calendarState.month] + ' ' + calendarState.year;

    if (calendarLabel) {
      calendarLabel.textContent = currentMonthLabel;
    }
    if (monthSelect && String(monthSelect.value) !== String(calendarState.month)) {
      monthSelect.value = String(calendarState.month);
    }
    if (yearSelect && String(yearSelect.value) !== String(calendarState.year)) {
      yearSelect.value = String(calendarState.year);
    }

    let cells = '';

    for (let index = 0; index < firstDay; index += 1) {
      const dayNumber = previousMonthDays - firstDay + index + 1;
      cells += '<button type="button" class="calendar-day calendar-day-outside" aria-disabled="true" tabindex="-1"><span>' + dayNumber + '</span></button>';
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const isToday = day === today.getDate() && calendarState.month === today.getMonth() && calendarState.year === today.getFullYear();
      const isWeekend = new Date(calendarState.year, calendarState.month, day).getDay() === 0 || new Date(calendarState.year, calendarState.month, day).getDay() === 6;
      const classes = ['calendar-day'];

      if (isToday) classes.push('is-today');
      if (isWeekend) classes.push('is-weekend');

      cells += '<button type="button" class="' + classes.join(' ') + '" aria-label="' + currentMonthLabel + ' ' + day + '"><span class="calendar-day-number">' + day + '</span><span class="calendar-day-state">Available</span></button>';
    }

    const remainingCells = 42 - (firstDay + daysInMonth);
    for (let nextDay = 1; nextDay <= remainingCells; nextDay += 1) {
      cells += '<button type="button" class="calendar-day calendar-day-outside" aria-disabled="true" tabindex="-1"><span>' + nextDay + '</span></button>';
    }

    grid.innerHTML = cells;
  }

  function setMonth(month) {
    calendarState.month = month;
    renderCalendar();
  }

  function setYear(year) {
    calendarState.year = year;
    renderCalendar();
  }

  function resetCalendarToToday() {
    calendarState.year = today.getFullYear();
    calendarState.month = today.getMonth();
    renderCalendar();
  }

  function updateServiceModal(data) {
    if (!modal) return;

    const titleText = (data.approved === 'true' ? '✓ ' : '') + (data.title || '');
    if (titleEl) titleEl.textContent = titleText;
    if (companyEl) companyEl.textContent = data.company || '';
    if (typeEl) typeEl.textContent = (data.type || 'other').replace(/_/g, ' ');
    if (descEl) descEl.textContent = data.desc || '';
    if (icon) icon.textContent = iconMap[data.type] || iconMap.other;

    resetCalendarToToday();
    window.openModal(modal);
  }

  buildMonthOptions();
  buildYearOptions();
  renderCalendar();

  if (monthSelect) {
    monthSelect.value = String(calendarState.month);
    monthSelect.addEventListener('change', function () {
      setMonth(parseInt(monthSelect.value, 10));
    });
  }

  if (yearSelect) {
    yearSelect.value = String(calendarState.year);
    yearSelect.addEventListener('change', function () {
      setYear(parseInt(yearSelect.value, 10));
    });
  }

  document.querySelectorAll('[data-calendar-nav]').forEach(function (button) {
    button.addEventListener('click', function () {
      const action = button.getAttribute('data-calendar-nav');

      if (action === 'prev') {
        const previous = new Date(calendarState.year, calendarState.month - 1, 1);
        calendarState.year = previous.getFullYear();
        calendarState.month = previous.getMonth();
      } else if (action === 'next') {
        const next = new Date(calendarState.year, calendarState.month + 1, 1);
        calendarState.year = next.getFullYear();
        calendarState.month = next.getMonth();
      } else {
        resetCalendarToToday();
        return;
      }

      renderCalendar();
    });
  });

  document.querySelectorAll('.service-card[data-service-id]').forEach(function (card) {
    function openFromCard() {
      updateServiceModal({
        title: card.dataset.serviceName || '',
        desc: card.dataset.serviceDesc || '',
        company: card.dataset.serviceCompany || '',
        type: card.dataset.serviceType || 'other',
        approved: card.dataset.serviceApproved || 'false',
      });
    }

    card.addEventListener('click', openFromCard);
    card.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openFromCard();
      }
    });
  });
});


