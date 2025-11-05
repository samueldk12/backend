// ============================================
// GLOBAL STATE
// ============================================

let currentQuiz = {
    questions: [],
    currentIndex: 0,
    score: 0,
    answers: []
};

// ============================================
// NAVIGATION
// ============================================

function toggleMenu() {
    const menu = document.querySelector('.nav-menu');
    menu.classList.toggle('active');
}

// ============================================
// LOCAL STORAGE - PROGRESS TRACKING
// ============================================

function getProgress() {
    const progress = localStorage.getItem('backendStudyProgress');
    if (!progress) {
        return {
            modules: {},
            exercises: {},
            interviews: {},
            quizStats: {
                totalQuizzes: 0,
                scores: [],
                bestScore: 0
            },
            startedAt: new Date().toISOString(),
            lastUpdated: new Date().toISOString()
        };
    }
    return JSON.parse(progress);
}

function saveProgress(progress) {
    progress.lastUpdated = new Date().toISOString();
    localStorage.setItem('backendStudyProgress', JSON.stringify(progress));
}

function markCompleted(type, id) {
    const progress = getProgress();
    if (!progress[type]) {
        progress[type] = {};
    }
    progress[type][id] = {
        completed: true,
        completedAt: new Date().toISOString()
    };
    saveProgress(progress);
}

function isCompleted(type, id) {
    const progress = getProgress();
    return progress[type] && progress[type][id] && progress[type][id].completed;
}

function toggleCompletion(type, id) {
    const progress = getProgress();
    if (!progress[type]) {
        progress[type] = {};
    }

    if (progress[type][id] && progress[type][id].completed) {
        delete progress[type][id];
    } else {
        progress[type][id] = {
            completed: true,
            completedAt: new Date().toISOString()
        };
    }

    saveProgress(progress);

    // Reload progress page if we're on it
    if (window.location.pathname.includes('progress.html')) {
        loadProgressPage();
    }
}

// ============================================
// MODULES PAGE
// ============================================

async function loadModules() {
    try {
        const response = await fetch('data/modules.json');
        const modules = await response.json();
        renderModules(modules);
    } catch (error) {
        console.error('Error loading modules:', error);
        document.getElementById('moduleGrid').innerHTML = `
            <p style="color: var(--danger); grid-column: 1/-1; text-align: center;">
                Erro ao carregar módulos. Por favor, tente novamente.
            </p>
        `;
    }
}

