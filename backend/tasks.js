const store = {};

export function addTask(caseId, { text, dueAt, assignedTo = 'lawyer' }) {
  const task = {
    id: (typeof crypto !== 'undefined' && crypto.randomUUID)
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2),
    text,
    dueAt,
    assignedTo,
    completed: false,
  };
  store[caseId] = store[caseId] || [];
  store[caseId].push(task);
  scheduleReminder(task);
  return task.id;
}

export function getTasks(caseId) {
  return store[caseId] || [];
}

function scheduleReminder(task) {
  const delay = new Date(task.dueAt).getTime() - Date.now();
  if (delay > 0) {
    setTimeout(() => sendReminder(task), delay);
  }
}

function sendReminder(task) {
  // placeholder for email/calendar API integration
  console.log(`Reminder: ${task.text} is due ${task.dueAt} for ${task.assignedTo}`);
}
