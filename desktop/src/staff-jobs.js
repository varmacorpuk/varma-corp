/* Desk-set current jobs for floor bubbles. Not kernel presence.
   Empty job → Resting. Click never grants authority. LIVE stays blocked. */
(function (global) {
  const RESTING = "Resting";

  /* Kernel workflow / presence tokens are not a current job. */
  const NOT_A_JOB = {
    "": true,
    OFFLINE: true,
    AVAILABLE: true,
    ONLINE: true,
    AWAY: true,
    PREPARING: true,
    "BRIEF READY": true,
    "BRIEF FAILED": true,
    "PACK READY": true,
    DENIED: true,
    CHALLENGED: true,
    "THESIS IN": true,
    "REVIEW READY": true,
  };

  /* 3 Sep 2026 paper-day seed when a desk status is empty. */
  const PAPER_DAY_JOBS = {
    ceo: "Running desk",
    "market-intelligence-research": "US pack",
    challenge: "Challenge",
    risk: "US ticket ready",
    trader: "Watching SHEL",
    "quant-strategy": "US-open rule",
    technology: "Backups",
  };

  const STAFF_ROSTER = [
    {
      slug: "ceo",
      display_name: "Jordan Hale · CEO",
      office_x: 320,
      office_y: 320,
    },
    {
      slug: "market-intelligence-research",
      display_name: "Asha Patel · Research",
      office_x: 480,
      office_y: 320,
    },
    {
      slug: "challenge",
      display_name: "Sam Okeke · Challenge",
      office_x: 384,
      office_y: 384,
    },
    {
      slug: "risk",
      display_name: "Elena Voss · Risk",
      office_x: 192,
      office_y: 192,
    },
    {
      slug: "trader",
      display_name: "Chris Adeyemi · Trader",
      office_x: 256,
      office_y: 192,
    },
    {
      slug: "quant-strategy",
      display_name: "Nina Kapoor · Quant",
      office_x: 480,
      office_y: 480,
    },
    {
      slug: "technology",
      display_name: "Owen Blake · Technology",
      office_x: 640,
      office_y: 480,
    },
  ];

  function isJobText(value) {
    const text = String(value || "").trim();
    if (!text) return false;
    return !NOT_A_JOB[text];
  }

  function resolveJob(emp, deskJobs) {
    const slug = emp && emp.slug;
    if (deskJobs && slug && Object.prototype.hasOwnProperty.call(deskJobs, slug)) {
      const fromDesk = String(deskJobs[slug] || "").trim();
      return fromDesk || RESTING;
    }
    if (emp && isJobText(emp.current_job)) return String(emp.current_job).trim();
    if (emp && isJobText(emp.status_bubble)) return String(emp.status_bubble).trim();
    if (slug && PAPER_DAY_JOBS[slug]) return PAPER_DAY_JOBS[slug];
    return RESTING;
  }

  function applyJobs(employees, deskJobs) {
    return (employees || []).map(function (emp) {
      const next = {};
      Object.keys(emp || {}).forEach(function (key) {
        next[key] = emp[key];
      });
      next.status_bubble = resolveJob(emp, deskJobs);
      return next;
    });
  }

  global.VarmaStaffJobs = {
    RESTING: RESTING,
    PAPER_DAY_JOBS: PAPER_DAY_JOBS,
    STAFF_ROSTER: STAFF_ROSTER,
    DISPLAY_OFF_BANNER: "Display off — staff still at work",
    isJobText: isJobText,
    resolveJob: resolveJob,
    applyJobs: applyJobs,
  };
})(window);
