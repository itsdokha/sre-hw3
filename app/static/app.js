const form = document.querySelector('#task-form');
const titleInput = document.querySelector('#title');
const submitButton = document.querySelector('#submit-button');
const cancelButton = document.querySelector('#cancel-button');
const message = document.querySelector('#message');
const list = document.querySelector('#tasks');
let editingTask = null;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `Ошибка HTTP ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

function showError(error) {
  message.textContent = error.message || 'Не удалось выполнить запрос';
}

function resetForm() {
  editingTask = null;
  form.reset();
  submitButton.textContent = 'Добавить';
  cancelButton.hidden = true;
}

async function refresh() {
  const tasks = await api('/api/tasks');
  list.replaceChildren();
  for (const task of tasks) {
    const item = document.createElement('li');
    item.className = `task${task.completed ? ' completed' : ''}`;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = task.completed;
    checkbox.setAttribute('aria-label', `Выполнена: ${task.title}`);
    checkbox.addEventListener('change', async () => {
      try {
        message.textContent = '';
        await api(`/api/tasks/${task.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: task.title, completed: checkbox.checked })
        });
        await refresh();
      } catch (error) { checkbox.checked = task.completed; showError(error); }
    });

    const title = document.createElement('span');
    title.className = 'task-title';
    title.textContent = task.title;

    const edit = document.createElement('button');
    edit.type = 'button';
    edit.className = 'secondary';
    edit.textContent = 'Изменить';
    edit.setAttribute('aria-label', `Изменить: ${task.title}`);
    edit.addEventListener('click', () => {
      editingTask = task;
      titleInput.value = task.title;
      submitButton.textContent = 'Сохранить';
      cancelButton.hidden = false;
      titleInput.focus();
    });

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'danger';
    remove.textContent = 'Удалить';
    remove.setAttribute('aria-label', `Удалить: ${task.title}`);
    remove.addEventListener('click', async () => {
      if (!confirm(`Удалить задачу «${task.title}»?`)) return;
      try {
        message.textContent = '';
        await api(`/api/tasks/${task.id}`, { method: 'DELETE' });
        if (editingTask?.id === task.id) resetForm();
        await refresh();
      } catch (error) { showError(error); }
    });

    item.append(checkbox, title, edit, remove);
    list.append(item);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const title = titleInput.value.trim();
  if (!title) return;
  try {
    message.textContent = '';
    await api(editingTask ? `/api/tasks/${editingTask.id}` : '/api/tasks', {
      method: editingTask ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, completed: editingTask?.completed ?? false })
    });
    resetForm();
    await refresh();
  } catch (error) { showError(error); }
});

cancelButton.addEventListener('click', resetForm);
refresh().catch(showError);