function renderModules(modules, filter = 'all') {
    const grid = document.getElementById('moduleGrid');
    grid.innerHTML = '';

    const filtered = filter === 'all' ? modules : modules.filter(m => m.category === filter);

    filtered.forEach(module => {
        const completed = isCompleted('modules', module.id);
        const card = document.createElement('div');
        card.className = 'feature-card';
        card.innerHTML = `
            <div class="feature-icon">
                <i class="${module.icon}"></i>
            </div>
            <h3>${module.name}</h3>
            <p>${module.description}</p>
            <div style="margin-top: 1rem;">
                ${module.topics.slice(0, 3).map(t =>
                    `<span class="badge badge-primary" style="margin-right: 0.5rem;">${t}</span>`
                ).join('')}
            </div>
            <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                <button class="btn btn-primary" style="flex: 1;" onclick="showModuleDetail('${module.id}')">
                    Ver Detalhes
                </button>
                <button class="btn ${completed ? 'btn-success' : 'btn-secondary'}"
                        onclick="toggleCompletion('modules', '${module.id}')"
                        title="${completed ? 'Marcar como não concluído' : 'Marcar como concluído'}">
                    <i class="fas fa-${completed ? 'check' : 'circle'}"></i>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterModules(category) {
    loadModules().then(() => {
        fetch('data/modules.json')
            .then(res => res.json())
            .then(modules => renderModules(modules, category));
    });
}

function showModuleDetail(moduleId) {
    fetch('data/modules.json')
        .then(res => res.json())
        .then(modules => {
            const module = modules.find(m => m.id === moduleId);
            if (!module) return;

            const completed = isCompleted('modules', module.id);
            const detail = document.getElementById('moduleDetail');
            detail.innerHTML = `
                <h2>${module.name}</h2>
                <p style="color: var(--gray); margin-bottom: 2rem;">${module.description}</p>

                <h3 style="margin-bottom: 1rem;">Tópicos Cobertos</h3>
                <div style="margin-bottom: 2rem;">
                    ${module.topics.map(t =>
                        `<span class="badge badge-primary" style="margin-right: 0.5rem; margin-bottom: 0.5rem;">${t}</span>`
                    ).join('')}
                </div>

                <h3 style="margin-bottom: 1rem;">Exemplos (${module.examples})</h3>
                <p style="color: var(--gray); margin-bottom: 2rem;">
                    Este módulo contém ${module.examples} exemplos práticos no repositório.
                </p>

                <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                    <a href="${module.githubPath}" class="btn btn-primary" target="_blank">
                        <i class="fab fa-github"></i> Ver no GitHub
                    </a>
                    <button class="btn ${completed ? 'btn-success' : 'btn-secondary'}"
                            onclick="toggleCompletion('modules', '${module.id}'); showModuleDetail('${module.id}')">
                        <i class="fas fa-${completed ? 'check-circle' : 'circle'}"></i>
                        ${completed ? 'Concluído' : 'Marcar como Concluído'}
                    </button>
                </div>
            `;

            document.getElementById('moduleModal').style.display = 'flex';
        });
}

function closeModal() {
    document.getElementById('moduleModal').style.display = 'none';
}

// ============================================
// PROJECTS PAGE
// ============================================

async function loadProjects() {
    try {
        const response = await fetch('data/projects.json');
        const data = await response.json();
        renderPracticeProjects(data.practice);
        renderInterviewProjects(data.interview);
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function renderPracticeProjects(projects) {
    const grid = document.getElementById('practiceGrid');
    grid.innerHTML = '';

    projects.forEach(project => {
        const completed = isCompleted('exercises', project.id);
        const card = document.createElement('div');
        card.className = 'feature-card';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <span class="badge badge-primary">${project.id}</span>
                ${completed ? '<span class="badge badge-success"><i class="fas fa-check"></i> Concluído</span>' : ''}
            </div>
            <h3>${project.name}</h3>
            <p>${project.description}</p>
            <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                <a href="${project.githubPath}" class="btn btn-primary" style="flex: 1;" target="_blank">
                    <i class="fab fa-github"></i> Ver Projeto
                </a>
                <button class="btn ${completed ? 'btn-success' : 'btn-secondary'}"
                        onclick="toggleCompletion('exercises', '${project.id}')">
                    <i class="fas fa-${completed ? 'check' : 'circle'}"></i>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderInterviewProjects(projects) {
    const lowLevel = projects.filter(p => p.type === 'low-level');
    const highLevel = projects.filter(p => p.type === 'high-level');

    renderProjectGroup(lowLevel, 'lowLevelGrid');
    renderProjectGroup(highLevel, 'highLevelGrid');
}

function renderProjectGroup(projects, gridId) {
    const grid = document.getElementById(gridId);
    grid.innerHTML = '';

    projects.forEach(project => {
        const completed = isCompleted('interviews', project.id);
        const card = document.createElement('div');
        card.className = 'feature-card';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <span class="badge badge-warning">${project.id}</span>
                <span style="font-size: 1.2rem;">${project.frequency}</span>
            </div>
            <h3>${project.name}</h3>
            <p>${project.description}</p>
            ${completed ? '<span class="badge badge-success" style="margin-top: 1rem;"><i class="fas fa-check"></i> Concluído</span>' : ''}
            <div style="margin-top: 1.5rem; display: flex; gap: 0.5rem;">
                <a href="${project.githubPath}" class="btn btn-primary" style="flex: 1;" target="_blank">
                    <i class="fab fa-github"></i> Ver Projeto
                </a>
                <button class="btn ${completed ? 'btn-success' : 'btn-secondary'}"
                        onclick="toggleCompletion('interviews', '${project.id}')">
                    <i class="fas fa-${completed ? 'check' : 'circle'}"></i>
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

function showTab(tab) {
    if (tab === 'practice') {
        document.getElementById('practiceProjects').style.display = 'block';
        document.getElementById('interviewProjects').style.display = 'none';
        document.getElementById('practiceTab').className = 'btn btn-primary';
        document.getElementById('interviewTab').className = 'btn btn-secondary';
    } else {
        document.getElementById('practiceProjects').style.display = 'none';
        document.getElementById('interviewProjects').style.display = 'block';
        document.getElementById('practiceTab').className = 'btn btn-secondary';
        document.getElementById('interviewTab').className = 'btn btn-primary';
    }
}

function closeProjectModal() {
    document.getElementById('projectModal').style.display = 'none';
}

// ============================================
// PROGRESS PAGE
// ============================================

async function loadProgressPage() {
    const progress = getProgress();

    // Calculate statistics
    const modulesCompleted = Object.keys(progress.modules || {}).length;
    const exercisesCompleted = Object.keys(progress.exercises || {}).length;
    const interviewsCompleted = Object.keys(progress.interviews || {}).length;

    const totalModules = 8;
    const totalExercises = 8;
    const totalInterviews = 12;
    const totalItems = totalModules + totalExercises + totalInterviews;
    const completedItems = modulesCompleted + exercisesCompleted + interviewsCompleted;

    const overallPercent = Math.round((completedItems / totalItems) * 100);
    const modulesPercent = Math.round((modulesCompleted / totalModules) * 100);
    const exercisesPercent = Math.round((exercisesCompleted / totalExercises) * 100);
    const interviewsPercent = Math.round((interviewsCompleted / totalInterviews) * 100);

    // Update summary cards
    document.getElementById('modulesCompleted').textContent = `${modulesCompleted}/${totalModules}`;
    document.getElementById('exercisesCompleted').textContent = `${exercisesCompleted}/${totalExercises}`;
    document.getElementById('interviewsCompleted').textContent = `${interviewsCompleted}/${totalInterviews}`;
    document.getElementById('overallProgress').textContent = `${overallPercent}%`;

    // Update progress bars
    document.getElementById('modulesPercent').textContent = `${modulesPercent}%`;
    document.getElementById('modulesBar').style.width = `${modulesPercent}%`;

    document.getElementById('exercisesPercent').textContent = `${exercisesPercent}%`;
    document.getElementById('exercisesBar').style.width = `${exercisesPercent}%`;

    document.getElementById('interviewsPercent').textContent = `${interviewsPercent}%`;
    document.getElementById('interviewsBar').style.width = `${interviewsPercent}%`;

    // Study stats
    const startDate = new Date(progress.startedAt);
    const daysStudying = Math.floor((new Date() - startDate) / (1000 * 60 * 60 * 24));

    document.getElementById('startDate').textContent = startDate.toLocaleDateString('pt-BR');
    document.getElementById('daysStudying').textContent = daysStudying;
    document.getElementById('lastUpdate').textContent = new Date(progress.lastUpdated).toLocaleString('pt-BR');

    // Load checklists
    await loadCheckLists();
}

async function loadCheckLists() {
    try {
        const [modulesRes, projectsRes] = await Promise.all([
            fetch('data/modules.json'),
            fetch('data/projects.json')
        ]);

        const modules = await modulesRes.json();
        const projects = await projectsRes.json();

        renderChecklist('moduleChecklist', modules, 'modules');
        renderChecklist('exerciseChecklist', projects.practice, 'exercises');
        renderChecklist('interviewChecklist', projects.interview, 'interviews');
    } catch (error) {
        console.error('Error loading checklists:', error);
    }
}

function renderChecklist(containerId, items, type) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    items.forEach(item => {
        const completed = isCompleted(type, item.id);
        const div = document.createElement('div');
        div.style.cssText = 'display: flex; align-items: center; padding: 0.75rem; border-bottom: 1px solid var(--gray-lighter);';
        div.innerHTML = `
            <input type="checkbox"
                   ${completed ? 'checked' : ''}
                   onchange="toggleCompletion('${type}', '${item.id}')"
                   style="margin-right: 1rem; width: 20px; height: 20px; cursor: pointer;">
            <span style="flex: 1; ${completed ? 'text-decoration: line-through; color: var(--gray);' : ''}">${item.name}</span>
            ${completed ? '<span class="badge badge-success"><i class="fas fa-check"></i></span>' : ''}
        `;
        container.appendChild(div);
    });
}

function exportProgress() {
    const progress = getProgress();
    const dataStr = JSON.stringify(progress, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'backend-study-progress.json';
    link.click();
}

function resetProgress() {
    if (confirm('Tem certeza que deseja resetar todo seu progresso? Esta ação não pode ser desfeita.')) {
        localStorage.removeItem('backendStudyProgress');
        location.reload();
    }
}

// ============================================
// QUIZ PAGE
// ============================================

const QUIZ_QUESTIONS = {
    fundamentos: [
        {
            question: "Qual a diferença entre Thread e Process?",
            options: [
                "A) Thread compartilha memória, Process não",
                "B) Process é mais rápido que Thread",
                "C) Thread não pode rodar em paralelo",
                "D) Não há diferença"
            ],
            correct: 0,
            explanation: "Threads compartilham o mesmo espaço de memória, enquanto Processes têm memória isolada."
        },
        {
            question: "O que é GIL (Global Interpreter Lock)?",
            options: [
                "A) Um tipo de threading",
                "B) Um lock que permite apenas 1 thread executar Python bytecode por vez",
                "C) Um tipo de processo",
                "D) Um framework de concorrência"
            ],
            correct: 1,
            explanation: "GIL é um mutex que protege acesso a objetos Python, permitindo apenas uma thread executar por vez."
        },
        {
            question: "Quando usar async/await ao invés de threads?",
            options: [
                "A) Sempre",
                "B) Para operações CPU-bound",
                "C) Para operações I/O-bound (network, disk)",
                "D) Nunca"
            ],
            correct: 2,
            explanation: "Async/await é ideal para I/O-bound. Para CPU-bound, use multiprocessing."
        }
    ],
    database: [
        {
            question: "O que é o problema N+1?",
            options: [
                "A) Fazer N queries em loop ao invés de 1 query com JOIN",
                "B) Ter N+1 tabelas no banco",
                "C) Usar N+1 índices",
                "D) Ter N+1 conexões"
            ],
            correct: 0,
            explanation: "N+1 é quando fazemos 1 query principal + N queries em loop (uma para cada item)."
        },
        {
            question: "Qual index usar para range queries (BETWEEN)?",
            options: [
                "A) Hash index",
                "B) B-Tree index",
                "C) Bitmap index",
                "D) Não precisa de index"
            ],
            correct: 1,
            explanation: "B-Tree é ideal para range queries. Hash index só funciona para equality (=)."
        }
    ],
    architecture: [
        {
            question: "Quando usar Cache-Aside vs Write-Through?",
            options: [
                "A) Cache-Aside para reads, Write-Through para writes",
                "B) Sempre usar Cache-Aside",
                "C) Cache-Aside = lazy loading, Write-Through = consistência forte",
                "D) São a mesma coisa"
            ],
            correct: 2,
            explanation: "Cache-Aside é mais comum (lazy). Write-Through garante cache sempre atualizado."
        }
    ],
    system_design: [
        {
            question: "Twitter: Push (write fanout) vs Pull (read fanout)?",
            options: [
                "A) Push para todos usuários",
                "B) Pull para todos usuários",
                "C) Hybrid: Push para users normais, Pull para celebridades",
                "D) Não importa"
            ],
            correct: 2,
            explanation: "Twitter usa hybrid: Push (<5k followers) e Pull (>5k) para evitar write amplification."
        },
        {
            question: "Como escalar para 100M conexões WebSocket?",
            options: [
                "A) 1 servidor gigante",
                "B) Múltiplos servidores + Redis Pub/Sub",
                "C) Não é possível",
                "D) Usar HTTP ao invés de WebSocket"
            ],
            correct: 1,
            explanation: "1 servidor suporta ~65k conexões. Usar múltiplos + Redis para routing."
        }
    ]
};

function startQuiz() {
    const topic = document.getElementById('topicSelect').value;
    const numQuestions = parseInt(document.getElementById('numQuestions').value);

    // Collect questions
    let allQuestions = [];
    if (topic === 'random') {
        for (let questions of Object.values(QUIZ_QUESTIONS)) {
            allQuestions = allQuestions.concat(questions);
        }
    } else {
        allQuestions = QUIZ_QUESTIONS[topic] || [];
    }

    // Shuffle and select
    allQuestions = allQuestions.sort(() => Math.random() - 0.5);
    currentQuiz.questions = allQuestions.slice(0, Math.min(numQuestions, allQuestions.length));
    currentQuiz.currentIndex = 0;
    currentQuiz.score = 0;
    currentQuiz.answers = [];

    // Show quiz
    document.getElementById('quizSetup').style.display = 'none';
    document.getElementById('quizQuestion').style.display = 'block';
    document.getElementById('totalQuestions').textContent = currentQuiz.questions.length;

    showQuestion();
}

function showQuestion() {
    const question = currentQuiz.questions[currentQuiz.currentIndex];

    document.getElementById('currentQuestion').textContent = currentQuiz.currentIndex + 1;
    document.getElementById('currentScore').textContent = currentQuiz.score;
    document.getElementById('questionText').textContent = question.question;

    const progress = ((currentQuiz.currentIndex + 1) / currentQuiz.questions.length) * 100;
    document.getElementById('quizProgress').style.width = progress + '%';

    const container = document.getElementById('optionsContainer');
    container.innerHTML = '';

    question.options.forEach((option, index) => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary';
        btn.style.cssText = 'text-align: left; justify-content: flex-start;';
        btn.textContent = option;
        btn.onclick = () => answerQuestion(index);
        container.appendChild(btn);
    });

    document.getElementById('explanation').style.display = 'none';
    document.getElementById('nextButton').style.display = 'none';
}

function answerQuestion(selectedIndex) {
    const question = currentQuiz.questions[currentQuiz.currentIndex];
    const correct = selectedIndex === question.correct;

    if (correct) {
        currentQuiz.score++;
        document.getElementById('currentScore').textContent = currentQuiz.score;
    }

    currentQuiz.answers.push({
        question: question.question,
        selected: selectedIndex,
        correct: question.correct,
        isCorrect: correct
    });

    // Show feedback
    const buttons = document.getElementById('optionsContainer').children;
    for (let i = 0; i < buttons.length; i++) {
        buttons[i].disabled = true;
        if (i === question.correct) {
            buttons[i].classList.remove('btn-secondary');
            buttons[i].classList.add('btn-success');
            buttons[i].innerHTML = '<i class="fas fa-check"></i> ' + buttons[i].textContent;
        } else if (i === selectedIndex) {
            buttons[i].classList.remove('btn-secondary');
            buttons[i].classList.add('btn-danger');
            buttons[i].innerHTML = '<i class="fas fa-times"></i> ' + buttons[i].textContent;
        }
    }

    document.getElementById('explanationText').textContent = question.explanation;
    document.getElementById('explanation').style.display = 'block';
    document.getElementById('nextButton').style.display = 'block';
}

function nextQuestion() {
    currentQuiz.currentIndex++;

    if (currentQuiz.currentIndex < currentQuiz.questions.length) {
        showQuestion();
    } else {
        showResults();
    }
}

function showResults() {
    const total = currentQuiz.questions.length;
    const score = currentQuiz.score;
    const percentage = Math.round((score / total) * 100);

    // Save quiz stats
    const progress = getProgress();
    if (!progress.quizStats) {
        progress.quizStats = { totalQuizzes: 0, scores: [], bestScore: 0 };
    }
    progress.quizStats.totalQuizzes++;
    progress.quizStats.scores.push(percentage);
    progress.quizStats.bestScore = Math.max(progress.quizStats.bestScore, percentage);
    saveProgress(progress);

    // Show results
    document.getElementById('quizQuestion').style.display = 'none';
    document.getElementById('quizResults').style.display = 'block';

    document.getElementById('finalScore').textContent = score;
    document.getElementById('finalTotal').textContent = total;
    document.getElementById('finalPercentage').textContent = percentage + '%';

    let icon = '🎉';
    let message = '';
    let color = 'var(--success)';

    if (percentage >= 80) {
        icon = '🎉';
        message = 'Excelente! Você domina o conteúdo!';
        color = 'var(--success)';
    } else if (percentage >= 60) {
        icon = '📚';
        message = 'Bom! Continue estudando para melhorar!';
        color = 'var(--warning)';
    } else {
        icon = '💪';
        message = 'Pratique mais e revise os conceitos!';
        color = 'var(--danger)';
    }

    document.getElementById('resultIcon').textContent = icon;
    document.getElementById('resultMessage').innerHTML = `
        <div style="padding: 1rem; background: ${color}20; color: ${color}; border-radius: var(--radius);">
            <strong>${message}</strong>
        </div>
    `;

    // Update stats
    const avgScore = Math.round(
        progress.quizStats.scores.reduce((a, b) => a + b, 0) / progress.quizStats.scores.length
    );

    document.getElementById('totalQuizzes').textContent = progress.quizStats.totalQuizzes;
    document.getElementById('bestScore').textContent = progress.quizStats.bestScore + '%';
    document.getElementById('avgScore').textContent = avgScore + '%';
}

function resetQuiz() {
    currentQuiz = {
        questions: [],
        currentIndex: 0,
        score: 0,
        answers: []
    };

    document.getElementById('quizResults').style.display = 'none';
    document.getElementById('quizSetup').style.display = 'block';
}

// ============================================
// MODAL STYLES (Add to CSS if needed)
// ============================================

// Add modal styles dynamically
const style = document.createElement('style');
style.textContent = `
    .modal {
        display: none;
        position: fixed;
        z-index: 9999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        align-items: center;
        justify-content: center;
        padding: 1rem;
    }

    .modal-content {
        background-color: var(--white);
        padding: 2rem;
        border-radius: var(--radius-lg);
        max-width: 800px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        position: relative;
        box-shadow: var(--shadow-xl);
    }

    .modal-close {
        position: absolute;
        top: 1rem;
        right: 1rem;
        font-size: 2rem;
        font-weight: bold;
        color: var(--gray);
        cursor: pointer;
        line-height: 1;
        transition: var(--transition);
    }

    .modal-close:hover {
        color: var(--dark);
    }

    .btn-success {
        background: var(--success) !important;
        color: var(--white) !important;
        border-color: var(--success) !important;
    }

    .btn-danger {
        background: var(--danger) !important;
        color: var(--white) !important;
        border-color: var(--danger) !important;
    }
`;
document.head.appendChild(style);
